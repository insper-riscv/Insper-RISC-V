"""O SoC sozinho, sem placa nem modelo de chip: a memória é do teste.

O teste faz o papel da BOOT_MEMORY (um programa de poucas instruções) e
do relógio de três fases, e observa a face da RAM interna. Os papéis de
E/S entram pelos genéricos do SoC: quatro chaves ativas em nível baixo
na janela 1 e nenhum botão nem display.

O programa espera as chaves sincronizarem, lê o registrador de pinos do
GPIO das chaves e guarda a palavra lida na RAM.
"""

from typing import Any

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tests.python.utils.checks import check

PHASE_NS = 10
RAM_BASE = 0x100000
NOP = 0x00000013
# lui x1,0x90000; lw x2,0x24(x1); lui x3,0x100; sw x2,0(x3); jal x0,0
PROGRAM = [NOP] * 24 + [0x900000B7, 0x0240A103, 0x001001B7, 0x0021A023, 0x0000006F]
SWITCHES_PHYSICAL = 0b0101
SWITCHES_SEEN = 0b1010
TIMEOUT_CYCLES = 600


def high(signal: Any) -> bool:
    """Say whether a signal is a resolved one; a signal not driven yet counts as low."""
    return signal.value.is_resolvable and int(signal.value) == 1


async def three_phase_clock(dut: Any) -> None:
    """Drive the fetch and the core clocks, one third of the period each."""
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


async def boot_memory(dut: Any) -> None:
    """Answer the instruction fetch like a synchronous ROM."""
    while True:
        await RisingEdge(dut.i_clk_fetch)
        if high(dut.o_if_rden):
            index = int(dut.o_if_addr.value)
            word = PROGRAM[index] if index < len(PROGRAM) else NOP
            dut.i_boot_data.value = word


async def start(dut: Any) -> dict[int, int]:
    """Start the clocks, the ROM and the watcher; release the reset."""
    writes: dict[int, int] = {}
    cocotb.start_soon(three_phase_clock(dut))
    cocotb.start_soon(boot_memory(dut))

    async def watch() -> None:
        while True:
            await RisingEdge(dut.i_clk_core)
            if high(dut.o_ram_en) and high(dut.o_ram_wren):
                writes[int(dut.o_ram_addr.value)] = int(dut.o_ram_wdata.value)

    cocotb.start_soon(watch())
    dut.i_rst.value = 1
    dut.io_switches.value = SWITCHES_PHYSICAL
    await Timer(10 * PHASE_NS, unit="ns")
    dut.i_rst.value = 0
    return writes


@cocotb.test()
async def test_active_low_switches_reach_the_program_inverted(dut: Any) -> None:
    """The word the program stores is the switches in the program polarity."""
    writes = await start(dut)
    for _ in range(TIMEOUT_CYCLES):
        await Timer(3 * PHASE_NS, unit="ns")
        if RAM_BASE in writes:
            break
    check(RAM_BASE in writes, "the program never stored the switches")
    got = writes[RAM_BASE]
    check(got == SWITCHES_SEEN, f"stored {got:#x}, wanted {SWITCHES_SEEN:#x}")


@cocotb.test()
async def test_chip_faces_stay_idle_without_external_memory(dut: Any) -> None:
    """With internal memories no request leaves by the chip faces."""
    await start(dut)
    for _ in range(100):
        await Timer(3 * PHASE_NS, unit="ns")
        check(not high(dut.o_flash_rden), "FLASH request")
        check(not high(dut.o_ramd_rden), "RAM data read")
        check(not high(dut.o_ramd_wren), "RAM data write")
        check(not high(dut.o_rami_rden), "RAM instruction read")
