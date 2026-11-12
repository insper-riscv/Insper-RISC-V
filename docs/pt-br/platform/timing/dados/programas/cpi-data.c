// RV32_EXT: M, Zicsr
// RV32_TEST_KIND: unit
// RV32_TIMEOUT_S: 90
#include <stdint.h>

#include "rv32_cpi.h"
#include "rv32_platform.h"
#include "rv32_sdram.h"
#include "rv32_test.h"

// Ciclos por instrução dos dados na de0-cv (Frente F, tarefa F.2): loads e stores da SDRAM e constantes da FLASH, que cabem ou não na cache de dados de 4 KiB.
// O formato da linha e os eventos contados estão em rv32_cpi.h.

// Escoadouro dos kernels: o resultado de cada um é gravado aqui para o compilador não o descartar.
static volatile uint32_t sink;
// Tabela na FLASH: 8 KiB, o dobro da cache de dados, então toda leitura sequencial falha a cada linha.
static const uint32_t flash_table[2048] = {
    1u, 2u, 3u, 4u, 5u, 6u, 7u, 8u, 9u, 10u, 11u, 12u, 13u, 14u, 15u, 16u,
};

// loads da SDRAM que cabem na cache de dados (1 KiB), com o uso logo depois do load.
static void k_sdram_load_use(void) {
    volatile uint32_t *m = RV32_SDRAM;
    uint32_t acc = 0;
    for (uint32_t i = 0; i < 256; i++) acc += m[i];
    sink = acc;
}

// loads da SDRAM varrendo 8 KiB (o dobro da cache de dados): uma falha a cada linha.
static void k_sdram_stream(void) {
    volatile uint32_t *m = RV32_SDRAM + 0x1000;
    uint32_t acc = 0;
    for (uint32_t i = 0; i < 2048; i++) acc += m[i];
    sink = acc;
}

// stores de palavra na SDRAM, 256 (a cache de dados é write-through).
static void k_sdram_store(void) {
    volatile uint32_t *m = RV32_SDRAM + 0x4000;
    for (uint32_t i = 0; i < 256; i++) m[i] = i;
}

// loads de constantes da FLASH que cabem na cache de dados (1 KiB).
static void k_flash_small(void) {
    uint32_t acc = 0;
    const volatile uint32_t *t = flash_table;
    for (uint32_t i = 0; i < 256; i++) acc += t[i];
    sink = acc;
}

// loads de constantes da FLASH varrendo 8 KiB (o dobro da cache de dados).
static void k_flash_stream(void) {
    uint32_t acc = 0;
    const volatile uint32_t *t = flash_table;
    for (uint32_t i = 0; i < 2048; i++) acc += t[i];
    sink = acc;
}

// Preenche a SDRAM, mede os cinco kernels de dados e falha se algum não mover os contadores.
int main(void) {
    cpi_sample_t overhead;
    cpi_setup();
    volatile uint32_t *m = RV32_SDRAM;
    for (uint32_t i = 0; i < 256; i++) m[i] = i * 3u + 1u;
    cpi_overhead(&overhead);
    if (cpi_run("sdram-load-use", k_sdram_load_use, &overhead)) RV32_FAIL(1);
    if (cpi_run("sdram-stream", k_sdram_stream, &overhead)) RV32_FAIL(1);
    if (cpi_run("sdram-store", k_sdram_store, &overhead)) RV32_FAIL(1);
    if (cpi_run("flash-small", k_flash_small, &overhead)) RV32_FAIL(1);
    if (cpi_run("flash-stream", k_flash_stream, &overhead)) RV32_FAIL(1);
    RV32_PASS();
}
