/* stdout, stdin e stderr da stdio da picolibc (printf, puts, putchar).
 *
 * O núcleo não tem dispositivo de saída, então a saída vai para um buffer na RAM que o
 * hospedeiro lê quando o programa termina: uma região fixa no topo da RAM, logo abaixo das
 * palavras que a BOOT_MEMORY zera (tohost e fromhost). O rv32im-fpga.specs a deixa fora do
 * tamanho da RAM, então a pilha nunca a alcança.
 *
 *   +0   length     bytes escritos, no máximo STDOUT_SIZE
 *   +4   truncated  1 quando um byte não coube, 0 no resto
 *   +8   data       STDOUT_SIZE bytes
 *
 * a partir de RV32_STDOUT_BASE (memory_map.h, gerado do platform.yaml). O buffer é linear:
 * cheio, os bytes seguintes são descartados e `truncated` vale 1. Não há entrada, e a leitura
 * informa fim de arquivo.
 */
#include <stdint.h>
#include <stdio.h>
#include <sys/cdefs.h>

#include "memory_map.h"

#define STDOUT_BASE RV32_STDOUT_BASE
#define STDOUT_SIZE 1024u

struct stdout_buffer {
    volatile uint32_t length;
    volatile uint32_t truncated;
    volatile char data[STDOUT_SIZE];
};

static int rv32_putc(char c, FILE *file)
{
    struct stdout_buffer *buf = (struct stdout_buffer *)STDOUT_BASE;
    uint32_t length = buf->length;

    (void)file;
    if (length < STDOUT_SIZE) {
        buf->data[length] = c;
        buf->length = length + 1u;
    } else {
        buf->truncated = 1u;
    }
    return (unsigned char)c;
}

static int rv32_getc(FILE *file)
{
    (void)file;
    return _FDEV_EOF;
}

static FILE rv32_stdio = FDEV_SETUP_STREAM(rv32_putc, rv32_getc, NULL, _FDEV_SETUP_RW);

FILE *const stdin = &rv32_stdio;
__strong_reference(stdin, stdout);
__strong_reference(stdin, stderr);
