"""Teste de entidade do piscador de LED (Blinky).

O genérico half_period é reduzido a poucos ciclos; o LED começa
apagado e inverte a cada half_period bordas de subida do clock.
"""

from itertools import pairwise
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

from tests.python.utils.checks import check

HALF_PERIOD = 5  # o half_period da entrada de tests.json
SETTLE_NS = 1
LEVELS = 2  # o LED tem dois níveis


async def start(dut: Any) -> None:
    """Start the clock and let the first edge pass.

    Parameters
    ----------
    dut : Any
        The device under test.
    """
    cocotb.start_soon(Clock(dut.i_clk, 20, unit="ns").start())
    await Timer(SETTLE_NS, unit="ns")


@cocotb.test()
async def test_the_led_starts_off(dut: Any) -> None:
    """Check that the LED is off before the first half period ends."""
    await start(dut)
    check(int(dut.o_led.value) == 0, "o LED começa apagado")
    await ClockCycles(dut.i_clk, HALF_PERIOD - 1)
    await Timer(SETTLE_NS, unit="ns")
    check(int(dut.o_led.value) == 0, "o LED não muda antes do meio período")


@cocotb.test()
async def test_the_led_toggles_every_half_period(dut: Any) -> None:
    """Check the toggle after each half period, several times."""
    await start(dut)
    seen: list[int] = []
    await ClockCycles(dut.i_clk, 1)
    for _ in range(4):
        await ClockCycles(dut.i_clk, HALF_PERIOD)
        await Timer(SETTLE_NS, unit="ns")
        seen.append(int(dut.o_led.value))
    check(len(set(seen)) == LEVELS, f"o LED não alternou: {seen}")
    check(
        all(a != b for a, b in pairwise(seen)),
        f"o LED inverte a cada meio período: {seen}",
    )


@cocotb.test()
async def test_the_period_is_two_half_periods(dut: Any) -> None:
    """Check the distance between two rising edges of the LED."""
    await start(dut)
    edges: list[int] = []
    previous = int(dut.o_led.value)
    for cycle in range(6 * HALF_PERIOD):
        await RisingEdge(dut.i_clk)
        await Timer(SETTLE_NS, unit="ns")
        now = int(dut.o_led.value)
        if now == 1 and previous == 0:
            edges.append(cycle)
        previous = now
    check(len(edges) >= LEVELS, f"poucas subidas do LED: {edges}")
    check(
        edges[1] - edges[0] == LEVELS * HALF_PERIOD,
        f"período de {edges[1] - edges[0]} ciclos",
    )
