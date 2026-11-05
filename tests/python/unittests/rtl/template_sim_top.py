"""Teste do topo da plataforma modelo com o programa mínimo."""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

from tests.python.utils.checks import check

FIRST = 0x5A
SECOND = 0x5B
RAM_BASE = 0x8000
POLL_CYCLES = 200
TIMEOUT_CYCLES = 200_000


async def watch_ram(dut: Any, writes: dict[int, int]) -> None:
    """Record every write on the RAM bus of the core.

    Parameters
    ----------
    dut : Any
        The device under test.
    writes : dict of int to int
        Filled with the last word written to each byte address.
    """
    while True:
        await RisingEdge(dut.pll_clk_idexmem)
        if int(dut.ram_en.value) and int(dut.ram_wren.value):
            writes[int(dut.ram_addr.value)] = int(dut.ram_wdata.value)


@cocotb.test()
async def test_the_program_runs(dut: Any) -> None:
    """Run the program and check the words it stores in the RAM."""
    writes: dict[int, int] = {}
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    dut.i_rst.value = 1
    await ClockCycles(dut.i_clk, 5)
    dut.i_rst.value = 0
    cocotb.start_soon(watch_ram(dut, writes))
    cycles = 0
    while RAM_BASE + 4 not in writes and cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.i_clk, POLL_CYCLES)
        cycles += POLL_CYCLES
    check(RAM_BASE + 4 in writes, "the program did not store its result")
    check(writes[RAM_BASE] == FIRST, f"first word {writes[RAM_BASE]:#x}")
    check(writes[RAM_BASE + 4] == SECOND, "second word is not 0x5B")
