"""Gera as imagens dos programas dos testes do topo modular.

Uso, da raiz do repositório:

    PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python \
        tests/python/gen_modular_images.py

O `riscv-tools` vem da imagem `ci-vhdl`, não das dependências do
projeto, e o mapa é o de `src/simulation/modular/platform.yaml`.

O programa guarda 0x5A na base da RAM, lê de volta, soma 1 e guarda o
resultado na palavra seguinte. A BOOT_MEMORY salta para a ROM, que começa
logo depois dela, e os quatro modelos usam as mesmas duas imagens, em
tests/python/unittests/rtl/data/modular/.
"""

from pathlib import Path

from riscv_tools.memory_map import load_platform, symbols

from tests.python.utils.rv32_asm import (
    T0,
    T1,
    T2,
    T3,
    T4,
    X0,
    addi,
    andi,
    beq,
    csrrs,
    hex_lines,
    jal,
    lui,
    lw,
    sw,
)

DATA = Path(__file__).resolve().parent / "unittests/rtl/data/modular"
ROOT = Path(__file__).resolve().parents[2]
MAP = symbols(load_platform(ROOT / "src/simulation/modular/platform.yaml"))
ROM_BASE = MAP["ROM.base"]  # a ROM começa logo depois da BOOT_MEMORY
RAM_BASE = MAP["RAM.base"]
ROM_BASE_WORDS = ROM_BASE // 4
RAM_HI20 = RAM_BASE >> 12
FIRST = 0x5A
CLINT_BASE = MAP["CLINT.base"]
MTIMECMP = CLINT_BASE + 0x4000  # mtimecmp do CLINT (metade baixa)
MTIME = CLINT_BASE + 0xBFF8  # mtime do CLINT (metade baixa)
CSR_MIP = 0x344
MTIP = 0x80  # bit 7 do mip
IRQ_DELAY = 40  # ciclos do mtime até o MTIP


def body(base_hi20: int, base_low: int) -> list[int]:
    """Return the program that stores 0x5A, reads it and stores 0x5B.

    Parameters
    ----------
    base_hi20 : int
        Upper 20 bits of the data base address.
    base_low : int
        Lower 12 bits of the data base address (0 for none).

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    words = [lui(T0, base_hi20)]
    if base_low:
        words.append(addi(T0, T0, base_low))
    words += [
        addi(T1, X0, FIRST),
        sw(T1, T0, 0),
        lw(T2, T0, 0),
        addi(T2, T2, 1),
        sw(T2, T0, 4),
        jal(X0, 0),
    ]
    return words


def irq_body(base_hi20: int) -> list[int]:
    """Return the program that raises MTIP in the CLINT, reading mip.

    The mtimecmp of the CLINT is not cleared by the reset of this top
    (its clear is synchronous and the clocks stop in reset), so the
    program first writes the largest value to it and reads mip at RAM+8
    (MTIP low). Then it arms mtimecmp to IRQ_DELAY ticks after the
    current mtime, polls mip until MTIP shows up and stores the masked
    bit at RAM+0 and 0x5B at RAM+4.

    Parameters
    ----------
    base_hi20 : int
        Upper 20 bits of the data base address.

    Returns
    -------
    list of int
        The instructions, ending in a loop on itself.
    """
    nop = addi(X0, X0, 0)
    return [
        lui(T0, MTIMECMP >> 12),
        lui(T4, base_hi20),
        lui(T1, (MTIME + 0x800) >> 12),
        addi(T2, X0, -1),
        sw(T2, T0, 0),
        sw(T2, T0, 4),
        nop,
        nop,
        nop,
        nop,
        csrrs(T3, CSR_MIP, X0),
        sw(T3, T4, 8),
        lw(T2, T1, MTIME - (((MTIME + 0x800) >> 12) << 12)),
        addi(T2, T2, IRQ_DELAY),
        sw(X0, T0, 4),
        sw(T2, T0, 0),
        csrrs(T3, CSR_MIP, X0),
        andi(T3, T3, MTIP),
        beq(T3, X0, -8),
        sw(T3, T4, 0),
        addi(T1, X0, FIRST + 1),
        sw(T1, T4, 4),
        jal(X0, 0),
    ]


def write(name: str, words: list[int]) -> None:
    """Write one image.

    Parameters
    ----------
    name : str
        File name inside the data folder.
    words : list of int
        The words of the image.
    """
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(hex_lines(words))


def main() -> None:
    """Write every image.

    The four models run the same two images, because the ROM always
    starts right after the BOOT_MEMORY and the RAM has the same address.
    """
    write("boot_to_rom.hex", [jal(X0, ROM_BASE_WORDS * 4)])
    write("rom_program.hex", [0] * ROM_BASE_WORDS + body(RAM_HI20, 0))
    write("rom_irq_program.hex", [0] * ROM_BASE_WORDS + irq_body(RAM_HI20))


if __name__ == "__main__":
    main()
