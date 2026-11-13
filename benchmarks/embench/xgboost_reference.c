/* SPDX-License-Identifier: Apache-2.0
 * Native reference check only: no timing from this program is a CPU score.
 */
#include <stdio.h>
int benchmark(void);
int verify_benchmark(int result);

int main(void)
{
    int result = benchmark();
    if (result != EMBENCH_EXPECTED_CORRECT || !verify_benchmark(result)
        || verify_benchmark(0) || verify_benchmark(result - 1)
        || verify_benchmark(result + 1)) {
        return 1;
    }
    printf("XGBoost exact-result oracle PASS: %d/128\n", result);
    return 0;
}
