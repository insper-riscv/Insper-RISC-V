"""Testbench cocotb da suíte 'sim' da plataforma modular.

Dá o clock em modular_sim_top, solta o reset e observa o barramento de
dados do núcleo até uma escrita na palavra baixa de tohost (a convenção
HTIF de rv32_test.h e de memory.tohost_addr do config.yaml), que traz o
resultado do programa, ou até o tempo se esgotar.

O topo monta a RAM de dois jeitos conforme a arquitetura (ver
modular_sim_top), e o mesmo programa roda nos dois:

- RAM do núcleo (sem cache de dados e sem chip externo): o barramento
  ram_* do topo, escrito quando ram_en e ram_wren estão altos.
- RAM via porta (chip externo ou atrás da cache de dados): o barramento
  externo sdram_*, cuja escrita termina quando sdram_ready e mem_advance
  estão altos na borda do clock do núcleo.

Os dois são vigiados ao mesmo tempo, porque o núcleo só aciona o que
corresponde à região do endereço. Para um teste do tipo "memory"
(GOLDEN_PATH definido, ver sim_runner.run_test) um PASS em tohost também
compara o conteúdo final da RAM, reconstruído de toda escrita vista nos
dois barramentos, com o golden.json.

A plataforma não tem periférico ligado: os programas de UART não rodam
nela.
"""

import logging
import os
from pathlib import Path
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from riscv_tools.mem_validator import compare_bytes, load_golden

import peripheral_models

LOG = logging.getLogger("cocotb.testbench")

TOHOST_ADDR = int(os.environ["TOHOST_ADDR"], 0)
# fromhost fica 8 bytes acima de tohost; o programa pede ao hospedeiro simulado o que fazer.
FROMHOST_ADDR = TOHOST_ADDR + 8
RAM_BASE = int(os.environ.get("RAM_BASE", "0"))
# A última página de 4 KiB da RAM guarda as palavras do hospedeiro,
# então o fim da RAM é o fim da página de tohost.
RAM_END = (TOHOST_ADDR | 0xFFF) + 1
# tohost, palavra baixa: 1 é aprovado, (código << 1) | 1 é falha com
# esse código.
TOHOST_PASS = 1
FULL_WORD = 0xF
_golden_path_env = os.environ.get("GOLDEN_PATH", "")
GOLDEN_PATH = Path(_golden_path_env) if _golden_path_env else None
TEST_NAME = os.environ.get("TEST_NAME", "?")

SIM_CLOCK = os.environ.get("SIM_CLOCK", "i_clk")
SIM_CLOCK_PERIOD_NS = int(os.environ.get("SIM_CLOCK_PERIOD_NS", "10"))
SIM_RESET = os.environ.get("SIM_RESET", "i_rst")
SIM_RESET_ACTIVE = int(os.environ.get("SIM_RESET_ACTIVE", "1"))
SIM_SAMPLE_CLOCK = os.environ.get("SIM_SAMPLE_CLOCK", "pll_clk_idexmem")
TIMEOUT_CYCLES = int(os.environ.get("SIM_TIMEOUT_CYCLES", "2000000"))
# O clock base é dividido por três para os estágios do núcleo.
TICKS_PER_CORE_CYCLE = 3


def check(condition: bool, message: str) -> None:
    """Levanta AssertionError com a mensagem se a condição é falsa."""
    if not condition:
        raise AssertionError(message)


def retired_now(dut: Any) -> int:
    """Devolve 1 se uma instrução é retirada nesta borda, senão 0."""
    try:
        return int(dut.core_retire.value == 1)
    except AttributeError, ValueError:
        return 0


def bus_write(
    dut: Any, enable: str, done: str | None
) -> tuple[int, int, int] | None:
    """Lê a escrita que termina nesta borda de um dos barramentos.

    Parameters
    ----------
    dut : Any
        O topo sob teste.
    enable : str
        Prefixo do barramento, ``ram`` (RAM do núcleo) ou ``sdram``
        (externo).
    done : str or None
        Nome do sinal que marca o fim do acesso, ou None quando a
        escrita vale enquanto os sinais de habilitação estão altos.

    Returns
    -------
    tuple of (int, int, int) or None
        Endereço, dado e habilitação de bytes, ou None quando a borda
        não termina escrita nenhuma.
    """
    if getattr(dut, f"{enable}_wren").value != 1:
        return None
    gate = "ram_en" if enable == "ram" else "mem_advance"
    if getattr(dut, gate).value != 1:
        return None
    if done is not None and getattr(dut, done).value != 1:
        return None
    try:
        address = int(getattr(dut, f"{enable}_addr").value)
        wdata = int(getattr(dut, f"{enable}_wdata").value)
        byteena = int(getattr(dut, f"{enable}_byteena").value)
    except ValueError:
        # Endereço ou dado indefinido: nada a aproveitar.
        return None
    return address, wdata, byteena


class RamImage:
    """Reconstrói o conteúdo da RAM das escritas vistas nos barramentos.

    ``ram_bytes`` leva um endereço de byte relativo à base da RAM ao seu
    valor, atualizado em toda escrita completa, respeitando a
    habilitação de bytes como a própria memória.
    """

    def __init__(self, dut: Any) -> None:
        """Vigia os barramentos de dados do topo dado."""
        self.dut = dut
        self.ram_bytes: dict[int, int] = {}
        self.host: peripheral_models.JtagHost | None = None

    def _record(self, address: int, wdata: int, byteena: int) -> None:
        """Guarda os bytes que a escrita habilita, se caírem na RAM."""
        if not RAM_BASE <= address < RAM_END:
            return
        word_base = address - (address % 4)
        for i in range(4):
            if byteena & (1 << i):
                self.ram_bytes[word_base + i - RAM_BASE] = (
                    wdata >> (8 * i)
                ) & 0xFF

    def tohost_write(self) -> int | None:
        """Registra a escrita desta borda e devolve a de tohost.

        Returns
        -------
        int or None
            A palavra escrita na palavra baixa de tohost, ou None quando
            esta borda não escreve nela.
        """
        for write in (
            bus_write(self.dut, "ram", None),
            bus_write(self.dut, "sdram", "sdram_ready"),
        ):
            if write is None:
                continue
            address, wdata, byteena = write
            self._record(address, wdata, byteena)
            if (
                self.host is not None
                and address // 4 == FROMHOST_ADDR // 4
                and byteena == FULL_WORD
            ):
                self.host.command(wdata)
            is_tohost = address // 4 == TOHOST_ADDR // 4
            if is_tohost and byteena == FULL_WORD and wdata & 1:
                return wdata
        return None


def finish_pass(image: RamImage, core_cycles: int, retired: int) -> None:
    """Confere a RAM contra o golden depois de um PASS em tohost.

    Parameters
    ----------
    image : RamImage
        Conteúdo da RAM reconstruído dos barramentos.
    core_cycles : int
        Ciclos do núcleo até o PASS.
    retired : int
        Instruções retiradas até o PASS.
    """
    cycles_used = core_cycles * TICKS_PER_CORE_CYCLE
    LOG.info("PASS")
    LOG.info("CLOCK CYCLES TAKEN %d", cycles_used)
    LOG.info("CORE CYCLES %d INSTRUCTIONS RETIRED %d", cycles_used, retired)
    if GOLDEN_PATH is None:
        return
    matches = compare_bytes(
        image.ram_bytes,
        load_golden(GOLDEN_PATH),
        actual_label=TEST_NAME,
        golden_label=GOLDEN_PATH.name,
    )
    check(
        matches,
        f"{TEST_NAME}: tohost PASS mas a RAM não bate com "
        f"{GOLDEN_PATH.name}, veja a diferença acima",
    )


@cocotb.test()
async def test_program(dut: Any) -> None:
    """Roda o programa até ele escrever o resultado em tohost."""
    LOG.info("running %s", TEST_NAME)

    clock = getattr(dut, SIM_CLOCK)
    sample_clock = getattr(dut, SIM_SAMPLE_CLOCK)
    cocotb.start_soon(Clock(clock, SIM_CLOCK_PERIOD_NS, unit="ns").start())
    reset = getattr(dut, SIM_RESET)
    reset.value = SIM_RESET_ACTIVE
    await ClockCycles(clock, 5)
    reset.value = 1 - SIM_RESET_ACTIVE

    image = RamImage(dut)
    image.host = peripheral_models.start(dut)
    core_cycles = 0
    retired = 0
    while core_cycles < TIMEOUT_CYCLES:
        await RisingEdge(sample_clock)
        core_cycles += 1
        retired += retired_now(dut)

        tohost = image.tohost_write()
        if tohost is None:
            continue
        if tohost == TOHOST_PASS:
            finish_pass(image, core_cycles, retired)
            return
        message = f"test signalled FAIL via RV32_FAIL(), code {tohost >> 1}"
        raise AssertionError(message)

    message = f"timed out after {TIMEOUT_CYCLES} cycles without a result"
    raise AssertionError(message)
