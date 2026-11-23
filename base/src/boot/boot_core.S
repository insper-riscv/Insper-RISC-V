/* boot_core.S: o núcleo comum do carregador fixo (a "máscara") de toda plataforma. Cada
 * `boot_memory.S` das plataformas é só um invólucro que inclui os cabeçalhos gerados e este arquivo.
 * O carregador é gravado uma vez na BOOT_MEMORY e não conhece o programa que inicia: sabe apenas
 * como uma imagem está disposta na FLASH. Não faz `sp`, `gp`, `tp`, `.data` nem `.bss`, que são do
 * `crt0` do programa.
 *
 * O invólucro inclui, antes deste arquivo e nesta ordem, `memory_map.h`, `flash_banks.h` (só a
 * plataforma com dois bancos de FLASH) e `boot_config.h`, todos gerados por
 * `riscv-tools generate-memory-map` a partir do `platform.yaml`. Duas chaves dependem deles.
 *
 *  - `RV32_TEST_WAIT` (a chave `boot.wait_restart` do `platform.yaml`) separa a BOOT de teste da de
 *    aplicação. Na de teste, `_reset` limpa `tohost`, `fromhost` e o cabeçalho do `stdout`, e o ponto
 *    de espera `rv32_wait_restart` fica fixo em 0x100 (ver boot_memory.ld), onde todo teste termina.
 *    Na de aplicação nada disso existe e o símbolo não é exportado.
 *  - `RV32_BANK_A_BASE` (de `flash_banks.h`) liga a escolha entre os bancos A e B da FLASH. Sem ela
 *    a BOOT salta direto para `RV32_BOOT_ENTRY`.
 *
 * Sequência de `_reset`:
 *
 *  1. Só na BOOT de teste, zera as palavras que o hospedeiro e o programa compartilham, nos endereços
 *     de memory_map.h. Elas precisam estar limpas a cada entrada, partida fria ou reinício: um
 *     `tohost` antigo diferente de zero parece "já terminou", e a saída do teste anterior não pode
 *     vazar para o próximo.
 *  2. Zera `x1` a `x31` (`x1` a `x15` no RV32E).
 *  3. Inclui os fragmentos do Core, um por extensão, sempre nesta ordem: Zicsr, Zicntr, Zihpm,
 *     Sscofpmf e Zifencei. Cada um se desliga sozinho com `#if RV32_HAS_<EXTENSÃO>`, usa só `t0`,
 *     `t1` e `t2` e rótulos numéricos locais. O `fence.i` é o do fragmento Zifencei, e por isso só
 *     existe quando o núcleo tem Zifencei.
 *  4. Se a plataforma define `RV32_BOOT_RAM_MAGIC`, aceita um programa deixado na RAM pelo
 *     hospedeiro: a palavra em `RV32_RAM_END - 8` com a magia e a em `RV32_RAM_END - 4` com o ponto
 *     de entrada. A magia é apagada, então a entrada vale uma vez.
 *  5. Com bancos, valida os dois (magia, CRC do cabeçalho, tamanho e CRC do conteúdo) e salta para a
 *     entrada (base + tamanho do cabeçalho) do banco válido de maior versão, A num empate. Um banco
 *     que não valida é descartado, então uma gravação interrompida cai para o outro. Sem banco
 *     válido, espera lendo `fromhost` e recomeça em `_reset` (a salvaguarda, nos dois builds).
 *     Sem bancos, salta para `RV32_BOOT_ENTRY`.
 *     O programa entra com a0 = 0 (o hart) e a1 = 0.
 *
 * O cabeçalho de 256 bytes de cada banco é escrito por último pela rotina de atualização, então um
 * banco de cabeçalho válido é um banco cuja gravação terminou:
 *
 *   +0 magia (RV32_IMAGE_MAGIC)   +4 tamanho do conteúdo em bytes
 *   +8 CRC-32 do conteúdo        +12 versão (maior é mais nova)
 *   +16 CRC-32 dos 16 primeiros bytes do cabeçalho
 *
 * (o formato do `riscv-tools flash-image`, src/riscv_tools/flash_image/header.py).
 *
 * `fromhost` é só a campainha e nunca o endereço de salto: o endereço vem do cabeçalho de um banco
 * que passou na validação.
 *
 * Só os registradores do RV32E são usados depois da zeragem (x1 a x15), e as rotinas são folhas que
 * voltam por `ra`, ou por `tp` no laço do CRC. O CRC-32 é o bit a bit (IEEE 802.3, polinômio
 * refletido 0xEDB88320), uma palavra de 32 bits por vez e sem tabela, porque a BOOT_MEMORY é só de
 * instruções: 5 instruções por bit, desenroladas para que uma palavra custe só o desvio do laço.
 *
 * Layout: `_reset` fica sozinho em `.text.reset` (o primeiro desvio), e todo o resto em
 * `.text.wait_restart`, a seção que os dois linker scripts gerados colocam logo depois. Na BOOT de
 * teste ela começa em 0x100, com `rv32_wait_restart` na primeira instrução.
 */

#ifndef RV32_BOOT_CONFIG_H
#error "boot_core.S: inclua memory_map.h, flash_banks.h e boot_config.h antes deste arquivo"
#endif

#define CRC_POLY 0xEDB88320

#ifdef RV32_BANK_A_BASE
#define BOOT_HAS_BANKS 1
#else
#define BOOT_HAS_BANKS 0
#endif

#if BOOT_HAS_BANKS || RV32_TEST_WAIT || defined(RV32_BOOT_RAM_MAGIC)
#ifndef RV32_RAM_END
#error "boot_core.S: memory_map.h sem RV32_RAM_END"
#endif
#endif

    .section .text.reset
    .global _reset
_reset:
    j    boot_start

    .section .text.wait_restart

#if BOOT_HAS_BANKS || RV32_TEST_WAIT
    /* O ponto de espera. Na BOOT de teste é onde o teste termina, depois de escrever tohost
     * (1 = passou, (código << 1) | 1 = falhou, ver rv32_test.h), e onde a BOOT para quando nenhum
     * banco é válido. O núcleo espera até o hospedeiro gravar uma nova imagem na FLASH e um valor
     * diferente de zero em fromhost, e recomeça em _reset. Ele mora aqui, e não na FLASH, porque a
     * FLASH é regravada enquanto o núcleo espera. Na BOOT de aplicação só serve à salvaguarda e o
     * símbolo não é exportado. */
#if RV32_TEST_WAIT
    .global rv32_wait_restart
rv32_wait_restart:
#endif
boot_park:
    li   t0, RV32_RAM_END

boot_park_poll:
    lw   t1, RV32_FROMHOST_ADDR - RV32_RAM_END(t0)
    beqz t1, boot_park_poll
    j    _reset
#endif

    /* O tratador de trap seguro que os fragmentos do Core escrevem em mtvec. Um trap durante a BOOT
     * (ou no programa antes de instalar o próprio tratador) para o núcleo aqui, em vez de reiniciar
     * sem fim. Alinhado a 4 bytes, como o modo direto do mtvec exige. */
    .balign 4
    .global rv32_boot_trap
rv32_boot_trap:
    j    rv32_boot_trap

boot_start:
#if RV32_TEST_WAIT
    li   t0, RV32_RAM_END
    sw   x0, RV32_FROMHOST_ADDR - RV32_RAM_END(t0)
    sw   x0, RV32_FROMHOST_ADDR - RV32_RAM_END + 4(t0)
    sw   x0, RV32_TOHOST_ADDR - RV32_RAM_END(t0)
    sw   x0, RV32_TOHOST_ADDR - RV32_RAM_END + 4(t0)
    li   t0, RV32_STDOUT_BASE    // cabeçalho do stdout
    sw   x0, 0(t0)               // tamanho
    sw   x0, 4(t0)               // truncado
#endif

    .irp r, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
    li   x\r, 0
    .endr
#if !RV32_IS_E
    .irp r, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31
    li   x\r, 0
    .endr
#endif

    /* Os fragmentos usam csr* e fence.i, que o montador só aceita com Zicsr e Zifencei no -march, e o
     * -march da BOOT é só a base (rv32i ou rv32e). A diretiva liga as duas extensões para o montador
     * e só aqui: cada fragmento se desliga sozinho com #if RV32_HAS_<EXTENSÃO>, então nenhuma
     * instrução de extensão sai num núcleo que não a tem. */
    .option push
    .option arch, +zicsr, +zifencei
#include "../../../Core/src/Zicsr/boot.inc"
#include "../../../Core/src/Zicntr/boot.inc"
#include "../../../Core/src/Zihpm/boot.inc"
#include "../../../Core/src/Sscofpmf/boot.inc"
#include "../../../Core/src/Zifencei/boot.inc"
    .option pop

#ifdef RV32_BOOT_RAM_MAGIC
    li   t0, RV32_RAM_END        // programa deixado na RAM pelo hospedeiro (magia e entrada nos 8 últimos bytes)
    lw   t1, -8(t0)
    li   t2, RV32_BOOT_RAM_MAGIC
#if BOOT_HAS_BANKS
    bne  t1, t2, bank_select
#else
    bne  t1, t2, boot_flash
#endif
    lw   a2, -4(t0)
    sw   x0, -8(t0)              // uma vez: o próximo reinício volta à FLASH
    jr   a2
#endif

#if BOOT_HAS_BANKS
    /* s0/s1: A válido (1) ou não (0) e sua versão; gp/tp: o mesmo para B. */
bank_select:
    li   a2, RV32_BANK_A_BASE
    li   a3, RV32_BANK_A_SIZE
    jal  ra, bank_check
    mv   s0, a0
    mv   s1, a1
    li   a2, RV32_BANK_B_BASE
    li   a3, RV32_BANK_B_SIZE
    jal  ra, bank_check
    mv   gp, a0
    mv   tp, a1
    beqz s0, bank_a_invalid
    beqz gp, boot_a             // só A é válido
    bltu s1, tp, boot_b         // os dois: B só quando estritamente mais nova
boot_a:
    li   t0, RV32_BANK_A_ENTRY
    j    boot_go
bank_a_invalid:
    beqz gp, boot_park          // nenhum banco válido: espera, seguro
boot_b:
    li   t0, RV32_BANK_B_ENTRY
boot_go:
    li   a0, 0                  // id do hart
    li   a1, 0
    jr   t0

    /* bank_check: a2 = base do banco, a3 = tamanho do banco.
     * Devolve a0 = 1 e a1 = versão quando a imagem é válida, a0 = 0 senão.
     * Altera t0-t2, sp, gp, tp, a4, a5. */
bank_check:
    lw   t0, 0(a2)
    li   t1, RV32_IMAGE_MAGIC
    bne  t0, t1, bank_bad
    mv   sp, a2                 // o CRC do cabeçalho cobre as 4 primeiras palavras
    li   gp, 4
    li   a4, -1
    jal  tp, crc_words
    not  a4, a4
    lw   t0, 16(a2)
    bne  a4, t0, bank_bad
    lw   a5, 4(a2)              // tamanho do conteúdo: não nulo, palavras inteiras, dentro do banco
    beqz a5, bank_bad
    andi t0, a5, 3
    bnez t0, bank_bad
    addi t0, a3, -RV32_IMAGE_HEADER_SIZE
    bltu t0, a5, bank_bad
    addi sp, a2, RV32_IMAGE_HEADER_SIZE
    srli gp, a5, 2
    li   a4, -1
    jal  tp, crc_words
    not  a4, a4
    lw   t0, 8(a2)
    bne  a4, t0, bank_bad
    lw   a1, 12(a2)
    li   a0, 1
    ret
bank_bad:
    li   a0, 0
    ret

    /* crc_words: sp = endereço, gp = número de palavras, a4 = registrador do CRC.
     * Devolve o registrador em a4 (ainda não invertido) e volta por tp.
     * Altera t0-t2, sp, gp. */
crc_words:
    li   t2, CRC_POLY
crc_next_word:
    beqz gp, crc_done
    lw   t0, 0(sp)
    xor  a4, a4, t0
    .rept 32                    // um bit por passo, em linha reta: nenhum desvio dentro da palavra
    andi t0, a4, 1
    neg  t0, t0                 // todos os bits em 1 quando o bit baixo está ligado
    and  t0, t0, t2
    srli a4, a4, 1
    xor  a4, a4, t0
    .endr
    addi sp, sp, 4
    addi gp, gp, -1
    j    crc_next_word
crc_done:
    jr   tp
#else
boot_flash:
    li   t0, RV32_BOOT_ENTRY     // o _start do crt0
    li   a0, 0                   // o hart (contrato de entrada: a0 = 0, a1 = 0)
    li   a1, 0
    jr   t0
#endif
