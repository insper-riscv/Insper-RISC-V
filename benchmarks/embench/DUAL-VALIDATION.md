# Dual-backend acceptance — 2026-11-12

This is a validation of the benchmark infrastructure, not a claim of CPU improvements.
No functional processor source or submodule revision differs between the measured sides.

## Executed evidence

- GitHub run [43144799156](https://github.com/insper-riscv/Insper-RISC-V/actions/runs/43144799156): all eleven simulation jobs passed. 209 fresh base measurements and 209 exact-contract cached candidate measurements; all paired deltas zero. Overall run correctly failed because physical runner access is not provisioned.
- Local laboratory DE0-CV acceptance: all eleven named Core profiles, nineteen verified programs each, three physical repetitions on each of two revisions: **1,254 fresh executions**, plus **44 positive/negative control runs**. All original verifiers passed. The DE2-115 was not programmed.
- Measured candidate/driver `880e2526b1ef3d6f1bb47a664981e701e1f1ebd5`; base `dfdf585e87355a739916cd3140adc40e21982aa3`. Later controller/report changes add coverage validation and absent-profile handling; these revisions were not falsely substituted into the physical provenance.
- Combined table generated with the current strict aggregator: 418 physical median measurements plus 418 source-equivalent cached simulation measurements, complete candidate/base rows for both backends. Native cache reuse explicitly preserves the original measurement provenance (run 43129374866); it is not new execution.
- Independent audit verified sealed record checksums, firmware/bitstream hashes, exact 19-program coverage, three samples, median cycles, balanced operation counters, matching instruction counts/ELFs across revisions, positive eight-instruction counter and rejection of nonzero exit.
- All multicorner timing slacks were nonnegative. Operating clock is the configured PLL **76.923077 MHz**, not a fresh oscilloscope measurement. Reported Fmax covers intra-core paths of the instrumented builds, not system Fmax.
- Maximum physical within-program repeat range was **0.625%**. Per-profile geometric mean base/candidate speed differences ranged from **−0.03034% to +0.02338%**. Identical instruction streams and small SDRAM/phase variations support no performance change; those differences are not gains.
- Two compiler containers capped at 3 GiB each and one measurement container at 768 MiB: **6.75 GiB combined cap, no swap**. Physical access serialized under the canonical lab locks.
- 34 adapter/report unit tests, the independent VHDL retirement-counter oracle, all thirteen existing root static checks, tree-location validation and Actions workflow lint passed.

The raw firmware, manifests, generated configuration, observer logs, Quartus timing/fitter reports, eleven bitstreams and independent audit were retained in `physical-dual-evidence-20261112.zip` in the local delivery workspace; the archive is not committed as a large binary. A compact audit is committed alongside this document.

## Merge assessment and remaining external step

The merge-tree audit against the stated main revision reports no conflicts. All 800 existing main files other than README.md, README.en.md, pyproject.toml and uv.lock remain byte-identical. No `src/`, processor submodule pointer, board definition, path catalog, or existing processor CI workflow is changed.

**Do not treat the complete PR automation as accepted yet.** Organization administration must enable the dedicated FPGA runner and SHA-pinned reusable workflow as described in [FPGA-SETUP.md](FPGA-SETUP.md), then a real Actions run must pass both backends. The provisioning gate intentionally stays red until then. No main merge was performed.
