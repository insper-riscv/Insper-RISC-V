"""O vídeo da plataforma doom: o núcleo desenha um quadro de teste.

O programa da SDRAM (`gen_doom_images.py`, `sdram_video.hex`) lê a
geometria e o formato do vídeo, escreve a paleta e o framebuffer pelo
barramento de periféricos, liga a exibição e escreve `tohost`. O teste
espera o `tohost`, confere o que o núcleo leu dos registradores e
captura um quadro inteiro da saída VGA, que compara com o modelo de
`doom_frame.py` pixel a pixel, junto com os dois sincronismos. O modo é
pequeno (40x20) para o quadro durar pouco, mas tem a estrutura do
640x480: área visível, pórticos e sincronismos negativos.
"""

from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge

from tests.python.unittests.rtl.sdram_sim_common import (
    sdram_word,
    start,
    wait_for_tohost,
)
from tests.python.utils import doom_frame as frame
from tests.python.utils.checks import check

RESULT_WORD = frame.RESULT_OFFSET // frame.WORD
# A linha em que o pulso de sincronismo vertical começa: a referência da
# captura, que marca a coluna 0 dessa linha.
VS_BEGIN = frame.V_VISIBLE + frame.V_FRONT
HS_BEGIN = frame.H_VISIBLE + frame.H_FRONT
Color = tuple[int, int, int]


def pins(dut: Any) -> tuple[Color, int, int]:
    """Read the video pins.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    tuple
        The color (red, green, blue), the horizontal and the vertical
        synchronism.
    """
    color = (
        int(dut.o_vga_r.value),
        int(dut.o_vga_g.value),
        int(dut.o_vga_b.value),
    )
    return color, int(dut.o_vga_hs.value), int(dut.o_vga_vs.value)


def expected(line: int, column: int) -> tuple[Color, int, int]:
    """Give what the pins show at a position of the frame.

    Parameters
    ----------
    line : int
        The line of the frame, from 0 to the total.
    column : int
        The column of the line.

    Returns
    -------
    tuple
        The color, the horizontal and the vertical synchronism (negative
        pulses, so low inside them).
    """
    visible = line < frame.V_VISIBLE and column < frame.H_VISIBLE
    color = frame.screen_color(column, line) if visible else frame.BLACK
    hs = 0 if HS_BEGIN <= column < HS_BEGIN + frame.H_SYNC else 1
    vs = 0 if VS_BEGIN <= line < VS_BEGIN + frame.V_SYNC else 1
    return color, hs, vs


async def capture_frame(dut: Any) -> list[tuple[Color, int, int]]:
    """Capture one whole frame, from the start of the vertical pulse.

    Parameters
    ----------
    dut : Any
        The device under test.

    Returns
    -------
    list of tuple
        One sample per pixel clock, in the order of the scan.
    """
    await FallingEdge(dut.o_vga_vs)
    await FallingEdge(dut.i_pixel_clk)
    samples: list[tuple[Color, int, int]] = []
    for _ in range(frame.H_TOTAL * frame.V_TOTAL):
        samples.append(pins(dut))
        await FallingEdge(dut.i_pixel_clk)
    return samples


@cocotb.test()
async def test_the_core_draws_a_frame_that_the_vga_shows(dut: Any) -> None:
    """The VGA output is the framebuffer through the palette."""
    cocotb.start_soon(
        Clock(dut.i_pixel_clk, frame.PIXEL_NS, unit="ns").start()
    )
    await start(dut)
    await wait_for_tohost(dut)
    geometry = await sdram_word(dut, RESULT_WORD)
    pixel_format = await sdram_word(dut, RESULT_WORD + 1)
    check(
        geometry == frame.GEOMETRY_VALUE,
        f"geometry read by the core {geometry:#x}",
    )
    check(
        pixel_format == frame.FORMAT_VALUE,
        f"format read by the core {pixel_format:#x}",
    )
    samples = await capture_frame(dut)
    for number, got in enumerate(samples):
        line = (VS_BEGIN + number // frame.H_TOTAL) % frame.V_TOTAL
        column = number % frame.H_TOTAL
        want = expected(line, column)
        check(
            got == want,
            f"line {line} column {column}: {got} != {want}",
        )
    shown = {color for color, _, _ in samples}
    check(
        len(shown) == len(frame.PALETTE) + 1,
        f"the frame shows {len(shown)} colors",
    )
