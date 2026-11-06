/* boot_rom.S: o carregador fixo da plataforma, gravado na BOOT_ROM. Ele não sabe qual programa
 * (conteúdo da ROM) está iniciando.
 *
 * Faz duas coisas.
 *
 *  - _reset (endereço 0): zera as palavras que o hospedeiro e o programa compartilham, no topo da
 *    RAM (o cabeçalho do stdout, tohost e fromhost, nos endereços de memory_map.h, que
 *    `riscv-tools generate-memory-map` escreve a partir do platform.yaml), e salta para o início
 *    da ROM, onde está o crt0 (_start, do rv32im-fpga.specs). O crt0 copia .data para a RAM,
 *    zera .bss e chama main; main retornando cai em _exit (_exit.c).
 *
 *  - rv32_wait_restart (fixo em 0x100, ver boot_rom.ld): onde todo programa termina. Ele
 *    segura o núcleo até o hospedeiro escrever fromhost e recomeça em _reset.
 *
 * As palavras precisam estar zeradas a cada entrada: um tohost antigo diferente de zero parece
 * "já terminou", e a saída do programa anterior não pode vazar para o próximo.
 */

#include "memory_map.h"

    .section .text.reset
    .global _reset
_reset:
    li   t0, RV32_RAM_END
    sw   x0, RV32_FROMHOST_ADDR - RV32_RAM_END(t0)
    sw   x0, RV32_FROMHOST_ADDR - RV32_RAM_END + 4(t0)
    sw   x0, RV32_TOHOST_ADDR - RV32_RAM_END(t0)
    sw   x0, RV32_TOHOST_ADDR - RV32_RAM_END + 4(t0)
    li   t0, RV32_STDOUT_BASE    // cabeçalho do stdout
    sw   x0, 0(t0)               // tamanho
    sw   x0, 4(t0)               // truncado
    li   t0, RV32_BOOT_ENTRY     // o _start do crt0
    jr   t0

    /* O programa já escreveu tohost (1 = passou, (código << 1) | 1 = falhou). O núcleo espera
     * aqui até o hospedeiro escrever um valor diferente de zero em fromhost, e recomeça em
     * _reset, que zera as duas palavras. */
    .section .text.wait_restart
    .global rv32_wait_restart
rv32_wait_restart:
    li   t0, RV32_RAM_END

rv32_wait_restart_poll:
    lw   t1, RV32_FROMHOST_ADDR - RV32_RAM_END(t0)
    beqz t1, rv32_wait_restart_poll
    j    _reset
