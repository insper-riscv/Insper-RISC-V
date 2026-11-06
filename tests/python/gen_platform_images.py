"""Gera as imagens dos programas mínimos das dez plataformas.

Uso, da raiz do repositório, com o ``riscv-tools`` da imagem
``dev_tools``:

    PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python \
        tests/python/gen_platform_images.py

Cada plataforma tem a sua pasta em
``tests/python/unittests/rtl/data/platforms/``. A BOOT_MEMORY salta para o
início da ROM (``boot_to_rom.hex``) e a ROM tem o programa a partir
dali. Todas rodam o programa mínimo (``rom_program.hex``), que guarda
0x5A na base da RAM, lê de volta, soma 1 e guarda o resultado na palavra
seguinte. As da FPGA com chaves, botões e display rodam também o
``board_program.hex``, e as duas de UART o ``uart_program.hex``. O mapa
é o do ``platform.yaml`` de cada uma.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.unittests.rtl.modular_common import FIRST
from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    T3,
    T4,
    X0,
    addi,
    andi,
    beq,
    hex_lines,
    jal,
    lui,
    lw,
    sw,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests/python/unittests/rtl/data/platforms"
T5 = 30
T6 = 31
# Valor que o programa das placas grava no display (HEX0 mostra 5).
DISPLAY_VALUE = 0x5A5
# Deslocamento, em bytes, do registrador de pinos sincronizados do GPIO.
GPIO_PINS = 0x24
# Marcador que fecha o programa; o teste o espera antes de conferir.
DONE = FIRST + 1
NOP = addi(X0, X0, 0)

TEST = (
    "test-integrated",
    "test-external-data",
    "test-external-instruction",
    "test-external",
)
BOARD = (
    "fpga-integrated",
    "fpga-external-data",
    "fpga-external-instruction",
    "fpga-external",
)
UART = ("fpga-uart-jtag", "fpga-uart-pins")


def platform_dir(name: str) -> Path:
    """Return the folder of a platform.

    Parameters
    ----------
    name : str
        Platform name, which is the name of its folder.

    Returns
    -------
    Path
        The folder with the ``platform.yaml``.
    """
    group = "simulation" if name.startswith("test-") else "cyclone-v"
    return ROOT / "src" / group / name


def body(ram_hi20: int) -> list[int]:
    """Return the minimal program: store 0x5A, read, add 1, store.

    Parameters
    ----------
    ram_hi20 : int
        Upper 20 bits of the RAM base.

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    return [
        lui(T0, ram_hi20),
        addi(T1, X0, FIRST),
        sw(T1, T0, 0),
        lw(T2, T0, 0),
        addi(T2, T2, 1),
        sw(T2, T0, 4),
        jal(X0, 0),
    ]


def board_body(
    ram_hi20: int, switches: int, keys: int, display: int
) -> list[int]:
    """Return the program of the switches, buttons and displays.

    It writes the display, reads the switches and the buttons through
    the synchronized pins of their GPIO, reads the display back and
    stores the three words at RAM+0, +4 and +8, and DONE at RAM+12.

    Parameters
    ----------
    ram_hi20 : int
        Upper 20 bits of the RAM base.
    switches, keys, display : int
        Bases of the three peripherals.

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    return [
        lui(T0, ram_hi20),
        lui(T1, display >> 12),
        lui(T2, switches >> 12),
        lui(T3, keys >> 12),
        *[NOP] * 12,
        addi(T4, X0, DISPLAY_VALUE),
        sw(T4, T1, 0),
        lw(T5, T2, GPIO_PINS),
        sw(T5, T0, 0),
        lw(T5, T3, GPIO_PINS),
        sw(T5, T0, 4),
        lw(T6, T1, 0),
        sw(T6, T0, 8),
        addi(T4, X0, DONE),
        sw(T4, T0, 12),
        jal(X0, 0),
    ]


def uart_pins_body(ram_hi20: int, uart: int) -> list[int]:
    """Return the program of the UART on the pins, looped back.

    It sends 0x55, waits for RX_VALID (bit 0 of STATUS), stores the
    STATUS that showed it at RAM+4 (reading the byte clears the bit),
    then the byte received at RAM+0, and DONE at +12.

    Parameters
    ----------
    ram_hi20 : int
        Upper 20 bits of the RAM base.
    uart : int
        Base of the UART.

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    return [
        lui(T0, ram_hi20),
        lui(T1, uart >> 12),
        *[NOP] * 4,
        addi(T4, X0, 0x55),
        sw(T4, T1, 0),
        lw(T5, T1, 8),
        andi(T6, T5, 1),
        beq(T6, X0, -8),
        sw(T5, T0, 4),
        lw(T5, T1, 4),
        sw(T5, T0, 0),
        addi(T4, X0, DONE),
        sw(T4, T0, 12),
        jal(X0, 0),
    ]


def uart_jtag_body(ram_hi20: int, uart: int) -> list[int]:
    """Return the program of the UART over JTAG: send 'H', echo +1.

    Parameters
    ----------
    ram_hi20 : int
        Upper 20 bits of the RAM base.
    uart : int
        Base of the UART.

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    return [
        lui(T0, ram_hi20),
        lui(T1, uart >> 12),
        *[NOP] * 4,
        addi(T4, X0, 0x48),
        sw(T4, T1, 0),
        lw(T5, T1, 4),
        andi(T6, T5, 0x100),
        beq(T6, X0, -8),
        andi(T5, T5, 0xFF),
        sw(T5, T0, 0),
        addi(T5, T5, 1),
        sw(T5, T1, 0),
        addi(T4, X0, DONE),
        sw(T4, T0, 12),
        jal(X0, 0),
    ]


def write(folder: Path, name: str, words: list[int]) -> None:
    """Write one image.

    Parameters
    ----------
    folder : Path
        Folder of the platform.
    name : str
        File name.
    words : list of int
        The words of the image.
    """
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(hex_lines(words))


def main() -> None:
    """Write the images of the ten platforms."""
    for name in (*TEST, *BOARD, *UART):
        table = symbols(load_platform(platform_dir(name) / "platform.yaml"))
        rom_words = (
            table["ROM.base" if "ROM.base" in table else "FLASH.base"] // 4
        )
        ram_hi20 = table["RAM.base"] >> 12
        folder = DATA / name
        write(folder, "boot_to_rom.hex", [jal(X0, rom_words * 4)])
        write(folder, "rom_program.hex", [0] * rom_words + body(ram_hi20))
        if name in BOARD:
            program = board_body(
                ram_hi20,
                table["SWITCHES.base"],
                table["KEYS.base"],
                table["DISPLAY.base"],
            )
            write(folder, "board_program.hex", [0] * rom_words + program)
        if name == "fpga-uart-pins":
            program = uart_pins_body(ram_hi20, table["UART.base"])
            write(folder, "uart_program.hex", [0] * rom_words + program)
        if name == "fpga-uart-jtag":
            program = uart_jtag_body(ram_hi20, table["UART.base"])
            write(folder, "uart_program.hex", [0] * rom_words + program)


if __name__ == "__main__":
    main()
