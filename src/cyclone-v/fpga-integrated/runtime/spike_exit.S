/* O que a BOOT_MEMORY faz no fim de um programa, para o ELF que o Spike executa.
 *
 * No hardware, rv32_wait_restart é código da BOOT_MEMORY num endereço fixo (rv32im-fpga.specs) e a
 * imagem do programa não tem nada ali. O Spike executa só a imagem do programa, então este
 * arquivo, ligado apenas a esse ELF (compilado com -DRV32_SPIKE, que tira o endereço fixo do
 * link), fornece a rotina. O programa já escreveu tohost, onde o Spike para, então a rotina só
 * espera.
 *
 * tohost e fromhost, que o Spike procura por nome, são as palavras do topo da RAM que a
 * BOOT_MEMORY reserva (ver boot_memory.S), como símbolos absolutos: este arquivo não ocupa espaço no
 * ELF, então todo endereço nele é o da imagem que o hardware carrega.
 */
#include "memory_map.h"

    .equ tohost, RV32_TOHOST_ADDR
    .equ fromhost, RV32_FROMHOST_ADDR
    .global tohost
    .global fromhost

    .section .text
    .global rv32_wait_restart
rv32_wait_restart:
1:  j    1b
