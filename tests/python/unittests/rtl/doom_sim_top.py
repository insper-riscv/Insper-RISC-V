"""O topo de simulação da plataforma doom: a BOOT_MEMORY e a FLASH.

A BOOT_MEMORY de verdade (`boot_memory.S`, montada por
`gen_doom_images.py`) limpa as palavras reservadas do topo da RAM e
salta para `boot.entry`, a base da FLASH. A FLASH está no mesmo chip de
SDRAM que a RAM, e a imagem do chip (`sdram_go.hex`) traz ali o programa
de teste, que guarda uma marca na RAM e escreve `tohost`. O teste lê o
chip pela porta de depuração do modelo e confere a marca e a parada.

O topo tem as mesmas portas do da `de0-cv`, então o relógio, o reset e a
leitura da SDRAM pela porta de depuração do chip são os de
`sdram_sim_common`.
"""

from typing import Any

import cocotb

from tests.python.gen_doom_images import (
    CLK_MEM_NS,
    MARK,
    MARK_OFFSET,
    RAM_BASE,
    TOHOST,
    ram_word,
)
from tests.python.unittests.rtl.sdram_sim_common import (
    sdram_word,
    start,
    wait_for_tohost,
)
from tests.python.utils.checks import check


@cocotb.test()
async def test_the_boot_memory_runs_the_flash_program_that_marks_the_ram(
    dut: Any,
) -> None:
    """The program in the FLASH runs, marks the RAM and stops."""
    await start(dut, CLK_MEM_NS)
    await wait_for_tohost(dut, ram_word(TOHOST))
    mark = await sdram_word(dut, ram_word(RAM_BASE + MARK_OFFSET))
    check(mark == MARK, f"RAM mark {mark:#x}")
