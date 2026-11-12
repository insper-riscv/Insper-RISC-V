# SDK 0.6.0 CPU profile acceptance — 2026-11-12

Processor baseline: dfdf585e87355a739916cd3140adc40e21982aa3.
Tools: pinned 1.13.0 plus SDK patch, unchanged.

- 36 SDK unit tests passed, including all eleven named profile configurations, preservation of memory/UART, reduced HPM limits in both tops, unsupported source extensions, SOF invalidation and fast-update profile guard.
- Real GCC16.1/GHDL6 execution of the division/printf probe passed for all eleven named profiles, with exact stdout.
- Existing seven real C CLI integration checks passed, including malloc/multiple sources, 1,200 output lines, failures and bounded loops.
- Real Rust 1.85.1 compilation, C-runtime linking and GHDL simulation passed for RV32I and RV32IM with exact stdout. Rustup was copied for isolated testing; the user's installed toolchain was not modified.
- Python lint, formatting and dependency checks passed.
- DE0-CV on USB-Blaster [1-6]: RV32I synthesis/programming then FPGA Fast Update both emitted exactly `profile=7\n`, no diagnostic output/errors. The first prototype exposed QSF literal-brace path handling; corrected double-quoted assignments passed real Quartus. The DE2-115 remained untouched. Container capped at 6 GiB, no swap.
- Local development checks used the pinned multilib image now referenced by templates and SDK CI. The prior single-variant image cannot be assumed safe for a CPU without M, so that combination is explicitly rejected.

No tracked processor RTL or platform memory map was edited. No main merge was performed. These tests do not certify other boards or explicit profile overrides on platforms other than internal-mem.
