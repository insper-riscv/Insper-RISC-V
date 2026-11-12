/* O _exit em que o crt0 da toolchain termina: main retornando (ou exit()) cai aqui, e a picolibc
 * não o fornece.
 *
 * Informa o resultado em tohost: código 0 é aprovado (1), qualquer outro é falha
 * ((código << 1) | 1). Depois entrega o núcleo ao rv32_wait_restart da BOOT_MEMORY, num endereço
 * fixo que o arquivo de specs lhe dá; a imagem do Spike usa o spike_exit.S.
 */
#include <stdint.h>

#include "memory_map.h"

/* Este arquivo implementa a biblioteca do runtime, não é um programa: ele define _exit, identificador que a
 * norma reserva à biblioteca (ISO/IEC 9899:2024, 7.1.3 e 6.4.3), como a libc do runtime deve fazer. */

/* A rotina da BOOT_MEMORY que espera o host carregar o próximo teste; não retorna. Declarada com o atributo
 * padrão [[noreturn]] (6.7.13.7), que precisa estar na primeira declaração. */
[[noreturn]] extern void rv32_wait_restart(void);

/* Declaração de _exit, para que a definição tenha protótipo anterior (-Wmissing-prototypes) e o [[noreturn]]
 * conste desde a primeira declaração (6.7.13.7). */
[[noreturn]] void _exit(int code);

/* Grava em tohost o resultado (1 para código 0, (código << 1) | 1 nos demais) e entrega o núcleo ao
 * rv32_wait_restart. */
void _exit(int code)
{
    volatile uint32_t *tohost = (volatile uint32_t *)RV32_TOHOST_ADDR;
    tohost[0] = code == 0 ? 1u : (((uint32_t)code << 1) | 1u);
    tohost[1] = 0u;
    rv32_wait_restart();
}
