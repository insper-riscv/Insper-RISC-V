/* stdin, stdout and stderr for the picolibc stdio.
 *
 * printf/puts/putchar send every byte through the physical serial UART and
 * also keep the existing copy in RAM for the JTAG and simulation checks.
 * scanf/getchar block until the serial UART receives a byte. The UART is
 * 115200 baud, 8N1, with separate 16-byte TX and RX FIFOs at
 * RV32_UART_BASE (memory_map.h, generated from platform.yaml).
 *
 * The RAM copy is a fixed region at the top of RAM, just below the words
 * the boot ROM clears (tohost, fromhost). rv32im-fpga.specs leaves it out
 * of RAM's size, so the stack never reaches it. The boot ROM clears the
 * header on every start.
 *
 *   +0   length     bytes written, at most STDOUT_SIZE
 *   +4   truncated  1 once a byte did not fit, 0 otherwise
 *   +8   data       STDOUT_SIZE bytes
 *
 * from RV32_STDOUT_BASE (memory_map.h, generated from platform.yaml).
 *
 * The buffer is linear: when it is full, further bytes are dropped from
 * the RAM copy and `truncated` is set, but they still reach the UART.
 * Spike has no UART device, so its build keeps only the RAM copy and reports
 * EOF on input.
 */
#include <stdint.h>
#include <stdio.h>
#include <sys/cdefs.h>

#include "memory_map.h"

#define STDOUT_BASE RV32_STDOUT_BASE
#define STDOUT_SIZE 1024u

#define UART_TX_DATA (*(volatile uint32_t *)(RV32_UART_BASE + 0u))
#define UART_RX_DATA (*(volatile uint32_t *)(RV32_UART_BASE + 4u))
#define UART_STATUS  (*(volatile uint32_t *)(RV32_UART_BASE + 8u))

#define UART_RX_VALID (UINT32_C(1) << 0)
#define UART_TX_READY (UINT32_C(1) << 1)

struct stdout_buffer {
    volatile uint32_t length;
    volatile uint32_t truncated;
    volatile char data[STDOUT_SIZE];
};

/* Programs use the serial path by default. A test concerned only with the
 * RAM mirror can provide a strong definition with value zero. */
__attribute__((weak)) volatile uint32_t rv32_stdio_uart_enabled = 1u;

#ifndef RV32_SPIKE
static void uart_putc(char c)
{
    if (rv32_stdio_uart_enabled == 0u)
        return;
    while ((UART_STATUS & UART_TX_READY) == 0u) {
    }
    UART_TX_DATA = (uint8_t)c;
}

static int uart_getc(void)
{
    if (rv32_stdio_uart_enabled == 0u)
        return _FDEV_EOF;
    while ((UART_STATUS & UART_RX_VALID) == 0u) {
    }
    return (uint8_t)UART_RX_DATA;
}
#else
static void uart_putc(char c) { (void)c; }
static int uart_getc(void) { return _FDEV_EOF; }
#endif

static int rv32_putc(char c, FILE *file)
{
    struct stdout_buffer *buf = (struct stdout_buffer *)STDOUT_BASE;
    uint32_t length = buf->length;

    (void)file;
    uart_putc(c);
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
    return uart_getc();
}

static FILE rv32_stdio = FDEV_SETUP_STREAM(rv32_putc, rv32_getc, NULL, _FDEV_SETUP_RW);

FILE *const stdin = &rv32_stdio;
__strong_reference(stdin, stdout);
__strong_reference(stdin, stderr);
