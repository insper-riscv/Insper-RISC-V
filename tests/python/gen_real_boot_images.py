"""Gera a BOOT_MEMORY real dos testes da plataforma modelo e da modular.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    uv run python tests/python/gen_real_boot_images.py
    uv run python tests/python/gen_real_boot_images.py --check

As imagens `boot_to_rom.hex` desses testes são só um `jal` para a ROM.
Estas são a `boot_memory.S` de verdade, montada pelo mesmo caminho do
`riscv-tools`, e rodam o mesmo programa mínimo da ROM. A plataforma
modelo é o núcleo mínimo (`rv32i`, sem Zicsr), e a modular é um núcleo
com Zicsr e interrupções, então os dois testes cobrem a BOOT sem nenhuma
extensão e com os fragmentos de Zicsr. Com `--check` o script só confere
se os arquivos estão em dia com a `boot_memory.S`.
"""

import argparse
import sys
import tempfile
from pathlib import Path

from riscv_tools import boot_memory

from tests.python.utils.rv32_asm import hex_lines

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "unittests/rtl/data"
TOOLCHAIN = {
    "gcc": "riscv32-unknown-elf-gcc",
    "objcopy": "riscv32-unknown-elf-objcopy",
}
# A pasta da plataforma e a das imagens do teste dela.
PLATFORMS = {
    "src/simulation/template": DATA / "template",
    "src/simulation/modular": DATA / "modular",
}


def real_boot_memory(platform: str) -> str:
    """Assemble the boot memory of a platform from its source.

    Parameters
    ----------
    platform : str
        The platform folder, relative to the repository root.

    Returns
    -------
    str
        The image, one word per line.
    """
    paths = {
        "boot_memory": f"{platform}/runtime/boot_memory.S",
        "boot_memory_linker_script": f"{platform}/runtime/boot_memory.ld",
    }
    with tempfile.TemporaryDirectory() as directory:
        hex_path = boot_memory.build_boot_memory(
            TOOLCHAIN, paths, ROOT, Path(directory)
        )
        words = [int(line, 16) for line in hex_path.read_text().split()]
    return hex_lines(words)


def write() -> None:
    """Write the image of each platform."""
    for platform, folder in PLATFORMS.items():
        target = folder / "boot_memory_real.hex"
        target.write_text(real_boot_memory(platform))
        print(f"wrote {target}")


def check() -> None:
    """Exit with 1 when an image is older than its `boot_memory.S`."""
    stale = [
        folder / "boot_memory_real.hex"
        for platform, folder in PLATFORMS.items()
        if not (folder / "boot_memory_real.hex").exists()
        or (folder / "boot_memory_real.hex").read_text()
        != real_boot_memory(platform)
    ]
    for target in stale:
        print(f"{target} is out of date: run the generator")
    if stale:
        sys.exit(1)
    print("the real boot images are up to date")


def main() -> None:
    """Write the images, or compare them with `--check`."""
    parser = argparse.ArgumentParser(description="Escreve a BOOT real")
    parser.add_argument("--check", action="store_true")
    if parser.parse_args().check:
        check()
    else:
        write()


if __name__ == "__main__":
    main()
