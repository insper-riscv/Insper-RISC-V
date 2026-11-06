"""ext_axi_interconnect with the cache in write-through mode.

Every store also goes to the SDRAM, so it needs no flush to be there.
"""

import cocotb

from tests.python.unittests.integration.checks import check_equal, check_true
from tests.python.unittests.integration.dut import Dut
from tests.python.unittests.integration.ext_axi_interconnect import (
    SDRAM,
    access,
    start,
)


@cocotb.test()
async def test_a_store_reaches_the_memory_without_a_flush(dut: Dut):
    """Check that the store is in the SDRAM when the access ends."""
    sdram, _ = await start(dut)
    await access(dut, SDRAM + 0x204, write=0xCAFE0001)
    check_equal(sdram.read(SDRAM + 0x204), 0xCAFE0001)
    check_true(sdram.writes, "no write burst or beat on the bus")


@cocotb.test()
async def test_the_stored_word_reads_back(dut: Dut):
    """Check that a load after the store sees the new word."""
    await start(dut)
    await access(dut, SDRAM + 0x304, write=0x0BADF00D)
    value, _ = await access(dut, SDRAM + 0x304)
    check_equal(value, 0x0BADF00D)
