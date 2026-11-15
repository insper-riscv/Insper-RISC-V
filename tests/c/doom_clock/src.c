// RV32_EXT: M,Zicsr,Zicntr
// RV32_TEST_KIND: unit
/* Teste do relógio da porta do DOOM (runtime/doom_clock.c) no Spike.
 *
 * Confere a conversão em milissegundos contra a conta em 64 bits (que só o teste usa), inclusive a passagem do
 * contador de 2^32 para 0, e que o CSR `time` real avança e nunca recua. O resultado sai como o código de retorno
 * de main: zero é aprovado e cada checagem que falha devolve o próprio código.
 */
#include <stdint.h>

#include "doom_clock.h"

/* Número de avanços sintéticos conferidos contra a conta em 64 bits. */
static constexpr uint32_t STEPS = 4000u;

/* Milissegundos de relógio real que o teste espera ver passar. */
static constexpr uint32_t REAL_MS_TARGET = 3u;

/* Limite de leituras do relógio real, para um contador parado não travar o teste. */
static constexpr uint32_t REAL_POLL_LIMIT = 200000u;

#ifdef RV32_SPIKE
/* Leituras do relógio real que o teste faz no Spike, onde o `time` não anda. */
static constexpr uint32_t SPIKE_POLLS = 1000u;
#endif

/* Gerador congruencial determinístico: o mesmo teste dá a mesma sequência no Spike e na placa. */
static uint32_t next_random(uint32_t *state)
{
    *state = *state * 1664525u + 1013904223u;
    return *state;
}

/* Escolhe um avanço do contador de tamanho variado: pequeno, médio ou quase 2^32. */
static uint32_t pick_delta(uint32_t *state)
{
    uint32_t raw = next_random(state);
    switch ((raw >> 28) & 3u) {
    case 0u:
        return raw % 3000u;
    case 1u:
        return raw >> 12;
    case 2u:
        return raw;
    default:
        return 0xFFFFFFFFu - (raw >> 20);
    }
}

/* A primeira chamada devolve zero qualquer que seja o contador. */
static int check_first_call(void)
{
    doom_clock_t clock = {};
    return doom_clock_advance(&clock, 0x12345678u) == 0u ? 0 : 1;
}

/* Avanços de milissegundo exato, de um tick a menos e a mais, e o resto que passa de um para o outro. */
static int check_remainders(void)
{
    doom_clock_t clock = {};
    (void)doom_clock_advance(&clock, 500u);
    if (doom_clock_advance(&clock, 1500u) != 1u) {
        return 2;
    }
    if (doom_clock_advance(&clock, 2499u) != 1u) {
        return 3;
    }
    if (doom_clock_advance(&clock, 2500u) != 2u) {
        return 4;
    }
    /* Dois restos de 999 somam 1998 ticks: um milissegundo e 998 de resto. */
    if (doom_clock_advance(&clock, 3499u) != 2u) {
        return 5;
    }
    if (doom_clock_advance(&clock, 4498u) != 3u) {
        return 6;
    }
    return doom_clock_advance(&clock, 4500u) == 4u ? 0 : 7;
}

/* Muitos avanços sintéticos, a partir de um contador que logo passa de 2^32 para 0, contra a conta em 64 bits. */
static int check_against_64_bit_reference(void)
{
    doom_clock_t clock = {};
    uint32_t state = 12345u;
    uint32_t ticks = 0xFFFFF000u;
    uint64_t total = 0u;
    (void)doom_clock_advance(&clock, ticks);
    for (uint32_t step = 0u; step < STEPS; step++) {
        uint32_t delta = pick_delta(&state);
        ticks += delta;
        total += delta;
        uint32_t expected = (uint32_t)(total / 1000u);
        if (doom_clock_advance(&clock, ticks) != expected) {
            return 8;
        }
    }
    return 0;
}

/* O avanço máximo de 32 bits, e o seu complemento, convertem exatos. */
static int check_extreme_deltas(void)
{
    doom_clock_t clock = {};
    (void)doom_clock_advance(&clock, 0u);
    /* 4294967295 ticks são 4294967 ms e 295 ticks de resto. */
    if (doom_clock_advance(&clock, 0xFFFFFFFFu) != 4294967u) {
        return 9;
    }
    /* Mais 705 ticks fecham 4294968 ms e deixam o resto em zero. */
    if (doom_clock_advance(&clock, 704u) != 4294968u) {
        return 10;
    }
    return 0;
}

/* O CSR `time` real avança e a função da porta nunca recua. O Spike sem dispositivos (a execução do spike-run, sem
 * CLINT) deixa o `time` em zero, então nele só a ausência de retrocesso é conferida; o avanço é conferido na
 * simulação da plataforma, onde o `time` espelha o mtime do CLINT. */
static int check_real_clock(void)
{
    if (DG_GetTicksMs() != 0u) {
        return 11;
    }
    uint32_t previous = 0u;
    for (uint32_t poll = 0u; poll < REAL_POLL_LIMIT; poll++) {
        uint32_t now = DG_GetTicksMs();
        if (now < previous) {
            return 12;
        }
        if (now >= REAL_MS_TARGET) {
            return 0;
        }
        previous = now;
#ifdef RV32_SPIKE
        if (poll >= SPIKE_POLLS) {
            return 0;
        }
#endif
    }
    return 13;
}

int main(void)
{
    int code = check_first_call();
    if (code == 0) {
        code = check_remainders();
    }
    if (code == 0) {
        code = check_against_64_bit_reference();
    }
    if (code == 0) {
        code = check_extreme_deltas();
    }
    if (code == 0) {
        code = check_real_clock();
    }
    return code;
}
