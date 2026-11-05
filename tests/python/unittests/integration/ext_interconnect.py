"""The external bus decoder, alone.

The testbench plays the core (one access on the port, held until ready,
then mem_advance), the memory behind the port and the eight peripheral
slots. Memory addresses pass through, peripheral addresses (bit 31) are
decoded into a one-clock pulse for the peripheral of the id in bits
30:28.

"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tests.python.unittests.integration.checks import check_equal, check_true
from tests.python.unittests.integration.dut import Dut

CLK_NS = 10
TIMEOUT = 50  # clocks an access may take
PERIPHERALS = 0x80000000  # first address of the peripherals
SLOTS = 8
MEM_ADDR = 0x40000100
MEM_VALUE = 0x12345678
MEM_READY_DELAY = 3  # clocks the memory takes to answer


def slot_word(slot: int) -> int:
    """Return the word peripheral slot answers with."""
    return 0xA5A5A500 | slot


def periph_addr(slot: int, word: int) -> int:
    """Return the address of a word in a peripheral window."""
    return PERIPHERALS | (slot << 28) | (word << 2)


async def start(dut: Dut, answering: tuple[int, ...] = tuple(range(SLOTS))):
    """Start the clock, reset and set what the peripherals answer."""
    dut.i_addr.value = 0
    dut.i_wdata.value = 0
    dut.i_byteena.value = 0
    dut.i_rden.value = 0
    dut.i_wren.value = 0
    dut.i_mem_advance.value = 0
    dut.i_m_ready.value = 0
    dut.i_m_rdata.value = MEM_VALUE
    dut.i_p_rdata.value = sum(
        slot_word(slot) << (32 * slot) for slot in answering
    )
    dut.i_rst.value = 1
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    for _ in range(4):
        await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    dut.i_rst.value = 0


class Port:
    """The core side of the port, with a log of what the slots saw."""

    def __init__(self, dut: Dut) -> None:
        """Keep the design and an empty log of pulses."""
        self.dut = dut
        self.we_pulses: list[int] = []
        self.re_pulses: list[int] = []
        self.memory_requests = 0

    async def access(self, addr: int, we: bool, wdata: int = 0) -> int:
        """Make one access. Returns the read data after the advance."""
        dut = self.dut
        dut.i_addr.value = addr
        dut.i_wdata.value = wdata
        dut.i_byteena.value = 0xF
        dut.i_wren.value = int(we)
        dut.i_rden.value = int(not we)
        self.we_pulses.clear()
        self.re_pulses.clear()
        self.memory_requests = 0
        for cycle in range(TIMEOUT):
            await Timer(1, unit="ns")
            self.we_pulses.append(int(dut.o_p_we.value))
            self.re_pulses.append(int(dut.o_p_re.value))
            if int(dut.o_m_rden.value) or int(dut.o_m_wren.value):
                self.memory_requests += 1
                dut.i_m_ready.value = int(cycle >= MEM_READY_DELAY)
            if int(dut.o_ready.value):
                break
            await RisingEdge(dut.i_clk)
        else:
            raise AssertionError("ready never came")
        dut.i_mem_advance.value = 1
        await RisingEdge(dut.i_clk)
        await Timer(1, unit="ns")
        value = int(dut.o_rdata.value)
        dut.i_mem_advance.value = 0
        dut.i_rden.value = 0
        dut.i_wren.value = 0
        dut.i_m_ready.value = 0
        return value


@cocotb.test()
async def test_memory_accesses_pass_through(dut: Dut):
    """A memory address reaches the memory side as it came."""
    await start(dut)
    port = Port(dut)
    value = await port.access(MEM_ADDR, False)
    check_equal(value, MEM_VALUE, "memory data")
    check_equal(int(dut.o_m_addr.value), MEM_ADDR)
    check_true(port.memory_requests > 0, "the memory saw a read")
    check_equal(set(port.re_pulses) | set(port.we_pulses), {0})
    await port.access(MEM_ADDR + 4, True, 0xCAFEF00D)
    check_equal(int(dut.o_m_wdata.value), 0xCAFEF00D)
    check_equal(int(dut.o_m_byteena.value), 0xF)


@cocotb.test()
async def test_memory_ready_is_the_memory_ready(dut: Dut):
    """Ready of a memory access follows the memory, not the decoder."""
    await start(dut)
    dut.i_addr.value = MEM_ADDR
    dut.i_rden.value = 1
    for _ in range(MEM_READY_DELAY):
        await RisingEdge(dut.i_clk)
        await Timer(1, unit="ns")
        check_equal(int(dut.o_ready.value), 0, "ready before the memory")
    dut.i_rden.value = 0


@cocotb.test()
async def test_a_peripheral_read_pulses_one_slot_once(dut: Dut):
    """A read raises the read pulse of its slot for a single clock."""
    await start(dut)
    port = Port(dut)
    for slot in range(SLOTS):
        value = await port.access(periph_addr(slot, 0x12), False)
        check_equal(value, slot_word(slot), f"slot {slot} data")
        check_equal(
            [p for p in port.re_pulses if p], [1 << slot], f"slot {slot}"
        )
        check_equal(sum(port.we_pulses), 0, "no write pulse on a read")
        check_equal(int(dut.o_p_addr.value), 0x12, "word offset")
        check_equal(port.memory_requests, 0, "memory left alone")


@cocotb.test()
async def test_a_peripheral_write_pulses_one_slot_once(dut: Dut):
    """A write raises the write pulse of its slot, with the data."""
    await start(dut)
    port = Port(dut)
    for slot in range(SLOTS):
        await port.access(periph_addr(slot, 0x34), True, 0xD0000000 | slot)
        check_equal(
            [p for p in port.we_pulses if p], [1 << slot], f"slot {slot}"
        )
        check_equal(sum(port.re_pulses), 0, "no read pulse on a write")
        check_equal(int(dut.o_p_wdata.value), 0xD0000000 | slot)
        check_equal(int(dut.o_p_addr.value), 0x34)
        check_equal(port.memory_requests, 0, "memory left alone")


@cocotb.test()
async def test_a_window_nobody_answers_reads_zero(dut: Dut):
    """A silent slot reads zero and still completes."""
    await start(dut, answering=(0, 1))
    port = Port(dut)
    check_equal(await port.access(periph_addr(5, 0), False), 0)
    await port.access(periph_addr(5, 0), True, 0x1)


@cocotb.test()
async def test_peripheral_data_stays_until_the_next_load(dut: Dut):
    """A peripheral load keeps its data until a memory load ends."""
    await start(dut)
    port = Port(dut)
    await port.access(periph_addr(3, 0), False)
    dut.i_addr.value = MEM_ADDR
    await Timer(1, unit="ns")
    check_equal(int(dut.o_rdata.value), slot_word(3), "own data kept")
    check_equal(await port.access(MEM_ADDR, False), MEM_VALUE)
    check_equal(int(dut.o_rdata.value), MEM_VALUE, "memory data back")


@cocotb.test()
async def test_peripheral_ready_holds_until_the_pipeline_advances(dut: Dut):
    """Ready of a peripheral access stays up with no second pulse."""
    await start(dut)
    dut.i_addr.value = periph_addr(2, 1)
    dut.i_rden.value = 1
    pulses = 0
    for _ in range(MEM_READY_DELAY + 3):
        await Timer(1, unit="ns")
        pulses += int(int(dut.o_p_re.value) != 0)
        await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    check_equal(int(dut.o_ready.value), 1, "ready held")
    check_equal(pulses, 1, "one pulse only")
    dut.i_rden.value = 0
