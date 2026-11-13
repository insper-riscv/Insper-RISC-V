/* SPDX-License-Identifier: Apache-2.0
 * One snapshot per host request, acknowledged only after publishing it.
 * The independent time reference is the host monotonic clock, not mtime.
 */
#include <stdint.h>
#include "memory_map.h"

#define SHARED ((volatile uint32_t *)(RV32_STDOUT_BASE + 768u))

int main(void)
{
    __asm__ volatile ("csrci 0x320, 5" ::: "memory");
    SHARED[0] = 0;
    SHARED[1] = 0;
    for (;;) {
        uint32_t request = SHARED[0];
        if (request != SHARED[1]) {
            uint32_t hi, lo, again;
            do {
                __asm__ volatile ("rdcycleh %0\nrdcycle %1\nrdcycleh %2"
                    : "=r" (hi), "=r" (lo), "=r" (again));
            } while (hi != again);
            SHARED[2] = lo;
            SHARED[3] = hi;
            __asm__ volatile ("fence rw,rw" ::: "memory");
            SHARED[1] = request;
        }
    }
}
