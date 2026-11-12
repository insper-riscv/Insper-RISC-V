"""O topo de simulação da external-data, com a FLASH de duas portas.

A BOOT_MEMORY guarda uma marca na SDRAM e salta para a FLASH. A FLASH
guarda outra marca, lê como dado uma palavra que ela mesma guarda (a
porta do estágio MEM, enquanto a busca usa a outra porta), copia essa
palavra para a SDRAM, escreve no display, guarda a terceira marca e
escreve em `tohost`. Nada roda a partir da SDRAM, porque a plataforma
não tem cache de instruções. O teste confere as marcas, a palavra lida
da FLASH, o display e a parada. As imagens saem de
`gen_external_data_images.py`.
"""

from typing import Any

import cocotb

from tests.python.unittests.rtl.de0_cv_sim_top import (
    BOOT_MARK,
    BOOT_WORD,
    DISPLAY_VALUE,
    FLASH_MARK,
    FLASH_WORD,
    SDRAM_MARK,
    SDRAM_WORD,
    TOHOST_WORD,
    sdram_word,
    start,
    wait_for_tohost,
)
from tests.python.utils.checks import check

# A palavra que a FLASH lê de si mesma e copia para a SDRAM.
FLASH_DATA = 0x5A5AF1A5
FLASH_DATA_WORD = 4


@cocotb.test()
async def test_both_flash_ports_serve_one_program(dut: Any) -> None:
    """Fetch and data load share one FLASH; tohost stops the program."""
    await start(dut)
    await wait_for_tohost(dut)
    words = {
        "BOOT_MEMORY mark": (BOOT_WORD, BOOT_MARK),
        "FLASH mark": (FLASH_WORD, FLASH_MARK),
        "SDRAM mark": (SDRAM_WORD, SDRAM_MARK),
        "FLASH data word": (FLASH_DATA_WORD, FLASH_DATA),
        "tohost": (TOHOST_WORD, 1),
    }
    for name, (index, expected) in words.items():
        got = await sdram_word(dut, index)
        check(got == expected, f"{name} {got:#x}")
    shown = int(dut.o_display_value.value)
    check(shown == DISPLAY_VALUE, f"display {shown:#x}")
