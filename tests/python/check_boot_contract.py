"""Confere o contrato do `boot_core.S` comum em cada plataforma.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    uv run python tests/python/check_boot_contract.py

Cada `boot_memory.S` de plataforma é montada pelo mesmo caminho do
`riscv-tools` (`build_boot_memory`), em cópias com o `boot_config.h`
trocado, e o resultado é conferido contra o contrato da BOOT:

1. Como está: o `fence.i` só existe quando o núcleo tem Zifencei, e o
   símbolo `rv32_wait_restart` só existe, fixo em 0x100, com
   `RV32_TEST_WAIT`.
2. Núcleo mínimo (nenhuma extensão): nenhum `fence.i` e nenhuma
   instrução de CSR, e a BOOT monta.
3. Núcleo completo (todas as extensões): o `fence.i` e as instruções de
   CSR dos fragmentos aparecem.
4. RV32E: a BOOT monta com `-march=rv32e`, ou seja, só usa `x0` a `x15`.
5. BOOT de aplicação (sem `RV32_TEST_WAIT`): o símbolo
   `rv32_wait_restart` não é exportado.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from riscv_tools import boot_memory

ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN = {
    "gcc": "riscv32-unknown-elf-gcc",
    "objcopy": "riscv32-unknown-elf-objcopy",
}
NM = "riscv32-unknown-elf-nm"
# A palavra do `fence.i` e o opcode SYSTEM, que o CSR usa.
FENCE_I = 0x0000100F
SYSTEM_OPCODE = 0x73
OPCODE_MASK = 0x7F
FUNCT3_SHIFT = 12
FUNCT3_MASK = 0x7
# O endereço fixo do ponto de espera da BOOT de teste.
WAIT_RESTART = 0x100
WAIT_SYMBOL = "rv32_wait_restart"
# As pastas do Core que o `boot_core.S` inclui.
FRAGMENTS = ("Zicsr", "Zicntr", "Zihpm", "Sscofpmf", "Zifencei")
# O linker script de uma BOOT de aplicação, que não fixa nenhum símbolo.
APP_LD = """\
MEMORY
{{
  boot_memory (rx) : ORIGIN = {origin}, LENGTH = {length}
}}
OUTPUT_ARCH("riscv")
ENTRY(_reset)
SECTIONS
{{
  .text.reset {origin} : {{ *(.text.reset) }} > boot_memory
  .text : {{ *(.text .text.*) }} > boot_memory
}}
"""
FLAG_OFF = re.compile(r"(RV32_HAS_\w+) 0")
FLAG_ON = re.compile(r"(RV32_HAS_\w+) 1")
DEFINE = re.compile(r"^#define (RV32_\w+) (\d+)$", re.MULTILINE)
LD_MEMORY = re.compile(r"ORIGIN = (\w+), LENGTH = (\w+)")
NM_LINE = re.compile(r"^([0-9a-f]+) \w (\w+)$", re.MULTILINE)


@dataclass(frozen=True)
class Built:
    """A BOOT montada.

    Attributes
    ----------
    words : list of int
        As palavras da imagem.
    symbols : dict of {str: int}
        O endereço de cada símbolo da tabela do ELF.
    """

    words: list[int]
    symbols: dict[str, int]


def platforms() -> list[Path]:
    """List the platforms that have a boot memory.

    Returns
    -------
    list of Path
        The platform folders, in order.
    """
    found = ROOT.glob("src/*/*/runtime/boot_memory.S")
    return sorted(path.parents[1] for path in found)


def build(platform: Path, header: str, ld_text: str, base: str) -> Built:
    """Assemble the boot memory of a platform with another header.

    Parameters
    ----------
    platform : Path
        The platform folder of the repository.
    header : str
        The content of `boot_config.h` to build with.
    ld_text : str
        The content of the linker script.
    base : str
        `i` or `e`, the base ISA of the boot memory build.

    Returns
    -------
    Built
        The words and the symbols of the image.
    """
    relative = platform.relative_to(ROOT)
    with tempfile.TemporaryDirectory() as directory:
        tree = Path(directory)
        runtime = tree / relative / "runtime"
        shutil.copytree(platform / "runtime", runtime)
        shutil.copytree(ROOT / "src/boot", tree / "src/boot")
        for name in FRAGMENTS:
            shutil.copytree(ROOT / "Core/src" / name, tree / "Core/src" / name)
        (runtime / "boot_config.h").write_text(header)
        (runtime / "boot_memory.ld").write_text(ld_text)
        paths = {
            "boot_memory": f"{relative}/runtime/boot_memory.S",
            "boot_memory_linker_script": f"{relative}/runtime/boot_memory.ld",
        }
        options = boot_memory.BootMemoryOptions(base=base)
        hex_path = boot_memory.build_boot_memory(
            TOOLCHAIN, paths, tree, tree / "out", options
        )
        words = [int(line, 16) for line in hex_path.read_text().split()]
        table = subprocess.run(  # noqa: S603
            [NM, str(tree / "out/boot_memory.elf")],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    symbols = {name: int(addr, 16) for addr, name in NM_LINE.findall(table)}
    return Built(words, symbols)


def csr_words(words: list[int]) -> list[int]:
    """Pick the CSR instructions of an image.

    Parameters
    ----------
    words : list of int
        The words of the image.

    Returns
    -------
    list of int
        The words with the SYSTEM opcode and a `funct3` other than zero
        (`ecall` and `ebreak` have `funct3` zero).
    """
    return [
        word
        for word in words
        if word & OPCODE_MASK == SYSTEM_OPCODE
        and (word >> FUNCT3_SHIFT) & FUNCT3_MASK
    ]


def app_ld(ld_text: str) -> str:
    """Write the linker script of the application boot memory.

    Parameters
    ----------
    ld_text : str
        The linker script of the platform, for the memory it declares.

    Returns
    -------
    str
        The same memory with no pinned symbol.
    """
    match = LD_MEMORY.search(ld_text)
    if match is None:
        raise ValueError("boot_memory.ld sem a memória boot_memory")
    return APP_LD.format(origin=match.group(1), length=match.group(2))


def check_as_is(platform: Path, header: str, ld_text: str) -> list[str]:
    """Check the boot memory as the platform generates it.

    Parameters
    ----------
    platform : Path
        The platform folder.
    header : str
        Its `boot_config.h`.
    ld_text : str
        Its linker script.

    Returns
    -------
    list of str
        The violations, empty when the contract holds.
    """
    flags = {name: int(value) for name, value in DEFINE.findall(header)}
    base = "e" if flags["RV32_IS_E"] else "i"
    built = build(platform, header, ld_text, base)
    found: list[str] = []
    if (FENCE_I in built.words) != bool(flags["RV32_HAS_ZIFENCEI"]):
        found.append("fence.i diverge de RV32_HAS_ZIFENCEI")
    address = built.symbols.get(WAIT_SYMBOL)
    if flags["RV32_TEST_WAIT"] and address != WAIT_RESTART:
        found.append(f"{WAIT_SYMBOL} deveria estar em {WAIT_RESTART:#x}")
    if not flags["RV32_TEST_WAIT"] and address is not None:
        found.append(f"{WAIT_SYMBOL} exportado sem RV32_TEST_WAIT")
    return found


def check_cores(platform: Path, header: str, ld_text: str) -> list[str]:
    """Check the minimal and the complete core and the RV32E build.

    Parameters
    ----------
    platform : Path
        The platform folder.
    header : str
        Its `boot_config.h`.
    ld_text : str
        Its linker script.

    Returns
    -------
    list of str
        The violations, empty when the contract holds.
    """
    minimal = FLAG_ON.sub(r"\1 0", header)
    full = FLAG_OFF.sub(r"\1 1", header)
    found: list[str] = []
    bare = build(platform, minimal, ld_text, "i")
    if FENCE_I in bare.words or csr_words(bare.words):
        found.append("o núcleo mínimo tem fence.i ou instrução de CSR")
    complete = build(platform, full, ld_text, "i")
    if FENCE_I not in complete.words or not csr_words(complete.words):
        found.append("o núcleo completo não tem fence.i ou CSR")
    embedded = minimal.replace("RV32_IS_E 0", "RV32_IS_E 1")
    build(platform, embedded, ld_text, "e")
    return found


def check_application(platform: Path, header: str, ld_text: str) -> list[str]:
    """Check the boot memory of an application.

    Parameters
    ----------
    platform : Path
        The platform folder.
    header : str
        Its `boot_config.h`.
    ld_text : str
        Its linker script.

    Returns
    -------
    list of str
        The violations, empty when the contract holds.
    """
    application = header.replace("RV32_TEST_WAIT 1", "RV32_TEST_WAIT 0")
    built = build(platform, application, app_ld(ld_text), "i")
    if WAIT_SYMBOL in built.symbols:
        return [f"{WAIT_SYMBOL} exportado na BOOT de aplicação"]
    return []


def main() -> None:
    """Check every platform, and exit with 1 on a broken contract."""
    failed = False
    for platform in platforms():
        runtime = platform / "runtime"
        header = (runtime / "boot_config.h").read_text()
        ld_text = (runtime / "boot_memory.ld").read_text()
        problems = [
            *check_as_is(platform, header, ld_text),
            *check_cores(platform, header, ld_text),
            *check_application(platform, header, ld_text),
        ]
        for problem in problems:
            print(f"{platform.relative_to(ROOT)}: {problem}")
        failed = failed or bool(problems)
    if failed:
        sys.exit(1)
    count = len(platforms())
    print(f"the boot memory of {count} platforms keeps the contract")


if __name__ == "__main__":
    main()
