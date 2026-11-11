# Integration validation — 2026-11-11

The first complete Actions run passed on commit
`ed7db18b57fd1fc52e0357674c8dc77445fa30c6`:
[run 43103981319](https://github.com/insper-riscv/Insper-RISC-V/actions/runs/43103981319).
All 13 jobs succeeded: planning, 11 measurement jobs and the final summary.
The downloaded summary was independently checked for 11 distinct profiles,
19 distinct passing programs per profile, valid record checksums, matching
revision/tool/workload metadata, and 209 matching CSV rows. No failed or
missing program was excluded from an aggregate.

## Complete CI workload

| Profile | Verified programs | Measurement wall time (minutes) |
|---|---:|---:|
| rv32i | 19/19 | 84.14 |
| rv32i_zmmul | 19/19 | 65.42 |
| rv32im | 19/19 | 67.21 |
| rv32im_zicclsm_zicntr_zifencei | 19/19 | 43.11 |
| rv32im_zicclsm_zicntr_zihpm_zifencei | 19/19 | 72.01 |
| rv32im_zicclsm_zicntr_zihpm_zifencei_reduced | 19/19 | 66.13 |
| rv32im_zicond | 19/19 | 33.28 |
| rv32im_zicsr | 19/19 | 58.18 |
| rv32im_zicsr_irq | 19/19 | 47.56 |
| rv32im_zicsr_zifencei | 19/19 | 29.75 |
| rv32im_zimop | 19/19 | 67.37 |

These are sums of benchmark execution wall times, excluding checkout and
other workflow setup. Jobs ran concurrently. Host wall time varies across
GitHub machines and is **not** the processor performance metric. The tables
in the Actions summary use measured core cycles and retirement events.
The `embench-summary` artifact contains Markdown, per-profile JSON and CSV;
batch artifacts contain simulator logs. Retention is 14 days.

## Independent checks

- All 16 adapter regression tests passed, including incomplete reports,
  comparison direction, cache corruption/profile binding, source/config
  invalidation and termination of timed-out child processes.
- The known assembly kernel retired exactly eight instructions: three
  branching, two memory and three compute. The squashed instruction was
  excluded, and a failing program exit was rejected.
- Original and efficient simulation storage models passed 2,048
  deterministic stimuli, including byte writes, read/write collisions,
  enables, aliases and independent ROM clocks.
- The independent XGBoost oracle reproduced 126 correct classifications
  out of 128, and rejected zero and off-by-one results. Every target run
  retained the upstream verifier and the additional exact-result guard.
- All 13 repository static-check steps passed locally: locked dependency
  synchronization, Ruff, Ruff format, pycodestyle, pydocstyle, Pylint,
  Pyright, Pyrefly, deptry, complexipy, CodeClone, Semgrep and dependency
  audit. Pyrefly emitted three non-blocking warnings and no errors.
- Workflow lint passed; its older runner-label database required only the
  narrow exception for the repository's existing `ubuntu-26.04` label.

The final adapter also ran CRC32 on two clean-source checkouts: target main
`dfdf585e87355a739916cd3140adc40e21982aa3` and candidate
`ed7db18b57fd1fc52e0357674c8dc77445fa30c6`. Both original verifiers passed,
with exactly 65,587 cycles and 23,590 instructions on RV32IM. The rendered
branch difference was +0.00%, as expected for unchanged processor sources.
The report correctly marked overall/group coverage incomplete for this
single-program control instead of presenting a complete suite score.

## Additional unchanged-loop test

WikiSort was also executed locally in `full` mode on RV32IM with its
original local scale factor of two. Its original verifier passed:

| Workload | Cycles | Instructions | Score or index/MHz |
|---|---:|---:|---:|
| CI, one local repetition | 1,394,822 | 878,756 | 1.298373556 (estimate) |
| Full, original two repetitions | 2,789,581 | 1,757,461 | 1.298402878 |

The indices differ by approximately 0.0023% for this program. This validates
that example; it does not establish the approximation error for all other
programs. The full-duration 209-job matrix and expanded generated-profile
matrix have **not** been run in full. The automatic CI suite runs all
algorithms and verifiers with reduced repetition counts, as documented in
[the methodology](README.md).

## Scope and limits

The branch starts at main commit
`dfdf585e87355a739916cd3140adc40e21982aa3`, independently of the SDK and KPI
branches. Tracked processor RTL, submodule pointers and platform
configuration were not changed. Local simulation and measurement jobs
used a hard 8 GiB memory limit with swap disabled; no waveforms were saved.

No PR was created to test an actual `pull_request` event, and nothing was
merged into main. The two-checkout comparison engine was exercised locally;
the deployed Actions execution above used the push event. FPGA frequency,
area and power were not measured by this integration. CI indices are not
certified full-duration Embench scores or comparisons with an old Insper CPU.
