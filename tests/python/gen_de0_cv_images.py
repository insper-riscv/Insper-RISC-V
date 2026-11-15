"""Gera as imagens do teste do topo de simulação da DE0-CV.

Uso, da raiz do repositório:

    PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python \
        tests/python/gen_de0_cv_images.py

O mapa é o de `src/cyclone-v/de0-cv/platform.yaml`: a SDRAM é um
chip só, com a FLASH no começo (o endereço dela no chip é o do SoC) e a
RAM depois dela. A imagem do chip (`sdram.hex`, da palavra 0) tem só a
FLASH, e o programa roda assim:

- a BOOT_MEMORY guarda `BOOT_MARK` na palavra 0 da RAM e salta para a
  FLASH;
- a FLASH guarda `FLASH_MARK` na palavra 3, o valor `DISPLAY_VALUE` no
  registrador do display, instala um tratador de exceção, tenta gravar
  na própria FLASH (o núcleo tem `AccessFaults`, então é uma falha de
  acesso de causa 7 com o endereço em `mtval`, e o dado não muda), copia
  o código da RAM para a RAM e salta para ele;
- o código da RAM guarda `SDRAM_MARK` na palavra 2 e `1` em `tohost`, e
  fica em laço.

As imagens ficam em tests/python/unittests/rtl/data/de0_cv/.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    T3,
    T4,
    X0,
    addi,
    csrrs,
    csrrw,
    hex_lines,
    jal,
    jalr,
    lui,
    lw,
    mret,
    sw,
)

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/de0_cv"
ROOT = Path(__file__).resolve().parents[2]
MAP = symbols(load_platform(ROOT / "src/cyclone-v/de0-cv/platform.yaml"))
FLASH_BASE = MAP["FLASH.base"]
FLASH_END = MAP["FLASH.end"]
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
DISPLAY_BASE = MAP["DISPLAY.base"]
# Onde o código da RAM começa, 4 KiB depois da base da RAM.
RAM_CODE_OFFSET = 0x1000
# Onde o tratador de exceção fica na FLASH, depois do programa.
HANDLER_OFFSET = 0x800
# A palavra protegida da FLASH que o programa tenta gravar, e o
# que a imagem guarda nela.
PROTECTED_OFFSET = 0x1000
PROTECTED_VALUE = 0xC0FFEE11
STORE_VALUE = 0x7B
BOOT_MARK = 0xB0
FLASH_MARK = 0xF1
SDRAM_MARK = 0x5D
DISPLAY_VALUE = 0x123
# Palavras da RAM (índice a partir da base) que o programa preenche.
MARK_WORD = {
    "boot": 0,
    "ram": 2,
    "flash": 3,
    "readback": 4,
    "cause": 5,
    "tval": 6,
}
STORE_ACCESS_FAULT = 7
CSR_MTVEC, CSR_MEPC, CSR_MCAUSE, CSR_MTVAL = 0x305, 0x341, 0x342, 0x343
BITS_LOW = 12
LOW_MASK = (1 << BITS_LOW) - 1
SIGN_BIT = 1 << (BITS_LOW - 1)
WORD = 4


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


def store_word(address: int, value: int) -> list[int]:
    """Return the instructions that store a 32-bit value at an address.

    Parameters
    ----------
    address : int
        Where to store.
    value : int
        The value.

    Returns
    -------
    list of int
        The instructions, using t0 for the address and t1 for the value.
    """
    return [
        *load_address(T0, address),
        *load_address(T1, value),
        sw(T1, T0, 0),
    ]


def ram_code() -> list[int]:
    """Return the program that runs from the RAM.

    Returns
    -------
    list of int
        The mark in the RAM, `tohost` and the loop.
    """
    return [
        *store_value(RAM_BASE + WORD * MARK_WORD["ram"], SDRAM_MARK),
        *store_value(TOHOST, 1),
        jal(X0, 0),
    ]


def handler() -> list[int]:
    """Return the exception handler that records the cause.

    Returns
    -------
    list of int
        It stores `mcause` and `mtval` in the RAM, steps `mepc` over the
        instruction that faulted and returns.
    """
    return [
        *load_address(T4, RAM_BASE),
        csrrs(T3, CSR_MCAUSE, X0),
        sw(T3, T4, WORD * MARK_WORD["cause"]),
        csrrs(T3, CSR_MTVAL, X0),
        sw(T3, T4, WORD * MARK_WORD["tval"]),
        csrrs(T3, CSR_MEPC, X0),
        addi(T3, T3, WORD),
        csrrw(X0, CSR_MEPC, T3),
        mret(),
    ]


def flash_program() -> list[int]:
    """Return the main program of the FLASH.

    Returns
    -------
    list of int
        The marks, the protected store, the copy of the RAM code and the
        jump to it.
    """
    protected = FLASH_BASE + PROTECTED_OFFSET
    words = [
        *store_value(RAM_BASE + WORD * MARK_WORD["flash"], FLASH_MARK),
        *store_value(DISPLAY_BASE, DISPLAY_VALUE),
        *load_address(T0, FLASH_BASE + HANDLER_OFFSET),
        csrrw(X0, CSR_MTVEC, T0),
        *store_value(protected, STORE_VALUE),
        *load_address(T0, protected),
        lw(T1, T0, 0),
        *load_address(T2, RAM_BASE),
        sw(T1, T2, WORD * MARK_WORD["readback"]),
    ]
    for index, word in enumerate(ram_code()):
        words += [
            *load_address(T0, RAM_BASE + RAM_CODE_OFFSET + WORD * index),
            *load_address(T1, word),
            sw(T1, T0, 0),
        ]
    words += [*load_address(T0, RAM_BASE + RAM_CODE_OFFSET), jalr(X0, T0, 0)]
    return words


def chip_image() -> list[int]:
    """Return the image of the chip: the FLASH from the word 0.

    Returns
    -------
    list of int
        The words of the chip, the FLASH at its own address.

    Raises
    ------
    ValueError
        If the main program runs into the handler.
    """
    main = flash_program()
    if WORD * len(main) > HANDLER_OFFSET:
        message = "the main program of the FLASH is too long"
        raise ValueError(message)
    words = [0] * (FLASH_BASE // WORD)
    words += main
    words += [0] * ((HANDLER_OFFSET - WORD * len(main)) // WORD)
    words += handler()
    words += [0] * (
        (PROTECTED_OFFSET - HANDLER_OFFSET - WORD * len(handler())) // WORD
    )
    words.append(PROTECTED_VALUE)
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
    """Write the images."""
    boot = store_value(RAM_BASE, BOOT_MARK)
    boot.append(jal(X0, FLASH_BASE - WORD * len(boot)))
    write("boot_memory.hex", boot)
    write("sdram.hex", chip_image())
    (DATA / "flash.hex").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
