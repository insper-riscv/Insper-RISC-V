# Peripheral expansion validation

Initial validation on 2026-11-19 was entirely local, before the feature
branches were published. No main merge or manual Actions dispatch was performed.

## Revisions

- Peripherals baseline: `61c6d9fc7c0b5313db7d201ffa656e8b58c5ac26`.
- Drivers: local branch `feat/new-peripheral-drivers-20261118`, commit
  `03cd4a00621c99e5331d992eefc46667217d6e84`.
- Processor/SDK baseline: `fbbfb4d0273cdc229decf010aaa8248eac2f6e44`;
  local integration branch `feat/sdk-new-peripherals-20261118`.
- Live baseline: `b5f4d42f01c39c87a0c87a78b1a0d162a399a457`;
  local branch `feat/new-peripheral-projects-20261118`, commit `45a1cbe`.
- SDK Tools pinned to `f7ea593b547d106e3913a703f3254ab92dbb7ddf`, with the
  existing SDK compatibility patch applied cleanly. The previous pin did not
  recognize MIPI/Wi-Fi, so retaining it would have broken their generation.

## Results

| Layer | Result |
| --- | --- |
| C | Strict C23 compilation, existing GPIO/peripheral regressions, new side-effect-aware bus models, USB HPI model: pass |
| Rust | 18 new workspaces: native/unit/doc tests, compile-fail examples, Clippy with warnings denied, RV32I and RV32IM release builds: pass |
| GPIO compatibility | Existing native Rust tests/docs, including added logical-group API: pass |
| SDK | 67 unit/regression tests: pass |
| Generated examples | All 18 new families: C example cross-compilation, Rust example checks for both RV32 targets: pass |
| Physical platform maps | Full C and Rust firmware builds for each of seven boards (14 projects): pass |
| Quartus setup | Generation of each of seven board projects, without synthesis: pass |
| Existing CPU behavior | Two existing C projects on RV32I, RV32IM and the interrupt profile (6 simulations), existing Rust GPIO project on RV32I/RV32IM (2 simulations): pass |
| RTL regressions | 23 existing peripheral suites: pass |
| Packaging | VS Code syntax/project-creation/menu tests; rebuilt VSIX compared with bundled package and source: pass |
| Static checks | SDK Ruff lint/format, deptry, actionlint for updated SDK workflow; Peripherals manifest/tree checks; Git whitespace checks: pass |

The RTL suites were Spi, SDSpi, I2cMaster, IRRegs, LCDRegs, PS2Keyboard, Mouse,
AudioMaster, Adxl345, Adxl345I2c, Adc128s022, Ltc2308, Max10Adc, EthRegisters,
TVRegs, MIPIRegs, SDNative, VideoRegs, HdmiRegs, HdmiTmdsTx, WIFIRegs, USB and
GPIOMixed. These are peripheral RTL regressions; they do not replace an
end-to-end C-driver/physical-device test.

The seven maps were DE0-CV, DE0-Nano, DE0-Nano-SoC, DE10-Lite, DE10-Nano,
DE2-115 and MKR Vidor 4000. Synthetic all-device maps used for compilation are
explicitly test fixtures, not claims that all devices exist on one board.

## Resource cap and artifacts

All compiler/simulator work ran in one container with 8,589,934,592 bytes RAM,
the same total memory/swap limit (no swap), two CPUs and two Cargo jobs.
Recorded cgroup peak: 4,809,355,264 bytes (about 4.48 GiB); no OOM events/kills.
Image: `ghcr.io/insper-riscv/ci-elf@sha256:904ada4f8adbba1904b44a123a9616ad56b8da89349079de1c385ce807d1fcea`.
Rust native/target builds used 1.85.1; current installed nightly supplied Clippy.

VSIX 0.10.0 SHA-256:
`9f58abbc10e7c3b3995a99118d809780c2ac4caa4b7af9ef1a7ab817d97411b0`.

Raw logs, JSON suite results and resource readings are retained locally in
`publication-review/driver-expansion/`. Reproduction commands and platform
configuration are in `NEW-PERIPHERALS.md` and Peripherals' `DRIVERS.md`.
The SDK workflow adds complete generated-project checks to its existing Rust
job; it does not allocate another runner.

## Limits

No physical FPGA/device acceptance test or Quartus synthesis was performed.
There is no complete SoC/device simulation model for the seven physical
peripheral maps; Simulate reports that explicitly. Existing simulation-capable
platforms remain available. Controller drivers do not include network stacks,
filesystems, USB enumeration or undocumented attached-chip startup sequences.

The SDK gitlink points at the tested, published Peripherals commit. Future
dependency commits must also be published before their consuming SDK branch so
remote recursive clones can fetch them. Installing only the VSIX does not
install the SDK sources.

## Existing-installation upgrade regression

A stale Tools checkout reproduced the reported bootstrap failure. Five new
tests cover initial installation/no-op reuse, revision upgrades preserving
edited/untracked files, patch upgrades/corrupt metadata, download/patch failures,
and activation rollback. At that stage the complete SDK suite contained 72 tests.
Boot preflight also checks all five Core fragments required by boot_core.S,
including mismatched populated submodules rather than only empty checkouts.

The affected Rust program was simulated both in an isolated project copy and
in its actual Dev Container, with the SDK mounted at /opt/rv32-sdk. After
aligning clean processor dependencies to their recorded revisions, stdout was:

```text
Hello from an RV32 Rust project.
values = [1, 2, 3, 4]
```

The old installed Tools checkout and prior bootstrap/preflight files were
preserved in SDK-local backup directories. Existing project sources were not
edited. The extension VSIX did not need changes for this SDK bootstrap fix.


## Rust allocation prelude regression

Runtime 0.10.0 re-exports the standard `alloc` namespace, `ToString`, `ToOwned`,
`Cow`, `Rc`, ordered maps/sets, queues and string-formatting helpers. These are
Rust standard `core`/`alloc` APIs, not replacement implementations or a full OS
standard library. No new crate dependencies were added.

Six native tests (two allocator and four no_std consumer tests), six runnable
or compiled documentation examples, Clippy with warnings denied, and RV32I/IM
runtime builds passed. The full SDK suite passed 73 tests, including a managed
runtime upgrade that preserves application source. The CI runtime fixture now
exercises the helpers on both RV32I and RV32IM RTL; both simulations passed.

The user's existing Rust calibration program was regenerated and simulated in
its actual Dev Container. Its main.rs SHA-256 remained unchanged, including its
existing `use alloc::string::ToString` import. Program stdout was exactly:

```text
The sum of all valid calibration results is 11387
```

An independent evaluation of the same input/operations also produced 11387.
Stderr was empty. The installed SDK runtime was backed up before replacement;
the project received its runtime update through normal managed generation.
Raw evidence is retained in publication-review/driver-expansion/rust-prelude/.
