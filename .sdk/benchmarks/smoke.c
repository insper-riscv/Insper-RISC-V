/* SPDX-License-Identifier: Apache-2.0 */
static volatile unsigned result;
void initialise_benchmark(void) { result = 0; }
void warm_caches(int heat) { (void)heat; }
int benchmark(void) {
    unsigned sum = 0;
    for (unsigned i = 0; i < 100; ++i) sum += i;
    result = sum;
    return (int)result;
}
int verify_benchmark(int value) { return value == 4950; }
