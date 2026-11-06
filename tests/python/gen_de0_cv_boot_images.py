"""Gera as imagens do teste da escolha de banca da boot ROM da DE0-CV.

Uso, da raiz do repositório, na imagem `dev_tools` (precisa do GCC de
RISC-V e do `riscv-tools`):

    export PYTHONPATH=.
    python tests/python/gen_de0_cv_boot_images.py
    python tests/python/gen_de0_cv_boot_images.py --check

A boot ROM é a `boot_rom.S` de verdade, montada pelo mesmo caminho do
`riscv-tools`. Cada banca recebe uma imagem montada por
`riscv_tools.flash_image.pack` (cabeçalho de 256 bytes e carga), e os
casos estragados mexem nos bytes depois de montada. O programa de cada
banca guarda uma marca na base da RAM, `a0 + 0x55` e `a1 + 0x66` nas
duas palavras seguintes e escreve `tohost`; a marca diz qual banca
rodou.

O arquivo `unittests/rtl/data/de0_cv_boot/images.json` guarda a boot ROM
e, por caso, as palavras de cada banca a partir do índice de palavra
dela na FLASH. O teste escreve a FLASH de cada caso com elas. Com
`--check` o script só confere se o arquivo está em dia com a
`boot_rom.S` e o `pack`.
"""

import argparse
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Any

from riscv_tools import boot_rom, flash_image
from riscv_tools.memory_map import load_platform, symbols

from tests.python.gen_de0_cv_images import load_address
from tests.python.utils.rv32_asm import T0, T1, T2, X0, addi, jal, sw

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "unittests/rtl/data/de0_cv_boot"
IMAGES = DATA / "images.json"
PLATFORM = ROOT / "src/cyclone-v/de0-cv/platform.yaml"
MAP = symbols(load_platform(PLATFORM))
RAM_BASE = MAP["RAM.base"]
TOHOST = MAP["tohost.base"]
BANK = {
    "A": (0x00001000, 124 * 1024),
    "B": (0x00020000, 128 * 1024),
}
WORD = 4
A0, A1 = 10, 11
A0_ADD, A1_ADD = 0x55, 0x66
ERASED = 0xFF
TOOLCHAIN = {
    "gcc": "riscv32-unknown-elf-gcc",
    "objcopy": "riscv32-unknown-elf-objcopy",
}
PATHS = {
    "boot_rom": "src/cyclone-v/de0-cv/runtime/boot_rom.S",
    "boot_rom_linker_script": "src/cyclone-v/de0-cv/runtime/boot_rom.ld",
}
# O espaço de marca: o caso e a banca dizem o que rodou.
MARK_BASE = 0x5C000000
CASE_SHIFT = 8
BANK_SHIFT = 4


def words_of(data: bytes) -> list[int]:
    """Split bytes into little-endian words.

    Parameters
    ----------
    data : bytes
        Bytes, a multiple of four.

    Returns
    -------
    list of int
        The words.
    """
    return [w for (w,) in struct.iter_unpack("<I", data)]


def program(mark: int) -> bytes:
    """Build the program of a bank.

    Parameters
    ----------
    mark : int
        What the program stores at the base of the RAM.

    Returns
    -------
    bytes
        The code: the mark, `a0 + 0x55`, `a1 + 0x66`, then `tohost`.
    """
    code = [
        *load_address(T0, RAM_BASE),
        *load_address(T1, mark),
        sw(T1, T0, 0),
        addi(T2, A0, A0_ADD),
        sw(T2, T0, WORD),
        addi(T2, A1, A1_ADD),
        sw(T2, T0, 2 * WORD),
        *load_address(T0, TOHOST),
        addi(T1, X0, 1),
        sw(T1, T0, 0),
        jal(X0, 0),
    ]
    return b"".join(struct.pack("<I", word) for word in code)


def padded(code: bytes, extra_words: int) -> bytes:
    """Put nops in front of the code.

    Parameters
    ----------
    code : bytes
        The program.
    extra_words : int
        How many `addi x0, x0, 0` come first.

    Returns
    -------
    bytes
        The program with a long run of nops before the stores.
    """
    nop = struct.pack("<I", addi(X0, X0, 0))
    return nop * extra_words + code


def image(bank: str, mark: int, version: int, extra: int = 0) -> bytes:
    """Pack the image of a bank with `flash-image pack`.

    Parameters
    ----------
    bank : str
        `A` or `B`.
    mark : int
        What the program stores.
    version : int
        Version in the header.
    extra : int, optional
        Nops before the program, for a longer payload.

    Returns
    -------
    bytes
        The header page and the payload.
    """
    size = BANK[bank][1]
    return flash_image.pack(padded(program(mark), extra), version, size)


def flip(data: bytes, offset: int) -> bytes:
    """Flip one bit of a byte.

    Parameters
    ----------
    data : bytes
        The image.
    offset : int
        Which byte.

    Returns
    -------
    bytes
        The image with the lowest bit of that byte inverted.
    """
    out = bytearray(data)
    out[offset] ^= 1
    return bytes(out)


def header_with(size: int) -> bytes:
    """Build a header page with a valid CRC and an invalid size.

    Parameters
    ----------
    size : int
        Size field of the header.

    Returns
    -------
    bytes
        The header page, followed by one word of payload.
    """
    body = struct.pack("<4I", flash_image.MAGIC, size, 0, 1)
    fields = body + struct.pack("<I", zlib.crc32(body))
    page = fields.ljust(flash_image.HEADER_SIZE, bytes([ERASED]))
    return page + bytes(WORD)


def mark_of(case: int, bank: str, version: int) -> int:
    """Compute the mark of a bank program.

    Parameters
    ----------
    case : int
        Number of the case.
    bank : str
        `A` or `B`.
    version : int
        Version of the image.

    Returns
    -------
    int
        A word that tells the case, the bank and the version.
    """
    letter = 1 if bank == "A" else 2
    return MARK_BASE | (case << CASE_SHIFT) | (letter << BANK_SHIFT) | version


def cases() -> list[dict[str, Any]]:
    """List the cases: what each bank holds and what must happen.

    Returns
    -------
    list of dict of {str: Any}
        For each case its name, a `banks` dict of bank to image and
        `expect` with the bank that runs (`A`, `B`) or `none`, plus the
        version for the mark.
    """

    def good(case: int, bank: str, version: int, extra: int = 0) -> bytes:
        return image(bank, mark_of(case, bank, version), version, extra)

    erased_page = bytes([ERASED]) * flash_image.HEADER_SIZE
    torn = good(7, "B", 9)
    start = len(erased_page)
    torn = erased_page + torn[start:]
    table: list[tuple[str, dict[str, bytes], str, int]] = [
        ("b-newer", {"A": good(0, "A", 1), "B": good(0, "B", 2)}, "B", 2),
        ("a-newer", {"A": good(1, "A", 3), "B": good(1, "B", 2)}, "A", 3),
        (
            "tie-goes-to-a",
            {"A": good(2, "A", 5), "B": good(2, "B", 5)},
            "A",
            5,
        ),
        ("only-a", {"A": good(3, "A", 1)}, "A", 1),
        ("only-b", {"B": good(4, "B", 1)}, "B", 1),
        (
            "b-payload-corrupt-falls-back-to-a",
            {"A": good(5, "A", 1), "B": flip(good(5, "B", 9), 0x104)},
            "A",
            1,
        ),
        (
            "a-payload-corrupt-falls-back-to-b",
            {"A": flip(good(6, "A", 9), 0x108), "B": good(6, "B", 1)},
            "B",
            1,
        ),
        (
            "interrupted-update-header-erased",
            {
                "A": good(7, "A", 1),
                "B": torn,
            },
            "A",
            1,
        ),
        (
            "header-version-tampered",
            {"A": flip(good(8, "A", 4), 12), "B": good(8, "B", 1)},
            "B",
            1,
        ),
        (
            "header-magic-bad",
            {"A": flip(good(9, "A", 4), 0), "B": good(9, "B", 1)},
            "B",
            1,
        ),
        (
            "size-larger-than-the-bank",
            {"A": header_with(0x7FFFFFFC), "B": good(10, "B", 1)},
            "B",
            1,
        ),
        (
            "size-not-a-whole-number-of-words",
            {"A": header_with(6), "B": good(11, "B", 1)},
            "B",
            1,
        ),
        ("long-payload", {"A": good(12, "A", 1, 200)}, "A", 1),
        (
            "both-corrupt-parks",
            {
                "A": flip(good(13, "A", 1), 0x104),
                "B": flip(good(13, "B", 2), 0x104),
            },
            "none",
            0,
        ),
        ("empty-flash-parks", {}, "none", 0),
    ]
    return [
        {"name": name, "banks": banks, "expect": expect, "version": version}
        for name, banks, expect, version in table
    ]


def build() -> dict[str, Any]:
    """Build the whole content of images.json.

    Returns
    -------
    dict of {str: Any}
        The boot ROM words and, for each case, the words of each bank
        by word index of the FLASH and the expected outcome.
    """
    with tempfile.TemporaryDirectory() as directory:
        hex_path = boot_rom.build_boot_rom(
            TOOLCHAIN, PATHS, ROOT, Path(directory)
        )
        rom_words = [int(line, 16) for line in hex_path.read_text().split()]
    out_cases: list[dict[str, Any]] = []
    for number, case in enumerate(cases()):
        banks = {
            bank: {"index": BANK[bank][0] // WORD, "words": words_of(data)}
            for bank, data in case["banks"].items()
        }
        expect = case["expect"]
        mark = 0
        if expect != "none":
            mark = mark_of(number, expect, case["version"])
        out_cases.append(
            {
                "name": case["name"],
                "banks": banks,
                "expect": expect,
                "mark": mark,
            }
        )
    return {"boot_rom": rom_words, "cases": out_cases}


def render(content: dict[str, Any]) -> str:
    """Format the file.

    Parameters
    ----------
    content : dict of {str: Any}
        What `build` returned.

    Returns
    -------
    str
        The JSON text, one bank image per line.
    """
    return json.dumps(content, separators=(",", ":")) + "\n"


def main() -> None:
    """Write images.json, or compare it with `--check`."""
    parser = argparse.ArgumentParser(description="Escreve images.json")
    parser.add_argument("--check", action="store_true")
    text = render(build())
    if parser.parse_args().check:
        if not IMAGES.exists() or IMAGES.read_text() != text:
            print(f"{IMAGES} is out of date: run the generator")
            sys.exit(1)
        print("images.json is up to date")
        return
    DATA.mkdir(parents=True, exist_ok=True)
    IMAGES.write_text(text)
    print(f"wrote {IMAGES}")


if __name__ == "__main__":
    main()
