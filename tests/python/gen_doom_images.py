"""Gera as imagens do teste do carregador da SDRAM da plataforma doom.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    python tests/python/gen_doom_images.py
    python tests/python/gen_doom_images.py --check

A BOOT_MEMORY é a `boot_memory.S` de verdade, montada pelo mesmo caminho
do `riscv-tools`. A banca A da FLASH recebe o `doom_loader.S` de
verdade, ligado em `base + 0x100` e empacotado por `flash_image.pack`.
A única diferença para a placa é o endereço da campainha (`launch`):
na placa ele fica na última página da RAM, que a cache de dados ignora,
e aqui fica em `RAM_BASE + LAUNCH_OFFSET`, porque a imagem da SDRAM
do simulador é linear a partir da base e a última página fica a
64 MiB dela.

A imagem da SDRAM é um programa de teste na base da RAM que guarda uma
marca e escreve `tohost`. Em `sdram_go.hex` a campainha já traz a magia
(o hospedeiro terminou de carregar); em `sdram_wait.hex` não traz, e o
carregador tem de esperar.

Os arquivos ficam em tests/python/unittests/rtl/data/doom/. Com
`--check` o script só confere se estão em dia.
"""

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from riscv_tools import boot_memory, flash_image
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
RUNTIME = ROOT / "src/cyclone-v/doom/runtime"
MAP = symbols(load_platform(PLATFORM))
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
# A banca A é a primeira da FLASH, e a FLASH começa na base dela.
BANK_A_BASE = MAP["FLASH.base"]
BANK_A_SIZE = MAP["FLASH.size"] // 2
BANK_A_ENTRY = BANK_A_BASE + flash_image.HEADER_SIZE
WORD = 4
# A campainha do teste: na primeira página da RAM, depois do código.
LAUNCH_OFFSET = 0x800
# A magia que o hospedeiro escreve (a mesma do doom_loader.S: "DOOM").
LAUNCH_MAGIC = 0x4D4F4F44
# A marca que o programa da SDRAM guarda e onde.
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
    "flash.hex",
    "sdram_go.hex",
    "sdram_wait.hex",
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


def loader_payload(directory: Path) -> bytes:
    """Assemble and link the loader for the entry of bank A.

    Parameters
    ----------
    directory : Path
        Scratch folder for the ELF and the flat binary.

    Returns
    -------
    bytes
        The payload of bank A, with the doorbell of the test.
    """
    elf = directory / "doom_loader.elf"
    binary = directory / "doom_loader.bin"
    launch = RAM_BASE + LAUNCH_OFFSET
    script = directory / "doom_loader.ld"
    script.write_text(
        f"ENTRY(_start)\nSECTIONS {{ . = {BANK_A_ENTRY:#x}; "
        ".text : { *(.text.loader) *(.text*) } }\n"
    )
    subprocess.run(  # noqa: S603
        [
            TOOLCHAIN["gcc"],
            "-march=rv32i_zifencei",
            "-mabi=ilp32",
            "-nostdlib",
            "-nostartfiles",
            f"-DDOOM_LAUNCH_ADDR={launch:#x}",
            f"-I{RUNTIME}",
            "-T",
            str(script),
            str(RUNTIME / "doom_loader.S"),
            "-o",
            str(elf),
        ],
        check=True,
    )
    subprocess.run(  # noqa: S603
        [TOOLCHAIN["objcopy"], "-O", "binary", str(elf), str(binary)],
        check=True,
    )
    return binary.read_bytes()


def words_of(data: bytes) -> list[int]:
    """Split bytes into little-endian words, padding the last one.

    Parameters
    ----------
    data : bytes
        The bytes.

    Returns
    -------
    list of int
        The words.
    """
    padded = data + bytes(-len(data) % WORD)
    return [w for (w,) in struct.iter_unpack("<I", padded)]


def sdram_program() -> list[int]:
    """Build the program the loader must reach at the base of the RAM.

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


def sdram_image(
    with_magic: bool, program: list[int] | None = None
) -> list[int]:
    """Lay out the SDRAM image of the test.

    Parameters
    ----------
    with_magic : bool
        Whether the doorbell already holds the magic.
    program : list of int or None
        The code at the base of the RAM; the mark program when None.

    Returns
    -------
    list of int
        The words from the base of the RAM up to the doorbell.

    Raises
    ------
    ValueError
        If the code runs into the words the results are stored in.
    """
    words = [0] * (LAUNCH_OFFSET // WORD + 1)
    program = sdram_program() if program is None else program
    if len(program) * WORD > RESULT_OFFSET:
        message = f"the program of {len(program)} words reaches the results"
        raise ValueError(message)
    words[: len(program)] = program
    if with_magic:
        words[LAUNCH_OFFSET // WORD] = LAUNCH_MAGIC
    return words


def build() -> dict[str, str]:
    """Build the text of every image file.

    Returns
    -------
    dict of {str: str}
        File name to its text.
    """
    with tempfile.TemporaryDirectory() as name:
        directory = Path(name)
        hex_path = boot_memory.build_boot_memory(
            TOOLCHAIN, PATHS, ROOT, directory / "boot"
        )
        boot = hex_path.read_text()
        payload = loader_payload(directory)
    image = flash_image.pack(payload, 1, BANK_A_SIZE)
    flash = [0] * (BANK_A_BASE // WORD) + words_of(image)
    return {
        "boot_memory.hex": boot,
        "flash.hex": hex_lines(flash),
        "sdram_go.hex": hex_lines(sdram_image(True)),
        "sdram_wait.hex": hex_lines(sdram_image(False)),
        "sdram_video.hex": hex_lines(sdram_image(True, video_program())),
        "sdram_kbd.hex": hex_lines(sdram_image(True, kbd_program())),
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
