"""Gera as imagens dos programas dos testes do topo modular.

Uso, da raiz do repositório:

    uv run python tests/python/gen_modular_images.py

Cada programa guarda 0x5A, lê de volta, soma 1 e guarda o resultado na
palavra seguinte; as imagens ficam em
tests/python/unittests/rtl/data/modular/.
"""

from pathlib import Path

from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    X0,
    addi,
    hex_lines,
    jal,
    jalr,
    lui,
    lw,
    sw,
)

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/modular"
FLASH_BASE_WORDS = 0x800 // 4  # a FLASH interna começa em 0x800
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


def boot_to(address_hi20: int | None) -> list[int]:
    """Return the BOOT_ROM that jumps to the code.

    Parameters
    ----------
    address_hi20 : int or None
        Upper 20 bits of the entry address; None jumps to the internal
        FLASH at 0x800.

    Returns
    -------
    list of int
        The instructions of the boot ROM.
    """
    if address_hi20 is None:
        return [jal(X0, 0x800)]
    return [lui(T0, address_hi20), jalr(X0, T0, 0)]


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
    """Write every image."""
    internal_flash = [0] * FLASH_BASE_WORDS
    write("boot_to_flash.hex", boot_to(None))
    write("boot_to_ext.hex", boot_to(0x40000))
    write("boot_to_ext_flash.hex", boot_to(0x20000))
    write("flash_internal_data_internal.hex", internal_flash + body(0x8, 0))
    write(
        "flash_internal_data_external.hex",
        internal_flash + body(0x40000, 0x100),
    )
    write("ext_code_data_internal.hex", body(0x8, 0))
    write("ext_code_data_external.hex", body(0x40000, 0x100))
    write("flash_external_code.hex", body(0x40000, 0x100))


if __name__ == "__main__":
    main()
