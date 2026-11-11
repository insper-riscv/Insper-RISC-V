// RV32_EXT: M
/* SPDX-License-Identifier: Apache-2.0 */
#include <inttypes.h>
#include <stdio.h>
#include "counters.h"
extern void initialise_benchmark(void);
extern void warm_caches(int);
extern int benchmark(void);
extern int verify_benchmark(int);
int main(void) {
    initialise_benchmark();
    warm_caches(1);
    uint64_t c0 = bench_cycles();
    uint64_t i0 = bench_instructions();
    int value = benchmark();
    __asm__ volatile ("fence rw,rw" ::: "memory");
    uint64_t i1 = bench_instructions();
    uint64_t c1 = bench_cycles();
    int verified = verify_benchmark(value) == 1;
    /* Verification and all UART/printf work are outside the measured region. */
    printf("RV32BENCH cycles=%" PRIu64 " instructions=%" PRIu64 " verified=%d\n",
           c1 - c0, i1 - i0, verified);
    return verified ? 0 : 1;
}
