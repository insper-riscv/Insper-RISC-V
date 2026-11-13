"""O SoC com N temporizadores: janelas lidas e linhas do PLIC."""

from typing import Any

import cocotb

from tests.python.unittests.rtl.soc_timers_common import check_timers, run


@cocotb.test()
async def test_timers_and_plic_lines(dut: Any) -> None:
    """Each timer answers on its window and raises its own line."""
    writes = await run(dut)
    check_timers(writes, 0)
