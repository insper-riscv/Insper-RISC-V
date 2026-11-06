"""The JTAG port of the debug registers, driven by the cocotb tests."""

from collections.abc import Awaitable, Callable
from functools import partial
from typing import Any

from cocotb.triggers import Timer

from tests.python.unittests.integration.dut import Dut

HALF_TCK_NS = 40


async def tck(dut: Dut, **states: bool) -> None:
    """Give one TCK pulse with the given scan states."""
    for name in ("cdr", "sdr", "udr", "uir"):
        getattr(dut, f"i_jtag_state_{name}").value = (
            1 if states.get(name) else 0
        )
    dut.i_jtag_tck.value = 0
    await Timer(HALF_TCK_NS, unit="ns")
    dut.i_jtag_tck.value = 1
    await Timer(HALF_TCK_NS, unit="ns")
    dut.i_jtag_tck.value = 0
    for name in ("cdr", "sdr", "udr", "uir"):
        getattr(dut, f"i_jtag_state_{name}").value = 0


async def load_ir(dut: Dut, value: int) -> None:
    """Load a value into the instruction register."""
    dut.i_jtag_ir_in.value = value
    await tck(dut, uir=True)


async def shift_bits(
    tdi: Any,
    tdo: Any,
    pulse: Callable[..., Awaitable[None]],
    length: int,
    value: int,
) -> int:
    """Capture, shift `length` bits (LSB first) and update.

    Parameters
    ----------
    tdi : Any
        The TDI handle of the port.
    tdo : Any
        The TDO handle of the port.
    pulse : Callable[..., Awaitable[None]]
        Gives one TCK pulse with the given scan states.
    length : int
        Number of bits of the register.
    value : int
        Bits shifted in.

    Returns
    -------
    int
        The bits shifted out.
    """
    await pulse(cdr=True)
    out = 0
    for i in range(length):
        tdi.value = (value >> i) & 1
        await Timer(1, unit="ns")
        out |= int(tdo.value) << i
        await pulse(sdr=True)
    await pulse(udr=True)
    return out


async def shift_dr(dut: Dut, length: int, value: int) -> int:
    """Capture, shift `length` bits (LSB first) and update.

    Returns the bits shifted out.

    """
    return await shift_bits(
        dut.i_jtag_tdi,
        dut.o_jtag_tdo,
        partial(tck, dut),
        length,
        value,
    )
