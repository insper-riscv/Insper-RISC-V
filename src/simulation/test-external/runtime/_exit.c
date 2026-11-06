/* O _exit em que o crt0 da toolchain termina: main retornando (ou exit()) cai aqui, e a picolibc
 * não o fornece.
 *
 * Informa o resultado em tohost: código 0 é aprovado (1), qualquer outro é falha
 * ((código << 1) | 1). Depois entrega o núcleo ao rv32_wait_restart da BOOT_ROM, num endereço
 * fixo que o arquivo de specs lhe dá; a imagem do Spike usa o spike_exit.S.
 */
#include "memory_map.h"

extern void rv32_wait_restart(void) __attribute__((noreturn));

void _exit(int code)
{
    volatile unsigned int *tohost = (volatile unsigned int *)RV32_TOHOST_ADDR;
    tohost[0] = code == 0 ? 1u : (((unsigned int)code << 1) | 1u);
    tohost[1] = 0u;
    rv32_wait_restart();
}
