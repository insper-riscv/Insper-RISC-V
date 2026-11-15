// RV32_EXT: M,Zicsr,Zicntr
// RV32_TEST_KIND: unit
// RV32_TIMEOUT_S: 60
/* Teste de teclado da plataforma doom na placa: uma seta apertada e solta.
 *
 * O teste liga a interrupção de recepção do teclado PS/2 (KBD, memory_map.h) e espera até 30 segundos o make e o
 * break de uma seta (conjunto 2 de scancodes: E0 seguido do código para apertar, e E0 F0 seguido do código para
 * soltar; cima 75, esquerda 6B, direita 74 e baixo 72). Imprime cada byte lido em hexadecimal na saída do console,
 * confere que a linha de interrupção do teclado chegou ao PLIC e que os cinco bytes são os de uma seta.
 * O resultado sai como o código de retorno de main: zero é aprovado e cada checagem que falha devolve o próprio
 * código. O Spike não tem o teclado, então nele main devolve zero sem tocar no dispositivo.
 *
 * Sem ninguém no teclado o teste termina com o código 3, e o transmissor e o estado do periférico já foram
 * conferidos antes (códigos 1 e 2).
 */
#include <stdint.h>
#include <stdio.h>

#include "doom_clock.h"
#include "memory_map.h"

#ifndef RV32_SPIKE

/* Offsets, em bytes a partir da base do teclado, dos registradores. */
static constexpr uint32_t REG_DATA = 0x00u;
static constexpr uint32_t REG_STATUS = 0x04u;
static constexpr uint32_t REG_CONTROL = 0x0Cu;

/* Bits do registrador de estado e do de controle. */
static constexpr uint32_t STATUS_RX_VALID = 1u << 0;
static constexpr uint32_t STATUS_TX_READY = 1u << 1;
static constexpr uint32_t STATUS_ERRORS = (1u << 2) | (1u << 3);
static constexpr uint32_t CONTROL_RX_IRQ = 1u << 0;

/* O prefixo estendido, o prefixo de soltar e os códigos das quatro setas. */
static constexpr uint32_t PREFIX_EXTENDED = 0xE0u;
static constexpr uint32_t PREFIX_BREAK = 0xF0u;
static constexpr uint32_t ARROW_CODES[4] = {0x75u, 0x6Bu, 0x74u, 0x72u};

/* Os bytes de uma seta apertada e solta, e o tempo de espera (30 s a 1 MHz). */
static constexpr uint32_t SEQUENCE_LENGTH = 5u;
static constexpr uint32_t WAIT_TICKS = 30000000u;

#define KBD_REG(offset) ((volatile uint32_t *)(RV32_KBD_BASE + (offset)))
#define PLIC_PENDING_WORD ((volatile uint32_t *)RV32_PLIC_PENDING)

/* Imprime um byte em dois dígitos hexadecimais e um espaço, só com putchar: o printf da libc não cabe na banca da
 * FLASH de 4 KiB em que o teste é ligado. */
static void print_byte(uint32_t value)
{
    static constexpr char DIGITS[] = "0123456789ABCDEF";
    putchar(DIGITS[(value >> 4) & 0xFu]);
    putchar(DIGITS[value & 0xFu]);
    putchar(' ');
}

/* Diz se um código é o de uma das quatro setas. */
static bool is_arrow(uint32_t code)
{
    for (uint32_t index = 0u; index < 4u; index++) {
        if (ARROW_CODES[index] == code) {
            return true;
        }
    }
    return false;
}

/* Confere que cinco bytes são E0 c E0 F0 c, com c o código de uma seta. */
static bool is_arrow_press_and_release(const uint32_t bytes[SEQUENCE_LENGTH])
{
    return bytes[0] == PREFIX_EXTENDED && is_arrow(bytes[1]) && bytes[2] == PREFIX_EXTENDED &&
           bytes[3] == PREFIX_BREAK && bytes[4] == bytes[1];
}

/* Espera um byte na fila e o devolve; devolve -1 se o limite de tempo passou. */
static int32_t read_byte(uint32_t start)
{
    while (doom_clock_read_ticks() - start < WAIT_TICKS) {
        if ((*KBD_REG(REG_STATUS) & STATUS_RX_VALID) != 0u) {
            return (int32_t)(*KBD_REG(REG_DATA) & 0xFFu);
        }
    }
    return -1;
}

#endif /* RV32_SPIKE */

int main(void)
{
#ifdef RV32_SPIKE
    return 0;
#else
    uint32_t status = *KBD_REG(REG_STATUS);
    if ((status & STATUS_TX_READY) == 0u) {
        return 1;
    }
    if ((status & STATUS_ERRORS) != 0u) {
        return 2;
    }
    *KBD_REG(REG_CONTROL) = CONTROL_RX_IRQ;
    uint32_t bytes[SEQUENCE_LENGTH] = {};
    uint32_t start = doom_clock_read_ticks();
    for (uint32_t index = 0u; index < SEQUENCE_LENGTH; index++) {
        int32_t value = read_byte(start);
        if (value < 0) {
            return 3;
        }
        bytes[index] = (uint32_t)value;
        print_byte((uint32_t)value);
        if (index == 0u && (*PLIC_PENDING_WORD & (1u << RV32_IRQ_KBD)) == 0u) {
            return 4;
        }
    }
    putchar('\n');
    return is_arrow_press_and_release(bytes) ? 0 : 5;
#endif
}
