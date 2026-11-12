/* SPDX-License-Identifier: Apache-2.0
 * The upstream XGBoost verifier accepts every nonnegative result at GSF<12.
 * Preserve its check and additionally require the independently reproduced
 * exact number of correct classifications. This runs after stop_trigger.
 */
int __real_verify_benchmark(int result);
int __wrap_verify_benchmark(int result);

int __wrap_verify_benchmark(int result)
{
    return __real_verify_benchmark(result) && result == EMBENCH_EXPECTED_CORRECT;
}
