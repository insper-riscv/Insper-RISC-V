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

## Dev Container extension installation

A new C project exposed an installation race: Dev Containers installed C/C++
from `customizations.vscode.extensions` while the bundled RV32 extension pack
also requested that dependency. VS Code failed with `ENOTEMPTY` when renaming
the same C/C++ extension directory, which aborted `postCreateCommand` before
SDK setup.

The container installer now passes `--do-not-include-pack-dependencies` when
installing the bundled VSIX. Dev Containers remains responsible for language
extensions; host-side installation of the extension pack is unchanged. A
per-agent lock serializes this script across postCreate/postAttach, and its
file descriptor is closed for the extension CLI. Real RV32 installation errors
still fail rather than being suppressed; no installed extensions are deleted.

Four regressions cover isolated installation, overlapping lifecycle calls,
idempotence and propagation of actual installation errors. A real VS Code
1.140.0 installation into an empty extension directory installed only RV32.
The failed C-project bootstrap was rerun successfully and its C firmware
compiled. Existing C/C++ and Rust Analyzer installations remained available.

For an existing container using the updated SDK, rerun:

```sh
bash "$RV32_SDK_ROOT/scripts/bootstrap-external.sh" "$RV32_PROJECT_ROOT"
```

No container rebuild is needed when the SDK directory is already bind-mounted.

The combined SDK suite passed 89 tests after this installer repair. Shell
syntax validation and Ruff checks also passed.

## Platform catalogue provenance and DE0-CV source closure

The extension's physical-board choices came from the existing maps under
`src/periph-examples/<board>/platform.yaml`, introduced in repository commit
`a85465bd5c8585f9e4035fb0a9be33e4286c3050`. Board pin and device information came
from `boards/<board>/board.yaml`. Exposing a map in the project creator did not
establish successful synthesis or physical validation for every board.

The current VSIX labels are ambiguous: `DE0-CV (legacy)` selects project
platform `de0-cv`, while `DE0-CV` selects `periph-de0-cv`. The latter includes
PS/2 keyboard/mouse and native SD hardware. The base `de0-cv` validation above
must not be presented as validation of that peripheral variant. CPU profiles
are a separate selection and do not select the board or memory/peripheral map.

An attempt to program the generated KEYBOARD example exposed missing source
closure entries for `ps2_keyboard`, `ps2_mouse_top` and `sd_native`. Their RTL
already existed in Peripherals, but the board target in `paths.yaml` did not
require those components. The DE0-CV target now includes them, and a regression
checks all three peripheral sources plus their PS/2 host dependency.

A read-only audit also found incomplete source coverage in the other six
peripheral example board targets. Those platforms remain unvalidated by this
repair; a catalogue entry alone is not a hardware support claim. This change
addresses the selected DE0-CV target. The source-closure repair initially passed 90 SDK tests.


### Peripheral DE0-CV follow-up (26 November)

Full synthesis exposed two further issues. Quartus appended its
`LAST_QUARTUS_VERSION` bookkeeping assignment to the generated QSF, causing
an incorrect post-programming hardware-change error. Cache schema 7 ignores
that assignment and normalizes trailing QSF whitespace; it still hashes the
actual tool version, device, constraints and RTL. It now also hashes root
`paths.yaml`, so changing the selected source closure invalidates the cache.
Two regressions cover bookkeeping versus real device changes and source-list
changes.

The peripheral platform also omitted `clocks.fetch`, which made the generated
top use the core clock for the synchronous boot ROM. The Core IF/ID register
captures instruction and PC at the core edge; with a shared edge, it captures
the previous ROM instruction alongside the current PC. A focused GHDL test
using the actual Core `reg_if_id` and a synchronous ROM model reproduced this
mismatch. Adding an explicit 50 MHz fetch clock at phase 0, before the 50 MHz
core at phase 8250 ps, passed the same interface test. This test did not
represent a full-SoC simulation or physical keyboard-input validation.

The complete SDK suite passed 93 tests; Ruff checks passed. Physical validation
of this revised peripheral configuration is recorded separately when complete.

### Expansion GPIO and stepper follow-up (27 November)

The previous isolated KEYBOARD programming log completed with `KEYBOARD
example: PASS` and `Program: PASS`. This established loading and execution of
that firmware, not reception of physical keyboard input.

The peripheral DE0-CV map exposed an expansion GPIO driver without actually
instantiating its register bank on the generated board top. The Tools repair
connects its MMIO window to an adaptive GPIO instance and the board's expansion
ports. It rejects out-of-range pins and overlapping claims by separate banks.
The current example's group 0 maps logical pins 0--7 to `GPIO_0[0..7]`.
Expansion GPIO interrupt routing remains disabled; this motor example polls
the CLINT and does not use GPIO interrupts.

Quartus also exposed a range-direction error for unassigned GPIO pins.
Peripherals now normalizes unconstrained direction/polarity vectors before
slicing. The existing GPIO testbench supplies ascending actuals, and a focused
GHDL regression checks forward/reverse half-step patterns on nonconsecutive
physical pins, unassigned-pin states and coil release. The old GPIO revision
failed that regression during elaboration. Explicitly sized SoC switch/key
generic actuals additionally fix GHDL's rejection of unconstrained `others`.

Cache schema 8 hashes only the selected private board view, while retaining
shared RTL inputs. A full compilation was initially rejected because SDK tests
generated unrelated board runtimes during synthesis. A regression now checks
that another board does not change the key, while changes to the selected top
still invalidate it. Private runtime generation also notices changes to Tools'
memory-map, top and port generators.

Validation passed 95 SDK tests, 206 relevant Tools tests, 38 GPIO cocotb tests
across seven configurations, and the three extension test files. Both stepper
applications cross-compiled; their timer-only paths and shortened forward/
reverse motor paths executed successfully on the modular simulated processor.
Only the simulation copies used shorter phase delays and step counts. The
physical projects select `periph-de0-cv`, with a 1 MHz CLINT, 2 ms minimum phase
delay and 1,024 half-steps in each direction.

The final Quartus build completed with zero errors and 99 warnings. Its 84
reported slack values were nonnegative (minimum 0.107 ns). Some I/O assignments
and setup/hold paths remained incompletely constrained; this was not a claim
of complete board-interface timing signoff. The SOF cache round-trip passed for
both application configurations, including verification that their additional
SDRAM debug-window metadata described the same platform and compiled design.

After reconnecting the DE0-CV, JTAG detected device `02B050DD` on
`USB-Blaster [6-1]`. Restarting the user-owned jtagd service recovered an
initial stale connection (`sudo -n killall jtagd` required a password). Full
programming with the C application hit the SOF cache and passed on the board;
the Rust application then passed using fast update. Both confirmed CLINT
progress and program output with motor outputs disabled.

A separate physical GPIO diagnostic verified output-register readback for
`0x55`, `0xaa`, `0x00` and `0xff`, restored the saved output value, and confirmed
that all eight GPIO directions remained inputs throughout. This established
MMIO access to the newly instantiated expansion bank without energizing pins.
It did not measure connector voltages or demonstrate mechanical motor motion.
`RUN_MOTOR` stays disabled pending identification of the actual IN1--IN4 wiring.
Examples and running instructions are in `examples/stepper/`. No main merge
was performed.


### Language servers (27 November)

The following editor repair did not change motor activation or GPIO RTL.
The SDK now generates clangd compilation databases for the original application
sources, additional sources and vendored drivers, using their configured header
directories and ISA/ABI. Dev Containers install clangd and its VS Code client.
Rust setup installs the rust-analyzer component matching the active toolchain;
the marketplace-bundled server required Rust 1.94+, whereas this SDK uses 1.85.1.
Analysis follows the project target, enables build scripts/macros and omits the
no-std-incompatible test harness. The standard dedicated target/rust-analyzer
directory resolves generated bindgen includes; the custom build/ location did not.

Real clangd checking completed with zero errors. A real rust-analyzer 1.85.1 LSP
session resolved GPIO type information, driver definitions and generated binding
definitions, including include! expansion. Cargo check, 99 SDK tests and the
three extension test files passed. Live 0.10.1 was packaged and installed locally,
and the SDK's bundled VSIX was updated. Existing containers require a rebuild
after Prepare Project so their extension/package installation is refreshed.
Details are in LANGUAGE-SERVERS.md. No GitHub push was performed in this step.
