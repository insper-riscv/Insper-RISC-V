# Overall Embench score after a merge into main

Automatic benchmarks run only after a PR is merged into `main`. A main push is
checked against GitHub's merged-PR metadata before any benchmark job starts.
Opening, updating or closing an unmerged PR never starts a benchmark. Explicit
manual runs remain available on main only.

The candidate is the resulting main commit (`github.sha`). The baseline is main
immediately before that update (`github.event.before`). This compares the incoming
branch as integrated into main with the prior processor state. It works for merge,
squash and rebase merges: the push's before SHA is the baseline for the entire
update, rather than just the first parent of the last rebased commit.

The overall index is:

```
100 × GM over profiles (GM over programs (previous-main cycles / merged-main cycles))
```

Previous main is 100. An index of 110 means a 10% geometric mean speed increase.
Each program has equal weight within a profile, then each profile has equal
weight. Complete, verified paired coverage is required for every planned
profile/program. Missing or incompatible measurements leave the total unavailable.
The shortened workload produces a CI index, not an official full Embench score.

## Simulation and bot comments

Measurements use hosted GHDL simulation. They include cycles, retired instructions,
CPI, IPC and branching/memory/compute mix. They do not measure physical FPGA clock,
Fmax, wall-clock program time or hardware MIPS. Quartus/FPGA testing is separate.

The bot posts or updates one comment on the merged PR when the main benchmark
starts and finishes. It validates the repository, main branch, exact merge commit,
numeric score data and run ordering. The PR head need not equal the resulting
merge/squash/rebase commit. Unmerged PRs, unrelated commits, fork runs and manual
runs cannot receive these automatic comments. The write-token workflow checks out
trusted main code only. The workflow must reach main before comments can activate.

## Runner budget and merge checks

The benchmark matrix uses at most **four measuring runners**, and one fixed
`embench-refs/heads/main` concurrency group permits only one active benchmark workflow.
Planning and summary jobs run before/after measurement; the bot uses a brief
separate job. This avoids occupying the organization's 20-runner pool with
concurrent per-PR matrices. SDK and reporting checks run once per PR commit,
rather than once for its push and again for its PR event.

GitHub concurrency and matrix limits are scoped to workflows in a repository;
they do not reserve four idle organization runners against unrelated teams' jobs.
No organization-wide runner limit or required functional check is modified.
Embench remains informational and must not be added to required merge checks.
It starts after the merge and cannot hold that merge up. Started benchmarks are
not cancelled by another merge. GitHub retains at most one pending run in a
concurrency group, so a burst of merges can replace an older pending run; the
next run still compares its exact main-before and main-after commits.

## Caches and verification

Both comparison sides use the same content-keyed cache paths. Keys cover processor
sources, instrumentation, tools, workload, profiles and programs. Records must
pass seal, verifier, provenance and coverage checks before reuse. A cold cache,
changed inputs or eviction requires measuring that side again. Main commits save
their successful results for subsequent main comparisons.

Tests cover score arithmetic, incomplete results, main-only triggering, worker
limits, merged-commit association, unmerged/direct-push rejection, stale comments
and artifact validation. Actual performance claims require benchmark JSON/CSV.
