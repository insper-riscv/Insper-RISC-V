"""Gera as imagens dos testes do topo de simulação da plataforma doom.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    python tests/python/gen_doom_images.py
    python tests/python/gen_doom_images.py --check

A BOOT_MEMORY é a `boot_memory.S` de verdade, montada pelo mesmo caminho
do `riscv-tools`: ela salta para a FLASH, em `boot.entry`. A FLASH e a
RAM estão no mesmo chip de SDRAM, e a imagem de cada teste é a do chip
inteiro, uma palavra por linha desde a palavra 0: o programa de teste
começa na base da FLASH (`FLASH_CHIP_OFFSET` dentro do chip) e a RAM
começa em `RAM_CHIP_OFFSET`. Na placa a FLASH fica no fim do chip e a
RAM no começo; o teste aproxima as duas (generics do topo
`flash_chip_offset_bytes` e `ram_chip_offset_bytes`) para a imagem ser
pequena.

O programa de `sdram_go.hex` guarda uma marca na RAM e escreve `tohost`;
os de `sdram_video.hex` e `sdram_kbd.hex` desenham um quadro e leem o
teclado.

Os arquivos ficam em tests/python/unittests/rtl/data/doom/. Com
`--check` o script só confere se estão em dia.
"""

import argparse
import sys
import tempfile
from pathlib import Path

from riscv_tools import boot_memory
from riscv_tools.memory_map import load_platform, symbols

from tests.python.gen_de0_cv_images import load_address
from tests.python.utils import doom_frame as frame
from tests.python.utils.rv32_asm import (
    A0,
    T0,
    T1,
    T2,
    T3,
    T4,
    X0,
    addi,
    andi,
    beq,
    hex_lines,
    jal,
    lw,
    sw,
)

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "unittests/rtl/data/doom"
PLATFORM = ROOT / "src/cyclone-v/doom/platform.yaml"
MAP = symbols(load_platform(PLATFORM))
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
WORD = 4
# Onde a FLASH e a RAM ficam dentro do chip no teste (os generics do
# topo): a FLASH na identidade do endereço do SoC e a RAM logo acima do
# espaço do programa, para a imagem do chip ficar pequena.
FLASH_CHIP_OFFSET = 0x1000
RAM_CHIP_OFFSET = 0x10000
# Período do clock da SDRAM do teste, em nanossegundos: o `clocks.mem`
# do platform.yaml (125 MHz), que o topo usa nos tempos de refresh.
CLK_MEM_NS = 8
# A marca que o programa de teste guarda e onde, na RAM.
MARK = 0xD00D
MARK_OFFSET = 0x100
TOOLCHAIN = {
    "gcc": "riscv32-unknown-elf-gcc",
    "objcopy": "riscv32-unknown-elf-objcopy",
}
PATHS = {
    "boot_memory": "src/cyclone-v/doom/runtime/boot_memory.S",
    "boot_memory_linker_script": "src/cyclone-v/doom/runtime/boot_memory.ld",
}
FILES = (
    "boot_memory.hex",
    "sdram_go.hex",
    "sdram_video.hex",
    "sdram_kbd.hex",
)
RESULT_OFFSET = frame.RESULT_OFFSET
VIDEO_BASE = MAP["VIDEO.base"]
KBD_BASE = MAP["KBD.base"]
PLIC_BASE = MAP["PLIC.base"]
# A fonte do teclado no PLIC: a primeira livre depois das fixas
# (`IRQ_KBD` do doom_map_pkg).
KBD_LINE = 5
# O desvio do laço de espera do teclado: volta à leitura do estado, duas
# instruções atrás do `beq`.
WAIT_BACK = -2 * WORD


def ram_word(address: int) -> int:
    """Return the index of the chip word that holds a RAM address.

    Parameters
    ----------
    address : int
        A byte address of the RAM in the map of the SoC.

    Returns
    -------
    int
        The index of the 32-bit word in the SDRAM chip.
    """
    return (RAM_CHIP_OFFSET + address - RAM_BASE) // WORD


def sdram_program() -> list[int]:
    """Build the program that marks the RAM and stops on `tohost`.

    Returns
    -------
    list of int
        The code: the mark at `RAM_BASE + MARK_OFFSET`, then `tohost`.
    """
    return [
        *load_address(T0, RAM_BASE + MARK_OFFSET),
        *load_address(T1, MARK),
        sw(T1, T0, 0),
        *load_address(T0, TOHOST),
        addi(T1, X0, 1),
        sw(T1, T0, 0),
        jal(X0, 0),
    ]


def finish() -> list[int]:
    """Build the end of a test program: write `tohost` and spin.

    Returns
    -------
    list of int
        The instructions.
    """
    return [
        *load_address(T0, TOHOST),
        addi(T1, X0, 1),
        sw(T1, T0, 0),
        jal(X0, 0),
    ]


def store_word(value: int, base: int, offset: int) -> list[int]:
    """Build the instructions that store a constant at `base + offset`.

    Parameters
    ----------
    value : int
        The 32-bit constant.
    base : int
        The register that holds the base address.
    offset : int
        The byte offset, within the range of an immediate.

    Returns
    -------
    list of int
        The instructions, using T1 for the constant.
    """
    return [*load_address(T1, value), sw(T1, base, offset)]


def video_program() -> list[int]:
    """Build the program that draws the test frame.

    The program reads the geometry and the format of the video, writes
    the palette and the framebuffer, turns the display on and stops on
    `tohost`.

    Returns
    -------
    list of int
        The code.
    """
    result = RAM_BASE + RESULT_OFFSET
    code = [
        *load_address(T0, VIDEO_BASE),
        *load_address(T2, result),
        lw(T1, T0, frame.VIDEO_GEOMETRY),
        sw(T1, T2, 0),
        lw(T1, T0, frame.VIDEO_FORMAT),
        sw(T1, T2, WORD),
    ]
    for index, color in enumerate(frame.PALETTE):
        code += store_word(color, T0, frame.VIDEO_PALETTE + WORD * index)
    code += load_address(T3, VIDEO_BASE + frame.VIDEO_FRAMEBUFFER)
    for index, word in enumerate(frame.framebuffer_words()):
        code += store_word(word, T3, WORD * index)
    code += [addi(T1, X0, 1), sw(T1, T0, frame.VIDEO_CONTROL)]
    return code + finish()


def wait_valid(base: int) -> list[int]:
    """Build the wait for a byte in the queue of the keyboard.

    Parameters
    ----------
    base : int
        The register that holds the base of the keyboard.

    Returns
    -------
    list of int
        The instructions: read the state until `RX_VALID` is set.
    """
    return [
        lw(T1, base, frame.KBD_STATUS),
        andi(T1, T1, frame.KBD_RX_VALID),
        beq(T1, X0, WAIT_BACK),
    ]


def kbd_program() -> list[int]:
    """Build the program that reads the keyboard.

    The program enables the line of the keyboard in the PLIC and the
    interrupt of the keyboard, claims the line with the first byte in
    the queue, and stores each scancode it reads, one word per byte,
    after the claim.

    Returns
    -------
    list of int
        The code.
    """
    result = RAM_BASE + RESULT_OFFSET
    code = [
        *load_address(T0, KBD_BASE),
        *load_address(T2, result),
        *load_address(T3, PLIC_BASE),
        *load_address(T4, PLIC_BASE + frame.PLIC_THRESHOLD),
        *load_address(A0, PLIC_BASE + frame.PLIC_ENABLE),
        *store_word(1, T3, frame.PLIC_PRIORITY_KBD),
        *load_address(T1, 1 << KBD_LINE),
        sw(T1, A0, 0),
        sw(X0, T4, 0),
        addi(T1, X0, frame.KBD_RX_IRQ_ENABLE),
        sw(T1, T0, frame.KBD_CONTROL),
        *store_word(1, T2, frame.READY_OFFSET - frame.RESULT_OFFSET),
        *wait_valid(T0),
        lw(T1, T4, WORD),
        sw(T1, T2, 0),
    ]
    for number in range(len(frame.SCANCODES)):
        code += wait_valid(T0)
        code += [lw(T1, T0, frame.KBD_DATA), sw(T1, T2, WORD * (1 + number))]
    return code + finish()


def chip_image(program: list[int]) -> list[int]:
    """Lay out the chip image of a test: the program at the FLASH.

    Parameters
    ----------
    program : list of int
        The code, which starts at the base of the FLASH.

    Returns
    -------
    list of int
        The words of the chip from the word 0 up to the end of the
        program.

    Raises
    ------
    ValueError
        If the program runs into the RAM in the chip.
    """
    words = [0] * (FLASH_CHIP_OFFSET // WORD) + program
    if len(words) * WORD > RAM_CHIP_OFFSET:
        message = f"the program of {len(program)} words reaches the RAM"
        raise ValueError(message)
    return words


def build() -> dict[str, str]:
    """Build the text of every image file.

    Returns
    -------
    dict of {str: str}
        File name to its text.
    """
    with tempfile.TemporaryDirectory() as name:
        hex_path = boot_memory.build_boot_memory(
            TOOLCHAIN, PATHS, ROOT, Path(name) / "boot"
        )
        boot = hex_path.read_text()
    return {
        "boot_memory.hex": boot,
        "sdram_go.hex": hex_lines(chip_image(sdram_program())),
        "sdram_video.hex": hex_lines(chip_image(video_program())),
        "sdram_kbd.hex": hex_lines(chip_image(kbd_program())),
    }


def main() -> None:
    """Write the images, or compare them with `--check`."""
    parser = argparse.ArgumentParser(description="Escreve as imagens")
    parser.add_argument("--check", action="store_true")
    texts = build()
    if parser.parse_args().check:
        stale = [
            n
            for n in FILES
            if not (DATA / n).exists() or (DATA / n).read_text() != texts[n]
        ]
        if stale:
            print(f"out of date: {', '.join(stale)}: run the generator")
            sys.exit(1)
        print("the doom images are up to date")
        return
    DATA.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (DATA / name).write_text(text)
        print(f"wrote {DATA / name}")


if __name__ == "__main__":
    main()
