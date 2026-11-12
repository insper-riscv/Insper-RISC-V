# PR benchmarks: simulation and DE0-CV

The `embench` check requires both backends for every named Core profile
listed in `Core/profiles/rv32*.yaml`. Each program keeps its upstream
verifier, with the additional exact-result check for XGBoost. The physical
run repeats each program three times and checks a known eight-instruction
assembly kernel, including a deliberately failing exit. A missing runner,
busy board, failing verifier, counter mismatch, missing artifact or timing
failure must not produce a successful `embench` check.

The comparison is the exact PR base commit versus the proposed merge
commit, using one measurement driver. There is no old-processor reference.
Manual dispatch can test the feature branch before a PR exists. Expanded
`scope=all` remains a **simulation-only** diagnostic; PRs use the named
matrix and require both backends. No benchmark runs on ordinary pushes.

## Reading the table

- Instructions are retired instructions inside the marker region, including
  its consistent call/return overhead; squashed instructions are excluded.
- IPC is instructions/cycles. The profile summary uses the weighted ratio
  `sum(instructions)/sum(cycles)`, and also reports mean instructions/program.
- Physical MIPS is IPC times configured CPU MHz. Physical elapsed time is
  cycles divided by that clock. Both use the generated PLL configuration,
  **not** a new oscilloscope or frequency-counter measurement on every PR.
- Quartus restricted core-domain Fmax is an intra-domain timing estimate of
  the **instrumented** build. It excludes cross-clock paths and is neither
  the system maximum frequency nor the operating clock. All reported
  multicorner setup/hold/recovery/removal/pulse-width slacks must pass before
  programming. Raw timing reports accompany the results.
- Simulation uses internal memories without caches; the board uses SDRAM,
  emulated FLASH and 4 KiB I/D caches. Their scores must not be averaged or
  interpreted as a hardware-versus-simulation speedup.
- CI uses one local repetition of each complete benchmark algorithm. Its
  normalized suite index is an **estimate**, not an official full-duration
  Embench result. The overall index uses a geometric mean across programs,
  separately for each backend/profile. Physical overall index also includes
  the configured frequency. Branching/memory/compute groups overlap and are
  diagnostic categories, not additional official Embench scores.
- Physical PR speed delta compares elapsed time, accounting for PLL changes;
  simulation delta compares cycles. Dashes mean unavailable, never zero.

## Hardware measurement

The builder appends `hardware_monitor.vhd.in` to a **build-directory copy**
of `Core/src/core/core.vhd`. `retirement_counter.vhd.in` observes the same
retirement pulse, PC and opcode as the native simulator. No architectural
CPU port, CSR, ISA extension or tracked processor source is changed.
Virtual JTAG instance 4 exports frozen 64-bit cycle/instruction/type
counters. A two-flop done synchronizer qualifies the stable result bus.
PC configuration is synchronized and written while the whole SoC is held
in reset. JTAG reads during the region do not access SDRAM.

The exact named profile's configuration and HPM generics replace the
platform's ISA defaults. Memory/cache/peripheral settings remain those of
the DE0-CV. Profiles without Zifencei use a build-only boot copy that
replaces the unsupported boot `FENCE.I` with a NOP. This is safe for this
harness because `flash_loader.load_image` holds `flash_halt`, which resets
the **whole SoC and its caches**, before every image. The normal platform
bootloader is unchanged. This harness must not be reused as a resetless
hot-patching bootloader.

Base/head may share a compiled bitstream **within one trusted job** only
when source/config/profile/tool/driver/workload fingerprints match. They
are still programmed and measured independently. Previous measurements
are deleted before reuse. Untrusted Actions caches are not used for FPGA
bitstreams. The bitstream and each packed firmware image are checked before
programming, and full provenance, samples, ELF files and reports are kept.

## Required lab setup

The existing organization runner `D-20003267-LINUX` belongs to group `FPGA`.
It needs Docker, Python 3.12+, Quartus Lite at `/opt/altera_lite/25.1std`,
and access to the existing JTAG daemon. The selected cable is currently
`USB-Blaster [1-6]`; the driver verifies its **02B050DD DE0-CV** identity
before programming. It refuses the DE2-115's 020F70DD identity. USB topology
changes require a reviewed trusted-driver update.

The driver respects the canonical DE0-CV lock and existing legacy lock
aliases. It fails if the board is in use. It never deletes or steals locks.
Compilers run offline in a pinned container with 8 GiB RAM, no swap, two
CPUs, no host credentials, Docker socket or USB, read-only system mounts
and no added capabilities. The separate trusted programming container uses
host networking to reach JTAG. Cancellation/timeout removes its container
and releases the board locks. A JTAG hang requires `sudo killall jtagd` per
the lab's operating procedure; a normal verifier failure does not.

**An organization administrator must enable repository/workflow access.**
The current account cannot administer runner groups, and the repository
currently has no accessible self-hosted runner. Preserve other lab users'
runner access; do not stop or re-register the shared runner.

In organization Settings → Actions → Runner groups → FPGA:

1. Add `insper-riscv/Insper-RISC-V` to repository access and permit its public
   repository to use the group.
2. Restrict workflow access to reviewed workflows. **Append the exact,
   full-SHA-pinned reusable `embench-hardware.yml` reference specified in the
   final validation record**, preserving other approved lab workflows.
   Never authorize arbitrary PR workflow files or a mutable PR branch.
3. Run the manual `embench` workflow on `embench-ci`; inspect the combined
   table and both job statuses before merging.

GitHub documents this restriction in
[Managing runner-group access](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/manage-access).
Only jobs directly defined in an allowlisted workflow may use the group.
The reusable workflow pins its driver separately, so PR scripts are never
executed on the lab host. Fork PRs need a maintainer-owned review branch for
physical execution; they must not receive an automatic physical pass.

## Local reproduction

Prepare clean recursive candidate/base checkouts and the pinned upstream
Embench checkout from `suite.yaml`. From a reviewed driver checkout on the
lab host:

```sh
python3 benchmarks/embench/hardware_host.py \
  --candidate /absolute/candidate --base /absolute/base \
  --upstream /absolute/embench-iot --profile rv32im \
  --output /absolute/new-output-directory
```

The output directory must not exist. Compilation and programming have
separate timeouts; profiles execute serially on the shared board. The
immutable image is defined in `hardware_host.py`, and the workflow never
installs an SDK into a user's project. Raw evidence is stored under
`candidate/build` and `base/build`; sealed records are under
`results/{candidate,base}/{profile}`.

Before merging, require the existing repository checks plus the combined
`embench` check. No amount of testing guarantees all future behavior;
missing physical CI access is an outstanding validation requirement, not
proof that the integration is ready.
