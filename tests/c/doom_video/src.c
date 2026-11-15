// RV32_EXT: M,Zicsr,Zicntr
// RV32_TEST_KIND: unit
/* Teste de vídeo da plataforma doom na placa: barras de cor com paleta.
 *
 * Escreve a paleta de 256 entradas e o framebuffer de 320x200 do vídeo indexado (VIDEO, memory_map.h) e liga a
 * exibição. A imagem, que fica no monitor depois que o programa termina, tem, de cima para baixo:
 *
 *   - 8 barras verticais de 40 colunas (branco, amarelo, ciano, verde, magenta, vermelho, azul e preto), nas
 *     linhas 0 a 149;
 *   - uma rampa de 16 níveis de cinza em barras de 20 colunas, nas linhas 150 a 199.
 *
 * Sem monitor, o teste confere o que o núcleo enxerga: a geometria e o formato lidos dos registradores do vídeo e o
 * contador de quadros, que tem de avançar com o clock de pixel. O resultado sai como o código de retorno de main:
 * zero é aprovado e cada checagem que falha devolve o próprio código. O Spike não tem o vídeo, então nele main
 * devolve zero sem tocar no dispositivo.
 */
#include <stdint.h>

#include "doom_clock.h"
#include "memory_map.h"

#ifndef RV32_SPIKE

/* Largura e altura do framebuffer da plataforma (io.video do platform.yaml). */
static constexpr uint32_t FB_WIDTH = 320u;
static constexpr uint32_t FB_HEIGHT = 200u;

/* Pixels de cada palavra do framebuffer indexado (8 bits por pixel). */
static constexpr uint32_t PIXELS_PER_WORD = 4u;

/* Offsets, em bytes a partir da base do vídeo, dos registradores e das duas janelas de escrita. */
static constexpr uint32_t REG_CONTROL = 0x00u;
static constexpr uint32_t REG_FRAMES = 0x08u;
static constexpr uint32_t REG_GEOMETRY = 0x0Cu;
static constexpr uint32_t REG_FORMAT = 0x10u;
static constexpr uint32_t PALETTE_OFFSET = 0x400u;
static constexpr uint32_t FRAMEBUFFER_OFFSET = 0x20000u;

/* O bit do formato indexado no registrador de formato e o campo dos bits por canal (23:16). */
static constexpr uint32_t FORMAT_INDEXED = 1u << 24;
static constexpr uint32_t FORMAT_CHANNEL_SHIFT = 16u;

/* Entradas da paleta, barras de cor (índices 0 a 7) e rampa de cinza (a partir do índice 16). */
static constexpr uint32_t PALETTE_ENTRIES = 256u;
static constexpr uint32_t COLOR_BARS = 8u;
static constexpr uint32_t GRAY_BASE = 16u;
static constexpr uint32_t GRAY_LEVELS = 16u;
/* A primeira linha da rampa de cinza; acima dela ficam as barras de cor. */
static constexpr uint32_t GRAY_FIRST_ROW = 150u;

/* Quadros que o teste espera ver passar, e o limite de ticks (1 MHz) da espera: 100 ms. */
static constexpr uint32_t FRAMES_WANTED = 3u;
static constexpr uint32_t FRAME_WAIT_TICKS = 100000u;

#define VIDEO_REG(offset) ((volatile uint32_t *)(RV32_VIDEO_BASE + (offset)))

/* As barras de cor em 8 bits por canal, na ordem da imagem. */
static constexpr uint8_t BAR_RGB[COLOR_BARS][3] = {
    {255u, 255u, 255u}, {255u, 255u, 0u}, {0u, 255u, 255u}, {0u, 255u, 0u},
    {255u, 0u, 255u},   {255u, 0u, 0u},   {0u, 0u, 255u},   {0u, 0u, 0u},
};

/* Reduz um canal de 8 bits para a largura do canal da placa. */
static uint32_t narrow(uint32_t value, uint32_t channel_bits)
{
    return value >> (8u - channel_bits);
}

/* Monta uma cor da paleta, vermelho nos bits altos, com canais de 8 bits reduzidos para a largura da placa. */
static uint32_t palette_color(uint32_t red, uint32_t green, uint32_t blue, uint32_t channel_bits)
{
    return (narrow(red, channel_bits) << (2u * channel_bits)) | (narrow(green, channel_bits) << channel_bits) |
           narrow(blue, channel_bits);
}

/* Escreve a paleta: as barras de cor, a rampa de cinza e preto no resto. */
static void write_palette(uint32_t channel_bits)
{
    for (uint32_t index = 0u; index < PALETTE_ENTRIES; index++) {
        uint32_t color = 0u;
        if (index < COLOR_BARS) {
            color = palette_color(BAR_RGB[index][0], BAR_RGB[index][1], BAR_RGB[index][2], channel_bits);
        } else if (index >= GRAY_BASE && index < GRAY_BASE + GRAY_LEVELS) {
            uint32_t level = (index - GRAY_BASE) * 17u;
            color = palette_color(level, level, level, channel_bits);
        }
        *VIDEO_REG(PALETTE_OFFSET + 4u * index) = color;
    }
}

/* Dá o índice de paleta do pixel (x, y) do framebuffer. */
static uint32_t pixel_index(uint32_t x, uint32_t y)
{
    if (y < GRAY_FIRST_ROW) {
        return x / (FB_WIDTH / COLOR_BARS);
    }
    return GRAY_BASE + x / (FB_WIDTH / GRAY_LEVELS);
}

/* Escreve o framebuffer, quatro pixels por palavra, o de menor coluna nos bits baixos. */
static void write_framebuffer(void)
{
    volatile uint32_t *word = VIDEO_REG(FRAMEBUFFER_OFFSET);
    for (uint32_t y = 0u; y < FB_HEIGHT; y++) {
        for (uint32_t x = 0u; x < FB_WIDTH; x += PIXELS_PER_WORD) {
            uint32_t packed = 0u;
            for (uint32_t slot = 0u; slot < PIXELS_PER_WORD; slot++) {
                packed |= pixel_index(x + slot, y) << (8u * slot);
            }
            *word = packed;
            word++;
        }
    }
}

/* Espera o contador de quadros avançar FRAMES_WANTED vezes; devolve verdadeiro se avançou a tempo. */
static bool frames_advance(void)
{
    uint32_t first = *VIDEO_REG(REG_FRAMES);
    uint32_t start = doom_clock_read_ticks();
    while (doom_clock_read_ticks() - start < FRAME_WAIT_TICKS) {
        if (*VIDEO_REG(REG_FRAMES) - first >= FRAMES_WANTED) {
            return true;
        }
    }
    return false;
}

#endif /* RV32_SPIKE */

int main(void)
{
#ifdef RV32_SPIKE
    return 0;
#else
    if (*VIDEO_REG(REG_GEOMETRY) != (FB_WIDTH | (FB_HEIGHT << 16))) {
        return 1;
    }
    uint32_t format = *VIDEO_REG(REG_FORMAT);
    if ((format & FORMAT_INDEXED) == 0u) {
        return 2;
    }
    write_palette((format >> FORMAT_CHANNEL_SHIFT) & 0xFFu);
    write_framebuffer();
    *VIDEO_REG(REG_CONTROL) = 1u;
    if (!frames_advance()) {
        return 3;
    }
    return 0;
#endif
}
