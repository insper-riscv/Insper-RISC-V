"""O carregador da SDRAM da plataforma doom sem a campainha.

A SDRAM não traz a magia (`sdram_wait.hex`), então o carregador,
depois de a BOOT_MEMORY conferir a banca A, fica esperando e nada da
imagem da SDRAM roda. O tempo de espera é o do teste do topo da
`de0-cv` para o programa terminar, bem maior que o do caso com
campainha (`doom_sim_top`).
"""

from typing import Any

import cocotb
from cocotb.triggers import ClockCycles

from tests.python.unittests.rtl.de0_cv_sim_top import (
    TIMEOUT_CYCLES,
    TOHOST_WORD,
    sdram_word,
    start,
)
from tests.python.unittests.rtl.doom_sim_top import MARK_WORD
from tests.python.utils.checks import check


@cocotb.test()
async def test_the_loader_waits_without_the_doorbell(dut: Any) -> None:
    """Without the magic nothing of the SDRAM image runs."""
    await start(dut)
    await ClockCycles(dut.i_clk, TIMEOUT_CYCLES)
    mark = await sdram_word(dut, MARK_WORD)
    tohost = await sdram_word(dut, TOHOST_WORD)
    check(mark == 0, f"the SDRAM program ran: mark {mark:#x}")
    check(tohost == 0, f"tohost written: {tohost:#x}")
