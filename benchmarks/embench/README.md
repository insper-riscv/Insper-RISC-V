# Embench in continuous integration

This integration starts from the processor's main branch, independently of
`kpi-benchmarks` and the Live SDK. It uses the modular simulation platform,
its memory map and runtime, and the explicit Core profile YAML files.
Processor sources and checked-in platform configuration are not modified.

See [validation evidence and tested limits](VALIDATION.md) for the first
complete 209-measurement Actions run and the independent adapter checks.

`suite.yaml` pins all 19 Embench IoT 2.0 programs. Upstream currently labels
2.0 as development releases; results identify the exact snapshot, rather
than claiming a final release. The upstream checkout and all verifiers stay intact; see workload modes below.

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

Per-program tables and CSV also report IPC (retired instructions per core
cycle), calculated as `instructions / cycles`, alongside CPI (`cycles /
instructions`). With an established operating frequency, throughput is
`instructions/second = IPC * frequency_Hz`, or `MIPS = IPC * frequency_MHz`.
IPC is therefore numerically equal to MIPS/MHz. No board frequency is
assumed, and host simulation speed is not processor instruction throughput.
These quantities describe the measured kernel; instruction count and ISA
can differ between profiles, so Embench scores and cycle deltas remain
necessary for comparing useful work.

## Workload modes and scores

The automatic `ci` mode executes every complete algorithm and its original
verifier, with one local repetition (`LOCAL_SCALE_FACTOR=1`), GSF=1 and one
warmup. Only that loop macro is changed in build-directory source copies;
no algorithm, input, expected result or verifier is changed. This keeps RTL
simulation practical on every PR. Each row records the original and used
scale factors and ELF hash. The upstream checkout is never edited.

Benchmarks are compiled as GNU C17, matching the upstream C sources
(including WikiSort's `bool` typedef). The platform runtime is compiled
separately as GNU C23. Compiler, libc and simulator identities are recorded.

The displayed CI index per MHz is:

```
reference_ms * 1000 / (measured_cycles * original_local_scale)
```

This extrapolates one local repetition to the original workload. Trigger
and loop overhead are not perfectly linear, so this is explicitly an
**estimated CI index, not an official full-duration Embench score**. PR
speed deltas use the measured cycles directly, with the same workload on
both sides; they do not use this extrapolation.

Manual `full` mode leaves the upstream loops unchanged (GSF=1). Its
score/MHz is `reference_ms * 1000 / measured_cycles`, following the upstream
normalization. The reference times come from the pinned suite's own
`baseline-data/speed.json` (the Embench reference platform, not an older
Insper CPU). Neither mode measures FPGA maximum frequency.

The upstream XGBoost verifier is permissive at GSF below 12 (its integer
threshold becomes zero). A link-time wrapper retains that original check
and additionally requires exactly 126 correct classifications out of 128
for one repetition. This exact result was independently reproduced using
the pinned source and dataset on the host compiler. The extra check runs
after `stop_trigger`, so it does not enter the measured interval. No
benchmark algorithm or expected dataset is changed.

Overall scores require all 19 programs to pass. Category summaries use the
fixed high-intensity groups in Table 1 of the paper, DOI
[10.1109/MC.2024.3511352](https://doi.org/10.1109/MC.2024.3511352): branching
at least 19%, memory at least 30%, compute at least 72%. Groups overlap.
These diagnostic group scores are local additions, not official separate
Embench scores. Group membership uses the paper's fixed classification;
the per-program instruction percentages are measured on our RTL.

## Actions

The `embench` workflow runs automatically only when a PR is opened,
updated with new commits, or reopened. Ordinary branch pushes and pushes
to main do not trigger it. Manual dispatch remains available. Each PR
compares the exact target `base.sha` with the
proposed merge tree (`github.sha`). Both use the same adapter and immutable
CI image, tool versions, benchmark commit, workload and memory settings.
The summary records the full revisions. No historical Insper CPU is used.

The default matrix is discovered from the explicit `Core/profiles/rv32*.yaml`
files (11 at introduction). Profiles from both comparison sides are included;
new or removed ones are marked unavailable on the corresponding side. All
19 programs run on each available profile. Compilation uses that profile's
ISA, including Zicond where enabled, and its exact hardware configuration.

`Actions > embench > Run workflow` provides:

- `scope=named, workload=ci`: the normal 11-profile suite.
- `scope=all, workload=ci`: the generated Core matrix plus explicit variants,
  in batches of three profiles (potentially expensive; manual only).
- `scope=named, workload=full`: unchanged benchmark repetition loops,
  sharded by program and profile so individual jobs remain bounded.

The GitHub UI only shows that manual button once the workflow file exists
on the default branch; see the
[GitHub event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch).
For this already registered workflow, the review branch can also be run
through the GitHub CLI without merging anything into main:

```sh
gh workflow run embench.yml --ref embench-ci -f scope=named -f workload=ci
```

`all + full` exceeds GitHub's 256-job matrix limit and is rejected with an
explicit message. It is not silently reduced to a sample.

Up to 11 measuring jobs run concurrently on separate GitHub machines.
Within each job all programs and comparison sides run serially. Containers have a hard 8 GiB RAM limit and
no swap; the summary job has a 2 GiB limit. No waveforms are generated.
Both workloads have a two-hour wall limit per program, and the workflow
bounds each measuring job. RTL execution of large kernels can be slow even
with one local repetition; this check can take substantially longer than
functional smoke tests. Cache hits and cancellation avoid redundant runs. New
commits cancel superseded runs.

Successful results are cached by the actual RTL, profile YAMLs, maps,
runtime inputs and the adapter/suite/tool identities. Base and candidate
have independent caches so an unchanged target base can be reused across
PR updates. Only small JSON records are cached. Presentation and unit-test edits do
not invalidate measured results; those checks still run on every job. A cache hit must also match
the requested program set and pass all result-integrity checks; its revision
label is refreshed to the current target. The summary shows failures and
missing results, and fails when required results are absent. JSON, CSV,
Markdown tables and diagnostic logs are uploaded with 14-day retention.
CSV exports include the workload, score type, scale factors, revision and
explicit count/percentage units.

All PR code runs with read-only repository permissions, no deployment
credentials and no lab/FPGA access. This workflow adds no PR comments,
merges or automatic commits. Existing CI checks remain intact.

## Local reproduction

Use the same pinned image as `.github/workflows/embench.yml`. Mount this
checkout and an upstream checkout at the suite's pinned commit. Inside that
container, from this repository's root:

```sh
PY=/opt/riscv-tools/riscv-tools/bin/python
$PY -m unittest benchmarks.embench.test_reporting -v
$PY -m benchmarks.embench.check_storage --output /tmp/storage-check
$PY -m benchmarks.embench.check_counter --upstream /path/to/embench-iot \
  --output /tmp/counter-check
$PY -m benchmarks.embench.run --upstream /path/to/embench-iot \
  --profile rv32im --output /tmp/rv32im-results
$PY -m benchmarks.embench.report --candidate /tmp/rv32im-results/results.json \
  --output /tmp/rv32im-summary.md
```

Add `--program crc32` for a smoke test or `--workload full` for unchanged
repetition loops. Use `--root /path/to/other-checkout` to test a base that
does not yet contain this integration. Compare two result files with the
report command's `--base /path/to/base/results.json`. Revisions may differ;
measurement contracts and workload settings must match.

The memory observer and efficient storage models are simulation-only
copies. `check_storage` compares the original and efficient models with
2,048 deterministic stimuli, byte masks, simultaneous read/write, address
aliases, enables and two independent ROM clocks. `check_counter` runs an
independently counted assembly kernel: eight retirement events (three
branches, two memory, three compute), a squashed instruction that must not
be counted, and a failing program exit that must be rejected. These checks
run before benchmarks in Actions.
