"""Auxiliares dos testes do topo de simulação modular.

Cada modelo roda o mesmo programa mínimo, que guarda 0x5A, lê de volta,
soma 1 e guarda o resultado na palavra seguinte. O que muda é onde o
código e os dados ficam, então o teste de cada modelo confere o lugar
certo.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

FIRST = 0x5A
SECOND = 0x5B
POLL_CYCLES = 200
TIMEOUT_CYCLES = 200_000
INTERNAL_RAM_BASE = 0x8000
EXTERNAL_DATA_INDEX = 0x100 // 4  # o programa externo grava em 0x40000100


async def start(dut: Any) -> None:
    """Start the clock and release the reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    """
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    dut.i_rst.value = 1
    dut.i_dbg_word_addr.value = 0
    await ClockCycles(dut.i_clk, 5)
    dut.i_rst.value = 0


async def watch_internal_ram(dut: Any, writes: dict[int, int]) -> None:
    """Record every write to the internal RAM of the core.

    Parameters
    ----------
    dut : Any
        The device under test.
    writes : dict of int to int
        Filled with the last word written to each byte address.
    """
    while True:
        await RisingEdge(dut.pll_clk_idexmem)
        if int(dut.o_ram_en.value) and int(dut.o_ram_wren.value):
            writes[int(dut.o_ram_addr.value)] = int(dut.o_ram_wdata.value)


async def external_word(dut: Any, index: int) -> int:
    """Read a word of the external RAM chip through the debug port.

    Parameters
    ----------
    dut : Any
        The device under test.
    index : int
        Word index from the start of the chip.

    Returns
    -------
    int
        The word.
    """
    dut.i_dbg_word_addr.value = index
    await ClockCycles(dut.i_clk, 2)
    return int(dut.o_dbg_word_data.value)


async def wait_for_external_result(dut: Any) -> tuple[int, int]:
    """Wait until both words are stored in the external chip.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    tuple of int
        The two words the program stored.

    Raises
    ------
    AssertionError
        If they do not show up before the timeout.
    """
    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.i_clk, POLL_CYCLES)
        cycles += POLL_CYCLES
        second = await external_word(dut, EXTERNAL_DATA_INDEX + 1)
        if second != 0:
            first = await external_word(dut, EXTERNAL_DATA_INDEX)
            return first, second
    message = "the program did not store its result in the external chip"
    raise AssertionError(message)


async def wait_for_internal_result(
    dut: Any, writes: dict[int, int]
) -> tuple[int, int]:
    """Wait until both words are written to the internal RAM.

    Parameters
    ----------
    dut : Any
        The device under test.
    writes : dict of int to int
        The writes recorded by watch_internal_ram.

    Returns
    -------
    tuple of int
        The two words the program stored.

    Raises
    ------
    AssertionError
        If they do not show up before the timeout.
    """
    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.i_clk, POLL_CYCLES)
        cycles += POLL_CYCLES
        second = writes.get(INTERNAL_RAM_BASE + 4)
        if second is not None:
            return writes.get(INTERNAL_RAM_BASE, 0), second
    message = "the program did not write its result to the internal RAM"
    raise AssertionError(message)
