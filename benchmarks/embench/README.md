# Embench in continuous integration

This integration starts from the processor's main branch, independently of
`kpi-benchmarks` and the Live SDK. It uses the modular simulation platform,
its memory map and runtime, and the explicit Core profile YAML files.
Processor sources and checked-in platform configuration are not modified.

`suite.yaml` pins all 19 Embench IoT 2.0 programs. Upstream currently labels
2.0 as development releases; results identify the exact snapshot, rather
than claiming a final release. Upstream sources and verifiers stay intact.

The native GHDL monitor measures core clock cycles and retirement events
between `start_trigger` and `stop_trigger`, after initialization and warmup.
It counts conditional branches and jumps as branching, loads and stores as
memory, and integer ALU/multiply/divide operations plus LUI/AUIPC as compute.
System/fence instructions have a separate `other` bucket. These are dynamic
instruction percentages, not percentages of execution time or independent
performance scores. Library code within the measured region is included.

Instrumentation is inserted into a build-directory copy of the Core only.
It observes the existing retirement pulse and EX PC/opcode; it neither adds
architectural counters nor enables extensions on profiles without Zicntr.
The start marker is excluded, its return and the call of stop_trigger are
included, and the stop marker is excluded. This fixed trigger overhead is
not subtracted. The original Embench verifier must pass after measurement;
a timing record without a successful program exit is never a valid result.

The first implementation uses internal ROM/RAM and no caches, identically
for every profile and comparison side. Simulation scores describe this
memory configuration, not FPGA Fmax or hardware wall-clock measurements.
