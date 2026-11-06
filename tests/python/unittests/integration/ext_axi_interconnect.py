"""ext_axi_interconnect, alone, with Python models around it.

The testbench plays the core (one access on the port, held until ready,
then mem_advance), the AXI4 slave of the SDRAM on the master port m0 and
the peripherals on the p_* bus. The cache moves a line as a burst of
four beats; the last 4 KB of the SDRAM space and the peripheral window
do not use it.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tests.python.unittests.integration.checks import check_equal, check_true
from tests.python.unittests.integration.dut import Dut

SDRAM = 0x40000000
UNCACHED = 0x43FFF000  # the last 4 KB of the SDRAM space
PERIPHERAL = 0x80000000
CACHE = 0xF0000000  # peripheral 7: write = flush, read = busy
SETTLE_NS = 1
TIMEOUT = 5000  # clocks an access may take
LINE_BEATS = 4
LAST_BEAT = LINE_BEATS - 1
SLOTS = 8
CACHE_SLOT = 7


def word_at(addr: int) -> int:
    """Return the word the SDRAM holds at an address at the start."""
    return (0x5D000000 + (addr >> 2) * 0x10001) & 0xFFFFFFFF


def slot_value(slot: int) -> int:
    """Return the word the peripheral of a slot answers a read with."""
    return 0xA0000000 + slot * 0x01010101


class Sdram:
    """The AXI4 slave of the SDRAM: a word memory that logs bursts."""

    def __init__(self) -> None:
        """Start with an empty memory and empty logs."""
        self.words: dict[int, int] = {}
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, int]] = []
        self.beats: list[tuple[int, int]] = []
        self.write_addr = 0
        self.write_beat = 0
        self.queue: list[int] = []

    def read(self, addr: int) -> int:
        """Return the word at a byte address."""
        return self.words.get(addr >> 2, word_at(addr))

    def store(self, addr: int, data: int, strobes: int) -> None:
        """Write the enabled bytes of the word at a byte address."""
        value = self.read(addr)
        for b in range(4):
            if (strobes >> b) & 1:
                mask = 0xFF << (8 * b)
                value = (value & ~mask) | (data & mask)
        self.words[addr >> 2] = value
        self.beats.append((addr, strobes))

    async def run(self, dut: Dut) -> None:
        """Answer every request at once, one transfer per clock."""
        for name in ("awready", "wready", "arready"):
            getattr(dut, f"i_m0_{name}").value = 1
        dut.i_m0_bresp.value = 0
        dut.i_m0_rresp.value = 0
        while True:
            await RisingEdge(dut.i_clk)
            self.take_write(dut)
            if int(dut.i_m0_bvalid.value) and int(dut.o_m0_bready.value):
                dut.i_m0_bvalid.value = 0
            self.take_read(dut)
            self.drive_read(dut)

    def take_write(self, dut: Dut) -> None:
        """Log AW, store the W beats and raise B at the last beat."""
        if int(dut.o_m0_awvalid.value):
            self.write_addr = int(dut.o_m0_awaddr.value)
            self.write_beat = 0
            self.writes.append((self.write_addr, int(dut.o_m0_awlen.value)))
        if int(dut.o_m0_wvalid.value):
            self.store(
                self.write_addr + 4 * self.write_beat,
                int(dut.o_m0_wdata.value),
                int(dut.o_m0_wstrb.value),
            )
            self.write_beat += 1
            if int(dut.o_m0_wlast.value):
                dut.i_m0_bvalid.value = 1

    def take_read(self, dut: Dut) -> None:
        """Log the AR transfer and queue the addresses of its beats."""
        if int(dut.o_m0_arvalid.value):
            base = int(dut.o_m0_araddr.value)
            length = int(dut.o_m0_arlen.value)
            self.reads.append((base, length))
            self.queue = [base + 4 * k for k in range(length + 1)]

    def drive_read(self, dut: Dut) -> None:
        """Offer the next beat of the read burst, one beat at a time."""
        if int(dut.i_m0_rvalid.value) and int(dut.o_m0_rready.value):
            self.queue.pop(0)
        if self.queue:
            dut.i_m0_rvalid.value = 1
            dut.i_m0_rdata.value = self.read(self.queue[0])
            dut.i_m0_rlast.value = int(len(self.queue) == 1)
        else:
            dut.i_m0_rvalid.value = 0
            dut.i_m0_rlast.value = 0


class Peripherals:
    """What the p_* bus saw: the accesses, in order, with the slot."""

    def __init__(self) -> None:
        """Start with an empty log."""
        self.accesses: list[tuple[str, int, int, int]] = []

    async def run(self, dut: Dut) -> None:
        """Log every strobe of the p_* bus."""
        while True:
            await RisingEdge(dut.i_clk)
            for kind, bus in (("w", dut.o_p_we), ("r", dut.o_p_re)):
                strobes = int(bus.value)
                for slot in range(SLOTS):
                    if (strobes >> slot) & 1:
                        self.accesses.append(
                            (
                                kind,
                                slot,
                                int(dut.o_p_addr.value),
                                int(dut.o_p_wdata.value),
                            )
                        )


async def post_edge(dut: Dut) -> None:
    """Wait for a clock edge and let the signals settle."""
    await RisingEdge(dut.i_clk)
    await Timer(SETTLE_NS, unit="ns")


async def start(dut: Dut) -> tuple[Sdram, Peripherals]:
    """Reset the DUT and start the clock and the models."""
    sdram, periph = Sdram(), Peripherals()
    for name in ("i_rden", "i_wren", "i_mem_advance", "i_flush"):
        getattr(dut, name).value = 0
    dut.i_addr.value = 0
    dut.i_wdata.value = 0
    dut.i_byteena.value = 0xF
    dut.i_rst.value = 1
    dut.i_m0_bvalid.value = 0
    dut.i_m0_rvalid.value = 0
    dut.i_m0_rlast.value = 0
    dut.i_m0_rdata.value = 0
    dut.i_p_rdata.value = sum(slot_value(s) << (32 * s) for s in range(SLOTS))
    await Timer(SETTLE_NS, unit="ns")
    cocotb.start_soon(Clock(dut.i_clk, 20, unit="ns").start())
    cocotb.start_soon(sdram.run(dut))
    cocotb.start_soon(periph.run(dut))
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    dut.i_rst.value = 0
    await post_edge(dut)
    return sdram, periph


async def access(
    dut: Dut, addr: int, write: int | None = None, be: int = 0xF
) -> tuple[int, int]:
    """Run one core access; return (read data, clocks until ready).

    `write` is the word to store, and None makes the access a read.
    """
    dut.i_addr.value = addr
    dut.i_wdata.value = write or 0
    dut.i_byteena.value = be
    dut.i_wren.value = int(write is not None)
    dut.i_rden.value = int(write is None)
    clocks = 0
    while True:
        await post_edge(dut)
        clocks += 1
        if int(dut.o_ready.value):
            break
        check_true(clocks < TIMEOUT, "the access never completed")
    dut.i_mem_advance.value = 1
    await post_edge(dut)
    dut.i_mem_advance.value = 0
    dut.i_rden.value = 0
    dut.i_wren.value = 0
    return int(dut.o_rdata.value), clocks


async def flush(dut: Dut) -> None:
    """Ask the cache for a flush as a program does and wait for it."""
    await access(dut, CACHE, write=1)
    for _ in range(TIMEOUT):
        value, _clocks = await access(dut, CACHE)
        if value == 0:
            return
    raise AssertionError("the flush never ended")


@cocotb.test()
async def test_a_cached_load_fetches_one_line(dut: Dut):
    """Check that a load miss is one burst of four, the line aligned."""
    sdram, _ = await start(dut)
    value, _ = await access(dut, SDRAM + 0x124)
    check_equal(sdram.reads, [(SDRAM + 0x120, LAST_BEAT)])
    check_equal(value, word_at(SDRAM + 0x124))
    for offset in (0x120, 0x128, 0x12C):
        value, _ = await access(dut, SDRAM + offset)
        check_equal(value, word_at(SDRAM + offset), f"+{offset:#x}")
    check_equal(len(sdram.reads), 1, "the line is in the cache")


@cocotb.test()
async def test_a_cached_store_reaches_the_memory_with_the_flush(dut: Dut):
    """Check that a store stays in the cache until the flush."""
    sdram, _ = await start(dut)
    await access(dut, SDRAM + 0x204, write=0xCAFE0001)
    check_equal(sdram.writes, [], "a write-back cache wrote through")
    value, _ = await access(dut, SDRAM + 0x204)
    check_equal(value, 0xCAFE0001)
    await flush(dut)
    check_equal(sdram.writes, [(SDRAM + 0x200, LAST_BEAT)])
    check_equal(sdram.read(SDRAM + 0x204), 0xCAFE0001)
    check_equal(sdram.read(SDRAM + 0x200), word_at(SDRAM + 0x200))


@cocotb.test()
async def test_the_flush_input_writes_the_dirty_lines_back(dut: Dut):
    """Check the i_flush port: dirty lines out, then flush done."""
    sdram, _ = await start(dut)
    await access(dut, SDRAM + 0x300, write=0x11112222)
    dut.i_flush.value = 1
    await post_edge(dut)
    dut.i_flush.value = 0
    done = False
    for _ in range(TIMEOUT):
        await post_edge(dut)
        done = done or bool(int(dut.o_flush_done.value))
        if done and not int(dut.o_busy.value):
            break
    check_true(done, "o_flush_done never rose")
    check_equal(sdram.read(SDRAM + 0x300), 0x11112222)


@cocotb.test()
async def test_the_uncached_window_goes_straight_to_the_bus(dut: Dut):
    """Check single-beat transfers for the shared words of the host."""
    sdram, _ = await start(dut)
    await access(dut, UNCACHED + 0x20, write=0x600D)
    check_equal(sdram.writes, [(UNCACHED + 0x20, 0)])
    check_equal(sdram.read(UNCACHED + 0x20), 0x600D)
    value, _ = await access(dut, UNCACHED + 0x20)
    check_equal(value, 0x600D)
    check_equal(sdram.reads, [(UNCACHED + 0x20, 0)])


@cocotb.test()
async def test_the_byte_enables_reach_the_bus(dut: Dut):
    """Check the strobes of an uncached store."""
    sdram, _ = await start(dut)
    base = sdram.read(UNCACHED + 0x40)
    await access(dut, UNCACHED + 0x40, write=0xAABBCCDD, be=0x5)
    want = (base & 0xFF00FF00) | (0xAABBCCDD & 0x00FF00FF)
    check_equal(sdram.read(UNCACHED + 0x40), want)


@cocotb.test()
async def test_a_peripheral_access_selects_one_slot(dut: Dut):
    """Check the strobe, the word index and the data of each slot."""
    sdram, periph = await start(dut)
    for slot in range(CACHE_SLOT):
        addr = PERIPHERAL | (slot << 28) | (0x15 << 2)
        value, _ = await access(dut, addr)
        check_equal(value, slot_value(slot), f"read slot {slot}")
        await access(dut, addr, write=0x1000 + slot)
    reads = [a for a in periph.accesses if a[0] == "r"]
    writes = [a for a in periph.accesses if a[0] == "w"]
    check_equal([a[1] for a in reads], list(range(CACHE_SLOT)))
    check_equal([a[1] for a in writes], list(range(CACHE_SLOT)))
    check_equal({a[2] for a in periph.accesses}, {0x15})
    check_equal([a[3] for a in writes], [0x1000 + s for s in range(7)])
    check_equal(sdram.reads, [], "a peripheral access reached the SDRAM")


@cocotb.test()
async def test_slot_7_is_the_cache_and_not_an_outside_peripheral(dut: Dut):
    """Check that slot 7 never shows on the p_* strobes."""
    _, periph = await start(dut)
    value, _ = await access(dut, CACHE)
    check_equal(value, 0, "an idle cache is not busy")
    await access(dut, CACHE, write=1)
    await flush(dut)
    check_true(
        all(a[1] != CACHE_SLOT for a in periph.accesses),
        "the cache control reached the outside",
    )
