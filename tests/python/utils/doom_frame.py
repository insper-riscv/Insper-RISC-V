"""Quadro de teste do vídeo e teclas do teclado da plataforma doom.

O programa de teste do vídeo (``gen_doom_images.py``) escreve a
paleta e o framebuffer definidos aqui, e o testbench (``doom_video.py``)
confere a saída VGA contra o modelo deste módulo. O programa de teste
do teclado lê da fila do teclado os scancodes que o testbench injeta.
O módulo só tem dados e o modelo, sem nada de simulação, para os dois
lados usarem o mesmo.
"""

# Onde os programas de teste guardam o que leram, em bytes a partir da
# base da RAM: depois do código e antes da campainha, uma palavra por
# valor. A palavra de pronto, que o programa do teclado escreve antes
# de esperar os bytes, fica mais adiante.
RESULT_OFFSET = 0x600
READY_OFFSET = 0x6F0
WORD = 4
# Geometria do framebuffer de teste, em pixels (uma linha são 4
# palavras).
FB_WIDTH = 16
FB_HEIGHT = 8
SCALE = 2
BITS_PER_PIXEL = 8
PIXELS_PER_WORD = 4
# Modo de teste pequeno, com a mesma estrutura do 640x480: visível,
# pórtico frontal, sincronismo e pórtico traseiro, com os dois
# sincronismos negativos. A imagem de 32x16 fica centrada em 40x20
# (faixas de 4 colunas e de 2 linhas).
H_VISIBLE, H_FRONT, H_SYNC, H_BACK = 40, 2, 4, 2
V_VISIBLE, V_FRONT, V_SYNC, V_BACK = 20, 1, 2, 1
H_TOTAL = H_VISIBLE + H_FRONT + H_SYNC + H_BACK
V_TOTAL = V_VISIBLE + V_FRONT + V_SYNC + V_BACK
# Período do clock de pixel do testbench, em nanossegundos.
PIXEL_NS = 40
# Bits por canal de cor da DE0-CV.
CHANNEL_BITS = 4
# A paleta de teste: cinza, vermelho, verde e azul, em RGB444.
PALETTE = (0x888, 0xF00, 0x0F0, 0x00F)
BLACK = (0, 0, 0)

# Registradores do vídeo, em bytes a partir da base (palavras de 0 a
# 4), e as regiões da janela (paleta na palavra 256, framebuffer na
# metade alta).
VIDEO_CONTROL = 0x00
VIDEO_GEOMETRY = 0x0C
VIDEO_FORMAT = 0x10
VIDEO_PALETTE = 0x400
VIDEO_FRAMEBUFFER = 0x20000
# O valor que os registradores de geometria e de formato devem ter.
GEOMETRY_VALUE = FB_WIDTH | (FB_HEIGHT << 16)
FORMAT_VALUE = BITS_PER_PIXEL | (SCALE << 8) | (CHANNEL_BITS << 16) | (1 << 24)

# Registradores do teclado, em bytes a partir da base.
KBD_DATA = 0x00
KBD_STATUS = 0x04
KBD_CONTROL = 0x0C
KBD_RX_VALID = 0x01
KBD_RX_IRQ_ENABLE = 0x01
# A fonte do teclado no PLIC e os registradores do PLIC que o programa
# usa.
PLIC_PRIORITY_KBD = 0x14
PLIC_ENABLE = 0x2000
PLIC_THRESHOLD = 0x200000
PLIC_CLAIM = 0x200004

# As setas em scancodes do conjunto 2: make com o prefixo estendido
# E0, e break com E0 F0.
EXTENDED = 0xE0
BREAK = 0xF0
ARROWS = (("up", 0x75), ("left", 0x6B), ("right", 0x74), ("down", 0x72))
SCANCODES = tuple(
    byte
    for _, code in ARROWS
    for byte in (EXTENDED, code, EXTENDED, BREAK, code)
)


def pixel_index(x: int, y: int) -> int:
    """Dá o índice de paleta do pixel (x, y) do framebuffer.

    Parameters
    ----------
    x : int
        Coluna do framebuffer.
    y : int
        Linha do framebuffer.

    Returns
    -------
    int
        O índice, de 0 a 3 (uma diagonal de quatro cores).
    """
    return (x + y) % len(PALETTE)


def framebuffer_words() -> list[int]:
    """Monta as palavras do framebuffer de teste.

    Returns
    -------
    list of int
        As palavras, com o pixel de menor coluna nos bits baixos.
    """
    words: list[int] = []
    for y in range(FB_HEIGHT):
        for block in range(FB_WIDTH // PIXELS_PER_WORD):
            word = 0
            for slot in range(PIXELS_PER_WORD):
                index = pixel_index(block * PIXELS_PER_WORD + slot, y)
                word |= index << (BITS_PER_PIXEL * slot)
            words.append(word)
    return words


def rgb(value: int) -> tuple[int, int, int]:
    """Separa uma cor de 12 bits nos três canais.

    Parameters
    ----------
    value : int
        A cor em RGB444.

    Returns
    -------
    tuple of int
        Vermelho, verde e azul, de 4 bits cada.
    """
    mask = (1 << CHANNEL_BITS) - 1
    return (
        (value >> (2 * CHANNEL_BITS)) & mask,
        (value >> CHANNEL_BITS) & mask,
        value & mask,
    )


def screen_color(x: int, y: int) -> tuple[int, int, int]:
    """Dá a cor esperada do pixel (x, y) da área visível da tela.

    Parameters
    ----------
    x : int
        Coluna da tela, de 0 a ``H_VISIBLE - 1``.
    y : int
        Linha da tela, de 0 a ``V_VISIBLE - 1``.

    Returns
    -------
    tuple of int
        A cor do pixel do framebuffer ampliado, ou preto nas faixas.
    """
    fx = x - (H_VISIBLE - FB_WIDTH * SCALE) // 2
    fy = y - (V_VISIBLE - FB_HEIGHT * SCALE) // 2
    if 0 <= fx < FB_WIDTH * SCALE and 0 <= fy < FB_HEIGHT * SCALE:
        return rgb(PALETTE[pixel_index(fx // SCALE, fy // SCALE)])
    return BLACK
