"""Programa mínimo das dez plataformas, conferido onde o mapa manda."""

from typing import Any

import cocotb

from tests.python.unittests.rtl.modular_common import FIRST, SECOND
from tests.python.unittests.rtl.platform_common import Results, start
from tests.python.utils.checks import check

TIMEOUT_CYCLES = 400_000
POLL_CYCLES = 200


@cocotb.test()
async def test_the_program_runs(dut: Any) -> None:
    """Run the program and check the two words at the RAM base."""
    results = Results(dut)
    await start(dut)
    cycles = 0
    second = 0
    while cycles < TIMEOUT_CYCLES and second == 0:
        await cocotb.triggers.ClockCycles(dut.i_clk, POLL_CYCLES)
        cycles += POLL_CYCLES
        second = await results.word(1)
    first = await results.word(0)
    check(first == FIRST, f"first word {first:#x}, wanted {FIRST:#x}")
    check(second == SECOND, f"second word {second:#x}, wanted {SECOND:#x}")
