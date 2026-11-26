"""O teclado PS/2 da plataforma doom: o núcleo lê as setas.

O programa da SDRAM (`gen_doom_images.py`, `sdram_kbd.hex`) liga a linha
do teclado no PLIC e a interrupção de recepção, avisa que está pronto,
espera cada byte na fila, lê o claim do PLIC com o primeiro e guarda os
scancodes na SDRAM. O testbench é o teclado: depois do aviso ele injeta,
pelas linhas open-drain do conector, o make e o break das quatro setas
em scancodes do conjunto 2 (`E0 75`, `E0 F0 75` e as demais), e confere
o que o núcleo guardou e o claim.
"""

from typing import Any

import cocotb
from cocotb.triggers import Timer

from tests.python.unittests.rtl.sdram_sim_common import (
    sdram_word,
    start,
    wait_for_tohost,
)
from tests.python.utils import doom_frame as frame
from tests.python.utils.checks import check

# Um quarto do período do clock PS/2 do dispositivo, em nanossegundos
# (mais rápido que um teclado de verdade, que a simulação não espera).
QUARTER_NS = 1000
RESULT_WORD = frame.RESULT_OFFSET // frame.WORD
READY_WORD = frame.READY_OFFSET // frame.WORD
# A fonte do teclado no PLIC.
KBD_LINE = 5
POLL_NS = 20_000
READY_LIMIT = 200


def frame_bits(byte: int) -> list[int]:
    """Give the 11 bits of a PS/2 frame, in the order they are sent.

    Parameters
    ----------
    byte : int
        The byte to send.

    Returns
    -------
    list of int
        The start bit, the eight data bits (least significant first),
        the odd parity bit and the stop bit.
    """
    data = [(byte >> number) & 1 for number in range(8)]
    parity = 1 - sum(data) % 2
    return [0, *data, parity, 1]


async def send_byte(dut: Any, byte: int) -> None:
    """Send a byte as the keyboard does, on the open-drain lines.

    Parameters
    ----------
    dut : Any
        The device under test.
    byte : int
        The byte to send.
    """
    for bit in frame_bits(byte):
        dut.i_ps2_dev_dat_low.value = 0 if bit else 1
        await Timer(QUARTER_NS, unit="ns")
        dut.i_ps2_dev_clk_low.value = 1
        await Timer(2 * QUARTER_NS, unit="ns")
        dut.i_ps2_dev_clk_low.value = 0
        await Timer(QUARTER_NS, unit="ns")
    dut.i_ps2_dev_dat_low.value = 0
    await Timer(8 * QUARTER_NS, unit="ns")


async def wait_ready(dut: Any) -> None:
    """Wait until the program is polling the keyboard.

    Parameters
    ----------
    dut : Any
        The device under test.

    Raises
    ------
    AssertionError
        If the program never says it is ready.
    """
    for _ in range(READY_LIMIT):
        await Timer(POLL_NS, unit="ns")
        if await sdram_word(dut, READY_WORD) != 0:
            return
    message = "the program never got ready"
    raise AssertionError(message)


@cocotb.test()
async def test_the_core_reads_the_arrow_keys(dut: Any) -> None:
    """The scancodes of the four arrows reach the core in order."""
    await start(dut)
    dut.i_ps2_dev_clk_low.value = 0
    dut.i_ps2_dev_dat_low.value = 0
    await wait_ready(dut)
    for byte in frame.SCANCODES:
        await send_byte(dut, byte)
    await wait_for_tohost(dut)
    claim = await sdram_word(dut, RESULT_WORD)
    check(claim == KBD_LINE, f"the PLIC claim was {claim}")
    got = [
        await sdram_word(dut, RESULT_WORD + 1 + number)
        for number in range(len(frame.SCANCODES))
    ]
    check(
        got == list(frame.SCANCODES),
        f"the core read {[hex(b) for b in got]}",
    )
