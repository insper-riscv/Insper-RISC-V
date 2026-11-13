# Overall Embench score and optional PR comments

The benchmark compares the incoming **PR head SHA** to **main**, frozen to the
main commit checked out when planning starts. It does not compare historical
processor generations or use the PR target's possibly outdated base SHA.
The adapter/instrumentation comes from a frozen trusted main revision during PR
runs; both sides use the same compiler, pinned suite and measurement contract.

The overall relative index is:

```
100 × GM over profiles (GM over programs (main cycles / PR cycles))
```

Main is 100; 110 means a geometric mean speed improvement of 10%, and 90 means a
10% reduction in relative speed. Each program has equal weight within a profile,
then each profile has equal weight. Complete, verified paired coverage is
required for **every planned profile/program**. A missing/new/removed profile,
failed program, invalid counter or incompatible contract leaves the total
unavailable; it is never silently excluded. Per-profile absolute geometric means
of score/MHz remain in the tables. The shortened `ci` workload is called a **CI
index**, not an official full Embench result. Simulation does not measure FPGA
clock frequency or physical instructions/second.

## Bot comment

`Embench PR score comment` receives workflow_run in_progress/completed events.
It creates/updates one github-actions[bot] comment, with a running state, the
overall index, profile table, main/head commit IDs, and a link to all artifacts.
It also updates a closed/merged PR after an already-running benchmark finishes.
Older runs and outdated PR heads cannot overwrite a newer result.

The commenting workflow only checks out main. It never executes PR code, reads
only bounded validated numeric JSON from that run, verifies the PR association
and head SHA through GitHub, and holds no permission to write repository source.
Labels and links are constructed by trusted code, not copied as artifact Markdown.
Both workflow files must be merged into main before workflow_run commenting can
activate. Fork PR benchmark execution still follows the organization's ordinary
first-time-contributor approval policy.

## Shared main cache

PR caches are isolated to each PR merge ref by GitHub. A main push touching
measurement/processor inputs therefore warms the default-branch cache once for
that input set. PR jobs can restore these default-branch results. Candidate and
baseline use the same content-keyed cache path/version, avoiding the old mismatch
between cache/candidate and cache/base. The key covers actual processor sources,
measurement instrumentation, tools, workload, profiles and programs.

Restored JSON must pass the existing seal, verifier, contract/source and program
coverage checks before reuse; provenance is refreshed to the current frozen SHA.
Changed inputs, cache eviction or an initial cold main cache require measuring
main again. This is intentional. The cache is an optimization, not permission to
reuse stale measurements. Small counter/oracle/storage checks still run.

## Merge behavior

Embench is informational. Do **not** add `plan`, `measure`, `Embench results
(informational)`, or `Embench PR score comment` to required status checks.
Existing functional checks stay required and unchanged. Failed benchmarks remain
visible as failures; they are not disguised as successes. Merging does not need
to wait for Embench. `cancel-in-progress: false` preserves started runs; no closed
PR event starts an unnecessary extra benchmark. Administrators and GitHub resource
limits can still cancel a run explicitly.

The active Only-PR repository ruleset was inspected during implementation:
required checks were vhdl-syntax, unit-tests, python-static-analysis and formal;
Embench was not required. No repository rules or merge permissions were weakened.

## Tests

Run the reporting/score unit suite, the Node comment tests (including stale runs,
closed PRs and invalid artifacts), actionlint, and the repository's Python checks.
Those tests use synthetic known ratios to verify arithmetic; they do not claim
new processor performance gains. Full benchmark JSON/CSV remains the evidence
for any score published by an actual run.
