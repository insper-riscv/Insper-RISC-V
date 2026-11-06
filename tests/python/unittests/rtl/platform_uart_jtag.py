"""UART pelo JTAG: o hospedeiro lê o 'H' e devolve um byte."""

from functools import partial
from typing import Any

import cocotb
from cocotb.triggers import Timer

from tests.python.unittests.integration.jtag import shift_bits
from tests.python.unittests.rtl.platform_common import Results, start
from tests.python.utils.checks import check

HALF_TCK_NS = 40
SCAN_BITS = 48
SENT = 0x48
PUSHED = 0x41
ECHOED = PUSHED + 1
PUSH = 1 << 8
MAX_SCANS = 400


async def tck(dut: Any, **states: bool) -> None:
    """Give one TCK pulse with the given scan states."""
    for name in ("cdr", "sdr", "udr", "uir"):
        getattr(dut, f"i_uart_state_{name}").value = int(
            bool(states.get(name))
        )
    dut.i_uart_tck.value = 0
    await Timer(HALF_TCK_NS, unit="ns")
    dut.i_uart_tck.value = 1
    await Timer(HALF_TCK_NS, unit="ns")
    dut.i_uart_tck.value = 0
    for name in ("cdr", "sdr", "udr", "uir"):
        getattr(dut, f"i_uart_state_{name}").value = 0


async def scan(dut: Any, command: int) -> int:
    """Capture, shift the 48-bit register LSB first and update.

    Returns
    -------
    int
        The bits shifted out.
    """
    return await shift_bits(
        dut.i_uart_tdi,
        dut.o_uart_tdo,
        partial(tck, dut),
        SCAN_BITS,
        command,
    )


def bytes_of(reply: int) -> list[int]:
    """Extract the valid bytes of a scan reply (bits 34:32 count)."""
    count = (reply >> 32) & 0x7
    return [(reply >> (8 * i)) & 0xFF for i in range(min(count, 4))]


@cocotb.test()
async def test_bytes_over_the_jtag(dut: Any) -> None:
    """Read the byte sent, push one back and read the echo."""
    results = Results(dut)
    await start(dut)
    dut.i_uart_ir_in.value = 1
    dut.i_uart_tck.value = 0
    await tck(dut, uir=True)
    seen: list[int] = []
    pushed = False
    for _ in range(MAX_SCANS):
        command = PUSH | PUSHED if (SENT in seen and not pushed) else 0
        pushed = pushed or bool(command)
        seen += bytes_of(await scan(dut, command))
        if ECHOED in seen:
            break
    check(SENT in seen, f"the host never read {SENT:#x}: {seen}")
    check(ECHOED in seen, f"the host never read {ECHOED:#x}: {seen}")
    await results.wait_done()
    got = await results.word(0)
    check(got == PUSHED, f"the program read {got:#x}, wanted {PUSHED:#x}")
