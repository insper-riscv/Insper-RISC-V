"""Teste do topo de hardware da plataforma internal-mem.

O core_fpga_test é o topo que o Quartus sintetiza. Aqui ele elabora no
GHDL com o PLL de simulação e com modelos em VHDL puro no lugar dos IPs
da Intel (tests/vhdl/fpga_ip_models.vhd), sem alterar o topo. A BOOT_ROM
salta para a FLASH e o programa mínimo guarda 0x5A na base da RAM, lê de
volta, soma 1 e guarda o resultado na palavra seguinte.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

from tests.python.unittests.rtl.board_program import (
    run_to_the_result,
    watch_ram,
)
from tests.python.utils.checks import check

CLOCK_NS = 20  # a placa tem um clock de 50 MHz
RESET_CYCLES = 5
LOCK_CYCLES = 10  # ciclos da referência até o PLL travar
LED_LOCKED, LED_RESET_N, LED_RUNNING, LED_HALT = 1, 2, 3, 4


async def start(dut: Any) -> None:
    """Start the board clock and release the push-button reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    """
    dut.i_fpga_reset_n.value = 0
    cocotb.start_soon(Clock(dut.i_clock_50, CLOCK_NS, unit="ns").start())
    await ClockCycles(dut.i_clock_50, RESET_CYCLES)
    dut.i_fpga_reset_n.value = 1


def led(dut: Any, index: int) -> int:
    """Return one red LED of the board.

    Parameters
    ----------
    dut : Any
        The device under test.
    index : int
        Index of the LED.

    Returns
    -------
    int
        The level of the LED.
    """
    return int(dut.o_ledr.value[index])


@cocotb.test()
async def test_the_board_program_runs(dut: Any) -> None:
    """Run the program and check the words it stores in the RAM."""
    writes: dict[int, int] = {}
    await start(dut)
    cocotb.start_soon(watch_ram(dut, writes))
    await run_to_the_result(dut.i_clock_50, writes)


@cocotb.test()
async def test_the_leds_follow_the_reset_and_the_pll(dut: Any) -> None:
    """Check the status LEDs in reset, after the lock and running."""
    dut.i_fpga_reset_n.value = 0
    cocotb.start_soon(Clock(dut.i_clock_50, CLOCK_NS, unit="ns").start())
    await ClockCycles(dut.i_clock_50, RESET_CYCLES)
    await Timer(1, unit="ns")
    check(led(dut, LED_LOCKED) == 0, "o PLL não trava com o reset apertado")
    check(led(dut, LED_RESET_N) == 0, "o LED do botão de reset acende")
    check(led(dut, LED_RUNNING) == 0, "o core está em reset")
    dut.i_fpga_reset_n.value = 1
    await ClockCycles(dut.i_clock_50, LOCK_CYCLES + 4)
    await Timer(1, unit="ns")
    check(led(dut, LED_LOCKED) == 1, "o PLL travou")
    check(led(dut, LED_RESET_N) == 1, "o botão de reset foi solto")
    check(led(dut, LED_RUNNING) == 1, "o core saiu do reset")
    check(led(dut, LED_HALT) == 0, "sem hospedeiro o core não é parado")


@cocotb.test()
async def test_the_uart_idles_high(dut: Any) -> None:
    """Check that the serial output rests at '1' with no byte sent."""
    await start(dut)
    for _ in range(20):
        await ClockCycles(dut.i_clock_50, 20)
        check(int(dut.o_uart_tx.value) == 1, "o_uart_tx fora do repouso")
