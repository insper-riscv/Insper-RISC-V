# SDK 0.5.0 acceptance — 2026-11-10

Processor baseline: 0ea346054db8f74d02910e81eda5f20504ec7a2f (main 0.4.2).
Tools baseline: 0340eefe0e95c674d68f7516c392b5c8f17cf7f3 (1.13.0), with committed SDK patch.

Passed on the final candidate:

- 30 SDK unit tests; Python lint, formatting and dependency analysis.
- All processor platform tops compile; generic, duplicate definition and IRQ checks pass (`make check`).
- Seven real C/GHDL checks cover multiple sources, header paths containing spaces,
  malloc, exact output without a newline, absent/stale output, 1,200 output lines,
  debug diagnostics, compile failures, nonzero exits and bounded infinite loops.
- Real Rust compilation and simulation, with exact stdout.
- A fresh SDK copy downloads/applies the pinned dependency, generates its runtime,
  compiles and simulates C without a prior virtual environment or generated view.
- Cyclone V USB-Blaster [1-2], chip ID 02B050DD, on the lab workstation:
  cold-cache synthesis/programming, cache-hit reprogramming without synthesis,
  C fast update with all 1,200 lines / 13,200 bytes, empty stdout without stale
  content, Rust simulation → FPGA fast update → simulation with correct relinking.
- Live extension: 10 unit checks, clean VSIX packaging and bundled/source content
  comparison. Real VS Code extension-host C and Rust command checks are recorded
  separately in the Live validation report.

The pinned Tools functional suite previously passed 890 tests with 10 skipped;
its static-analysis test was excluded because SDK checks run separately.

No processor RTL is changed by the SDK additions. Upstream's ordinary runtime
and memory map remain unchanged. The SDK runtime view is generated separately.
This does not certify other boards or SDK platforms. No Rust allocator is supplied.
No merge has been performed as part of this validation.
