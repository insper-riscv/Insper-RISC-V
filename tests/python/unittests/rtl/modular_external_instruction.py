"""Modelo external-instruction do topo modular: resultado na RAM."""

from typing import Any

import cocotb

from tests.python.unittests.rtl.modular_common import (
    FIRST,
    SECOND,
    wait_for_internal_result,
    watch_internal_ram,
)
from tests.python.unittests.rtl.platform_common import start
from tests.python.utils.checks import check


@cocotb.test()
async def test_the_program_runs(dut: Any) -> None:
    """Run the program and check the words in the internal RAM."""
    writes: dict[int, int] = {}
    cocotb.start_soon(watch_internal_ram(dut, writes))
    await start(dut)
    first, second = await wait_for_internal_result(dut, writes)
    check(first == FIRST, f"first word {first:#x}, wanted {FIRST:#x}")
    check(second == SECOND, f"second word {second:#x}, wanted {SECOND:#x}")
