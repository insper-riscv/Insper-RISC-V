"""Auxiliares dos testes das dez plataformas.

As dez plataformas rodam o mesmo topo, ``modular_sim_top``, e cada uma
tem o seu mapa. O teste descobre onde o resultado do programa fica pelos
genéricos do topo (a base da RAM e se a RAM é do núcleo ou externa), que
vêm do pacote
gerado do ``platform.yaml`` da plataforma.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

POLL_CYCLES = 200
TIMEOUT_CYCLES = 400_000
# O programa guarda o marcador no fim, depois dos resultados.
DONE = 0x5B
DONE_WORD = 3


async def start(dut: Any, reset_cycles: int = 5) -> None:
    """Start the clock and release the reset.

    Parameters
    ----------
    dut : Any
        The device under test.
    reset_cycles : int, optional
        Cycles of the base clock with the reset held.
    """
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    dut.i_rst.value = 1
    dut.i_dbg_word_addr.value = 0
    await ClockCycles(dut.i_clk, reset_cycles)
    dut.i_rst.value = 0


def ram_is_internal(dut: Any) -> bool:
    """Say whether the RAM is the vector inside the core.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    bool
        True when the RAM is not reached through the port of the core.
    """
    return not (int(dut.ram_external.value) or int(dut.has_dcache.value))


def ram_base(dut: Any) -> int:
    """Read the byte address of the RAM from the generic of the top.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    int
        The base of the RAM.
    """
    return int(dut.ram_base_kib.value) * 1024


class Results:
    """Read the words the program wrote to the RAM."""

    def __init__(self, dut: Any) -> None:
        """Start watching the RAM of the core when it is internal.

        Parameters
        ----------
        dut : Any
            The device under test.
        """
        self.dut = dut
        self.internal = ram_is_internal(dut)
        self.base = ram_base(dut)
        self.writes: dict[int, int] = {}
        if self.internal:
            cocotb.start_soon(self._watch())

    async def _watch(self) -> None:
        """Record every write to the internal RAM of the core."""
        while True:
            await RisingEdge(self.dut.pll_clk_idexmem)
            if int(self.dut.o_ram_en.value) and int(self.dut.o_ram_wren.value):
                self.writes[int(self.dut.o_ram_addr.value)] = int(
                    self.dut.o_ram_wdata.value
                )

    async def word(self, index: int) -> int:
        """Read the word ``index`` from the RAM base.

        Parameters
        ----------
        index : int
            Word index from the RAM base.

        Returns
        -------
        int
            The word, zero when nothing was written.
        """
        if self.internal:
            return self.writes.get(self.base + 4 * index, 0)
        self.dut.i_dbg_word_addr.value = index
        await ClockCycles(self.dut.i_clk, 2)
        return int(self.dut.o_dbg_word_data.value)

    async def wait_done(self) -> None:
        """Wait for the closing marker of the program.

        Raises
        ------
        AssertionError
            If the marker does not show up before the timeout.
        """
        cycles = 0
        while cycles < TIMEOUT_CYCLES:
            await ClockCycles(self.dut.i_clk, POLL_CYCLES)
            cycles += POLL_CYCLES
            if await self.word(DONE_WORD) == DONE:
                return
        message = "the program did not store its closing marker"
        raise AssertionError(message)
