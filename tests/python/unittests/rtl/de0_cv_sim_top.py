"""O topo de simulação da DE0-CV: BOOT_MEMORY, FLASH e RAM na SDRAM.

O programa tem um pedaço em cada região do mapa. A BOOT_MEMORY guarda
uma marca na RAM e salta para a FLASH; a FLASH guarda outra marca,
escreve no registrador do display, tenta gravar nela mesma (a falha de
acesso de causa 7 chega ao tratador, e a FLASH não muda), copia o código
da RAM para a RAM e salta para ele; esse guarda a terceira marca e
escreve em `tohost`. O teste lê o chip pela porta de depuração do
modelo e confere as marcas, a falha, o display e a parada. As imagens
saem de `gen_de0_cv_images.py`.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from tests.python.gen_de0_cv_images import (
    BOOT_MARK,
    DISPLAY_VALUE,
    FLASH_BASE,
    FLASH_END,
    FLASH_MARK,
    MARK_WORD,
    PROTECTED_OFFSET,
    PROTECTED_VALUE,
    RAM_BASE,
    SDRAM_MARK,
    STORE_ACCESS_FAULT,
    TOHOST,
    WORD,
)
from tests.python.utils.checks import check

CLK_NS = 10  # clock base do núcleo (dividido por três dentro do topo)
CLK_MEM_NS = 10  # clock da SDRAM, sem relação fixa com o do núcleo
RESET_CYCLES = 5
POLL_CYCLES = 500
TIMEOUT_CYCLES = 600_000
# A RAM começa dentro do chip logo depois da FLASH (FLASH_END do mapa).
RAM_CHIP_OFFSET = FLASH_END
# A palavra da FLASH que o programa tenta gravar.
PROTECTED_ADDRESS = FLASH_BASE + PROTECTED_OFFSET


def ram_word(address: int) -> int:
    """Return the chip word index of an address of the RAM.

    Parameters
    ----------
    address : int
        A byte address of the RAM in the map of the SoC.

    Returns
    -------
    int
        The index of the 32-bit word in the SDRAM chip.
    """
    return (RAM_CHIP_OFFSET + address - RAM_BASE) // WORD


TOHOST_WORD = ram_word(TOHOST)
BOOT_WORD = ram_word(RAM_BASE + WORD * MARK_WORD["boot"])
SDRAM_WORD = ram_word(RAM_BASE + WORD * MARK_WORD["ram"])
FLASH_WORD = ram_word(RAM_BASE + WORD * MARK_WORD["flash"])
READBACK_WORD = ram_word(RAM_BASE + WORD * MARK_WORD["readback"])
CAUSE_WORD = ram_word(RAM_BASE + WORD * MARK_WORD["cause"])
TVAL_WORD = ram_word(RAM_BASE + WORD * MARK_WORD["tval"])


async def start(dut: Any) -> None:
    """Start both clocks and release the reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    """
    cocotb.start_soon(Clock(dut.i_clk, CLK_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.i_clk_mem, CLK_MEM_NS, unit="ns").start())
    dut.i_rst.value = 1
    dut.i_dbg_word_addr.value = 0
    await ClockCycles(dut.i_clk, RESET_CYCLES)
    dut.i_rst.value = 0


async def sdram_word(dut: Any, index: int) -> int:
    """Read a word of the SDRAM chip model through the debug port.

    Parameters
    ----------
    dut : Any
        The device under test.
    index : int
        Word index from the start of the chip (the FLASH is there, the
        RAM starts at the end of the FLASH).

    Returns
    -------
    int
        The word.
    """
    dut.i_dbg_word_addr.value = index
    await ClockCycles(dut.i_clk_mem, 3)
    await Timer(1, unit="ns")
    return int(dut.o_dbg_word_data.value)


async def wait_for_tohost(dut: Any) -> None:
    """Wait until the program writes a nonzero value to tohost.

    Parameters
    ----------
    dut : Any
        The device under test.

    Raises
    ------
    AssertionError
        If it does not happen before the timeout.
    """
    cycles = 0
    while cycles < TIMEOUT_CYCLES:
        await ClockCycles(dut.i_clk, POLL_CYCLES)
        cycles += POLL_CYCLES
        if await sdram_word(dut, TOHOST_WORD) != 0:
            return
    message = "the program never wrote tohost"
    raise AssertionError(message)


@cocotb.test()
async def test_boot_flash_and_ram_code_run_and_stop_on_tohost(
    dut: Any,
) -> None:
    """Each region leaves its mark and the program stops on tohost."""
    await start(dut)
    await wait_for_tohost(dut)
    boot = await sdram_word(dut, BOOT_WORD)
    flash = await sdram_word(dut, FLASH_WORD)
    sdram = await sdram_word(dut, SDRAM_WORD)
    tohost = await sdram_word(dut, TOHOST_WORD)
    check(boot == BOOT_MARK, f"BOOT_MEMORY mark {boot:#x}")
    check(flash == FLASH_MARK, f"FLASH mark {flash:#x}")
    check(sdram == SDRAM_MARK, f"RAM code mark {sdram:#x}")
    check(tohost == 1, f"tohost {tohost:#x}")


@cocotb.test()
async def test_a_store_to_the_flash_is_an_access_fault_and_changes_nothing(
    dut: Any,
) -> None:
    """The store faults with cause 7 and the FLASH keeps its word."""
    await start(dut)
    await wait_for_tohost(dut)
    cause = await sdram_word(dut, CAUSE_WORD)
    tval = await sdram_word(dut, TVAL_WORD)
    readback = await sdram_word(dut, READBACK_WORD)
    in_chip = await sdram_word(dut, PROTECTED_ADDRESS // WORD)
    check(cause == STORE_ACCESS_FAULT, f"mcause {cause:#x}, want 7")
    check(tval == PROTECTED_ADDRESS, f"mtval {tval:#x}")
    check(readback == PROTECTED_VALUE, f"read back {readback:#x}")
    check(in_chip == PROTECTED_VALUE, f"the chip holds {in_chip:#x}")


@cocotb.test()
async def test_the_display_register_takes_the_flash_write(dut: Any) -> None:
    """The write to the display slot reaches the display value."""
    await start(dut)
    await wait_for_tohost(dut)
    value = int(dut.o_display_value.value)
    check(value == DISPLAY_VALUE, f"display {value:#x}")
