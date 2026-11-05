// RV32_EXT: M, Zicsr
// RV32_TEST_KIND: unit
// RV32_TIMEOUT_S: 90
#include "rv32_test.h"
#include "rv32_platform.h"
#include "rv32_cpi.h"

// Ciclos por instrução do núcleo na de0-cv (Frente F, tarefa F.2). Laço de inteiros, desvios, multiplicação e divisão, fundidas e não fundidas.
// O formato da linha e os eventos contados estão em rv32_cpi.h.

static volatile unsigned int sink;

// laço de inteiros, 256 iterações de soma, ou-exclusivo e deslocamento.
static void k_int_loop(void) {
    unsigned int acc = 1;
    for (unsigned int i = 0; i < 256; i++) acc = (acc + i) ^ (acc >> 3);
    sink = acc;
}

// desvios, metade tomada e metade não, 256 iterações em assembly.
static void k_branches(void) {
    unsigned int acc = 0, i = 0, n = 256, t;
    __asm__ volatile(
        "1: andi %[t], %[i], 1\n"
        "   beqz %[t], 2f\n"
        "   addi %[acc], %[acc], 3\n"
        "2: addi %[i], %[i], 1\n"
        "   bne  %[i], %[n], 1b\n"
        : [acc] "+r"(acc), [i] "+r"(i), [t] "=&r"(t)
        : [n] "r"(n));
    sink = acc;
}

// multiplicações independentes, 128 MUL seguidos com operandos diferentes.
static void k_mul(void) {
    unsigned int x = 3, y = 5, r = 0;
    for (unsigned int i = 0; i < 128; i++) {
        __asm__ volatile("mul %0, %1, %2" : "=r"(r) : "r"(x), "r"(y));
        x += r | 1u;
        y += 2u;
    }
    sink = r;
}

// MULH seguido de MUL com os mesmos operandos (par que a fusão atende), 64 pares.
static void k_mulh_mul_fused(void) {
    unsigned int x = 0x89ABCDEFu, y = 0x01234567u, h = 0, l = 0;
    for (unsigned int i = 0; i < 64; i++) {
        __asm__ volatile("mulh %0, %2, %3\n mul %1, %2, %3" : "=&r"(h), "=&r"(l) : "r"(x), "r"(y));
        x += h ^ l;
        y += 3u;
    }
    sink = x;
}

// MULH seguido de MUL com operandos diferentes (sem fusão), 64 pares.
static void k_mulh_mul_plain(void) {
    unsigned int x = 0x89ABCDEFu, y = 0x01234567u, z = 0x00FEDCBAu, h = 0, l = 0;
    for (unsigned int i = 0; i < 64; i++) {
        __asm__ volatile("mulh %0, %2, %3\n mul %1, %2, %4" : "=&r"(h), "=&r"(l) : "r"(x), "r"(y), "r"(z));
        x += h ^ l;
        y += 3u;
        z += 5u;
    }
    sink = x;
}

// DIV seguido de REM com os mesmos operandos (par que a fusão atende), 32 pares.
static void k_div_rem_fused(void) {
    unsigned int x = 0x7FFFFF01u, y = 1000u, q = 0, r = 0;
    for (unsigned int i = 0; i < 32; i++) {
        __asm__ volatile("div %0, %2, %3\n rem %1, %2, %3" : "=&r"(q), "=&r"(r) : "r"(x), "r"(y));
        x += q ^ r;
        y += 7u;
    }
    sink = x;
}

// DIV seguido de DIV com operandos diferentes (sem fusão), 32 pares.
static void k_div_div_plain(void) {
    unsigned int x = 0x7FFFFF01u, y = 1000u, z = 77u, q = 0, r = 0;
    for (unsigned int i = 0; i < 32; i++) {
        __asm__ volatile("div %0, %2, %3\n div %1, %2, %4" : "=&r"(q), "=&r"(r) : "r"(x), "r"(y), "r"(z));
        x += q ^ r;
        y += 7u;
        z += 3u;
    }
    sink = x;
}

int main(void) {
    cpi_sample_t overhead;
    cpi_setup();
    cpi_overhead(&overhead);
    if (cpi_run("int-loop", k_int_loop, &overhead)) RV32_FAIL(1);
    if (cpi_run("branches", k_branches, &overhead)) RV32_FAIL(1);
    if (cpi_run("mul", k_mul, &overhead)) RV32_FAIL(1);
    if (cpi_run("mulh-mul-fused", k_mulh_mul_fused, &overhead)) RV32_FAIL(1);
    if (cpi_run("mulh-mul-plain", k_mulh_mul_plain, &overhead)) RV32_FAIL(1);
    if (cpi_run("div-rem-fused", k_div_rem_fused, &overhead)) RV32_FAIL(1);
    if (cpi_run("div-div-plain", k_div_div_plain, &overhead)) RV32_FAIL(1);
    RV32_PASS();
}
