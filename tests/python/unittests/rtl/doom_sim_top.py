"""O topo de simulação da plataforma doom: o carregador da SDRAM.

A BOOT_MEMORY de verdade confere a banca A da FLASH (cabeçalho e
CRC-32) e salta para o `doom_loader.S` de verdade. O carregador espera
a campainha (`launch`) e salta para a base da SDRAM, onde o hospedeiro
já carregou o programa. Dois casos usam as imagens de
`gen_doom_images.py`:

- este módulo (`sdram_go.hex`): a campainha já traz a magia, então o
  programa da SDRAM roda, guarda a marca, escreve `tohost`, e o
  carregador zera a campainha;
- `doom_sim_wait` (`sdram_wait.hex`): a campainha está zerada, então o
  carregador espera e nada da SDRAM roda.

O topo tem as mesmas portas do da `de0-cv`, então o relógio, o reset e a
leitura da SDRAM pela porta de depuração do chip são os de
`de0_cv_sim_top`.
"""

from typing import Any

import cocotb

from tests.python.unittests.rtl.de0_cv_sim_top import (
    sdram_word,
    start,
    wait_for_tohost,
)
from tests.python.utils.checks import check

MARK = 0xD00D
# Índices de palavra na SDRAM (a disposição de gen_doom_images.py).
MARK_WORD = 0x100 // 4
LAUNCH_WORD = 0x800 // 4


@cocotb.test()
async def test_the_loader_jumps_to_the_sdram_image_on_the_doorbell(
    dut: Any,
) -> None:
    """With the magic set, the image runs and clears the doorbell."""
    await start(dut)
    await wait_for_tohost(dut)
    mark = await sdram_word(dut, MARK_WORD)
    launch = await sdram_word(dut, LAUNCH_WORD)
    check(mark == MARK, f"SDRAM program mark {mark:#x}")
    check(launch == 0, f"the doorbell was not cleared: {launch:#x}")
