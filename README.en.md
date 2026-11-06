# Insper-RISC-V

🌐 [Português](README.md) · [English](README.en.md)

![Pipeline diagram](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

32-bit RISC-V SoC in VHDL. The core is an in-order five-stage pipeline implementing RV32IM with the Zicsr, Zicntr, Zihpm, Zifencei and Zicclsm extensions, in 60 profiles generated from one matrix. This repository is the top of the project. It wires the core (`Core`), the memories (`Memory`), the peripherals (`Peripherals`) and the shared blocks (`Common-Components`) into two platforms, the `internal-mem` simulation platform and the DE0-CV board (Cyclone V), and it holds the Quartus project, the runtime, the memory map, the platform testbenches and the joint continuous integration. The work is split into repositories of the [insper-riscv](https://github.com/insper-riscv) organization, one per responsibility.

## 1. Documentation

- [AUTHORS.en.md](AUTHORS.en.md): authors with commits in the repository, with name and GitHub account.
- [CONTRIBUTING.en.md](CONTRIBUTING.en.md): mandatory contribution rules, the VHDL-2008, C23 and Python standards, documentation rules and the checks before opening a Pull Request.
- [CITATION.cff](CITATION.cff): metadata to cite the software.
- [docs/pt-br/](docs/pt-br): guides (board, simulation and KPIs), platforms (memory, boot and runtime) and diagnosed defects (in Portuguese).
- [docs/en/interconnect/ext_interconnect.md](docs/en/interconnect/ext_interconnect.md): the external interconnect, which decodes the platform map between the SDRAM and the peripherals, its AXI4 variant and the integration tests.
- [docs/pt-br/guide/kpis.md](docs/pt-br/guide/kpis.md): KPI scripts (frequency, resources, CPI and tests) from a Quartus run (in Portuguese).

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
| `src/simulation/modular/` | Configurable simulation top, with the ROM and the RAM inside or outside the chip and the instruction and data caches present or not, in the 16 combinations, 1 MB FLASH and RAM and 4 kbit caches by default. It runs the programs of the Tests repository and is the base of the ACT4 simulation |
| `src/simulation/template/` | Minimal model platform (internal RAM and ROM, optional UART over JTAG, `rv32i` profile), the starting point of the new architecture guide |
| `src/cyclone-v/external-data/` | The DE0-CV board platform with the BOOT_ROM and the two-port FLASH inside the FPGA (a single copy, rewritten over JTAG) and the SDRAM behind the data cache, plus a JTAG UART and a display. The Quartus top is `external-data_top.vhd` and the simulation top is `rv32im_external_data_sim_test` |
| `src/cyclone-v/de0-cv/` | The DE0-CV board platform, with the BOOT_ROM in the core and the FLASH and the SDRAM behind the caches, plus a JTAG UART and a display. The Quartus top is `de0-cv_top.vhd` and the simulation top is `rv32im_sdram_flash_sim_test` |

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
make all        # paths, integration check, and the tests and formal proofs of this repository
```

The tools come from the `ci-vhdl` image (`ghcr.io/insper-riscv/ci-vhdl`) of Infra, which the continuous integration runs in.

| Target | What it runs |
| :--- | :--- |
| `make paths` | Existence of the paths the configuration of this repository lists (`paths.yaml`, `riscv-tools check-paths`) and the shape of the tree |
| `make check` | The build of the simulation top of each platform with the pinned submodules and the check that no entity or package is defined in two repositories |
| `make memory-map` | Agreement of every copy of the memory map with the `platform.yaml` of the platform |
| `make unit-tests` | Cocotb tests of the platforms of this repository, plus `memory-map` |
| `make formal` | Formal proofs (SymbiYosys) of the interconnect of this repository, with the engine of `FORMAL_ENGINE` (`bitwuzla` by default; the CI runs `yices`, `bitwuzla`, `boolector` and `abc-bmc3`) |

Each repository runs only its own checks, tests and proofs; those of the submodules run in the CI of each one.

## 5. Board

The Quartus project of the DE0-CV (Cyclone V 5CEBA4F23) is `src/cyclone-v/de0-cv/de0-cv.qpf`. Programming it and running tests on it is done by `riscv-tools run` from `Tests`, as described in [placa.md](docs/pt-br/guide/placa.md) (in Portuguese).

## 6. KPIs

`scripts/kpi_report.py` and `scripts/compare_kpis.py` generate the KPI reports (clock, resources, CPI and tests) from a Quartus run, as described in [docs/pt-br/guide/kpis.md](docs/pt-br/guide/kpis.md).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](LICENSE).
