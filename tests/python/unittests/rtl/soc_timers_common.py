"""Auxiliares dos testes do SoC com zero, um e três temporizadores.

O topo `soc_timers_top` liga `timers` temporizadores nas janelas de
índice 0, 1 e 2 da tabela padrão (0x80000000, 0x90000000 e
0xA0000000), nas fontes 5, 7 e 8 do PLIC. O programa roda sempre igual: grava um valor de
topo diferente em cada uma das três janelas e o lê de volta, liga os
temporizadores 0 e 2 com a interrupção habilitada, espera e lê o
registrador de pendências do PLIC.
"""

from typing import Any

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tests.python.utils.checks import check
from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    T3,
    T4,
    X0,
    addi,
    jal,
    lui,
    lw,
    sw,
)

PHASE_NS = 10
RAM_BASE = 0x100000
NOP = addi(X0, X0, 0)
WINDOWS = (0x80000, 0x90000, 0xA0000)
LINES = (5, 7, 8)
TOP_OFFSET = 0x0C
CONFIG_ON = 0b1001
PLIC_PENDING_HI20 = 0xF0001
MARK = 0x55
WAIT_NOPS = 200
TIMEOUT_CYCLES = 4000


def program() -> list[int]:
    """Build the program the three variants run.

    Returns
    -------
    list of int
        The instructions: the top registers of the three windows at
        RAM words 0 to 2, the pending word of the PLIC at word 3 and
        the end mark at word 4.
    """
    words = [NOP] * 24 + [lui(T4, RAM_BASE >> 12)]
    for i, window in enumerate(WINDOWS):
        words += [
            lui(T0, window),
            addi(T1, X0, 0x11 * (i + 1)),
            sw(T1, T0, TOP_OFFSET),
            lw(T2, T0, TOP_OFFSET),
            sw(T2, T4, 4 * i),
        ]
    for window in (WINDOWS[0], WINDOWS[2]):
        words += [lui(T0, window), addi(T1, X0, CONFIG_ON), sw(T1, T0, 0)]
    words += [NOP] * WAIT_NOPS
    words += [lui(T3, PLIC_PENDING_HI20), lw(T2, T3, 0), sw(T2, T4, 12)]
    words += [addi(T1, X0, MARK), sw(T1, T4, 16), jal(X0, 0)]
    return words


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


async def run(dut: Any) -> dict[int, int]:
    """Run the program until the end mark and return the RAM writes.

    Parameters
    ----------
    dut : Any
        The `soc_timers_top`.

    Returns
    -------
    dict of int to int
        The last word written to each byte address of the RAM.
    """
    writes: dict[int, int] = {}
    cocotb.start_soon(three_phase_clock(dut))
    cocotb.start_soon(boot_memory(dut, program()))

    async def watch() -> None:
        while True:
            await RisingEdge(dut.i_clk_core)
            if high(dut.o_ram_en) and high(dut.o_ram_wren):
                writes[int(dut.o_ram_addr.value)] = int(dut.o_ram_wdata.value)

    cocotb.start_soon(watch())
    dut.i_rst.value = 1
    await Timer(10 * PHASE_NS, unit="ns")
    dut.i_rst.value = 0
    for _ in range(TIMEOUT_CYCLES):
        await Timer(3 * PHASE_NS, unit="ns")
        if RAM_BASE + 16 in writes:
            break
    check(RAM_BASE + 16 in writes, "the program never reached its end")
    return writes


def check_timers(writes: dict[int, int], count: int) -> None:
    """Check what the program read back and the PLIC pending word.

    Parameters
    ----------
    writes : dict of int to int
        The RAM writes of the program.
    count : int
        How many timers the SoC has.
    """
    for i in range(3):
        got = writes[RAM_BASE + 4 * i]
        want = 0x11 * (i + 1) if i < count else 0
        check(got == want, f"top of window {i} is {got:#x}, wanted {want:#x}")
    pending = writes[RAM_BASE + 12]
    want = 0
    for i in (0, 2):
        if i < count:
            want |= 1 << LINES[i]
    check(pending == want, f"PLIC pending {pending:#x}, wanted {want:#x}")
