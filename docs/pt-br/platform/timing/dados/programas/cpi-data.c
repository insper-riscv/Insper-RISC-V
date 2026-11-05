// RV32_EXT: M, Zicsr
// RV32_TEST_KIND: unit
// RV32_TIMEOUT_S: 90
#include "rv32_test.h"
#include "rv32_platform.h"
#include "rv32_sdram.h"
#include "rv32_cpi.h"

// Ciclos por instrução dos dados na de0-cv (Frente F, tarefa F.2): loads e stores da SDRAM e constantes da FLASH, que cabem ou não na cache de dados de 4 KiB.
// O formato da linha e os eventos contados estão em rv32_cpi.h.

static volatile unsigned int sink;
// Tabela na FLASH: 8 KiB, o dobro da cache de dados, então toda leitura sequencial falha a cada linha.
static const unsigned int flash_table[2048] = {
    1u, 2u, 3u, 4u, 5u, 6u, 7u, 8u, 9u, 10u, 11u, 12u, 13u, 14u, 15u, 16u,
};

// loads da SDRAM que cabem na cache de dados (1 KiB), com o uso logo depois do load.
static void k_sdram_load_use(void) {
    volatile unsigned int *m = RV32_SDRAM;
    unsigned int acc = 0;
    for (unsigned int i = 0; i < 256; i++) acc += m[i];
    sink = acc;
}

// loads da SDRAM varrendo 8 KiB (o dobro da cache de dados): uma falha a cada linha.
static void k_sdram_stream(void) {
    volatile unsigned int *m = RV32_SDRAM + 0x1000;
    unsigned int acc = 0;
    for (unsigned int i = 0; i < 2048; i++) acc += m[i];
    sink = acc;
}

// stores de palavra na SDRAM, 256 (a cache de dados é write-through).
static void k_sdram_store(void) {
    volatile unsigned int *m = RV32_SDRAM + 0x4000;
    for (unsigned int i = 0; i < 256; i++) m[i] = i;
}

// loads de constantes da FLASH que cabem na cache de dados (1 KiB).
static void k_flash_small(void) {
    unsigned int acc = 0;
    const volatile unsigned int *t = flash_table;
    for (unsigned int i = 0; i < 256; i++) acc += t[i];
    sink = acc;
}

// loads de constantes da FLASH varrendo 8 KiB (o dobro da cache de dados).
static void k_flash_stream(void) {
    unsigned int acc = 0;
    const volatile unsigned int *t = flash_table;
    for (unsigned int i = 0; i < 2048; i++) acc += t[i];
    sink = acc;
}

int main(void) {
    cpi_sample_t overhead;
    cpi_setup();
    volatile unsigned int *m = RV32_SDRAM;
    for (unsigned int i = 0; i < 256; i++) m[i] = i * 3u + 1u;
    cpi_overhead(&overhead);
    if (cpi_run("sdram-load-use", k_sdram_load_use, &overhead)) RV32_FAIL(1);
    if (cpi_run("sdram-stream", k_sdram_stream, &overhead)) RV32_FAIL(1);
    if (cpi_run("sdram-store", k_sdram_store, &overhead)) RV32_FAIL(1);
    if (cpi_run("flash-small", k_flash_small, &overhead)) RV32_FAIL(1);
    if (cpi_run("flash-stream", k_flash_stream, &overhead)) RV32_FAIL(1);
    RV32_PASS();
}
