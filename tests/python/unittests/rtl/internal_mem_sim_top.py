"""Teste do topo de simulação da plataforma internal-mem.

O topo monta o núcleo com a BOOT_MEMORY, a FLASH, a RAM e a UART
simuladas, alimentados pelo gerador de clock de três fases. A
BOOT_MEMORY salta para a FLASH e o programa mínimo guarda 0x5A na base
da RAM, lê de volta, soma 1 e guarda o resultado na palavra seguinte.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from tests.python.unittests.rtl.board_program import (
    run_to_the_result,
    watch_ram,
)
from tests.python.utils.checks import check


async def start(dut: Any) -> None:
    """Start the clock and release the reset after a few cycles.

    Parameters
    ----------
    dut : Any
        The device under test.
    """
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    dut.i_rst.value = 1
    await ClockCycles(dut.i_clk, 5)
    dut.i_rst.value = 0


@cocotb.test()
async def test_the_program_runs(dut: Any) -> None:
    """Run the program and check the words it stores in the RAM."""
    writes: dict[int, int] = {}
    await start(dut)
    cocotb.start_soon(watch_ram(dut, writes))
    await run_to_the_result(dut.i_clk, writes)


@cocotb.test()
async def test_the_phases_never_overlap(dut: Any) -> None:
    """Check that the three clock phases are never high together."""
    await start(dut)
    await ClockCycles(dut.i_clk, 3)
    for _ in range(60):
        await Timer(3, unit="ns")
        high = (
            int(dut.pll_clk_if.value),
            int(dut.pll_clk_idexmem.value),
            int(dut.pll_clk_wb.value),
        )
        check(sum(high) <= 1, f"fases do clock sobrepostas: {high}")


@cocotb.test()
async def test_the_uart_idles_high(dut: Any) -> None:
    """Check that the serial output rests at '1' with no byte sent."""
    await start(dut)
    for _ in range(30):
        await ClockCycles(dut.i_clk, 10)
        check(int(dut.o_uart_tx.value) == 1, "o_uart_tx fora do repouso")
