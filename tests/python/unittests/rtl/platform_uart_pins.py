"""UART pelos pinos: o programa envia 0x55 e o recebe em laço."""

from typing import Any

import cocotb
from cocotb.triggers import Edge

from tests.python.unittests.rtl.platform_common import Results, start
from tests.python.utils.checks import check

BYTE = 0x55
RX_VALID = 0x1


async def loopback(dut: Any) -> None:
    """Connect the transmitter pin to the receiver pin."""
    while True:
        await Edge(dut.o_uart_tx)
        dut.i_uart_rx.value = dut.o_uart_tx.value


@cocotb.test()
async def test_byte_over_the_pins(dut: Any) -> None:
    """Send a byte on the TX pin and read it back from the RX pin."""
    results = Results(dut)
    dut.i_uart_rx.value = 1
    cocotb.start_soon(loopback(dut))
    await start(dut)
    await results.wait_done()
    received = await results.word(0)
    status = await results.word(1)
    check(received & 0xFF == BYTE, f"received {received:#x}, wanted {BYTE:#x}")
    check(status & RX_VALID, f"STATUS {status:#x} has no RX_VALID")
