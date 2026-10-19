# Live C workspace

Complete setup, environment variables, simulation and FPGA instructions are
documented in [`../docs/VSCODE_LIVE_C.md`](../docs/VSCODE_LIVE_C.md).

Edit `c/live/src.c`, then use **Terminal > Run Task** in VS Code.

- `RV32: Simulate C program` runs the program with GHDL/cocotb.
- `RV32: Run C on FPGA (first/full configuration)` synthesizes and programs
  the board, then runs the program. Use it once, or after changing VHDL.
- `RV32: Run C on FPGA (fast JTAG update)` changes only the application image.
  It is the normal edit/run loop and does not synthesize the FPGA again.
- `RV32: Run C on FPGA (reuse existing SOF)` is for a power-cycled board when
  the already-built `.sof` still matches the VHDL sources.

The program's return value is reported through the mailbox. `printf`, `puts`
and `putchar` are copied from the RAM stdout buffer and printed after a real
FPGA run.
