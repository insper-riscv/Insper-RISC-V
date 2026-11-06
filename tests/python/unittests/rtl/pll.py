"""Teste de entidade do modelo comportamental do PLL (pll).

As três saídas repetem a referência de 50 MHz com defasagens de 0,
6667 e 13333 ps, e o locked sobe LOCK_CYCLES ciclos depois de o reset
descer.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from tests.python.utils.checks import check

PERIOD_NS = 20
LOCK_CYCLES = 10
PHASE_1_PS = 6667
PHASE_2_PS = 13333


async def start(dut: Any, reset_cycles: int = 3) -> None:
    """Start the reference clock and release the reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    reset_cycles : int
        Reference cycles the reset stays high.
    """
    dut.rst.value = 1
    cocotb.start_soon(Clock(dut.refclk, PERIOD_NS, unit="ns").start())
    await ClockCycles(dut.refclk, reset_cycles)
    dut.rst.value = 0


@cocotb.test()
async def test_the_outputs_follow_the_reference(dut: Any) -> None:
    """Check that outclk_0 is the reference clock itself."""
    await start(dut)
    await ClockCycles(dut.refclk, 2)
    for _ in range(PERIOD_NS * 2):
        await Timer(1, unit="ns")
        check(
            int(dut.outclk_0.value) == int(dut.refclk.value),
            "outclk_0 acompanha a referência",
        )


@cocotb.test()
async def test_the_phases_are_delayed(dut: Any) -> None:
    """Check the delay of outclk_1 and outclk_2 from an edge."""
    await start(dut)
    await ClockCycles(dut.refclk, 3)
    # Logo após a borda de subida da referência: as fases atrasadas
    # ainda estão em nível baixo (ou no nível do ciclo anterior).
    await Timer(PHASE_1_PS - 500, unit="ps")
    check(int(dut.outclk_1.value) == 0, "outclk_1 ainda não subiu")
    await Timer(1000, unit="ps")
    check(int(dut.outclk_1.value) == 1, "outclk_1 subiu após 6667 ps")
    check(int(dut.outclk_2.value) == 0, "outclk_2 ainda não subiu")
    await Timer(PHASE_2_PS - PHASE_1_PS, unit="ps")
    check(int(dut.outclk_2.value) == 1, "outclk_2 subiu após 13333 ps")


@cocotb.test()
async def test_locked_rises_after_the_lock_cycles(dut: Any) -> None:
    """Check that locked is low in reset and rises after the lock."""
    await start(dut)
    check(int(dut.locked.value) == 0, "locked baixo logo após o reset")
    await ClockCycles(dut.refclk, LOCK_CYCLES - 2)
    check(int(dut.locked.value) == 0, "locked ainda baixo")
    await ClockCycles(dut.refclk, 4)
    await Timer(1, unit="ns")
    check(int(dut.locked.value) == 1, "locked alto depois do tempo")


@cocotb.test()
async def test_reset_drops_locked(dut: Any) -> None:
    """Check that a reset drops locked and the lock starts again."""
    await start(dut)
    await ClockCycles(dut.refclk, LOCK_CYCLES + 3)
    check(int(dut.locked.value) == 1, "travado antes do reset")
    dut.rst.value = 1
    await Timer(1, unit="ns")
    check(int(dut.locked.value) == 0, "o reset assíncrono derruba locked")
    await ClockCycles(dut.refclk, 3)
    dut.rst.value = 0
    await ClockCycles(dut.refclk, 3)
    check(int(dut.locked.value) == 0, "locked espera de novo o tempo")
    await ClockCycles(dut.refclk, LOCK_CYCLES + 2)
    check(int(dut.locked.value) == 1, "travou outra vez")
