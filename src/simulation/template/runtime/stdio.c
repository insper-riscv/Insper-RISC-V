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

/* Este arquivo implementa a biblioteca do runtime, não é um programa: ele define stdin, stdout e stderr,
 * identificadores que a norma reserva à biblioteca (ISO/IEC 9899:2024, 7.1.3 e 6.4.3), como a libc do
 * runtime deve fazer. O __strong_reference é o único recurso fora da norma aqui: é uma macro de
 * <sys/cdefs.h> da picolibc que expande em um atributo GNU de alias, e a norma não tem equivalente para
 * dar a três nomes o mesmo objeto. */

/* Tamanho do buffer de stdout, em bytes. */
static constexpr uint32_t STDOUT_SIZE = 1024u;

/* Cabeçalho do buffer de stdout seguido dos bytes, no layout descrito acima. */
struct stdout_buffer {
    volatile uint32_t length;
    volatile uint32_t truncated;
    volatile char data[STDOUT_SIZE];
};

/* Guarda o byte no buffer de stdout e devolve o byte; o stdio da picolibc o chama. O segundo parâmetro, o
 * fluxo, não é usado e fica sem nome (ISO/IEC 9899:2024, 6.9.2). */
static int rv32_putc(char c, FILE *)
{
    struct stdout_buffer *buf = (struct stdout_buffer *)RV32_STDOUT_BASE;
    uint32_t length = buf->length;

    if (length < STDOUT_SIZE) {
        buf->data[length] = c;
        buf->length = length + 1u;
    } else {
        buf->truncated = 1u;
    }
    return (unsigned char)c;
}

/* Não há entrada: toda leitura informa fim de arquivo. */
static int rv32_getc(FILE *)
{
    return _FDEV_EOF;
}

/* O fluxo único que a picolibc usa para stdin, stdout e stderr. */
static FILE rv32_stdio = FDEV_SETUP_STREAM(rv32_putc, rv32_getc, nullptr, _FDEV_SETUP_RW);

/* stdin e, como alias do mesmo objeto, stdout e stderr. */
FILE *const stdin = &rv32_stdio;
__strong_reference(stdin, stdout);
__strong_reference(stdin, stderr);
