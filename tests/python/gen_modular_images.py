"""Gera as imagens dos programas dos testes do topo modular.

Uso, da raiz do repositório:

    uv run python tests/python/gen_modular_images.py

O programa guarda 0x5A na base da RAM, lê de volta, soma 1 e guarda o
resultado na palavra seguinte. A BOOT_ROM salta para a ROM, que começa
logo depois dela, e os quatro modelos usam as mesmas duas imagens, em
tests/python/unittests/rtl/data/modular/.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    X0,
    addi,
    hex_lines,
    jal,
    lui,
    lw,
    sw,
)

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/modular"
ROOT = Path(__file__).resolve().parents[2]
MAP = symbols(load_platform(ROOT / "src/simulation/modular/platform.yaml"))
ROM_BASE = MAP["ROM.base"]  # a ROM começa logo depois da BOOT_ROM
RAM_BASE = MAP["RAM.base"]
ROM_BASE_WORDS = ROM_BASE // 4
RAM_HI20 = RAM_BASE >> 12
FIRST = 0x5A


def body(base_hi20: int, base_low: int) -> list[int]:
    """Return the program that stores 0x5A, reads it and stores 0x5B.

    Parameters
    ----------
    base_hi20 : int
        Upper 20 bits of the data base address.
    base_low : int
        Lower 12 bits of the data base address (0 for none).

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    words = [lui(T0, base_hi20)]
    if base_low:
        words.append(addi(T0, T0, base_low))
    words += [
        addi(T1, X0, FIRST),
        sw(T1, T0, 0),
        lw(T2, T0, 0),
        addi(T2, T2, 1),
        sw(T2, T0, 4),
        jal(X0, 0),
    ]
    return words


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
    """Write every image.

    The four models run the same two images, because the ROM always
    starts right after the BOOT_ROM and the RAM has the same address.
    """
    write("boot_to_rom.hex", [jal(X0, ROM_BASE_WORDS * 4)])
    write("rom_program.hex", [0] * ROM_BASE_WORDS + body(RAM_HI20, 0))


if __name__ == "__main__":
    main()
