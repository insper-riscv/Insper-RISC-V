# Simulation of the hardware top

`riscv-tools sim` has two profiles. The default (`config.yaml`) simulates a top made for simulation, with the memories as plain VHDL arrays. The `config.fpga-sim.yaml` profile simulates the **real hardware top** (`core_fpga_test`), with the three real Quartus memories (BOOT_ROM, FLASH and RAM) running on Intel's own simulation models. This guide explains what the second profile covers in addition, how to run it and what stays on the hardware only.

## 1. What changes compared to the default sim

| Piece | `config.yaml` (default) | `config.fpga-sim.yaml` |
| :--- | :--- | :--- |
| Top | `rv32i3stage_core_sim_test` | `core_fpga_test`, the same file as the Quartus project, unchanged |
| Memories | `ROM_simulation` and `RAM_simulation` (VHDL arrays) | `boot_rom`, `flash` and `ram`, the Quartus wrappers over the `altsyncram` model, plus the FLASH loader |
| Loaded image | `.hex`, through a VHDL generic | `.mif`, through the IP `init_file` (`init.mif` and `boot_rom_init.mif`), the same images as the hardware |
| RAM address | Absolute bus address | Address relative to `ram_base`, as on the hardware (see `core_fpga_test.vhd`) |
| Clock | `clk_gen_3way`, pulses of a base clock three times faster | `pll_sim.vhd`, three 50 MHz clocks, 50 % duty cycle, shifted 0, 6667 and 13333 ps, like the real PLL |
| Reset | Active high (`i_rst`) | `i_fpga_reset_n`, active low, plus the wait for the PLL `locked` |

The core (`rv32im_pipeline_core.vhd`) is the same in both profiles.

The real PLL (`src/simulation/internal-mem/pll/pll.vhd`) wraps an `altera_pll` IP whose simulation model is SystemVerilog, which GHDL does not run. The file `src/simulation/internal-mem/pll/pll_sim.vhd` has the same entity and ports, with the parameters of `pll_0002.v`, and takes its place only in simulation. It is not part of the Quartus project.

## 2. Prerequisites

1. The Quartus simulation library, `altera_mf_components.vhd` and `altera_mf.vhd`, in `<Quartus>/eda/sim_lib/`. It comes with Quartus, so this profile runs where Quartus is installed, and not on a GitHub-hosted runner.
2. The `QUARTUS_ROOTDIR` variable pointing to the `quartus` directory of the installation (for example `/opt/altera_lite/25.1std/quartus`).
3. GHDL, GCC with picolibc and Spike, as in the default sim (the `ci-elf` image has all three).
4. The Core, Memory and Peripherals checkouts next to the test project (`../Core`, `../Memory`, `../Peripherals`), or the submodules of this repository.

## 3. How to run

```bash
export QUARTUS_ROOTDIR=/opt/altera_lite/25.1std/quartus

uv run riscv-tools --config tools/riscv_build/config.yaml generate-header
uv run riscv-tools --config tools/riscv_build/config.yaml compile --emit mif
uv run riscv-tools --config tools/riscv_build/config.fpga-sim.yaml sim
```

To run only the three UART tests on the FPGA top:

```bash
uv run riscv-tools --config tools/riscv_build/config.fpga-sim.yaml \
  sim --only uart-echo,uart-tx,uart-errors
```

`compile --emit mif` generates the images and goldens in `build/real/`, and `sim` with the new profile reads those images, generates the BOOT_ROM `.mif` and runs the tests. The `altera_mf` library is analyzed once per run inside `build/sim/sim_work/<simulation-profile>/libraries`. The profile name combines the top with a stable fingerprint of the full configuration, avoiding reuse of incompatible artifacts between profiles.

## 4. What the verification does

The test module (`src/simulation/internal-mem/testbench/test_c_program.py`) is the same for both profiles. It watches the RAM write bus (`ram_wren`, `ram_en`, `ram_addr`, `ram_wdata`, `ram_byteena`), looks for the write to `tohost` (1 is PASS, `(code << 1) | 1` is FAIL) and, in memory tests, compares the reconstructed RAM content with the golden. The hardware top profile only changes what it drives, through environment variables (`sim.env`): clock and reset name, period, sampling clock (`pll_clk_idexmem`, the RAM one) and cycle limit.

## 5. What stays on the hardware only

| Item | Why |
| :--- | :--- |
| FLASH write over JTAG (In-System Memory Content Editor) and `fromhost` coming from the host | They only exist on the board. In simulation the image is loaded from the file |
| Timing and synthesis | The simulation is functional. It does not see maximum frequency, setup and hold violations or optimization |
| Real initial state of the FPGA | The simulation initializes memory and registers in a predictable way |
| RAM content read from inside the IP | GHDL only exposes signals, so the content is reconstructed from the bus, not read from the memory |
| Real PLL | Replaced by `pll_sim.vhd`, with no jitter or real lock time |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
