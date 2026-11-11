## Experimental Evaluation

The evaluation distinguishes functional verification, execution performance and
implementation cost. Passing a test does not establish a speedup, and a configured
PLL frequency does not by itself establish the maximum operating frequency.

For a controlled historical comparison, the RTL was frozen at commit
`2115e4c8f49f75f9ef045bb59cf375c36f02b3ca`, the last first-parent main commit found
before July 2026 in the available history. The current design uses the processor
submodules pinned by SDK commit `3cc70ad2`. No processor RTL was modified for the
experiment. The baseline sources were verified against Git objects and both
versions executed identical instruction bytes. The original synchronous memory
tops were retained; only a small working set was accessed. Clock cycles were
observed externally between two RAM-store markers, avoiding the need to add
performance CSRs to the older processor. Boot and data initialization were excluded.

Three independently elaborated runs per design produced identical counts in each
of six controlled microbenchmarks. A multiply-high/low pair with shared operands
required 100 cycles on the baseline and 68 cycles on the current design, a 32.00%
reduction. A quotient/remainder pair required 104 and 70 cycles, respectively, a
32.69% reduction. These kernels deliberately contain spacing so both designs
produce the independently calculated answer. When the second operation used
different operands, both designs required 100 cycles for multiplication and 104
cycles for division. These negative controls support attribution of the savings
to result reuse. The dependent ADDI control tied at 131 cycles. The load-use loop
regressed from 513 to 577 cycles, a 12.48% increase. Consequently, no general CPU
speedup or aggregate score is inferred from these targeted kernels.

Fourteen additional current-design kernels checked aligned and misaligned loads
and stores against a little-endian software model. Accesses crossing a word
boundary added one cycle in the measured internal-memory cases; accesses within
a word retained the aligned cost. Nineteen existing RTL tests covering arithmetic
result reuse, misaligned accesses and FENCE.I/cache-flush protocols also passed.

Application characterization comprises 54 new physical runs on a Cyclone V
5CEBA4F23C7 at a nominal 50 MHz: eighteen pinned Embench 1.0 workloads, each
repeated three times. All runs passed their original verifiers, with identical
cycle and retired-instruction counts across repetitions of each workload.
CRC-32, EDN and integer matrix multiplication required medians of 219.461 ms,
522.484 ms and 363.347 ms, respectively. Their counters exactly reproduced the
fifteen earlier physical runs, although the new output harness and binaries are
kept in a separate dataset. The new dataset also covers Huffman coding, AES,
SHA-256, N-body, JPEG, QR-code generation and other workloads. These are raw
cycle-derived times, including counter/fence overhead, rather than historical
speedups or an official aggregate Embench score. The CPU_MHZ=1 workload scale is
independent of the nominal PLL clock. Cubic, the nineteenth workload, exceeded
the available program memory and was not executed. No external measurement of
the configured clock frequency was performed.

The evidence package retains raw measurements, expected and observed checksums,
source and binary hashes, unsuccessful attempts, reproduction commands and the
matched Quartus reports for the physical bitstream. The historical comparison is
limited to controlled RTL execution; an end-to-end FPGA comparison of historical
and current application firmware remains necessary before claiming a generational
application-level speedup.
