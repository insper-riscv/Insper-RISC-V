"""The AXI4 slave in front of the peripheral window.

The testbench plays the AXI4 master and the eight peripheral slots. A
single 4-byte aligned INCR beat becomes a one-clock pulse for the
peripheral of the id in bits 30:28; anything else is answered SLVERR
and touches no peripheral.

"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tests.python.unittests.integration.axi_router import (
    read,
    read_burst,
    write,
    write_burst,
)
from tests.python.unittests.integration.checks import check_equal, check_true
from tests.python.unittests.integration.dut import Dut

CLK_NS = 10
SLOTS = 8
PERIPHERALS = 0x80000000
OKAY, SLVERR = 0, 2
LAST_BEAT = 3
SIZE_WORD, SIZE_BYTE = 2, 0
BURST_INCR, BURST_FIXED = 1, 0


def slot_word(slot: int) -> int:
    """Return the word peripheral slot answers with."""
    return 0x5A5A5A00 | slot


def periph_addr(slot: int, word: int) -> int:
    """Return the address of a word in a peripheral window."""
    return PERIPHERALS | (slot << 28) | (word << 2)


class Peripherals:
    """The peripheral side: answers every slot, logs every pulse."""

    def __init__(self, dut: Dut, answering: tuple[int, ...]) -> None:
        """Set what the slots answer and start the log."""
        self.dut = dut
        self.log: list[tuple[str, int, int, int, int]] = []
        dut.i_p_rdata.value = sum(
            slot_word(slot) << (32 * slot) for slot in answering
        )
        cocotb.start_soon(self.run())

    async def run(self) -> None:
        """Log the pulses of every clock."""
        dut = self.dut
        while True:
            await RisingEdge(dut.i_clk)
            fields = (
                int(dut.o_p_addr.value),
                int(dut.o_p_wdata.value),
                int(dut.o_p_byteena.value),
            )
            we, re = int(dut.o_p_we.value), int(dut.o_p_re.value)
            if we:
                self.log.append(("w", we, *fields))
            if re:
                self.log.append(("r", re, *fields))


async def setup(
    dut: Dut, answering: tuple[int, ...] = tuple(range(SLOTS))
) -> Peripherals:
    """Reset the design and start its clock and peripherals."""
    for sig in ("awvalid", "wvalid", "arvalid", "bready", "rready"):
        getattr(dut, f"i_s_{sig}").value = 0
    for channel in ("aw", "ar"):
        getattr(dut, f"i_s_{channel}len").value = 0
        getattr(dut, f"i_s_{channel}size").value = SIZE_WORD
        getattr(dut, f"i_s_{channel}burst").value = BURST_INCR
    dut.i_s_wlast.value = 1
    dut.i_rst.value = 1
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    peripherals = Peripherals(dut, answering)
    for _ in range(3):
        await RisingEdge(dut.i_clk)
    dut.i_rst.value = 0
    await Timer(1, unit="ns")
    return peripherals


@cocotb.test()
async def test_a_write_pulses_the_selected_peripheral(dut: Dut):
    """One write beat gives one write pulse, with the bus beside it."""
    periph = await setup(dut)
    for slot in range(SLOTS):
        periph.log.clear()
        resp = await write(
            dut, periph_addr(slot, 0x21), 0xC0DE0000 | slot, 0x6
        )
        check_equal(resp, OKAY, f"slot {slot} response")
        check_equal(
            periph.log, [("w", 1 << slot, 0x21, 0xC0DE0000 | slot, 0x6)]
        )


@cocotb.test()
async def test_a_read_returns_the_peripheral_word(dut: Dut):
    """One read beat gives one read pulse and the word of that slot."""
    periph = await setup(dut)
    for slot in range(SLOTS):
        periph.log.clear()
        got = await read(dut, periph_addr(slot, 0x05))
        check_equal(got, (slot_word(slot), OKAY), f"slot {slot}")
        check_equal([entry[:2] for entry in periph.log], [("r", 1 << slot)])


@cocotb.test()
async def test_a_silent_window_reads_zero_and_takes_writes(dut: Dut):
    """A silent slot reads zero and accepts a write, both OKAY."""
    await setup(dut, answering=(0,))
    check_equal(await read(dut, periph_addr(6, 0)), (0, OKAY))
    check_equal(await write(dut, periph_addr(6, 0), 0x1), OKAY)


@cocotb.test()
async def test_a_write_burst_is_refused_and_touches_nothing(dut: Dut):
    """A four-beat write gets SLVERR once its beats are consumed."""
    periph = await setup(dut)
    resp = await write_burst(
        dut, periph_addr(1, 0), [(i, 0xF) for i in range(4)]
    )
    check_equal(resp, SLVERR)
    check_equal(periph.log, [], "no peripheral touched")
    check_equal(await write(dut, periph_addr(1, 0), 0x7), OKAY)


@cocotb.test()
async def test_a_read_burst_gives_zeros_with_slverr(dut: Dut):
    """A four-beat read gets four zero beats, each SLVERR."""
    periph = await setup(dut)
    got = await read_burst(dut, periph_addr(2, 0), 4)
    want = [(0, SLVERR, int(i == LAST_BEAT)) for i in range(4)]
    check_equal(got, want, got)
    check_equal(periph.log, [], "no peripheral touched")


@cocotb.test()
async def test_other_sizes_and_burst_types_are_refused(dut: Dut):
    """Only a 4-byte INCR beat is served."""
    periph = await setup(dut)
    resp = await write_burst(
        dut, periph_addr(3, 0), [(1, 0xF)], fmt=(SIZE_BYTE, BURST_INCR)
    )
    check_equal(resp, SLVERR, "byte size")
    resp = await write_burst(
        dut, periph_addr(3, 0), [(1, 0xF)], fmt=(SIZE_WORD, BURST_FIXED)
    )
    check_equal(resp, SLVERR, "fixed burst")
    got = await read_burst(dut, periph_addr(3, 0), 1, size=SIZE_BYTE)
    check_equal(got, [(0, SLVERR, 1)])
    check_true(not periph.log, "no peripheral touched")


@cocotb.test()
async def test_an_unaligned_address_is_refused(dut: Dut):
    """A beat that is not word aligned gets SLVERR."""
    periph = await setup(dut)
    check_equal(await write(dut, periph_addr(0, 1) + 2, 0x9), SLVERR)
    check_equal(await read(dut, periph_addr(0, 1) + 1), (0, SLVERR))
    check_true(not periph.log, "no peripheral touched")
