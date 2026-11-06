"""Gera as imagens do teste do topo de simulação da DE0-CV.

Uso, da raiz do repositório:

    PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python \
        tests/python/gen_de0_cv_images.py

O mapa é o de `src/cyclone-v/de0-cv/platform.yaml`. Cada região roda um
pedaço do programa e deixa uma marca na SDRAM:

- a BOOT_MEMORY guarda `BOOT_MARK` na palavra 0 e salta para a FLASH;
- a FLASH guarda `FLASH_MARK` na palavra 3, o valor `DISPLAY_VALUE` no
  registrador do display e salta para o código da SDRAM;
- a SDRAM (imagem gravada no tempo zero) guarda `SDRAM_MARK` na
  palavra 2 e `1` em `tohost`, e fica em laço.

As imagens ficam em tests/python/unittests/rtl/data/de0_cv/.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.utils.rv32_asm import (
    T0,
    T1,
    X0,
    addi,
    hex_lines,
    jal,
    jalr,
    lui,
    sw,
)

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/de0_cv"
ROOT = Path(__file__).resolve().parents[2]
MAP = symbols(load_platform(ROOT / "src/cyclone-v/de0-cv/platform.yaml"))
FLASH_BASE = MAP["FLASH.base"]
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
DISPLAY_BASE = MAP["DISPLAY.base"]
# Onde o código da SDRAM começa, 4 KiB depois da base da RAM.
SDRAM_CODE_OFFSET = 0x1000
BOOT_MARK = 0xB0
FLASH_MARK = 0xF1
SDRAM_MARK = 0x5D
DISPLAY_VALUE = 0x123
BITS_LOW = 12
LOW_MASK = (1 << BITS_LOW) - 1
SIGN_BIT = 1 << (BITS_LOW - 1)


def load_address(rd: int, address: int) -> list[int]:
    """Return the instructions that put an address in a register.

    Parameters
    ----------
    rd : int
        Destination register.
    address : int
        The 32-bit address.

    Returns
    -------
    list of int
        A lui and, when the low bits are not zero, an addi that
        compensates the sign extension of the immediate.
    """
    low = address & LOW_MASK
    high = address >> BITS_LOW
    if low & SIGN_BIT:
        high += 1
        low -= 1 << BITS_LOW
    words = [lui(rd, high & 0xFFFFF)]
    if low:
        words.append(addi(rd, rd, low))
    return words


def store_value(address: int, value: int) -> list[int]:
    """Return the instructions that store a small value at an address.

    Parameters
    ----------
    address : int
        Where to store.
    value : int
        The value, at most 11 bits.

    Returns
    -------
    list of int
        The instructions, using t0 for the address and t1 for the value.
    """
    return [*load_address(T0, address), addi(T1, X0, value), sw(T1, T0, 0)]


def write(name: str, words: list[int]) -> None:
    """Write one image.

    Parameters
    ----------
    name : str
        File name inside the data folder.
    words : list of int
        The words of the image.
    """
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(hex_lines(words))


def main() -> None:
    """Write the three images."""
    boot = store_value(RAM_BASE, BOOT_MARK)
    boot.append(jal(X0, FLASH_BASE - 4 * len(boot)))
    flash = [
        *store_value(RAM_BASE + 12, FLASH_MARK),
        *store_value(DISPLAY_BASE, DISPLAY_VALUE),
        *load_address(T0, RAM_BASE + SDRAM_CODE_OFFSET),
        jalr(X0, T0, 0),
    ]
    sdram = [
        *store_value(RAM_BASE + 8, SDRAM_MARK),
        *store_value(TOHOST, 1),
        jal(X0, 0),
    ]
    write("boot_memory.hex", boot)
    write("flash.hex", [0] * (FLASH_BASE // 4) + flash)
    write("sdram.hex", [0] * (SDRAM_CODE_OFFSET // 4) + sdram)


if __name__ == "__main__":
    main()
