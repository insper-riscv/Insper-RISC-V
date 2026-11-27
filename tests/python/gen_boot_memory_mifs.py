"""Gera as imagens `boot_memory_init.mif` versionadas das plataformas.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    uv run python tests/python/gen_boot_memory_mifs.py
    uv run python tests/python/gen_boot_memory_mifs.py --check

A IP da BOOT_MEMORY lê o `boot_memory_init.mif` na compilação do
Quartus, e o `riscv-tools board generate` copia o arquivo versionado da
plataforma para o projeto. Se o arquivo ficar para trás da
`boot_memory.S` ou do `platform.yaml` (que muda as bancas da FLASH no
`flash_banks.h` e o linker script), a placa roda uma BOOT_MEMORY de
outro mapa, e o cabeçalho da banca é lido fora da FLASH. Aqui cada MIF é
montado pelo mesmo caminho do `program` (`boot_memory.S`, o linker
script gerado e a profundidade de `memory.boot_memory_words`), e com
`--check` o script só confere se o arquivo versionado é igual a ele.
"""

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Any

from riscv_tools import bin_to_image, boot_memory
from riscv_tools.settings import load_config

ROOT = Path(__file__).resolve().parents[2]
# A pasta da configuração de cada plataforma com BOOT_MEMORY de placa e
# o MIF versionado dela (relativo à raiz do repositório).
PLATFORMS = {
    "src/cyclone-v/de0-cv": "src/cyclone-v/de0-cv/boot_memory_init.mif",
    "src/cyclone-v/doom": "src/cyclone-v/doom/boot_memory_init.mif",
    "src/cyclone-v/external-data": (
        "src/cyclone-v/external-data/boot_memory_init.mif"
    ),
    "src/simulation/internal-mem": (
        "src/simulation/internal-mem/quartus/boot_memory_init.mif"
    ),
}


def built_mif(platform: str) -> str:
    """Monta o MIF da BOOT_MEMORY de uma plataforma a partir do fonte.

    Parameters
    ----------
    platform : str
        A pasta da plataforma, relativa à raiz do repositório.

    Returns
    -------
    str
        O texto do MIF, com a profundidade da BOOT_MEMORY.
    """
    cfg: dict[str, Any] = load_config(ROOT / platform / "config.yaml")
    with tempfile.TemporaryDirectory() as directory:
        build_dir = Path(directory)
        boot_memory.build_boot_memory(
            cfg["toolchain"],
            cfg["paths"],
            ROOT,
            build_dir,
            boot_memory.BootMemoryOptions(base=cfg["isa"]["base"]),
        )
        mif = build_dir / "boot_memory.mif"
        bin_to_image.bin_to_mif(
            build_dir / "boot_memory.bin",
            mif,
            depth=cfg["memory"]["boot_memory_words"],
        )
        return mif.read_text(encoding="utf-8")


def write() -> None:
    """Escreve o MIF de cada plataforma."""
    for platform, target in PLATFORMS.items():
        (ROOT / target).write_text(built_mif(platform), encoding="utf-8")
        print(f"wrote {target}")


def check() -> None:
    """Sai com 1 quando um MIF está atrás do `boot_memory.S`."""
    stale = [
        target
        for platform, target in PLATFORMS.items()
        if not (ROOT / target).is_file()
        or (ROOT / target).read_text(encoding="utf-8") != built_mif(platform)
    ]
    for target in stale:
        print(f"{target} is out of date: run gen_boot_memory_mifs.py")
    if stale:
        sys.exit(1)
    print("the boot_memory_init.mif of every platform is up to date")


def main() -> None:
    """Escreve os MIFs, ou os compara com `--check`."""
    parser = argparse.ArgumentParser(description="Escreve os MIFs da BOOT")
    parser.add_argument("--check", action="store_true")
    if parser.parse_args().check:
        check()
    else:
        write()


if __name__ == "__main__":
    main()
