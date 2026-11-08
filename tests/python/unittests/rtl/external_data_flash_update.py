"""A troca de programa pelo carregador da FLASH, ponta a ponta.

A sequência da seção 6.2 do contrato de entrada
(`docs/pt-br/platform/contrato-de-entrada.md`), no topo de simulação da
external-data com a boot memory de verdade. O programa da FLASH roda e
deixa `tohost` em 1. O hospedeiro manda o comando de parada pela porta
JTAG do carregador, o núcleo entra em reset e para (o contador que o
programa incrementa não anda), o hospedeiro grava o programa novo no
STREAM e confere a contagem e a soma do carregador, e o comando de
liberação solta o reset para o núcleo partir do endereço 0. A boot
memory zera `tohost` antes de saltar, então o programa novo lê zero e
não o 1 que o anterior deixou, e é ele que deixa a marca e o `tohost`
novos. As imagens: o programa antigo e a boot memory saem de
`gen_external_data_images.py`, e o novo é montado aqui.
"""

from types import SimpleNamespace
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from tests.python.unittests.integration.jtag import load_ir, shift_dr
from tests.python.unittests.rtl.de0_cv_sim_top import (
    CLK_MEM_NS,
    CLK_NS,
    RESET_CYCLES,
    TOHOST_WORD,
    sdram_word,
)
from tests.python.utils.checks import check
from tests.python.utils.rv32_asm import (
    T0,
    T1,
    X0,
    addi,
    jal,
    lui,
    lw,
    sw,
)

IR_CMD, IR_STREAM = 1, 2
OP_NOP, OP_HALT, OP_RUN, OP_SUMMARY, OP_CURSOR = 0, 1, 2, 5, 6
BUSY, HALTED = 1, 2
WORD_MASK = 0xFFFFFFFF
POLL_CYCLES = 500
TIMEOUT_CYCLES = 400_000
SETTLE_COMMANDS = 200
FLASH_BASE = 0x1000
RAM_BASE = 0x40000000
TOHOST = 0x43FFFFE8
OLD_MARK_WORD, OLD_MARK = 4, 0x1A
NEW_MARK_WORD, NEW_MARK = 5, 0x2B
SEEN_TOHOST_WORD = 6
COUNTER_WORD = 7
NEW_TOHOST = 2
ENTRY_INDEX = FLASH_BASE // 4
SIGN_LIMIT = 0x800


def flash_port(dut: Any) -> SimpleNamespace:
    """Map the FLASH_* ports of the top to the names the helpers use.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    SimpleNamespace
        An object with the JTAG signals of the loader as `i_jtag_*` and
        `o_jtag_tdo`, as `unittests.integration.jtag` reads them.
    """
    return SimpleNamespace(
        i_jtag_tck=dut.FLASH_TCK,
        i_jtag_tdi=dut.FLASH_TDI,
        o_jtag_tdo=dut.FLASH_TDO,
        i_jtag_ir_in=dut.FLASH_IR_IN,
        i_jtag_state_cdr=dut.FLASH_STATE_CDR,
        i_jtag_state_sdr=dut.FLASH_STATE_SDR,
        i_jtag_state_udr=dut.FLASH_STATE_UDR,
        i_jtag_state_uir=dut.FLASH_STATE_UIR,
    )


def high_low(address: int) -> tuple[int, int]:
    """Split an address for a `lui` and an `addi`.

    Parameters
    ----------
    address : int
        The 32-bit address.

    Returns
    -------
    tuple of (int, int)
        The 20-bit upper part, corrected for the sign of the lower
        part, and the signed 12-bit lower part.
    """
    low = address & 0xFFF
    high = address >> 12
    if low >= SIGN_LIMIT:
        high += 1
        low -= 2 * SIGN_LIMIT
    return high & 0xFFFFF, low


def new_program() -> list[int]:
    """Build the program the host streams into the FLASH.

    Returns
    -------
    list of int
        It stores a mark, copies the `tohost` it finds into the SDRAM
        (the boot memory must have cleared it), writes a new `tohost`
        and loops.
    """
    ram_high, ram_low = high_low(RAM_BASE)
    host_high, host_low = high_low(TOHOST)
    return [
        lui(T0, ram_high),
        addi(T0, T0, ram_low),
        addi(T1, X0, NEW_MARK),
        sw(T1, T0, 4 * NEW_MARK_WORD),
        lui(T1, host_high),
        addi(T1, T1, host_low),
        lw(T1, T1, 0),
        sw(T1, T0, 4 * SEEN_TOHOST_WORD),
        lui(T1, host_high),
        addi(T1, T1, host_low),
        addi(T0, X0, NEW_TOHOST),
        sw(T0, T1, 0),
        jal(X0, 0),
    ]


async def command(
    port: SimpleNamespace, op: int, addr: int = 0, data: int = 0
):
    """Shift one command into the CMD register.

    Returns
    -------
    tuple of (int, int, int)
        Status, word address and data of the previous command.
    """
    value = (op << 60) | ((addr & 0xFFFFFF) << 32) | (data & WORD_MASK)
    out = await shift_dr(port, 64, value)
    return out >> 56, (out >> 32) & 0xFFFFFF, out & WORD_MASK


async def settle(port: SimpleNamespace):
    """Shift NOPs until the previous command has finished.

    Returns
    -------
    tuple of (int, int, int)
        Status, word address and data of the finished command.
    """
    for _ in range(SETTLE_COMMANDS):
        status, word, data = await command(port, OP_NOP)
        if not status & BUSY:
            return status, word, data
    message = "the loader never finished the command"
    raise AssertionError(message)


async def stream(port: SimpleNamespace, words: list[int]) -> None:
    """Shift the words into the STREAM register in a single scan."""
    await load_ir(port, IR_STREAM)
    value = 0
    for i, word in enumerate(words):
        value |= word << (32 * i)
    await shift_dr(port, 32 * len(words) + 1, (value << 1) | 1)
    await load_ir(port, IR_CMD)
    await settle(port)


async def wait_for_word(dut: Any, index: int, want: int) -> None:
    """Wait until a word of the SDRAM holds a value."""
    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.CLK, POLL_CYCLES)
        cycles += POLL_CYCLES
        if await sdram_word(dut, index) == want:
            return
    message = f"SDRAM word {index} never became {want:#x}"
    raise AssertionError(message)


@cocotb.test()
async def test_the_host_replaces_the_program_and_the_core_boots_it(
    dut: Any,
) -> None:
    """Halt, write, check and release: the new program boots."""
    cocotb.start_soon(Clock(dut.CLK, CLK_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.CLK_MEM, CLK_MEM_NS, unit="ns").start())
    port = flash_port(dut)
    dut.reset.value = 1
    dut.DBG_WORD_ADDR.value = 0
    await ClockCycles(dut.CLK, RESET_CYCLES)
    dut.reset.value = 0
    await wait_for_word(dut, TOHOST_WORD, 1)
    check(await sdram_word(dut, OLD_MARK_WORD) == OLD_MARK, "old mark")
    await load_ir(port, IR_CMD)
    await settle(port)

    await command(port, OP_HALT)
    status, _, _ = await settle(port)
    check(bool(status & HALTED), f"the loader is not halted ({status:#x})")
    await ClockCycles(dut.CLK, 2 * POLL_CYCLES)
    frozen = await sdram_word(dut, COUNTER_WORD)
    await ClockCycles(dut.CLK, 4 * POLL_CYCLES)
    check(
        await sdram_word(dut, COUNTER_WORD) == frozen,
        "the program kept running after the halt",
    )
    check(await sdram_word(dut, TOHOST_WORD) == 1, "tohost changed")

    words = new_program()
    await command(port, OP_CURSOR, ENTRY_INDEX)
    await settle(port)
    await stream(port, words)
    await command(port, OP_SUMMARY)
    _, written, total = await settle(port)
    check(written == len(words), f"the loader counted {written} words")
    want = sum(w + ENTRY_INDEX + i for i, w in enumerate(words)) & WORD_MASK
    check(total == want, f"checksum {total:#x}, want {want:#x}")

    await command(port, OP_RUN)
    status, _, _ = await settle(port)
    check(not status & HALTED, "the loader is still halted")
    await wait_for_word(dut, TOHOST_WORD, NEW_TOHOST)
    check(await sdram_word(dut, NEW_MARK_WORD) == NEW_MARK, "new mark")
    seen = await sdram_word(dut, SEEN_TOHOST_WORD)
    check(seen == 0, f"the boot memory left tohost at {seen:#x}")
    await Timer(1, unit="ns")
