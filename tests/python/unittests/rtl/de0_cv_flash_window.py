"""A FLASH da DE0-CV é lida inteira, e não só no primeiro 1 MiB.

O roteador de região devolvia zero para a leitura a partir de 1 MiB da
base da FLASH enquanto o SoC não lhe passava a janela da FLASH. O
programa do teste lê palavras da FLASH a 2 MiB e a 8 MiB do começo do
chip e as guarda na RAM. As imagens são escritas por `cases`, porque
têm milhões de palavras, e o topo é o mesmo de `De0CvSimTop`.
"""

from pathlib import Path
from typing import Any

import cocotb

from tests.python.gen_de0_cv_images import (
    FLASH_BASE,
    RAM_BASE,
    TOHOST,
    WORD,
    load_address,
    store_value,
)
from tests.python.unittests.rtl.de0_cv_sim_top import (
    ram_word,
    sdram_word,
    start,
    wait_for_tohost,
)
from tests.python.utils.checks import check
from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    X0,
    hex_lines,
    jal,
    lw,
    sw,
)

BOOT_HEX = Path(__file__).parent / "data/de0_cv/boot_memory.hex"
MIB = 1 << 20
# Onde o programa lê as palavras, no chip (a FLASH vem primeiro).
OFFSETS = {"2MiB": 2 * MIB, "8MiB": 8 * MIB}
MARKS = {"2MiB": 0xA1B2C3D4, "8MiB": 0x0DDBA11F}
WORD_OF = {"2MiB": 8, "8MiB": 9}


def program() -> list[int]:
    """Return the program that copies the far words to the RAM.

    Returns
    -------
    list of int
        For each far word a load from the FLASH and a store in the RAM,
        then `tohost`.
    """
    words: list[int] = []
    for name, offset in OFFSETS.items():
        words += [
            *load_address(T0, offset),
            lw(T1, T0, 0),
            *load_address(T2, RAM_BASE + WORD * WORD_OF[name]),
            sw(T1, T2, 0),
        ]
    words += [*store_value(TOHOST, 1), jal(X0, 0)]
    return words


def cases(build_dir: Path) -> list[dict[str, Any]]:
    """Write the chip image and list the simulation.

    Parameters
    ----------
    build_dir : Path
        Where the image is written.

    Returns
    -------
    list of dict of {str: Any}
        The one simulation, with the image files as generics.
    """
    image = [0] * (max(OFFSETS.values()) // WORD + 1)
    code = program()
    start = FLASH_BASE // WORD
    end = start + len(code)
    image[start:end] = code
    for name, offset in OFFSETS.items():
        image[offset // WORD] = MARKS[name]
    path = build_dir / "sdram-window.hex"
    path.write_text(hex_lines(image))
    return [
        {
            "name": "far-words",
            "parameters": {
                "BOOT_MEMORY_FILE": str(BOOT_HEX),
                "SDRAM_FILE": str(path),
            },
            "env": {},
            "wave": False,
        }
    ]


@cocotb.test()
async def test_the_flash_is_read_above_one_mebibyte(dut: Any) -> None:
    """The words at 2 MiB and 8 MiB reach the RAM, not zero."""
    await start(dut)
    await wait_for_tohost(dut)
    for name, mark in MARKS.items():
        index = ram_word(RAM_BASE + WORD * WORD_OF[name])
        got = await sdram_word(dut, index)
        check(got == mark, f"{name}: read {got:#x}, want {mark:#x}")
