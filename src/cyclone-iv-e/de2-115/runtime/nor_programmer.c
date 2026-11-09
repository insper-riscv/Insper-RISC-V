// RV32_EXT: M,Zifencei
// RV32_TEST_KIND: unit
#include <stdint.h>

#include "rv32_flash_update.h"
#include "rv32_platform.h"
#include "rv32_test.h"

// O programador de NOR: o programa que o hospedeiro deixa na SDRAM (pela porta de depuração) para gravar uma
// banca do chip NOR quando o chip não guarda nada que possa rodar. A memória de boot o inicia pela sua entrada
// na RAM (número mágico e entrada nos últimos 8 bytes da RAM); ele lê o trabalho que o hospedeiro deixou
// (número mágico, banca de destino, tamanho em bytes, sinalizadores) e a imagem depois dele, apaga e grava a
// banca pelos comandos do controlador da FLASH, lê de volta e para em rv32_wait_restart com o tohost
// preenchido. NOR_JOB_ADDR e NOR_IMAGE_ADDR vêm da construção do riscv-tools (nor_program), os mesmos números
// em que ele carrega os dados do hospedeiro; por virem de -D na linha de comando, são macros.

// Número mágico que abre o trabalho ('NROP').
static constexpr uint32_t NOR_JOB_MAGIC = 0x504F524Eu;
// Palavras reservadas para a cópia da rotina de atualização na SDRAM.
static constexpr uint32_t ROUTINE_WORDS = 256u;

// Buffer da cópia da rotina de atualização.
static uint32_t ram_code[ROUTINE_WORDS];

// Lê o trabalho, grava a banca, e em caso de divergência registra a primeira palavra que difere.
int main(void) {
    volatile uint32_t *job = (volatile uint32_t *)NOR_JOB_ADDR;
    if (job[0] != NOR_JOB_MAGIC) RV32_FAIL(1);
    int status = rv32_update_bank(job[1], (uint8_t *)NOR_IMAGE_ADDR, job[2], job[3], ram_code, ROUTINE_WORDS);
    if (status == RV32_UPDATE_MISMATCH) {
        // informa a primeira palavra que difere após o trabalho: o deslocamento, o que foi enviado e o que o chip guarda
        volatile uint32_t *sent = (volatile uint32_t *)NOR_IMAGE_ADDR;
        volatile uint32_t *chip = (volatile uint32_t *)job[1];
        for (uint32_t i = 0; i < job[2] / 4u; i++) {
            if (sent[i] != chip[i]) {
                job[4] = 4u * i;
                job[5] = sent[i];
                job[6] = chip[i];
                break;
            }
        }
    }
    if (status != RV32_UPDATE_OK) RV32_FAIL(10u + (uint32_t)status);
    RV32_PASS();
}
