"""Relógio de três fases e BOOT_MEMORY de teste, comuns ao SoC.

Os testes do SoC sozinho (``soc_roles`` e ``soc_timers_*``) fazem o
papel da BOOT_MEMORY e do relógio de três fases; o que muda de um para
o outro é só o programa.
"""

from typing import Any

from cocotb.triggers import RisingEdge, Timer

PHASE_NS = 10
NOP = 0x00000013


def high(signal: Any) -> bool:
    """Say whether a signal is resolved and high."""
    return signal.value.is_resolvable and int(signal.value) == 1


async def three_phase_clock(dut: Any) -> None:
    """Drive the fetch and core clocks, one third of the period each."""
    dut.i_clk_fetch.value = 0
    dut.i_clk_core.value = 0
    while True:
        dut.i_clk_fetch.value = 1
        await Timer(PHASE_NS, unit="ns")
        dut.i_clk_fetch.value = 0
        dut.i_clk_core.value = 1
        await Timer(PHASE_NS, unit="ns")
        dut.i_clk_core.value = 0
        await Timer(PHASE_NS, unit="ns")


async def boot_memory(dut: Any, words: list[int]) -> None:
    """Answer the instruction fetch like a synchronous ROM."""
    while True:
        await RisingEdge(dut.i_clk_fetch)
        if high(dut.o_if_rden):
            index = int(dut.o_if_addr.value)
            dut.i_boot_data.value = words[index] if index < len(words) else NOP
