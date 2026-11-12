// RV32_EXT: M, Zicsr
// RV32_TEST_KIND: unit
// RV32_TIMEOUT_S: 90
#include <stdint.h>

#include "rv32_cpi.h"
#include "rv32_platform.h"
#include "rv32_test.h"

// Ciclos por instrução da busca na de0-cv (Frente F, tarefa F.2): instruções em linha reta, que não cabem na cache de instruções de 4 KiB, e um laço que cabe.
// O formato da linha e os eventos contados estão em rv32_cpi.h.

// Escoadouro dos kernels: o resultado de cada um é gravado aqui para o compilador não o descartar.
static volatile uint32_t sink;
// busca em linha reta de 8 KiB (2048 addi), o dobro da cache de instruções: uma falha por linha.
static void k_fetch_straight(void) {
    __asm__ volatile(
        ".rept 2048\n"
        "addi x5, x5, 1\n"
        ".endr\n"
        :
        :
        : "x5");
}

// busca de um laço pequeno que cabe na cache de instruções, 1024 voltas de 4 instruções.
static void k_fetch_loop(void) {
    uint32_t i = 1024;
    __asm__ volatile(
        "1: addi %0, %0, -1\n"
        "   nop\n"
        "   nop\n"
        "   bnez %0, 1b\n"
        : "+r"(i));
}

// Mede os dois kernels de busca e falha se algum não mover os contadores.
int main(void) {
    cpi_sample_t overhead;
    cpi_setup();
    cpi_overhead(&overhead);
    if (cpi_run("fetch-straight", k_fetch_straight, &overhead)) RV32_FAIL(1);
    if (cpi_run("fetch-loop", k_fetch_loop, &overhead)) RV32_FAIL(1);
    RV32_PASS();
}
