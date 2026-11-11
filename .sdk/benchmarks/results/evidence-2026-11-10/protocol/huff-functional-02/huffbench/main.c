// RV32_EXT: M
/* SPDX-License-Identifier: Apache-2.0 */
#include <stdio.h>
#include "counters.h"
extern void initialise_benchmark(void);
extern void warm_caches(int);
extern int evidence_once(void);
extern int verify_benchmark(int);
static char *append_number(char *out, uint64_t value) {
    char reverse[20];
    unsigned count = 0;
    do { reverse[count++] = (char)('0' + value % 10); value /= 10; } while (value);
    while (count) *out++ = reverse[--count];
    return out;
}
static char *append_text(char *out, const char *text) {
    while (*text) *out++ = *text++;
    return out;
}
int main(void) {
    initialise_benchmark();
    /* correctness-only: no warm-up */
    uint64_t c0 = bench_cycles();
    uint64_t i0 = bench_instructions();
    int value = evidence_once();
    __asm__ volatile ("fence rw,rw" ::: "memory");
    uint64_t i1 = bench_instructions();
    uint64_t c1 = bench_cycles();
    int verified = verify_benchmark(value) == 1;
    /* Verification and all UART/printf work are outside the measured region. */
    char line[128];
    char *out = append_text(line, "RV32BENCH cycles=");
    out = append_number(out, c1 - c0);
    out = append_text(out, " instructions=");
    out = append_number(out, i1 - i0);
    out = append_text(out, " verified=");
    *out++ = verified ? '1' : '0';
    *out = '\0';
    puts(line);
    return verified ? 0 : 1;
}
