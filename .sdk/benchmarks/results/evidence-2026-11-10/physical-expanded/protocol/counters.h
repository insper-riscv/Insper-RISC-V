/* SPDX-License-Identifier: Apache-2.0 */
#ifndef RV32_BENCH_COUNTERS_H
#define RV32_BENCH_COUNTERS_H
#include <stdint.h>
/* Read high/low/high so rollover of the low half cannot tear a snapshot.
 * The memory clobber prevents compiler motion across measurement boundaries. */
#define RV32_COUNTER(name, low_csr, high_csr) \
static inline uint64_t name(void) { \
    uint32_t high, low, again; \
    do { \
        __asm__ volatile (".option push\n.option arch,+zicsr\n" \
            "csrr %0, " #high_csr "\ncsrr %1, " #low_csr \
            "\ncsrr %2, " #high_csr "\n.option pop" \
            : "=&r"(high), "=&r"(low), "=&r"(again) :: "memory"); \
    } while (high != again); \
    return ((uint64_t)high << 32) | low; \
}
RV32_COUNTER(bench_cycles, 0xb00, 0xb80)
RV32_COUNTER(bench_instructions, 0xb02, 0xb82)
#endif
