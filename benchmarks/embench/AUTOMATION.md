# Main-merge benchmarks: simulation only

The `embench` check runs on hosted GitHub machines using GHDL. It requires
neither FPGA access nor Quartus, JTAG, lab credentials or a self-hosted runner.
Automatic runs start only for a merged update to main. PR activity does not run
benchmarks. Explicit manual dispatch is restricted to main.

Each main merge compares its resulting commit with the main-before push SHA. Profiles
are discovered from both sides' Core YAML files; unavailable profiles are
explicitly marked. All 19 pinned Embench IoT programs run on every available
named profile, with the same compiler, adapter, memory model and workload.
No historical version of the Insper processor is used as the comparison.

## Reading the results

Each profile has candidate and base tables with per-program cycles, retired
instructions, CPI, IPC, normalized index and branching/memory/compute mix.
The summary retains the geometric mean index, GSD, diagnostic operation
groups and merge cycle-speed deltas. Mean instructions/program and weighted
IPC (`sum(instructions)/sum(cycles)`) require a complete verified suite.

The native monitor observes retirement between the benchmark markers;
squashed instructions are excluded. The memory platform uses internal
ROM/RAM without caches. Host simulator speed is not CPU performance.
Physical clock, Fmax, elapsed hardware time and MIPS are not measured.
With an independently established operating clock, MIPS would equal
IPC times clock MHz; this workflow does not infer that clock.

The normal CI workload executes one repetition of each complete algorithm,
with initialization, warmup and the original verifier. Its normalized index
per MHz is an extrapolated estimate, not an official full-duration Embench
score. Merge deltas use measured cycles directly. Manual `workload=full`
preserves the upstream loops. Operation categories overlap and are local
diagnostic summaries, not separate official Embench scores.

## Integrity and resources

Each measuring container is limited to 8 GiB RAM, no swap and two CPUs.
Programs and comparison sides run serially within a job. Up to four measuring jobs
use separate hosted machines; the summary container is limited to 2 GiB.
No waveforms are generated. A fixed concurrency group allows only one active
benchmark workflow. New merges do not cancel a started benchmark.

The original benchmark verifier (plus the stricter XGBoost result check)
must pass. Memory-model equivalence and independent counter oracles run
before measurements. Missing artifacts, failed verifiers or measuring jobs
fail the check. Scores are never substituted for missing results.

Small successful JSON records may be reused only when the actual source,
profile, runtime, memory, workload and tool fingerprints match. A report or
workflow edit does not change those measurement inputs. Reuse is recorded;
it is not described as a new simulation. JSON, CSV, logs and Markdown tables
are retained as Actions artifacts for fourteen days.

Measurement jobs use read-only repository permissions. A separate trusted
publisher can update the merged PR with its main benchmark result. It cannot
write repository source. SDK checks avoid duplicate push and PR runs.
The manual hardware harness and historical physical evidence are retained,
but there is no automatic FPGA workflow or hardware acceptance gate.

See [README.md](README.md) for reproduction and metric definitions and
[SIMULATION-VALIDATION.md](SIMULATION-VALIDATION.md) for this change's checks.


See [PR-SCORE.md](PR-SCORE.md) for the complete overall-index formula, shared main
cache, optional merge behavior, and safe bot comment publisher.
