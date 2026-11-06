"""O topo de simulação da DE0-CV: BOOT_MEMORY, FLASH, SDRAM e `tohost`.

O programa tem um pedaço em cada região do mapa. A BOOT_MEMORY guarda uma
marca na SDRAM e salta para a FLASH; a FLASH guarda outra marca, escreve
no registrador do display e salta para o código que a SDRAM já tem desde
o tempo zero; esse guarda a terceira marca e escreve em `tohost`. O
teste lê a SDRAM pela porta de depuração do chip e confere as marcas, o
display e a parada. As imagens saem de `gen_de0_cv_images.py`.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from tests.python.utils.checks import check

CLK_NS = 10  # clock base do núcleo (dividido por três dentro do topo)
CLK_MEM_NS = 10  # clock da SDRAM (SDRAM_TCK_PS do platform.yaml), sem relação fixa com o do núcleo
RESET_CYCLES = 5
POLL_CYCLES = 500
TIMEOUT_CYCLES = 400_000
BOOT_MARK, FLASH_MARK, SDRAM_MARK = 0xB0, 0xF1, 0x5D
DISPLAY_VALUE = 0x123
# Índices de palavra na SDRAM: a marca de cada região e o `tohost`.
BOOT_WORD, FLASH_WORD, SDRAM_WORD = 0, 3, 2
TOHOST_WORD = (0x43FFFFE8 - 0x40000000) // 4


async def start(dut: Any) -> None:
    """Start both clocks and release the reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    """
    cocotb.start_soon(Clock(dut.CLK, CLK_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.CLK_MEM, CLK_MEM_NS, unit="ns").start())
    dut.reset.value = 1
    dut.DBG_WORD_ADDR.value = 0
    await ClockCycles(dut.CLK, RESET_CYCLES)
    dut.reset.value = 0


async def sdram_word(dut: Any, index: int) -> int:
    """Read a word of the SDRAM chip model through the debug port.

    Parameters
    ----------
    dut : Any
        The device under test.
    index : int
        Word index from the base of the RAM.

    Returns
    -------
    int
        The word.
    """
    dut.DBG_WORD_ADDR.value = index
    await ClockCycles(dut.CLK_MEM, 3)
    await Timer(1, unit="ns")
    return int(dut.DBG_WORD_DATA.value)


async def wait_for_tohost(dut: Any) -> None:
    """Wait until the program writes a nonzero value to tohost.

    Parameters
    ----------
    dut : Any
        The device under test.

    Raises
    ------
    AssertionError
        If it does not happen before the timeout.
    """
    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.CLK, POLL_CYCLES)
        cycles += POLL_CYCLES
        if await sdram_word(dut, TOHOST_WORD) != 0:
            return
    message = "the program never wrote tohost"
    raise AssertionError(message)


@cocotb.test()
async def test_boot_flash_and_sdram_code_run_and_stop_on_tohost(
    dut: Any,
) -> None:
    """Each region leaves its mark and the program stops on tohost."""
    await start(dut)
    await wait_for_tohost(dut)
    boot = await sdram_word(dut, BOOT_WORD)
    flash = await sdram_word(dut, FLASH_WORD)
    sdram = await sdram_word(dut, SDRAM_WORD)
    tohost = await sdram_word(dut, TOHOST_WORD)
    check(boot == BOOT_MARK, f"BOOT_MEMORY mark {boot:#x}")
    check(flash == FLASH_MARK, f"FLASH mark {flash:#x}")
    check(sdram == SDRAM_MARK, f"SDRAM mark {sdram:#x}")
    check(tohost == 1, f"tohost {tohost:#x}")


@cocotb.test()
async def test_the_display_register_takes_the_flash_write(dut: Any) -> None:
    """The write to the display slot reaches the display value."""
    await start(dut)
    await wait_for_tohost(dut)
    value = int(dut.DISPLAY_VALUE.value)
    check(value == DISPLAY_VALUE, f"display {value:#x}")
