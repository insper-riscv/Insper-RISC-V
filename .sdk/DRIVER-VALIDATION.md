# SDK/Live 0.8.0 project and example acceptance — 2026-11-12

The extension now creates Rust 2024 firmware projects and can initialize an
existing Rust folder without overwriting its files. Remote folder URI scheme
and SSH authority are preserved. Run actions use the nearest project TOML while
retaining a real VS Code workspace task scope.

Validated locally in a pinned image with an 8 GiB/no-swap/two-CPU limit:

- 57 SDK unit tests passed, including standalone per-driver projects, inherited
  platform/profile, disabled recursion, compiler input exclusion, edit protection,
  current descriptor preflight and serial-versus-JTAG backend selection.
- Six generated modular projects passed actual CPU simulation: CLINT, GPIO,
  PLIC, TIMER, UART and DISPLAY. The default internal-memory serial UART example
  also passed simulation; its slot 4 does not imply JTAG. Parent refresh after
  running child projects passed without claiming child build artifacts.
- All five generated DE0-CV projects compiled through the public SDK command,
  including FLASH. No physical programming or Quartus synthesis was performed.
  The FLASH sample only reads status and issues no erase/program command.
- The full GPIO and Peripherals examples passed in RV32I, RV32IM and
  rv32im_zicsr_irq (six executions). Both now contain matching independent
  container/editor/task infrastructure. Peripherals defaults to the IRQ profile.
- An actual project copied from the extension's Rust template compiled/linked
  and simulated with exact Hello stdout on both default RV32IM and RV32I using
  Rust 1.85.1. stderr was empty. No GPIO Rust wrapper code was generated.
- All three Node test files passed, covering registered commands, actual Rust
  creation, preservation of existing source, remote URI handling, and nested
  example task arguments. The VSIX payload was verified against source and the
  SDK's bundled copy. Compose validation passed for both full C examples and
  the Rust template; SDK lint/format/dependency checks passed.

Example sources are supplied by Peripherals descriptors and emitted only for
available drivers on supported SDK platforms. Their mains are excluded from
parent compiler inputs. Each child disables further example generation.
Managed files retain overwrite protection; copy the child project to customize.
Device widths/capacities follow platform I/O, explicit generic overrides or
literal RTL defaults rather than MMIO slot sizes.

No processor RTL, normal platform map or C driver ABI changed. No main merge
or new PR was performed. Historical acceptance records follow below.

---

# SDK 0.7.1 peripheral driver acceptance — 2026-11-12

Current Peripherals commit: `0b44c0b` on `c-drivers`. This is a software-only
addition: no VHDL, formal property, Common-Components pin or platform map changed.
The previous SDK 0.7.0 acceptance is retained below as historical context.

Validated in the pinned multilib CI image with one container capped at 8 GiB
RAM, no swap and two CPUs:

- 53 SDK unit tests passed, including changed map addresses, IRQ aliases,
  explicit CPU-profile elaboration requirements and managed-file protection.
- Six actual CPU RTL simulations passed with exact application stdout:
  `examples/gpio` and `examples/peripherals`, each on RV32I, RV32IM and
  `rv32im_zicsr_irq`. GPIO uses constructors, numeric pin indices, bounded
  condition polling and no arbitrary settle delay. The combined example checks
  TIMER overflow/read-clear, UART readiness/transmit/empty receive behavior and
  display digit writes. With the interrupt fabric enabled, it additionally checks
  coherent CLINT time, safe deadline/software IRQ accesses and GPIO-to-PLIC
  pending/claim/complete. It does not claim full serial/JTAG host I/O coverage.
- Both native C MMIO test binaries passed with AddressSanitizer and
  UndefinedBehaviorSanitizer. All seven drivers compile with strict warnings
  on the host and for both RV32I/RV32IM (fourteen cross-compilations).
  RAM-backed tests do not emulate hardware side effects or timing.
- The complete peripheral VHDL syntax and cocotb suite passed: 207 tests across
  thirty test entries, zero failures/skips. Those tests independently cover
  device-side behavior; FLASH was not executed by C on a physical board or on
  the modular CPU, which does not map FLASH_CTRL.
- SDK Ruff lint/format and dependency checks passed. Paths/tree checks passed
  with all driver descriptors. The Live 0.7.1 Node tests and syntax checks passed;
  its rebuilt VSIX was checked byte-for-byte against the bundled copy and source,
  including the new `.clang-format` project template.

CLINT and PLIC are not vendored when a CPU profile removes the SoC interrupt
fabric. The modular SDK-only simulation view now enables its declared display;
normal processor configuration and hardware behavior are unchanged. No driver
installs trap handlers or enables machine interrupts automatically.

Instance bases come from the platform map; internal register offsets follow
RTL and remain private C implementation details. GPIO pins and display digits
are zero-based size_t indices; PLIC source zero is reserved. Constructors require
actual device widths/capacities rather than guessing them from MMIO slot sizes.

No main merge, new pull request or physical board access was performed.

---

# SDK 0.7.0 peripheral driver acceptance, 2026-11-12

Baseline processor main is dfdf585e87355a739916cd3140adc40e21982aa3. The GPIO
addition advances only the Peripherals pointer; its VHDL, common submodule and
formal properties remain identical to the baseline. Other processor submodules,
platform maps and normal runtimes are unchanged.

Validated locally with the pinned multilib CI image:

- 46 SDK tests, including map-derived absolute addresses, slot/IRQ ID distinction,
  UART-only maps, two instances sharing one implementation, too-small windows,
  unsafe paths, symlinks, edited/unmanaged files, stale owned-file removal,
  automatic C linking, simulation-only FPGA rejection and hardware-cache behavior.
- Actual C driver execution on the modular CPU/GPIO RTL in RV32I, RV32IM and
  rv32im_zicsr_irq. Exact stdout verified direction/output, set/clear/toggle,
  synchronized pins, rising/falling interrupts, read-and-clear status and two
  independent instances. These were CPU executions of the vendored C implementation,
  not host mocks. Default internal memories use compact private simulation models.
- Previous eleven-profile GCC/GHDL, seven C integration, two Rust target and
  RV32I FPGA Program/Fast Update acceptance is recorded in PROFILE-VALIDATION.md.
  GPIO is not mapped by the default FPGA platform; no physical GPIO validation
  is claimed. The modular SDK view cannot program a board.
- SDK lint, formatting and dependency checks passed. The Live package tests
  cover the three editor buttons and the new driver-refresh command. The VSIX
  payload/version was verified against rebuilt source.

Peripherals validation additionally passed the full make check, make test,
make paths and make formal (default Bitwuzla). All 158 proof/mutation expectations
were met: 43 proofs/covers passed, 115 intentional mutants were rejected, zero
formal warnings. All thirteen repository static checks passed. The formal Python
environment now declares SymbiYosys's Click dependency; the plain image had failed
before reaching any verdict without it. The remote container was capped at 6 GiB
without swap; local SDK containers were capped at 8 GiB without swap.

No main merge or new pull request was created. Existing PR 134 was resolved using
the modern SDK, retaining the C example under examples/live-c. Its prior full CI
passed after correcting the example folder naming rule. The final combined head
must pass CI again before merge; do not substitute the earlier result for it.
