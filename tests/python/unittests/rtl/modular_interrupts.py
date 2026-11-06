"""Interrupções no topo modular: o MTIP do CLINT chega ao mip do núcleo.

O programa (rom_irq_program.hex) lê o mip antes de armar o timer, arma o
mtimecmp do CLINT, espera o bit MTIP do mip e guarda o resultado na RAM
interna. O mtime do CLINT conta um tick por ciclo do núcleo e não depende
do CSR time.
"""

from typing import Any

import cocotb

from tests.python.unittests.rtl.modular_common import (
    RAM_BASE,
    SECOND,
    start,
    wait_for_internal_result,
    watch_internal_ram,
)
from tests.python.utils.checks import check

MTIP = 0x80


@cocotb.test()
async def test_mtip_shows_up_in_mip(dut: Any) -> None:
    """The timer line is low before the arming and MTIP is set after it."""
    writes: dict[int, int] = {}
    cocotb.start_soon(watch_internal_ram(dut, writes))
    await start(dut, reset_cycles=30)
    seen, marker = await wait_for_internal_result(dut, writes)
    before = writes.get(RAM_BASE + 8)
    check(before == 0, f"mip before the timer is armed: {before}")
    check(seen == MTIP, f"MTIP bit of mip is {seen:#x}, wanted {MTIP:#x}")
    check(marker == SECOND, f"end marker {marker:#x}, wanted {SECOND:#x}")
