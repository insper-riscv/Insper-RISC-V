"""Measure identical store-delimited kernels without adding CSRs to old RTL."""

import json
import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer


@cocotb.test()
async def compare_kernel(dut):
    old = os.environ["VARIANT"] == "baseline"
    clock = getattr(dut, "clk" if old else "i_clk")
    reset = getattr(dut, "reset" if old else "i_rst")
    reset.value = 1
    cocotb.start_soon(Clock(clock, 10, unit="ns").start())
    await Timer(100, unit="ns")
    reset.value = 0
    start = None
    checksum = None
    expected = int(os.environ["EXPECTED"])
    for cycle in range(100000):
        await FallingEdge(dut.pll_clk_idexmem)
        if int(dut.ram_en.value) and int(dut.ram_wren.value):
            address = int(dut.ram_addr.value)
            data = int(dut.ram_wdata.value)
            if address == 0x8100 and data == 1 and start is None:
                start = cycle
            if address == 0x8104:
                checksum = data
            if address == 0x8108 and data == 1 and start is not None:
                result = dict(
                    variant=os.environ["VARIANT"],
                    kernel=os.environ["KERNEL"],
                    cycles=cycle - start,
                    checksum=checksum,
                    expected=expected,
                    verified=checksum == expected,
                    measurement="RAM store-to-store core clock cycles",
                )
                Path(os.environ["RESULT"]).write_text(
                    json.dumps(result, indent=2) + "\n"
                )
                assert checksum == expected, result
                return
    raise AssertionError(
        "Kernel did not signal completion within 100000 core cycles"
    )
