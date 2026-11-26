/* doom_clock.h -- o relógio em milissegundos da porta do DOOM (doomgeneric).
 *
 * A porta pede só uma função de tempo, DG_GetTicksMs, e a consulta por polling. O relógio sai do CSR `time` do
 * Zicntr, que a plataforma espelha do mtime do CLINT (platform.yaml, `interrupts.mtime_hz`).
 */

#ifndef DOOM_CLOCK_H
#define DOOM_CLOCK_H

#include <stdint.h>

/* O estado do relógio entre duas leituras: o contador `time` da última leitura, os ticks que ainda não completam
 * um milissegundo e os milissegundos contados desde a primeira leitura. */
typedef struct {
    bool started;
    uint32_t last_ticks;
    uint32_t sub_ms_ticks;
    uint32_t ms;
} doom_clock_t;

/* Avança o relógio até o valor `ticks` do contador e devolve os milissegundos contados desde a primeira chamada
 * (zero nela). Usa só os 32 bits baixos do contador: o relógio perde tempo se duas chamadas ficarem mais de 2^32
 * ticks afastadas (71,6 minutos a 1 MHz). Não faz divisão de 64 bits nem a instrução `div`. */
uint32_t doom_clock_advance(doom_clock_t *clock, uint32_t ticks);

/* Lê os 32 bits baixos do CSR `time`. */
uint32_t doom_clock_read_ticks(void);

/* A função de tempo da doomgeneric (o nome é o da porta): milissegundos desde a primeira chamada. */
uint32_t DG_GetTicksMs(void);

#endif
