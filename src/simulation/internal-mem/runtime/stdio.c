/* stdin, stdout e stderr da stdio da picolibc.
 *
 * printf/puts/putchar enviam cada byte pela UART serial física e também mantêm a cópia existente na RAM
 * para as conferências da JTAG e da simulação. scanf/getchar bloqueiam até a UART serial receber um byte. A
 * UART tem 115200 baud, 8N1, com FIFOs de TX e de RX separadas de 16 bytes, em RV32_UART_BASE (memory_map.h,
 * gerado do platform.yaml).
 *
 * A cópia na RAM é uma região fixa no topo da RAM, logo abaixo das palavras que a BOOT_MEMORY zera (tohost,
 * fromhost). O rv32im-fpga.specs a deixa fora do tamanho da RAM, então a pilha nunca a alcança. A
 * BOOT_MEMORY zera o cabeçalho a cada partida.
 *
 *   +0   length     bytes escritos, no máximo STDOUT_SIZE
 *   +4   truncated  1 quando um byte não coube, 0 no resto
 *   +8   data       STDOUT_SIZE bytes
 *
 * a partir de RV32_STDOUT_BASE (memory_map.h, gerado do platform.yaml).
 *
 * O buffer é linear: cheio, os bytes seguintes são descartados da cópia na RAM e `truncated` vale 1, mas
 * ainda chegam à UART. O Spike não tem dispositivo de UART, então a sua construção mantém só a cópia na RAM
 * e informa EOF na entrada.
 */
#include <stdint.h>
#include <stdio.h>
#include <sys/cdefs.h>

#include "memory_map.h"

/* Este arquivo implementa a biblioteca do runtime, não é um programa: ele define stdin, stdout e stderr,
 * identificadores que a norma reserva à biblioteca (ISO/IEC 9899:2024, 7.1.3 e 6.4.3), como a libc do
 * runtime deve fazer. O __strong_reference e o atributo [[gnu::weak]] são os recursos fora da norma aqui: o primeiro é uma macro de
 * <sys/cdefs.h> da picolibc que expande em um atributo GNU de alias, e a norma não tem equivalente para
 * dar a três nomes o mesmo objeto; o segundo marca um símbolo fraco, que a norma também não oferece. */

/* Tamanho do buffer de stdout, em bytes. */
static constexpr uint32_t STDOUT_SIZE = 1024u;

#ifndef RV32_SPIKE
/* Bit do registrador de estado que indica um byte na FIFO de recepção. */
static constexpr uint32_t UART_RX_VALID = UINT32_C(1) << 0;

/* Bit do registrador de estado que indica lugar na FIFO de transmissão. */
static constexpr uint32_t UART_TX_READY = UINT32_C(1) << 1;
#endif

/* Registradores de transmissão, de recepção e de estado da UART serial. Ficam como macros porque o lvalue de
 * um endereço fixo não pode ser constexpr (ISO/IEC 9899:2024, 6.7.2: só o ponteiro nulo); o acesso é volatile
 * (6.7.4.1) e alinhado a palavra. */
#define UART_TX_DATA (*(volatile uint32_t *)(RV32_UART_BASE + 0u))
#define UART_RX_DATA (*(volatile uint32_t *)(RV32_UART_BASE + 4u))
#define UART_STATUS  (*(volatile uint32_t *)(RV32_UART_BASE + 8u))

/* Cabeçalho do buffer de stdout seguido dos bytes, no layout descrito acima. */
struct stdout_buffer {
    volatile uint32_t length;
    volatile uint32_t truncated;
    volatile char data[STDOUT_SIZE];
};

/* Os programas usam o caminho serial por padrão. Um teste que só se interessa pelo espelho na RAM pode
 * fornecer uma definição forte com valor zero. [[gnu::weak]] não tem equivalente na norma. */
[[gnu::weak]] volatile uint32_t rv32_stdio_uart_enabled = 1u;

#ifndef RV32_SPIKE
/* Envia um byte à UART serial, esperando lugar na FIFO; não faz nada se o caminho serial está desligado. */
static void uart_putc(char c)
{
    if (rv32_stdio_uart_enabled == 0u)
        return;
    while ((UART_STATUS & UART_TX_READY) == 0u) {
    }
    UART_TX_DATA = (uint8_t)c;
}

/* Lê um byte da UART serial, esperando um chegar; informa EOF se o caminho serial está desligado. */
static int uart_getc(void)
{
    if (rv32_stdio_uart_enabled == 0u)
        return _FDEV_EOF;
    while ((UART_STATUS & UART_RX_VALID) == 0u) {
    }
    return (uint8_t)UART_RX_DATA;
}
#else
/* O Spike não tem a UART: o byte é descartado. */
static void uart_putc(char)
{
}

/* O Spike não tem a UART: a entrada informa EOF. */
static int uart_getc(void)
{
    return _FDEV_EOF;
}
#endif

/* Envia o byte à UART, guarda-o no buffer de stdout e devolve o byte; o stdio da picolibc o chama. O
 * segundo parâmetro, o fluxo, não é usado e fica sem nome (ISO/IEC 9899:2024, 6.9.2). */
static int rv32_putc(char c, FILE *)
{
    struct stdout_buffer *buf = (struct stdout_buffer *)RV32_STDOUT_BASE;
    uint32_t length = buf->length;

    uart_putc(c);
    if (length < STDOUT_SIZE) {
        buf->data[length] = c;
        buf->length = length + 1u;
    } else {
        buf->truncated = 1u;
    }
    return (unsigned char)c;
}

/* Lê um byte da UART serial para o scanf e o getchar. */
static int rv32_getc(FILE *)
{
    return uart_getc();
}

/* O fluxo único que a picolibc usa para stdin, stdout e stderr. */
static FILE rv32_stdio = FDEV_SETUP_STREAM(rv32_putc, rv32_getc, nullptr, _FDEV_SETUP_RW);

/* stdin e, como alias do mesmo objeto, stdout e stderr. */
FILE *const stdin = &rv32_stdio;
__strong_reference(stdin, stdout);
__strong_reference(stdin, stderr);
