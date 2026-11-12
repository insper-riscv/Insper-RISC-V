# Simulation-only CI validation — 2026-11-12

The PR workflow now requires only hosted GHDL simulation. The reusable
physical workflow and its runner-label configuration were removed. There
is no hardware job, physical artifact download, combined-backend report
call or physical acceptance gate. Other workflows, processor sources,
platform YAMLs, submodule pins and Live SDK functionality are unchanged.

Local validation used the same image digest as the workflow, in a container
limited to 8 GiB RAM, no swap and two CPUs:

- 37 adapter/report/manual-harness unit tests passed. New regressions cover
  simulation-only aggregation, missing base artifacts, weighted IPC,
  incomplete suites, stale revisions, wrong backend/profile/program sets,
  false profile absence and unknown result status.
- All 22 preserved simulation records (11 profiles, candidate and base)
  passed integrity checks: 418 verified program rows. The new aggregator
  generated complete candidate/base tables and CSV files without any
  physical artifacts. These are reused historical measurements at
  `880e2526b1ef3d6f1bb47a664981e701e1f1ebd5` and
  `dfdf585e87355a739916cd3140adc40e21982aa3`, not new executions.
- A fresh, uncached `rv32im/crc32` simulation passed its verifier:
  65,587 core cycles, 23,590 retired instructions, CPI 2.780288.
  It ran before committing the presentation changes; its revision remains
  the actual checked-out parent, `c6c87452c4355570db3a8a7ecd08432b7c2a089f`.
- Repository Ruff lint/format, changed-file pycodestyle/pydocstyle/Pylint
  (10/10), project Pyright/Pyrefly, dependency checking and changed-file
  complexity checks passed. Workflow Actionlint passed with only the
  existing narrow exclusion for its outdated ubuntu-26.04 label database.
- `git diff --check` passed. A merge-tree check against main at
  `dfdf585e87355a739916cd3140adc40e21982aa3` found no conflicts.

The measurement adapter, memory models, firmware, suite and tool pins are
unchanged. Existing exact-input caches remain valid. Clock, Fmax and MIPS
are intentionally not reported as measured simulation results.

No board was accessed and no main merge was performed.
