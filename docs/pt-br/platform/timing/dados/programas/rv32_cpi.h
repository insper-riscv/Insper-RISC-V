#ifndef RV32_CPI_H
#define RV32_CPI_H

#include <stdint.h>
#include <stdio.h>

/* Medição de ciclos por instrução dos programas cpi-core e cpi-mem (Frente F, tarefa F.2).
 * Cada kernel roda duas vezes entre leituras de cycle, instret e dos oito contadores de eventos do
 * Zihpm: a primeira passada parte de caches frias e a segunda das caches que a primeira deixou. O
 * custo de uma janela vazia (as leituras e a chamada) é descontado de todas as medidas.
 *
 * Eventos contados (mhpmevent3 a mhpmevent10): 1 parada de muldiv, 2 espera de memória externa,
 * 3 desvio tomado, 5 falha da cache de instruções, 6 falha da cache de dados, 7 espera da FLASH,
 * 8 parada de load-use e 9 operação de muldiv fundida. */

/* Registrador de estado da UART JTAG. Fica como macro porque um ponteiro para endereço fixo não pode ser
 * constexpr (ISO/IEC 9899:2024, 6.7.2: só o ponteiro nulo); o acesso é volatile (6.7.4.1) e alinhado a palavra. */
#define CPI_UART_STATUS ((volatile uint32_t *)0xC0000008u)

/* Máximo de leituras do estado à espera de o hospedeiro varrer a UART. */
static constexpr uint32_t CPI_ATTACH_POLLS = 40000000u;
/* Máximo de leituras do estado à espera de o hospedeiro esvaziar a UART. */
static constexpr uint32_t CPI_DRAIN_POLLS = 8000000u;
/* Profundidade da fila de transmissão da UART, em bytes. */
static constexpr uint32_t CPI_TX_DEPTH = 64u;
/* Quantidade de contadores lidos por amostra: cycle, instret e os oito de eventos. */
static constexpr uint32_t CPI_NCOUNT = 10u;

/* Diz se um hospedeiro varreu a UART (bit 17 do registrador de estado). */
static inline bool cpi_host_attached(uint32_t status) {
    return ((status >> 17) & 1u) != 0u;
}

/* Lugares livres na fila de transmissão, tirados do registrador de estado (bits 7 a 0). */
static inline uint32_t cpi_tx_free(uint32_t status) {
    return status & 0xFFu;
}

/* Uma leitura dos dez contadores. */
typedef struct {
    uint32_t v[CPI_NCOUNT];
} cpi_sample_t;

/* Um kernel medido: função sem argumentos nem resultado. */
typedef void (*cpi_kernel_fn)(void);

/* Lê e escreve um csr de número constante. Ficam como macros porque o número do csr entra no texto do assembly
 * pelo operador # do pré-processador (ISO/IEC 9899:2024, 6.10.5.2). */
#define CPI_CSRR(dst, csr) __asm__ volatile("csrr %0, " #csr : "=r"(dst))
#define CPI_CSRW(csr, src) __asm__ volatile("csrw " #csr ", %0" ::"r"(src))

/* Espera o hospedeiro varrer a UART e programa os oito contadores de eventos. */
static inline void cpi_setup(void) {
    for (uint32_t polls = 0; polls < CPI_ATTACH_POLLS && !cpi_host_attached(*CPI_UART_STATUS); polls++) {
    }
    CPI_CSRW(0x323, 1u);
    CPI_CSRW(0x324, 2u);
    CPI_CSRW(0x325, 3u);
    CPI_CSRW(0x326, 5u);
    CPI_CSRW(0x327, 6u);
    CPI_CSRW(0x328, 7u);
    CPI_CSRW(0x329, 8u);
    CPI_CSRW(0x32A, 9u);
}

/* Lê os dez contadores na ordem cycle, instret, mhpmcounter3 a mhpmcounter10. */
static inline void cpi_snap(cpi_sample_t *s) {
    uint32_t a, b, c, d, e, f, g, h, i, j;
    CPI_CSRR(a, 0xC00);
    CPI_CSRR(b, 0xC02);
    CPI_CSRR(c, 0xB03);
    CPI_CSRR(d, 0xB04);
    CPI_CSRR(e, 0xB05);
    CPI_CSRR(f, 0xB06);
    CPI_CSRR(g, 0xB07);
    CPI_CSRR(h, 0xB08);
    CPI_CSRR(i, 0xB09);
    CPI_CSRR(j, 0xB0A);
    s->v[0] = a; s->v[1] = b; s->v[2] = c; s->v[3] = d; s->v[4] = e;
    s->v[5] = f; s->v[6] = g; s->v[7] = h; s->v[8] = i; s->v[9] = j;
}

/* Guarda em `out` a diferença b - a, contador a contador. */
static inline void cpi_diff(cpi_sample_t *out, const cpi_sample_t *a, const cpi_sample_t *b) {
    for (uint32_t i = 0; i < CPI_NCOUNT; i++) out->v[i] = b->v[i] - a->v[i];
}

/* Roda um kernel e guarda a diferença das leituras. */
static inline void cpi_measure(cpi_kernel_fn fn, cpi_sample_t *out) {
    cpi_sample_t a, b;
    cpi_snap(&a);
    fn();
    cpi_snap(&b);
    cpi_diff(out, &a, &b);
}

/* Kernel vazio, para medir o custo da janela. */
static void cpi_empty(void) {}

/* Mede a janela vazia, depois de aquecer a leitura dos contadores. */
static inline void cpi_overhead(cpi_sample_t *out) {
    cpi_measure(cpi_empty, out);
    cpi_measure(cpi_empty, out);
}

/* Mede as duas passadas de um kernel e imprime uma linha na UART via JTAG:
 * "cpi <kernel> <cycle> <instret> <e5> <e6> <e7> | <cycle> <instret> <e1> <e2> <e3> <e5> <e6> <e7> <e8> <e9>",
 * a passada fria antes da barra e a quente depois (inteiros com sinal: o desconto da janela vazia pode deixar -1 ou -2 num evento de espera). Devolve 0 se os
 * contadores de ciclo e de instruções se moveram. A conversão para int de um valor sem sinal fora da faixa tem
 * resultado definido pela implementação (ISO/IEC 9899:2024, 6.3.2); aqui é intencional, para mostrar o sinal. */
static inline int cpi_run(const char *name, cpi_kernel_fn fn, const cpi_sample_t *overhead) {
    cpi_sample_t raw_c, raw_w, c, w;
    cpi_measure(fn, &raw_c);
    cpi_measure(fn, &raw_w);
    cpi_diff(&c, overhead, &raw_c);
    cpi_diff(&w, overhead, &raw_w);
    printf("cpi %s %d %d %d %d %d | %d %d %d %d %d %d %d %d %d %d\n", name, (int)c.v[0], (int)c.v[1], (int)c.v[5], (int)c.v[6], (int)c.v[7],
           (int)w.v[0], (int)w.v[1], (int)w.v[2], (int)w.v[3], (int)w.v[4], (int)w.v[5], (int)w.v[6], (int)w.v[7], (int)w.v[8], (int)w.v[9]);
    /* a UART guarda poucos bytes: espera o hospedeiro esvaziá-la antes da linha seguinte (com limite,
     * para que uma placa sem ninguém ligado termine) */
    for (uint32_t polls = 0; polls < CPI_DRAIN_POLLS && cpi_tx_free(*CPI_UART_STATUS) < CPI_TX_DEPTH; polls++) {
    }
    return (w.v[1] == 0 || w.v[0] < w.v[1] || c.v[1] == 0) ? 1 : 0;
}

#endif
