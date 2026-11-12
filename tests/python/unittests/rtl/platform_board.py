"""Chaves, botões e displays: o programa os lê e os escreve."""

from typing import Any

import cocotb

from tests.python.unittests.rtl.platform_common import Results, start
from tests.python.utils.checks import check

SWITCHES = 0x2A5
KEYS = 0x9
# O programa grava 0x5A5; HEX0 mostra o dígito 5 (0010010, nível baixo).
DISPLAY_VALUE = 0x5A5
HEX0_FIVE = 0b0010010


@cocotb.test()
async def test_switches_keys_and_display(dut: Any) -> None:
    """Drive SW and KEY, run the program and check what it did."""
    results = Results(dut)
    dut.io_sw.value = SWITCHES
    dut.io_key.value = KEYS
    await start(dut)
    await results.wait_done()
    switches = await results.word(0)
    keys = await results.word(1)
    shown = await results.word(2)
    check(switches == SWITCHES, f"SW read {switches:#x}, wanted {SWITCHES:#x}")
    check(keys == KEYS, f"KEY read {keys:#x}, wanted {KEYS:#x}")
    check(shown == DISPLAY_VALUE, f"display read back {shown:#x}")
    value = int(dut.o_display_value.value)
    check(value == DISPLAY_VALUE, f"display value {value:#x}")
    hex0 = int(dut.o_display_hex.value) & 0x7F
    check(hex0 == HEX0_FIVE, f"HEX0 is {hex0:#09b}, wanted {HEX0_FIVE:#09b}")
