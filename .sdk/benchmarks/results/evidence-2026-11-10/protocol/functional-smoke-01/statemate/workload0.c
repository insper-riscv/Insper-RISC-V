/* Upstream warnings remain visible in logs; do not alter algorithms. */
#pragma GCC diagnostic warning "-Wunused-variable"
#pragma GCC diagnostic warning "-Wunused-parameter"
#pragma GCC diagnostic warning "-Wmaybe-uninitialized"
#pragma GCC diagnostic warning "-Wunused-but-set-variable"
#pragma GCC diagnostic warning "-Wabsolute-value"
#pragma GCC diagnostic warning "-Wunterminated-string-initialization"
#pragma GCC diagnostic warning "-Wmisleading-indentation"
#define CPU_MHZ 1
#include "/review/RV32/.sdk/vendor/embench/src/statemate/libstatemate.c"

int evidence_once(void) { return benchmark_body(1); }
