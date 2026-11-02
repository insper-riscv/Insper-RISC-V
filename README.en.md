# Insper-RISC-V

🌐 [Português](README.md) · [English](README.en.md)

![Pipeline diagram](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

32-bit RISC-V SoC in VHDL. The core is an in-order five-stage pipeline implementing RV32IM with the Zicsr, Zicntr, Zihpm, Zifencei and Zicclsm extensions, in 60 profiles generated from one matrix. This repository is the top of the project. It wires the core (`Core`), the memories (`Memory`), the peripherals (`Peripherals`) and the shared blocks (`Common-Components`) into two platforms, the `internal-mem` simulation platform and the DE0-CV board (Cyclone V), and it holds the Quartus project, the runtime, the memory map, the platform testbenches and the joint continuous integration. The work is split into repositories of the [insper-riscv](https://github.com/insper-riscv) organization, one per responsibility.

## 1. Documentation

- [AUTHORS.en.md](AUTHORS.en.md): authors with commits in the repository, with name and GitHub account.
- [CONTRIBUTING.en.md](CONTRIBUTING.en.md): mandatory contribution rules, the VHDL-2008, C23 and Python standards, documentation rules and the checks before opening a Pull Request.
- [CITATION.cff](CITATION.cff): metadata to cite the software.
- [docs/pt-br/platform/](docs/pt-br/platform): memory architecture, boot, runtime, board programming and simulation of the hardware top (in Portuguese).
- [docs/README_kpis.md](docs/README_kpis.md): KPI scripts (frequency, resources, CPI and tests) from a Quartus run (in Portuguese).

## 2. Repositories

| Repository | Responsibility | Depends on |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | The toolchain image (GCC with picolibc, Spike, GHDL, uv) the continuous integration runs in | Nothing |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`, to build, simulate, run on the board, certify and verify | Infra (at run time) |
| [Common-Components](https://github.com/insper-riscv/Common-Components) | The generic VHDL blocks (adder, flip-flop, registers, multiplexers, one-hot decoder and tri-state buffer) | Nothing |
| [Core](https://github.com/insper-riscv/Core) | The processor in VHDL, by ISA extension, profiles and per-entity tests | Common-Components |
| [Memory](https://github.com/insper-riscv/Memory) | Memories, caches, controllers and simulation models | Core (memory interface) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO, TIMER and UART, with per-entity tests | Common-Components |
| [Tests](https://github.com/insper-riscv/Tests) | The test programs (`asm/`, `c/`), goldens and the flows that run them | This repository, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | The official ACT4 suite (riscv-arch-test) | This repository, Tools |

`Common-Components`, `Core`, `Memory` and `Peripherals` are the submodules of this repository.

## 3. Platforms

| Path | Platform |
| :--- | :--- |
| `src/simulation/internal-mem/` | Simulation-only platform, with BOOT_ROM, FLASH and RAM inside the FPGA and the `rv32i3stage_core_sim_test` simulation top. It is the base of the pipeline entity tests |
| `src/cyclone-v/de0-cv/` | The DE0-CV board platform, with the BOOT_ROM in the core and the FLASH and the SDRAM behind the caches, plus a JTAG UART and a display. The Quartus top is `core_fpga_sdram_flash.vhd` and the simulation top is `rv32im_sdram_flash_sim_test` |

Every platform has the same structure.

| Folder or file | Content |
| :--- | :--- |
| `platform.yaml` | The memory map and the list of each hand-written copy of it, checked by `riscv-tools check-memory-map` |
| `config.yaml` | `riscv-tools` configuration for toolchain, memory, Quartus and simulation |
| `quartus/` | The Quartus project (`.qpf`, `.qsf`, `.sdc`, hardware top and `.mif` images) |
| `pll/` | The PLL IP |
| `rtl/` | The simulation top and the modules of the platform |
| `runtime/` | `rv32im-fpga.specs`, `boot_rom.S`, `boot_rom.ld`, `_exit.c`, `stdio.c` and `spike_exit.S` |
| `testbench/` | `test_c_program.py`, the cocotb testbench that decides PASS or FAIL of a program |

The per-entity tests of the platform RTL are in `tests/python/`, with the `tests.json` catalog that drives them.

## 4. Cloning and Running

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
make all        # paths, VHDL check, per-entity tests and formal proofs
```

The tools come from the `ci-vhdl` image (`ghcr.io/insper-riscv/ci-vhdl`) of Infra, which the continuous integration runs in.

| Target | What it runs |
| :--- | :--- |
| `make paths` | Existence of every path the configuration lists (`paths.yaml`, `riscv-tools check-paths`) |
| `make check` | VHDL syntax check of each repository, the elaboration of each `Core` profile, the build of the simulation top of each platform and the check that no entity or package is defined in two repositories |
| `make memory-map` | Agreement of every copy of the memory map with the `platform.yaml` of the platform |
| `make unit-tests` | Per-entity tests (cocotb and GHDL) of each repository and of the platforms, plus `memory-map` |
| `make formal` | Formal proofs (SymbiYosys and z3) of each repository that has them |

## 5. Board

The Quartus project of the DE0-CV (Cyclone V 5CEBA4F23) is `src/cyclone-v/de0-cv/quartus/core_fpga_sdram_flash.qpf`. Programming it and running tests on it is done by `riscv-tools run` from `Tests`, as described in [HARDWARE_PROGRAMMING.md](docs/pt-br/platform/HARDWARE_PROGRAMMING.md) (in Portuguese).

## 6. KPIs

`scripts/kpi_report.py` and `scripts/compare_kpis.py` generate the KPI reports (clock, resources, CPI and tests) from a Quartus run, as described in [docs/README_kpis.md](docs/README_kpis.md).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](LICENSE).
