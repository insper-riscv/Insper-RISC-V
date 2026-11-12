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
