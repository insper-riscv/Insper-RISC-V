# The `internal-mem` platform: the simulation platform

## 1. What it is

A Cyclone V 5CEBA4F23 with BOOT_ROM, FLASH and RAM inside the FPGA. It is the base of the pipeline entity tests and of the simulation with plain VHDL arrays, and it also has a hardware top (`core_fpga_test`) to check the Quartus project.

## 2. Structure

| Path | Content |
| :--- | :--- |
| `platform.yaml` | The memory map (regions, reserved words, boot entry points and peripheral windows) and the list of each hand-written copy of it, checked by `riscv-tools check-memory-map` |
| `quartus/` | The Quartus project of the board, with `core_fpga_test.vhd` (hardware top), `.qpf`, `.qsf`, `.sdc` and the initial `.mif` images |
| `pll/` | The PLL IP (50 MHz in three phases) and `pll_sim.vhd`, the behavioral substitute that simulates it |
| `rtl/` | The simulation top `rv32i3stage_core_sim_test` (plain VHDL arrays in place of the memory IPs), `clk_gen_3way` and `Blinky` |
| `runtime/` | What the platform adds to the toolchain picolibc, with `rv32im-fpga.specs`, `boot_rom.S`, `boot_rom.ld`, `memory_map.h`, `_exit.c`, `stdio.c` and `spike_exit.S` |
| `testbench/` | `test_c_program.py`, the cocotb testbench that watches the RAM write bus to decide PASS or FAIL of a program |
| `config.yaml`, `config.fpga-sim.yaml` | `riscv-tools` configuration for the platform, of the simulation top and of the hardware top over the Intel `altera_mf` models |

## 3. Use by a project

A project that runs tests on this platform extends its configuration and adds only its own paths.

```yaml
extends: <path>/src/simulation/internal-mem/config.yaml
paths: {include_dir: ..., build_dir: build, c_dir: c, asm_dir: asm}
```

The paths inside `config.yaml` are relative to the root of the repository. The `sim.python_path` field puts `testbench/` on the search path of the simulation test module.

## 4. Serial UART

Peripheral window 4, at `0xC0000000`, contains the physical serial UART. It operates at 115200 baud with 8N1 framing and has independent 16-byte transmit and receive queues. The hardware top connects RX to pin M16 and TX to pin C16 of the DE0-CV. The simulation top exposes the same lines to the testbench.

The map has `TX_DATA` at `0xC0000000`, `RX_DATA` at `0xC0000004`, `STATUS` at `0xC0000008`, and `CONTROL` at `0xC000000C`. The complete register and queue contract is in the [serial UART documentation](https://github.com/insper-riscv/Peripherals/blob/main/docs/en/UART/serial_uart.md).

This UART differs from the JTAG UART of the `de0-cv` platform. Both peripherals use the same window in different platforms, but they have separate host interfaces and status maps.

## 5. Verification

| Target | What it checks |
| :--- | :--- |
| `make memory-map` | Agreement of each copy of the memory map with `platform.yaml` |
| `make check-tops` | The simulation top elaborates in GHDL |
| `make test` | cocotb per-entity tests of the platform RTL |
