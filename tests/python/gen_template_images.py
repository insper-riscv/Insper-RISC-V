"""Gera as imagens dos programas do teste do topo da plataforma modelo.

Uso, da raiz do repositório:

    PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python \
        tests/python/gen_template_images.py

O mapa é o de `src/simulation/template/platform.yaml`. O programa é o
do topo modular (guarda 0x5A na base da RAM, lê de volta, soma 1 e
guarda o resultado na palavra seguinte), e a BOOT_MEMORY salta para a
ROM, que começa logo depois dela. As imagens ficam em
tests/python/unittests/rtl/data/template/.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.gen_modular_images import body
from tests.python.utils.rv32_asm import X0, hex_lines, jal

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/template"
ROOT = Path(__file__).resolve().parents[2]
MAP = symbols(load_platform(ROOT / "src/simulation/template/platform.yaml"))
ROM_BASE = MAP["ROM.base"]
RAM_BASE = MAP["RAM.base"]


def main() -> None:
    """Write the BOOT_MEMORY image and the ROM image."""
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "boot_to_rom.hex").write_text(hex_lines([jal(X0, ROM_BASE)]))
    program = [0] * (ROM_BASE // 4) + body(RAM_BASE >> 12, 0)
    (DATA / "rom_program.hex").write_text(hex_lines(program))


if __name__ == "__main__":
    main()
