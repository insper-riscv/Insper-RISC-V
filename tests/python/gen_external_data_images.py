"""Gera as imagens do teste do topo de simulação da external-data.

Uso, da raiz do repositório:

    PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python \
        tests/python/gen_external_data_images.py

O mapa é o de `src/cyclone-v/external-data/platform.yaml`. A BOOT_ROM
guarda `BOOT_MARK` na palavra 0 da SDRAM e salta para a FLASH. A FLASH
guarda `FLASH_MARK` na palavra 3, lê de volta, como dado, uma palavra
que ela mesma guarda (`FLASH_DATA`, pela segunda porta) e a copia para
a palavra 4, escreve `DISPLAY_VALUE` no display, guarda `SDRAM_MARK` na
palavra 2, escreve `1` em `tohost` e fica em laço. Nenhum código roda a
partir da SDRAM, porque a plataforma não tem cache de instruções.

As imagens ficam em tests/python/unittests/rtl/data/external_data/.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.gen_de0_cv_images import load_address, store_value
from tests.python.utils.rv32_asm import (
    T0,
    T1,
    X0,
    hex_lines,
    jal,
    lw,
    sw,
)

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/external_data"
ROOT = Path(__file__).resolve().parents[2]
PLATFORM = ROOT / "src/cyclone-v/external-data/platform.yaml"
MAP = symbols(load_platform(PLATFORM))
FLASH_BASE = MAP["FLASH.base"]
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
DISPLAY_BASE = MAP["DISPLAY.base"]
BOOT_MARK = 0xB0
FLASH_MARK = 0xF1
SDRAM_MARK = 0x5D
DISPLAY_VALUE = 0x123
# A palavra que a FLASH guarda para si e o deslocamento dela.
FLASH_DATA = 0x5A5AF1A5
FLASH_DATA_OFFSET = 0x400


def main() -> None:
    """Write the two images."""
    boot = store_value(RAM_BASE, BOOT_MARK)
    boot.append(jal(X0, FLASH_BASE - 4 * len(boot)))
    flash = [
        *store_value(RAM_BASE + 12, FLASH_MARK),
        *load_address(T0, FLASH_BASE + FLASH_DATA_OFFSET),
        lw(T1, T0, 0),
        *load_address(T0, RAM_BASE + 16),
        sw(T1, T0, 0),
        *store_value(DISPLAY_BASE, DISPLAY_VALUE),
        *store_value(RAM_BASE + 8, SDRAM_MARK),
        *store_value(TOHOST, 1),
        jal(X0, 0),
    ]
    image = [0] * (FLASH_BASE // 4) + flash
    data_word = (FLASH_BASE + FLASH_DATA_OFFSET) // 4
    image += [0] * (data_word - len(image)) + [FLASH_DATA]
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "boot_rom.hex").write_text(hex_lines(boot))
    (DATA / "flash.hex").write_text(hex_lines(image))


if __name__ == "__main__":
    main()
