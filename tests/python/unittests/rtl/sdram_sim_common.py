"""Auxiliares dos testes de topo com a SDRAM no começo do mapa da RAM.

As plataformas external-data e doom têm a RAM no início do chip de SDRAM
(a FLASH fica fora dele), então o índice de palavra do chip é o da RAM
desde a sua base. A DE0-CV divide o chip entre a FLASH e a RAM e tem os
seus auxiliares em `de0_cv_sim_top.py`.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

CLK_NS = 10  # clock base do núcleo (dividido por três dentro do topo)
CLK_MEM_NS = 10  # clock da SDRAM, sem relação fixa com o do núcleo
RESET_CYCLES = 5
POLL_CYCLES = 500
TIMEOUT_CYCLES = 400_000
BOOT_MARK, FLASH_MARK, SDRAM_MARK = 0xB0, 0xF1, 0x5D
DISPLAY_VALUE = 0x123
# Índices de palavra na SDRAM: a marca de cada região e o `tohost`.
BOOT_WORD, FLASH_WORD, SDRAM_WORD = 0, 3, 2
TOHOST_WORD = (0x43FFFFE8 - 0x40000000) // 4


async def start(dut: Any, clk_mem_ns: int = CLK_MEM_NS) -> None:
    """Start both clocks and release the reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    clk_mem_ns : int
        Period of the SDRAM clock, which must be the one the top was
        built for (`sdram_tck_ps`).
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.i_clk_mem, clk_mem_ns, unit="ns").start())
    dut.i_rst.value = 1
    dut.i_dbg_word_addr.value = 0
    await ClockCycles(dut.i_clk, RESET_CYCLES)
    dut.i_rst.value = 0


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
    dut.i_dbg_word_addr.value = index
    await ClockCycles(dut.i_clk_mem, 3)
    await Timer(1, unit="ns")
    return int(dut.o_dbg_word_data.value)


async def wait_for_tohost(
    dut: Any,
    tohost_word: int = TOHOST_WORD,
    timeout_cycles: int = TIMEOUT_CYCLES,
) -> None:
    """Wait until the program writes a nonzero value to tohost.

    Parameters
    ----------
    dut : Any
        The device under test.
    tohost_word : int
        Word index of tohost in the chip.
    timeout_cycles : int
        Core cycles to wait before giving up.

    Raises
    ------
    AssertionError
        If it does not happen before the timeout.
    """
    cycles = 0
    while cycles < timeout_cycles:
        await ClockCycles(dut.i_clk, POLL_CYCLES)
        cycles += POLL_CYCLES
        if await sdram_word(dut, tohost_word) != 0:
            return
    message = "the program never wrote tohost"
    raise AssertionError(message)
