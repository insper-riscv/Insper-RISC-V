"""A boot ROM da DE0-CV escolhe a banca da FLASH pelo cabeçalho.

O topo de simulação roda a `boot_rom.S` de verdade, cujas palavras estão
em `data/de0_cv_boot/images.json`, geradas por
`gen_de0_cv_boot_images.py`. Cada caso do arquivo é uma simulação:
`cases` escreve a imagem da BOOT_ROM e a da FLASH do caso, com as duas
bancas montadas pelo `riscv-tools flash-image pack` e estragadas como o
caso pede (uma banca mais nova, uma carga corrompida, uma atualização
interrompida com o cabeçalho apagado, as duas inválidas), e o runner as
passa como genéricos do topo. O programa da banca que roda guarda uma
marca na SDRAM, `a0 + 0x55` e `a1 + 0x66`; o teste confere a marca, os
registradores de entrada e, quando nenhuma banca vale, que o núcleo
fica parado no `rv32_wait_restart` sem rodar nada.
"""

import json
import os
from pathlib import Path
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles

from tests.python.unittests.rtl.de0_cv_sim_top import (
    CLK_MEM_NS,
    CLK_NS,
    TOHOST_WORD,
    sdram_word,
)
from tests.python.utils.checks import check

IMAGES = Path(__file__).parent / "data/de0_cv_boot/images.json"
POLL_CYCLES = 2000
TIMEOUT_CYCLES = 3_000_000
SETTLE_CYCLES = 4000
PARK_CYCLES = 150_000
PARK_SAMPLES = 8
WAIT_RESTART = 0x100
WAIT_RESTART_END = 0x114
A0_WORD, A1_WORD = 1, 2
A0_SEEN, A1_SEEN = 0x55, 0x66
RESET_CYCLES = 5


def cases(build_dir: Path) -> list[dict[str, Any]]:
    """Write the ROM images of every case and list the simulations.

    Parameters
    ----------
    build_dir : Path
        Where the images are written.

    Returns
    -------
    list of dict of {str: Any}
        One simulation per case: its name, the image files as generics
        and the case in the environment.
    """
    content = json.loads(IMAGES.read_text())
    boot_path = build_dir / "boot_rom.hex"
    boot_path.write_text(hex_text(content["boot_rom"]))
    runs: list[dict[str, Any]] = []
    for case in content["cases"]:
        words: list[int] = []
        for bank in case["banks"].values():
            words += [0] * (bank["index"] - len(words))
            words += bank["words"]
        flash_path = build_dir / f"flash-{case['name']}.hex"
        flash_path.write_text(hex_text(words or [0]))
        runs.append(
            {
                "name": case["name"],
                "parameters": {
                    "BOOT_ROM_FILE": str(boot_path),
                    "ROM_FILE": str(flash_path),
                },
                "env": {"BOOT_CASE": case["name"]},
                "wave": False,
            }
        )
    return runs


def hex_text(words: list[int]) -> str:
    """Format words as an image file, one hexadecimal word per line.

    Parameters
    ----------
    words : list of int
        The words.

    Returns
    -------
    str
        The text of the file.
    """
    return "".join(f"{word:08X}\n" for word in words)


async def wait_for_tohost(dut: Any) -> bool:
    """Wait for the program to write tohost.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    bool
        True when tohost became nonzero before the timeout.
    """
    waited = 0
    while waited < TIMEOUT_CYCLES:
        await ClockCycles(dut.CLK, POLL_CYCLES)
        waited += POLL_CYCLES
        if await sdram_word(dut, TOHOST_WORD) != 0:
            return True
    return False


async def check_parked(dut: Any, name: str) -> None:
    """Check that no bank ran and the core waits in rv32_wait_restart.

    Parameters
    ----------
    dut : Any
        The device under test.
    name : str
        The case, for the messages.
    """
    await ClockCycles(dut.CLK, PARK_CYCLES)
    for _ in range(PARK_SAMPLES):
        await ClockCycles(dut.CLK, 7)
        address = int(dut.if_addr.value)
        check(
            WAIT_RESTART <= address < WAIT_RESTART_END,
            f"{name}: the core is at {address:#x}, not in rv32_wait_restart",
        )
    check(
        await sdram_word(dut, TOHOST_WORD) == 0, f"{name}: tohost was written"
    )
    mark = await sdram_word(dut, 0)
    check(mark == 0, f"{name}: a program stored the mark {mark:#x}")


@cocotb.test()
async def test_the_boot_rom_chooses_the_bank(dut: Any) -> None:
    """The case of the environment boots the bank the policy says."""
    name = os.environ["BOOT_CASE"]
    case = next(
        c for c in json.loads(IMAGES.read_text())["cases"] if c["name"] == name
    )
    cocotb.start_soon(Clock(dut.CLK, CLK_NS, unit="ns").start())
    cocotb.start_soon(Clock(dut.CLK_MEM, CLK_MEM_NS, unit="ns").start())
    dut.reset.value = 1
    dut.DBG_WORD_ADDR.value = 0
    await ClockCycles(dut.CLK, RESET_CYCLES)
    dut.reset.value = 0
    await ClockCycles(dut.CLK, SETTLE_CYCLES)
    if case["expect"] == "none":
        await check_parked(dut, name)
        return
    check(await wait_for_tohost(dut), f"{name}: no program wrote tohost")
    mark = await sdram_word(dut, 0)
    check(
        mark == case["mark"],
        f"{name}: mark {mark:#x}, want {case['mark']:#x} "
        f"(bank {case['expect']})",
    )
    a0 = await sdram_word(dut, A0_WORD)
    a1 = await sdram_word(dut, A1_WORD)
    check(a0 == A0_SEEN, f"{name}: a0 + 0x55 is {a0:#x}, a0 was not 0")
    check(a1 == A1_SEEN, f"{name}: a1 + 0x66 is {a1:#x}, a1 was not 0")
