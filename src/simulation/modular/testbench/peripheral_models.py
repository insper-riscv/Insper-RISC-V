"""O mundo externo dos periféricos do topo modular.

Serve aos programas de ``asm-plic/``.

Dois modelos rodam ao lado do núcleo:

- a UART pelos pinos tem o transmissor ligado de volta ao receptor,
  então
  um byte escrito em ``TX_DATA`` volta por ``RX_DATA``;
- o hospedeiro da UART sobre JTAG varre o registrador de 48 bits da
  cadeia, como o programa ``riscv-tools console`` faz na placa. Ele só
  roda quando o programa pede, por uma palavra escrita em ``fromhost``:
  1 liga as varreduras e empurra um byte (0xA5) uma vez, 2 liga as
  varreduras sem empurrar (o hospedeiro só esvazia a fila de
  transmissão) e 0 as desliga.

O pino de uma GPIO é dirigido pela própria saída do bloco: o programa
configura o pino como saída e o move, e a entrada sincronizada o
acompanha.
"""

import logging
import os
from typing import Any

import cocotb
from cocotb.triggers import First, Timer

LOG = logging.getLogger("cocotb.testbench")
HALF_TCK_NS = 40
SCAN_BITS = 48
PUSH_FLAG = 1 << 8
HOST_BYTE = 0xA5
HOST_STOP = 0
HOST_JTAG_PUSH = 1
HOST_JTAG_DRAIN = 2
IDLE_NS = 1000
STATES = ("cdr", "sdr", "udr", "uir")


async def uart_loopback(dut: Any) -> None:
    """Liga a linha de transmissão da UART pelos pinos à de recepção.

    Parameters
    ----------
    dut : Any
        O topo sob teste.
    """
    dut.i_uart_rx.value = 1
    while True:
        await dut.o_uart_tx.value_change
        dut.i_uart_rx.value = dut.o_uart_tx.value


class JtagHost:
    """O hospedeiro da UART sobre JTAG, que varre a cadeia se pedido."""

    def __init__(self, dut: Any) -> None:
        """Deixa a cadeia parada.

        Parameters
        ----------
        dut : Any
            O topo sob teste.
        """
        self.dut = dut
        self.scanning = False
        self.push_pending = False
        dut.i_uart_tck.value = 0
        dut.i_uart_tdi.value = 0
        dut.i_uart_ir_in.value = 0
        for name in STATES:
            getattr(dut, f"i_uart_state_{name}").value = 0

    def command(self, word: int) -> None:
        """Executa uma palavra que o programa escreveu em fromhost.

        Parameters
        ----------
        word : int
            0 desliga, 1 liga e empurra um byte, 2 liga sem empurrar.
        """
        if word == HOST_STOP:
            self.scanning = False
        elif word in (HOST_JTAG_PUSH, HOST_JTAG_DRAIN):
            self.scanning = True
            self.push_pending = word == HOST_JTAG_PUSH

    async def _tck(self, **states: bool) -> None:
        """Dá um pulso de TCK nos estados dados.

        Parameters
        ----------
        **states : bool
            Os estados da cadeia ligados no pulso.
        """
        for name in STATES:
            getattr(self.dut, f"i_uart_state_{name}").value = int(
                bool(states.get(name))
            )
        self.dut.i_uart_tck.value = 0
        await Timer(HALF_TCK_NS, unit="ns")
        self.dut.i_uart_tck.value = 1
        await Timer(HALF_TCK_NS, unit="ns")
        self.dut.i_uart_tck.value = 0
        for name in STATES:
            getattr(self.dut, f"i_uart_state_{name}").value = 0

    async def _scan(self, command: int) -> None:
        """Captura, desloca 48 bits (do menos significativo) e atualiza.

        Parameters
        ----------
        command : int
            A palavra deslocada para dentro: o flag de push e o byte.
        """
        await self._tck(cdr=True)
        for i in range(SCAN_BITS):
            self.dut.i_uart_tdi.value = (command >> i) & 1
            await Timer(1, unit="ns")
            await self._tck(sdr=True)
        await self._tck(udr=True)

    async def run(self) -> None:
        """Seleciona o registrador de dados e varre enquanto ligado."""
        self.dut.i_uart_ir_in.value = 1
        await self._tck(uir=True)
        while True:
            if not self.scanning:
                await Timer(IDLE_NS, unit="ns")
                continue
            command = 0
            if self.push_pending:
                command = PUSH_FLAG | HOST_BYTE
                self.push_pending = False
            await self._scan(command)


async def trace_interrupts(dut: Any) -> None:
    """Registra cada mudança das linhas do PLIC e do MEIP.

    Só roda com ``SIM_TRACE_IRQ=1``.

    Parameters
    ----------
    dut : Any
        O topo sob teste.
    """
    while True:
        await First(dut.irq_lines.value_change, dut.irq_external.value_change)
        plic = dut.g_interrupts.u_plic
        LOG.info(
            "irq_lines=%s irq_external=%s pending=%s enable=%s "
            "priorities=%s threshold=%s",
            dut.irq_lines.value,
            dut.irq_external.value,
            plic.pending.value,
            plic.enable_reg.value,
            plic.priorities.value,
            plic.threshold.value,
        )


def start(dut: Any) -> JtagHost | None:
    """Inicia os modelos que o topo tem portas para.

    Parameters
    ----------
    dut : Any
        O topo sob teste.

    Returns
    -------
    JtagHost or None
        O hospedeiro JTAG, ou None quando o topo não tem a cadeia.
    """
    if not hasattr(dut, "o_uart_tx"):
        return None
    if os.environ.get("SIM_TRACE_IRQ") and hasattr(dut, "irq_lines"):
        cocotb.start_soon(trace_interrupts(dut))
    cocotb.start_soon(uart_loopback(dut))
    if not hasattr(dut, "i_uart_tck"):
        return None
    host = JtagHost(dut)
    cocotb.start_soon(host.run())
    return host
