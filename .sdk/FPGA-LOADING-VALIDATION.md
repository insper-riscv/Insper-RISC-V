# DE0-CV Rust loading repair

## Configuration

```toml
[project]
name = "app"
language = "rust"
manifest = "Cargo.toml"
platform = "de0-cv"
cpu_profile = "auto"
generate_drivers = true
```

`de0-cv` uses separate FLASH and RAM windows in SDRAM. Preserve their chip
offsets from `platform.yaml`; subtracting only the CPU-visible RAM base is
insufficient. The SDRAM Virtual JTAG instance is 3. This platform selects the
explicit `memory-v0.6` control protocol implemented by its Memory dependency.
Other platforms retain the default Tools protocol.

## Changes

- Generate the Quartus board project before fingerprinting or compiling it.
  Generated projects use two compilation processors.
- Package Rust firmware with the same bank header and CRC contract used by C.
  Preserve ROM origins when producing memory images.
- Carry SDRAM window offsets, JTAG instance and protocol into loading and stdout
  reads. Banked images are validated before transfer; only the declared image
  is transferred and the header is written last.
- Keep CPU-hold confirmation and board CRC checks in the compatibility adapter.
  The legacy protocol is explicitly selected, not an automatic unsafe fallback.
- Include the standard `alloc::string::ToString` trait and other allocation and
  formatting helpers in the Rust prelude. These reuse `core`/`alloc`.
- Preserve a previous Tools checkout when activating an updated SDK dependency.

Memory and Peripherals are pinned to the companion repair commits. Tools is
pinned through `.sdk/dependencies.json`; the existing SDK compatibility patch
still supplies include directories and bounded external-tool invocations.

## Validation — 26 November 2026

The original local tree passed:

| Suite | Passing tests |
| --- | ---: |
| SDK unit tests | 83 |
| Tools loader/SDRAM tests | 38 |
| GPIO cocotb, seven configurations | 38 |
| Display cocotb, ten configurations | 28 |
| SDRAM integration cocotb | 74 |
| Hold, CRC and JTAG protocol cocotb | 34 |

The DE0-CV completed Quartus compilation, programming, firmware loading and
cached reprogramming. All 84 reported timing checks had nonnegative slack;
minimum reported slack was +0.087 ns. The tested SOF SHA-256 was
`67c0d7aebedf5708f51c3efd929b48a3690c56dae86286cb8ddeabfcdebbe5c3`.
The unmodified Rust application returned 11387 and 12848 CLINT ticks on both
physical runs. At this platform's divider, 1001 ns/tick gave 0.012860848 s.
This was execution timing, not synthesis or host loading time.

Tests ran with an 8 GiB memory limit, no additional swap, and two CPUs. Normal
SDK output contained only the application text; diagnostics remained in the
project log. The SOF cache was checked using the already compiled and physically
verified bitstream, then the complete cached programming command passed.

These results describe these pinned branches, not compatibility with later
changes on `main`. No main-branch merge was performed.

## Host JTAG access

The existing Dev Container uses host networking. Run the JTAG server on the
computer that owns the USB-Blaster. A server started with `--user-start` expires
after two idle minutes, which can be shorter than synthesis. Keep the host
server alive during the build; a transient user service was used in validation.
Do not let a container without USB access replace it with its own server.


## Publication checks

The isolated publication tree passed 85 SDK unit tests (including upgrade
rollback tests). The clean Tools branch passed 44 loader/protocol tests. Native
Rust checks passed two allocator tests, four prelude consumer tests and six
executed documentation tests; the existing target-entry documentation example
remained ignored on the native target. The container did not provide rustfmt
for its Rust 1.85.1 toolchain, so no successful rustfmt check is claimed.

A fresh Tools preparation fetched the published pinned commit and applied the
SDK patch successfully. The new Tcl adapter was present in that installation.
SDK and modified Tools Python files passed Ruff checks. The original local
checkouts were left in place; publication used separate Git worktrees.
