"""Gera as imagens do teste do carregador da SDRAM da plataforma doom.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    python tests/python/gen_doom_images.py
    python tests/python/gen_doom_images.py --check

A BOOT_MEMORY é a `boot_memory.S` de verdade, montada pelo mesmo caminho
do `riscv-tools`. A banca A da FLASH recebe o `doom_loader.S` de
verdade, ligado em `base + 0x100` e empacotado por `flash_image.pack`.
A única diferença para a placa é o endereço da campainha (`launch`):
na placa ele fica na última página da RAM, que a cache de dados ignora,
e aqui fica em `RAM_BASE + LAUNCH_OFFSET`, porque a imagem da SDRAM
do simulador é linear a partir da base e a última página fica a
64 MiB dela.

A imagem da SDRAM é um programa de teste na base da RAM que guarda uma
marca e escreve `tohost`. Em `sdram_go.hex` a campainha já traz a magia
(o hospedeiro terminou de carregar); em `sdram_wait.hex` não traz, e o
carregador tem de esperar.

Os arquivos ficam em tests/python/unittests/rtl/data/doom/. Com
`--check` o script só confere se estão em dia.
"""

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from riscv_tools import boot_memory, flash_image
from riscv_tools.memory_map import load_platform, symbols

from tests.python.gen_de0_cv_images import load_address
from tests.python.utils.rv32_asm import T0, T1, X0, addi, hex_lines, jal, sw

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "unittests/rtl/data/doom"
PLATFORM = ROOT / "src/cyclone-v/doom/platform.yaml"
RUNTIME = ROOT / "src/cyclone-v/doom/runtime"
MAP = symbols(load_platform(PLATFORM))
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
# A banca A é a primeira da FLASH, e a FLASH começa na base dela.
BANK_A_BASE = MAP["FLASH.base"]
BANK_A_SIZE = MAP["FLASH.size"] // 2
BANK_A_ENTRY = BANK_A_BASE + flash_image.HEADER_SIZE
WORD = 4
# A campainha do teste: na primeira página da RAM, depois do código.
LAUNCH_OFFSET = 0x800
# A magia que o hospedeiro escreve (a mesma do doom_loader.S: "DOOM").
LAUNCH_MAGIC = 0x4D4F4F44
# A marca que o programa da SDRAM guarda e onde.
MARK = 0xD00D
MARK_OFFSET = 0x100
TOOLCHAIN = {
    "gcc": "riscv32-unknown-elf-gcc",
    "objcopy": "riscv32-unknown-elf-objcopy",
}
PATHS = {
    "boot_memory": "src/cyclone-v/doom/runtime/boot_memory.S",
    "boot_memory_linker_script": "src/cyclone-v/doom/runtime/boot_memory.ld",
}
FILES = (
    "boot_memory.hex",
    "flash.hex",
    "sdram_go.hex",
    "sdram_wait.hex",
)


def loader_payload(directory: Path) -> bytes:
    """Assemble and link the loader for the entry of bank A.

    Parameters
    ----------
    directory : Path
        Scratch folder for the ELF and the flat binary.

    Returns
    -------
    bytes
        The payload of bank A, with the doorbell of the test.
    """
    elf = directory / "doom_loader.elf"
    binary = directory / "doom_loader.bin"
    launch = RAM_BASE + LAUNCH_OFFSET
    script = directory / "doom_loader.ld"
    script.write_text(
        f"ENTRY(_start)\nSECTIONS {{ . = {BANK_A_ENTRY:#x}; "
        ".text : { *(.text.loader) *(.text*) } }\n"
    )
    subprocess.run(  # noqa: S603
        [
            TOOLCHAIN["gcc"],
            "-march=rv32i_zifencei",
            "-mabi=ilp32",
            "-nostdlib",
            "-nostartfiles",
            f"-DDOOM_LAUNCH_ADDR={launch:#x}",
            f"-I{RUNTIME}",
            "-T",
            str(script),
            str(RUNTIME / "doom_loader.S"),
            "-o",
            str(elf),
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603
        [TOOLCHAIN["objcopy"], "-O", "binary", str(elf), str(binary)],
        check=True,
    )
    return binary.read_bytes()


def words_of(data: bytes) -> list[int]:
    """Split bytes into little-endian words, padding the last one.

    Parameters
    ----------
    data : bytes
        The bytes.

    Returns
    -------
    list of int
        The words.
    """
    padded = data + bytes(-len(data) % WORD)
    return [w for (w,) in struct.iter_unpack("<I", padded)]


def sdram_program() -> list[int]:
    """Build the program the loader must reach at the base of the RAM.

    Returns
    -------
    list of int
        The code: the mark at `RAM_BASE + MARK_OFFSET`, then `tohost`.
    """
    return [
        *load_address(T0, RAM_BASE + MARK_OFFSET),
        *load_address(T1, MARK),
        sw(T1, T0, 0),
        *load_address(T0, TOHOST),
        addi(T1, X0, 1),
        sw(T1, T0, 0),
        jal(X0, 0),
    ]


def sdram_image(with_magic: bool) -> list[int]:
    """Lay out the SDRAM image of the test.

    Parameters
    ----------
    with_magic : bool
        Whether the doorbell already holds the magic.

    Returns
    -------
    list of int
        The words from the base of the RAM up to the doorbell.
    """
    words = [0] * (LAUNCH_OFFSET // WORD + 1)
    program = sdram_program()
    words[: len(program)] = program
    if with_magic:
        words[LAUNCH_OFFSET // WORD] = LAUNCH_MAGIC
    return words


def build() -> dict[str, str]:
    """Build the text of every image file.

    Returns
    -------
    dict of {str: str}
        File name to its text.
    """
    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        hex_path = boot_memory.build_boot_memory(
            TOOLCHAIN, PATHS, ROOT, directory / "boot"
        )
        boot = hex_path.read_text()
        payload = loader_payload(directory)
    image = flash_image.pack(payload, 1, BANK_A_SIZE)
    flash = [0] * (BANK_A_BASE // WORD) + words_of(image)
    return {
        "boot_memory.hex": boot,
        "flash.hex": hex_lines(flash),
        "sdram_go.hex": hex_lines(sdram_image(True)),
        "sdram_wait.hex": hex_lines(sdram_image(False)),
    }


def main() -> None:
    """Write the images, or compare them with `--check`."""
    parser = argparse.ArgumentParser(description="Escreve as imagens")
    parser.add_argument("--check", action="store_true")
    texts = build()
    if parser.parse_args().check:
        stale = [
            n
            for n in FILES
            if not (DATA / n).exists() or (DATA / n).read_text() != texts[n]
        ]
        if stale:
            print(f"out of date: {', '.join(stale)}: run the generator")
            sys.exit(1)
        print("the doom images are up to date")
        return
    DATA.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (DATA / name).write_text(text)
        print(f"wrote {DATA / name}")


if __name__ == "__main__":
    main()
