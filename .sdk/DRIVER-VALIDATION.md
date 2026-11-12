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
