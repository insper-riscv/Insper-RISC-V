"""Auxiliares dos testes dos topos que rodam o programa mínimo.

O programa guarda 0x5A na base da RAM, lê de volta, soma 1 e guarda o
resultado na palavra seguinte. A RAM do core fica em 0x8000 nas
plataformas internal-mem.
"""

from typing import Any

from cocotb.triggers import ClockCycles

from tests.python.unittests.rtl.template_sim_top import (
    FIRST,
    POLL_CYCLES,
    SECOND,
    TIMEOUT_CYCLES,
    watch_ram,
)
from tests.python.utils.checks import check

RAM_BASE = 0x8000

__all__ = ["RAM_BASE", "run_to_the_result", "watch_ram"]


async def run_to_the_result(clock: Any, writes: dict[int, int]) -> None:
    """Wait for the two stores of the program and check their words.

    Parameters
    ----------
    clock : Any
        The clock signal the polling counts.
    writes : dict of int to int
        The words written to the RAM bus, by byte address.
    """
    for _ in range(TIMEOUT_CYCLES // POLL_CYCLES):
        if RAM_BASE + 4 in writes:
            break
        await ClockCycles(clock, POLL_CYCLES)
    check(RAM_BASE + 4 in writes, "the program did not store its result")
    check(writes[RAM_BASE] == FIRST, f"first word {writes[RAM_BASE]:#x}")
    check(writes[RAM_BASE + 4] == SECOND, "second word is not 0x5B")
