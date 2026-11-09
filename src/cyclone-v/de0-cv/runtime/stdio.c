/* stdout, stdin e stderr da stdio da picolibc (printf, puts, putchar).
 *
 * O núcleo não tem dispositivo de saída, então a saída vai para um buffer na RAM que o hospedeiro lê pela
 * JTAG quando o teste termina: uma região fixa no topo da RAM, logo abaixo das palavras que a BOOT_MEMORY
 * zera (tohost e fromhost). O rv32im-fpga.specs a deixa fora do tamanho da RAM, então a pilha nunca a
 * alcança. A BOOT_MEMORY zera o cabeçalho a cada partida.
 *
 *   +0   length     bytes escritos, no máximo STDOUT_SIZE
 *   +4   truncated  1 quando um byte não coube, 0 no resto
 *   +8   data       STDOUT_SIZE bytes
 *
 * a partir de RV32_STDOUT_BASE (memory_map.h, gerado do platform.yaml).
 *
 * O buffer é linear: cheio, os bytes seguintes são descartados e `truncated` vale 1. Não há entrada, e a
 * leitura informa fim de arquivo.
 *
 * Cada byte também vai à UART JTAG, que um console do hospedeiro lê enquanto o programa roda. A UART é uma
 * vista ao vivo: o buffer continua sendo a cópia que o teste confere. Um programa só imprime na UART depois
 * que um hospedeiro a varreu (bit 17 do registrador de estado), de modo que um sem ninguém ouvindo nunca é
 * atrasado; quando alguém ouve, ele espera um lugar na fila, até um limite, e então descarta o byte. O
 * Spike não tem esse dispositivo: a sua construção pula a UART.
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

#ifndef RV32_SPIKE
/* Máximo de leituras do estado da UART à espera de lugar na fila de transmissão. */
static constexpr uint32_t UART_WAIT_POLLS = 200000u;
#endif

/* Registradores de dados de transmissão e de estado da UART JTAG. Ficam como macros porque um ponteiro para
 * endereço fixo não pode ser constexpr (ISO/IEC 9899:2024, 6.7.2: só o ponteiro nulo); o acesso é volatile
 * (6.7.4.1) e alinhado a palavra. */
#define UART_TXDATA ((volatile uint32_t *)RV32_UART_BASE)
#define UART_STATUS ((volatile uint32_t *)(RV32_UART_BASE + 8u))

/* Lugares livres na fila de transmissão, tirados do registrador de estado (bits 7 a 0). */
static inline uint32_t uart_free(uint32_t status)
{
    return status & 0xFFu;
}

/* Diz se um hospedeiro varreu a UART (bit 17 do registrador de estado). */
static inline bool uart_attached(uint32_t status)
{
    return ((status >> 17) & 1u) != 0u;
}

/* Cabeçalho do buffer de stdout seguido dos bytes, no layout descrito acima. */
struct stdout_buffer {
    volatile uint32_t length;
    volatile uint32_t truncated;
    volatile char data[STDOUT_SIZE];
};

#ifndef RV32_SPIKE
/* Envia um byte à UART quando há um hospedeiro ouvindo, esperando lugar na fila até o limite. */
static void uart_put(char c)
{
    uint32_t status = *UART_STATUS;

    if (!uart_attached(status))
        return;
    for (uint32_t polls = 0; uart_free(status) == 0u; polls++) {
        if (polls == UART_WAIT_POLLS)
            return;
        status = *UART_STATUS;
    }
    *UART_TXDATA = (uint8_t)c;
}
#else
/* O Spike não tem a UART: o byte é descartado. */
static void uart_put(char)
{
}
#endif

/* Guarda o byte no buffer de stdout (e o envia à UART) e devolve o byte; o stdio da picolibc o chama. O
 * segundo parâmetro, o fluxo, não é usado e fica sem nome (ISO/IEC 9899:2024, 6.9.2). */
static int rv32_putc(char c, FILE *)
{
    struct stdout_buffer *buf = (struct stdout_buffer *)RV32_STDOUT_BASE;
    uint32_t length = buf->length;

    uart_put(c);
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
