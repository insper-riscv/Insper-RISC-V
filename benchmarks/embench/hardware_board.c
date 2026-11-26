/* SPDX-License-Identifier: Apache-2.0
 * Hardware-only Embench port. No UART or host activity enters the ROI.
 * Requires the platform's machine counters (Zicsr + Zicntr).
 * Uses 32 bytes in the otherwise unused reserved stdout payload.
 */
#include <stdint.h>
#include "memory_map.h"
#include "support.h"

#define RESULT ((volatile uint32_t *)(RV32_STDOUT_BASE + 768u))

void initialise_board(void)
{
    RESULT[0] = 0;
}

void start_trigger(void)
{
    __asm__ volatile (
        "csrsi 0x320, 5\n"
        "csrw 0xb00, zero\ncsrw 0xb80, zero\n"
        "csrw 0xb02, zero\ncsrw 0xb82, zero\n"
        "csrci 0x320, 5\n" ::: "memory");
}

void stop_trigger(void)
{
    uint32_t cycles, cycles_hi, instructions, instructions_hi;
    __asm__ volatile (
        "csrsi 0x320, 5\n"
        "csrr %0, 0xb00\ncsrr %1, 0xb80\n"
        "csrr %2, 0xb02\ncsrr %3, 0xb82\n"
        : "=r" (cycles), "=r" (cycles_hi),
          "=r" (instructions), "=r" (instructions_hi) :: "memory");
    RESULT[1] = 1;
    RESULT[2] = cycles;
    RESULT[3] = cycles_hi;
    RESULT[4] = instructions;
    RESULT[5] = instructions_hi;
    __asm__ volatile ("fence rw,rw" ::: "memory");
    RESULT[0] = 0x454d4248u;
}
