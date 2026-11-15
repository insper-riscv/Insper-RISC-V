/* doom_clock.c -- DG_GetTicksMs pelo CSR `time` do Zicntr.
 *
 * O `time` da plataforma doom é o mtime do CLINT, que soma 1 a cada 77 ciclos do núcleo (76,923077 MHz), ou seja,
 * 999.001 ticks por segundo. O platform.yaml nomeia 1 MHz (`interrupts.mtime_hz`, RV32_MTIME_HZ em memory_map.h), e é
 * esse o valor que a conversão usa: um tick vale 1 microssegundo e o relógio anda 0,1 % mais devagar que o tempo real,
 * o que o jogo (35 tics por segundo) não percebe.
 *
 * A conversão em milissegundos divide por 1000 sem a instrução `div` (CPI de cerca de 11 neste núcleo): uma multiplicação
 * pelo inverso, que a `mulhu` faz em um passo. O relógio soma o avanço do contador a cada leitura, em 32 bits, em vez de
 * converter o valor de 64 bits (timeh:time), que pediria uma divisão de 64 bits da libgcc.
 */
#include <stdint.h>

#include "doom_clock.h"
#include "memory_map.h"

/* O inverso e o deslocamento da divisão por 1000: x / 1000 == (x * 0x10624DD3) >> 38 para todo x de 32 bits, porque
 * 0x10624DD3 = ceil(2^38 / 1000) erra por 56 partes em 2^38 e 56 * 2^32 < 2^38. Vale só para mtime_hz de 1 MHz. */
static constexpr uint64_t DIV1000_MAGIC = 0x10624DD3u;
static constexpr unsigned DIV1000_SHIFT = 38u;

/* Ticks do contador por milissegundo. */
static constexpr uint32_t TICKS_PER_MS = RV32_MTIME_HZ / 1000u;

/* Se o mtime_hz da plataforma mudar, o inverso acima deixa de valer e a conversão tem de ser refeita. */
static_assert(TICKS_PER_MS == 1000u, "DIV1000_MAGIC supõe mtime_hz de 1 MHz");

/* O estado do relógio da porta: DG_GetTicksMs é a única que o usa. */
static doom_clock_t port_clock;

/* Divide por 1000 com uma multiplicação (o `mulhu` da extensão M), sem a instrução `div`. */
static uint32_t div1000(uint32_t value)
{
    return (uint32_t)(((uint64_t)value * DIV1000_MAGIC) >> DIV1000_SHIFT);
}

uint32_t doom_clock_advance(doom_clock_t *clock, uint32_t ticks)
{
    if (!clock->started) {
        clock->started = true;
        clock->last_ticks = ticks;
        return 0u;
    }
    /* A subtração sem sinal dá o avanço certo mesmo quando o contador passou de 2^32 para 0. */
    uint32_t delta = ticks - clock->last_ticks;
    clock->last_ticks = ticks;

    uint32_t whole_ms = div1000(delta);
    /* O resto do avanço (menos de 1000) soma ao que já estava pendente (menos de 1000): no máximo um milissegundo a mais. */
    uint32_t pending = clock->sub_ms_ticks + (delta - whole_ms * TICKS_PER_MS);
    if (pending >= TICKS_PER_MS) {
        pending -= TICKS_PER_MS;
        whole_ms += 1u;
    }
    clock->sub_ms_ticks = pending;
    clock->ms += whole_ms;
    return clock->ms;
}

uint32_t doom_clock_read_ticks(void)
{
    uint32_t ticks;
    /* A norma não tem leitura de CSR; o `csrr` do `time` é o acesso que o Zicntr define (RISC-V Unprivileged, cap. 12). */
    __asm__ volatile("csrr %0, time" : "=r"(ticks));
    return ticks;
}

uint32_t DG_GetTicksMs(void)
{
    return doom_clock_advance(&port_clock, doom_clock_read_ticks());
}
