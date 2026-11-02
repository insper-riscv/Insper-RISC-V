"""Montador mínimo de RV32I para os programas dos testes do topo."""

X0 = 0
T0 = 5
T1 = 6
T2 = 7


def lui(rd: int, imm20: int) -> int:
    """Encode ``lui rd, imm20``.

    Parameters
    ----------
    rd : int
        Destination register.
    imm20 : int
        The 20 bits that go to bits 31:12.

    Returns
    -------
    int
        The 32-bit instruction.
    """
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0x37


def addi(rd: int, rs1: int, imm12: int) -> int:
    """Encode ``addi rd, rs1, imm12``.

    Parameters
    ----------
    rd : int
        Destination register.
    rs1 : int
        Source register.
    imm12 : int
        Signed 12-bit immediate.

    Returns
    -------
    int
        The 32-bit instruction.
    """
    return ((imm12 & 0xFFF) << 20) | (rs1 << 15) | (rd << 7) | 0x13


def lw(rd: int, rs1: int, imm12: int) -> int:
    """Encode ``lw rd, imm12(rs1)``.

    Parameters
    ----------
    rd : int
        Destination register.
    rs1 : int
        Base register.
    imm12 : int
        Signed 12-bit offset.

    Returns
    -------
    int
        The 32-bit instruction.
    """
    return ((imm12 & 0xFFF) << 20) | (rs1 << 15) | (2 << 12) | (rd << 7) | 0x03


def sw(rs2: int, rs1: int, imm12: int) -> int:
    """Encode ``sw rs2, imm12(rs1)``.

    Parameters
    ----------
    rs2 : int
        Register that is stored.
    rs1 : int
        Base register.
    imm12 : int
        Signed 12-bit offset.

    Returns
    -------
    int
        The 32-bit instruction.
    """
    high = (imm12 >> 5) & 0x7F
    low = imm12 & 0x1F
    return (
        (high << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (2 << 12)
        | (low << 7)
        | 0x23
    )


def jal(rd: int, offset: int) -> int:
    """Encode ``jal rd, offset``.

    Parameters
    ----------
    rd : int
        Link register.
    offset : int
        Signed byte offset, even, within 1 MiB.

    Returns
    -------
    int
        The 32-bit instruction.
    """
    bit20 = (offset >> 20) & 1
    bits10_1 = (offset >> 1) & 0x3FF
    bit11 = (offset >> 11) & 1
    bits19_12 = (offset >> 12) & 0xFF
    imm = (bit20 << 19) | (bits10_1 << 9) | (bit11 << 8) | bits19_12
    return (imm << 12) | (rd << 7) | 0x6F


def jalr(rd: int, rs1: int, imm12: int) -> int:
    """Encode ``jalr rd, rs1, imm12``.

    Parameters
    ----------
    rd : int
        Link register.
    rs1 : int
        Base register.
    imm12 : int
        Signed 12-bit offset.

    Returns
    -------
    int
        The 32-bit instruction.
    """
    return ((imm12 & 0xFFF) << 20) | (rs1 << 15) | (rd << 7) | 0x67


def hex_lines(words: list[int]) -> str:
    """Format words as the image files: one hexadecimal word per line.

    Parameters
    ----------
    words : list of int
        The 32-bit words of the image.

    Returns
    -------
    str
        The text of the file, ending in a newline.
    """
    return "".join(f"{word & 0xFFFFFFFF:08X}\n" for word in words)
