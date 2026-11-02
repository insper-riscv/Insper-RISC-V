"""Modelo external do topo modular: resultado no chip externo."""

from typing import Any

import cocotb

from tests.python.unittests.rtl.modular_common import (
    FIRST,
    SECOND,
    start,
    wait_for_external_result,
)
from tests.python.utils.checks import check


@cocotb.test()
async def test_the_program_runs(dut: Any) -> None:
    """Run the program and check the words in the external chip."""
    await start(dut)
    first, second = await wait_for_external_result(dut)
    check(first == FIRST, f"first word {first:#x}, wanted {FIRST:#x}")
    check(second == SECOND, f"second word {second:#x}, wanted {SECOND:#x}")
