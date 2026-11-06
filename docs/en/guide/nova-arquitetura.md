# How to create a new architecture in Insper-RISC-V

This guide takes a clean clone of `Insper-RISC-V` to a new platform running in simulation (and, if there is a board, on the FPGA). A platform is a folder `src/<family>/<platform>/` with its memory map, its selection of memories and peripherals and its Core profile. The running example is called `example`, in the `simulation` family, with a larger RAM and the `rv32im` profile instead of the model platform's.

## 1. What a platform is

### 1.1. The blocks

| Block | Repository | What it provides |
| :--- | :--- | :--- |
| Core | `Core` | The processor, chosen by a profile (base `rv32i` or `rv32e` plus the extensions) |
| Memory | `Memory` | BOOT_ROM, ROM, RAM, caches, FLASH chip and region router |
| Peripherals | `Peripherals` | UART, GPIO, timer and display, each with an `soc` side (family independent) and a per-family side |
| Common-Components | `Common-Components` | Multiplexers, registers and utility packages, present as a submodule in the other three |
| Insper-RISC-V | this repository | Pins the version of each submodule and holds the platforms, which connect the blocks |

### 1.2. What the platform contains

| File | Written by | Content |
| :--- | :--- | :--- |
| `platform.yaml` | A person | Source of the memory map, Core profile, reserved words, peripherals and files to generate |
| `rtl/<platform>_map_pkg.vhd` | `riscv-tools generate-memory-map` | VHDL constants of the map and of the profile |
| `runtime/rv32im-fpga.specs`, `runtime/boot_rom.ld`, `runtime/memory_map.h` | `riscv-tools generate-memory-map` | Linker parameters, BOOT_ROM script and runtime addresses |
| `rtl/<platform>_sim_top.vhd` | A person | Top, which only instantiates and connects the blocks |
| `runtime/boot_rom.S`, `_exit.c`, `stdio.c`, `spike_exit.S` | A person | What the program finds when it starts and when it ends |
| `config.yaml` | A person | `riscv-tools` configuration to build and simulate |

### 1.3. Reference example

The `de0-cv` platform (`src/cyclone-v/de0-cv/`) shows the complete case.

```text
 BOOT_ROM 4 KiB          Core (rv32im_...)             peripherals (bit 31 = 1)
 external ROM (FLASH) <-- instruction and data caches --> UART over JTAG (id 4)
 external RAM (SDRAM) <-- region router / interconnect --> display (id 5)
```

The model platform `src/simulation/template/` is the minimal version, with internal memories only, and is the starting point of chapter 3.

## 2. Prepare the environment

### 2.1. Clone

```bash
git clone --recurse-submodules git@github.com:insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
```

| Expected output | Common error and cause |
| :--- | :--- |
| Four submodules downloaded (`Common-Components`, `Core`, `Memory`, `Peripherals`) | Empty submodule folders, from a clone without `--recurse-submodules`. Run `git submodule update --init --recursive` |

### 2.2. Tools

The `riscv-tools` commands, `ghdl`, GCC with picolibc and Spike come from the Infra image. To run a command inside it:

```bash
docker run --rm -v "$PWD":/w -w /w ghcr.io/insper-riscv/dev_tools:latest <command>
```

The commands in the next chapters that start with `riscv-tools`, `make` or `ghdl` run this way, or in the shell of a container of the same image. If the container runs as a different user from the clone's, add `--user "$(id -u):$(id -g)"`.

### 2.3. Initial state

```bash
make all
```

| Expected output | Common error and cause |
| :--- | :--- |
| `paths OK`, `tree OK`, the platforms elaborate and the tests pass | `ghdl: command not found`, from running outside the image |

### 2.4. Quartus (board only)

For a Cyclone V FPGA platform, install Quartus Prime Lite on the host and leave `quartus_sh`, `quartus_pgm` and `jtagconfig` in the `PATH`. Chapter 10 uses them.

## 3. Create the platform folder

### 3.1. Copy the model

```bash
cp -r src/simulation/template src/simulation/example
```

### 3.2. Rename

The files that carry the platform name go from `template_*` to `example_*`, and the word `template` inside the files becomes `example`.

```bash
cd src/simulation/example
mv rtl/template_map_pkg.vhd rtl/example_map_pkg.vhd
mv rtl/template_sim_top.vhd rtl/example_sim_top.vhd
grep -rl template . | xargs sed -i 's/template/example/g'
cd ../../..
```

| Expected output | Common error and cause |
| :--- | :--- |
| `grep -r template src/simulation/example` finds nothing | `check-vhdl-style` reports an entity name different from the file, from forgetting to rename one of the two files in `rtl/` |

## 4. Describe the platform in `platform.yaml`

`platform.yaml` is the single source of the map. Nothing of the map is written by hand in another file.

### 4.1. Fields

| Field | What it defines |
| :--- | :--- |
| `platform` | Platform name |
| `profile` | Core profile, as `rv32i` or `rv32e` followed by the extensions (`rv32im`, `rv32im_zicsr`) |
| `profiles` | Path of `Core/profiles/matrix.yaml`, the profile specification |
| `regions` | Each region with `name`, `base`, `size` (a power of two or a sum, such as `1M-4K`), `kind` (`rom` or `ram`) and `exec` |
| `reserved` | The three words at the top of the RAM, `stdout`, `tohost` and `fromhost`, which must fit inside the RAM region |
| `boot` | `entry`, the address of the ROM `_start`, and `wait_restart`, the fixed address of the wait routine |
| `peripherals` | Each peripheral with `name`, `base` and `id` (bits 30:28 of the address) |
| `generate` | The files to write and the parameters of the VHDL package |
| `config` | What `config.yaml` reads from the map |

### 4.2. Edit

For the example, the RAM goes to 64 KiB and the profile to `rv32im`. The RAM starts at `0x8000`, so it ends at `0x18000`, and the reserved words move down with it.

```yaml
platform: example
profile: rv32im
regions:
  - {name: BOOT_ROM, base: 0x00000000, size: 4K,  kind: rom, exec: true}
  - {name: ROM,      base: 0x00001000, size: 28K, kind: rom, exec: true}
  - {name: RAM,      base: 0x00008000, size: 64K, kind: ram}
reserved:
  stdout:   {base: 0x00017BE0, size: 1K+8}
  tohost:   {base: 0x00017FE8, size: 8}
  fromhost: {base: 0x00017FF0, size: 8}
```

The `generate` lines say `src/simulation/template/...`; the rename of step 3.2 already moved them to `example`.

### 4.3. Generate and check

```bash
riscv-tools --root . generate-memory-map --platform src/simulation/example/platform.yaml
riscv-tools --root . check-memory-map --platform src/simulation/example/platform.yaml
```

| Expected output | Common error and cause |
| :--- | :--- |
| Four `generated:` lines (specs, `boot_rom.ld`, `memory_map.h`, VHDL package) and `memory map OK` | `reserved stdout ... is not inside a RAM region`, because the reserved addresses were left outside the RAM after changing its size |
| `HAS_M` true and `RAM_END_KIB` equal to 96 in the generated package | `profile` with a name that is not in `matrix.yaml` |

When the map changes, run the first command again. The `--check` of the same command fails if a generated file is out of date.

### 4.4. Register in the repository

The CONTRIBUTING requires updating `paths.yaml`, the `Makefile` and the documentation when files are added. For the new platform:

| File | What to add |
| :--- | :--- |
| `paths.yaml` | The platform files in the `references` list and the path fields of `config.yaml` |
| `Makefile` | The variable `P<x> := src/simulation/example`, the lines of `memory-map`, `generate` and `generate-check` and the top elaboration in `check-tops`, which reads the sources from `riscv-tools sources` |
| `paths.yaml` (`provides`) | The component of the top, with its sources and what it requires; `scripts/generate_sources.py` gains the list file of the platform |
| `docs/pt-br/platform/` | An `example.md` document and the row in the folder `README.md` table, with the mirror in `docs/en/` |

## 5. Choose the Core profile

### 5.1. The profile rule

The name of a profile is the base followed by the extensions in the order of `Core/profiles/matrix.yaml`, joined by `_`.

| Part | Values |
| :--- | :--- |
| Base | `rv32i` (32 registers) or `rv32e` (16) |
| Extensions, in this order | `zicclsm`, `zicsr`, `zicntr`, `zihpm`, `zifencei`, `zmmul`, `m` |

`zicntr` and `zihpm` imply `zicsr`, so the name never cites `zicsr` alongside them; `m` implies `zmmul`, and `m` and `zmmul` do not appear together. All other combinations are valid, which gives 60 profiles. To list them:

```bash
riscv-tools profiles --spec Core/profiles/matrix.yaml --format names
```

### 5.2. How the top passes the profile to the `core`

`generate-memory-map` writes one `HAS_*` constant per extension in the package (`HAS_E`, `HAS_M`, `HAS_ZICSR` and the others). The top connects them to the `core` generics of the same name, and the value comes from the `profile` of `platform.yaml` (step 6.3).

### 5.3. A profile that does not exist

If no profile fits, the new extension goes into `Core/profiles/matrix.yaml` as a pull request in the `Core` repository, with the extension folder in `Core/src/<extension>/`. The `Core` contribution guide describes the path. After that, the submodule pointer in this repository advances and the new profile holds on every platform.

## 6. Write the top

### 6.1. Structure of `<platform>_sim_top.vhd`

The simulation top of the model platform has six blocks, which the example keeps.

| Instance | Entity | Origin |
| :--- | :--- | :--- |
| `u_clock` | `clk_gen_3way` | `src/simulation/internal-mem/rtl/` |
| `u_core` | `core` | `Core/src/core/` |
| `u_boot_rom` | `rom_simulation` | `Memory/src/ROM/SoC/` |
| `u_rom` | `rom_simulation` (two ports) | `Memory/src/ROM/SoC/` |
| `u_ram` | `ram_simulation` | `Memory/src/RAM/SoC/` |
| `u_uart` (optional) | `jtag_uart` | `Peripherals/src/UART/jtag/` |

The core has three memory outputs: instruction fetch (BOOT_ROM and ROM), the data port of the ROM and the RAM, and the external bus, through which the peripherals pass.

### 6.2. Size generics

The memory sizes are power-of-two generics whose default comes from the generated package (`BOOT_ROM_SIZE_BYTES`, `ROM_STORAGE_BYTES`, `RAM_STORAGE_BYTES`). No size is written in the top.

### 6.3. Profile and map in the `core`

In the `generic map` of the `core`, each `has_*` receives the `HAS_*` constant of the package, and the region limits (`rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib`) receive the constants of the same name. If the profile of step 4.2 turns on `M`, `HAS_M` already arrives true, and nothing else changes in the top.

### 6.4. Window of each peripheral

The external bus of the core hands the top the address, the write data and the read and write enables. The UART answers when the four highest address bits are those of `UART_BASE`, which comes from the package, and the read data returns to the core on the cycle after the request. For a new peripheral, repeat the pattern: a selector by address, the enables filtered by the selector, the read data registered. For several peripherals on a board platform, use the `ext_interconnect` of `src/interconnect/`, which separates the SDRAM from the peripheral window and hands each one the word offset (`de0-cv_top.vhd` shows the use).

### 6.5. CONTRIBUTING conventions

| Rule | Application in the top |
| :--- | :--- |
| `i_` and `o_` ports | `i_clk`, `i_rst`, `o_uart_tdo` |
| `u_` labels | `u_core`, `u_ram` |
| 72-column header | `-- ====` block at the start of the file, in Portuguese |
| Docstring per declaration | A comment in Portuguese above each generic, port, signal and constant |
| Direct instantiation | `u_x : entity work.name`, without `component` |

### 6.6. Check

```bash
riscv-tools --root . check-vhdl-style
```

| Expected output | Common error and cause |
| :--- | :--- |
| `vhdl style OK` | A declaration without the comment above it, or a port without prefix |

### 6.7. Elaborate

```bash
mkdir -p build/example
ghdl -a --std=08 --workdir=build/example $(riscv-tools vhdl-sort \
    $(find Common-Components/src Core/src -name '*.vhd' -not -path 'Core/src/common/*') \
    Memory/src/RAM/SoC/ram_simulation.vhd Memory/src/ROM/SoC/rom_simulation.vhd \
    Peripherals/src/UART/jtag/jtag_uart.vhd \
    src/simulation/internal-mem/rtl/clk_gen_3way.vhd \
    src/simulation/example/rtl/*.vhd)
ghdl -e --std=08 --workdir=build/example example_sim_top
```

| Expected output | Common error and cause |
| :--- | :--- |
| No error message | `unit "..." not found`, from a missing file in the list or from it being out of order (`vhdl-sort` orders it) |

## 7. Runtime

The runtime is what the program finds when it starts and when it ends. The four hand-written files come from the model, and the map reaches them through the three files generated in chapter 4.

### 7.1. The files

| File | What it does | What changes with the map |
| :--- | :--- | :--- |
| `runtime/boot_rom.S` | `_reset` clears `stdout`, `tohost` and `fromhost` and jumps to `RV32_BOOT_ENTRY`; `rv32_wait_restart` waits for `fromhost` | Nothing, reads the addresses from `memory_map.h` |
| `runtime/boot_rom.ld` | BOOT_ROM link script, with `rv32_wait_restart` at `0x100` | Generated |
| `runtime/rv32im-fpga.specs` | Linker parameters (`__flash`, `__flash_size`, `__ram`, `__ram_size`) and the picolibc crt0 | Generated |
| `runtime/memory_map.h` | RAM, `tohost`, `fromhost`, `stdout`, boot entry and UART addresses | Generated |
| `runtime/_exit.c` | Writes the result in `tohost` and enters `rv32_wait_restart` | Nothing |
| `runtime/stdio.c` | Takes `printf` and `putchar` to the `stdout` buffer in the RAM | Nothing |
| `runtime/spike_exit.S` | The same program end for the Spike ELF | Nothing |

### 7.2. How `tohost` ends a program

| Value written to `tohost` | Meaning |
| :--- | :--- |
| `1` | Program passed (`main` returned 0) |
| `(code << 1) \| 1` | Program failed with the given code |
| `0` | Not finished yet |

The testbench watches the writes on the RAM bus, and the first nonzero write at the `tohost` address ends the simulation with the result.

### 7.3. Check

```bash
make memory-map
```

| Expected output | Common error and cause |
| :--- | :--- |
| `memory map OK` and `generated files OK` | `generated files are out of date`, from editing `platform.yaml` without running `generate-memory-map` again |

## 8. Simulation top and first program

### 8.1. The `config.yaml`

It gathers, for `riscv-tools`, what belongs to the platform.

| Section | Content |
| :--- | :--- |
| `toolchain` | GCC, `objcopy` and the platform `rv32im-fpga.specs` |
| `memory_map` | `platform.yaml`, where the bases, `tohost` and `fromhost` come from |
| `paths` | Runtime sources (`_exit.c`, `stdio.c`), `boot_rom.S` and `boot_rom.ld` |
| `sim.toplevel` | `example_sim_top` |
| `sim.vhdl_sources` | All sources, in dependency order, written by `make generate-sources` |
| `sim.test_module`, `sim.python_path` | The cocotb testbench, `testbench.test_c_program` of the `internal-mem` platform |
| `sim.parameters` | `BOOT_ROM_FILE` and `ROM_FILE` with the images of each program |
| `emulator.sources` | `spike_exit.S` |

The `sim.vhdl_sources` list is not edited by hand. It comes from the component of the top in the `provides` of the platform `paths.yaml`, which declares the components the top requires, and `make generate-sources` writes it in analysis order. If the top gains a peripheral, its component enters the `requires` of the top and the list is regenerated.

### 8.2. The testbench

`testbench/test_c_program.py` of `internal-mem` runs the clock, releases the reset, watches the writes on the RAM bus (`ram_addr`, `ram_wren`, `ram_en`, `ram_wdata`, `ram_byteena`) and stops at `tohost`. Any top that exposes these signals with these names reuses it, and the example's top does.

### 8.3. The first program

The programs live in the `Tests` repository (`asm/` and `c/`). It extends each platform's `config.yaml` through a generated file.

```bash
cd Tests
riscv-tools platform sync --prefix Insper-RISC-V \
    --source Insper-RISC-V/src/simulation/example/config.yaml \
    --output tools/riscv_build/config.platform-example.yaml
```

Create `tools/riscv_build/config.example.yaml` with the content below and run a program from `Tests/asm/`.

```yaml
extends: config.platform-example.yaml
paths:
  include_dir: tools/riscv_build/include
  build_dir: build-example
  c_dir: c
  asm_dir: asm
```

```bash
riscv-tools --config tools/riscv_build/config.example.yaml compile --emit hex --only arithmetic-add
riscv-tools --config tools/riscv_build/config.example.yaml sim --only arithmetic-add
```

| Expected output | Common error and cause |
| :--- | :--- |
| `PASS` of the program, with `tohost` read from the bus | `timeout` without `tohost`, when the BOOT_ROM does not jump to the ROM (`boot.entry` different from the ROM start) or the program was linked for another map |
| `compile` produces `manifest.json` with the program | Link error with `region ... overflowed`, when the program does not fit in the 28 KiB ROM |

## 9. Certification

### 9.1. What is generated

ACT4 needs one target per profile: the UDB YAML, the Sail configuration, the `test_config.yaml`, the model macros and the link script. The `Certification` repository generates them with `tools/riscv_build/gen_profiles.py` for each profile of `Core/profiles/matrix.yaml`, from the platform map. `riscv-tools profiles` lists the profiles that hold for the platform.

### 9.2. Run the chosen profile

```bash
cd Certification
riscv-tools --config tools/riscv_build/config.profile-rv32im.yaml certify
```

To restrict to the profile extensions, add `--extensions I,M`. The command builds the suite for the target, compiles the tests with GCC, simulates in GHDL and compares the result with Sail.

| Expected output | Common error and cause |
| :--- | :--- |
| All tests of the profile pass | Failure in a test that writes code into the ROM (`Zifencei-fence.i`), because the ROM ignores stores. The target uses the variant with the test body in the RAM |
| Target and profile configuration exist after `gen_profiles.py` | `profile ... not found`, because the platform profile is not in `matrix.yaml` |

## 10. Board

This chapter applies only if the platform has an FPGA. The `de0-cv` is the reference.

### 10.1. Quartus project files

| File | Content |
| :--- | :--- |
| `<platform>.qpf` | The project, with the revision |
| `<platform>.qsf` | Device, pins and the list of VHDL and IP sources, written by `make generate-sources` and checked against the disk by `check-paths` |
| `<platform>.sdc` | The clocks and the input and output constraints, written from the platform clocks |
| `pll/` | The PLL IP that generates the core clocks |
| `<platform>_synth.tcl` | Compiles with the chosen seed; with the `map` argument it only synthesizes |
| `<platform>_program.sh` | Programs the `.sof` through the first cable of `jtagconfig` |
| `<platform>_top.vhd` | The board top, which connects the PLL, the core, the board memories and the peripherals |

### 10.2. Timing constraints

The `.sdc` declares the input clock (`create_clock`), the PLL clocks (`derive_pll_clocks`) and the uncertainty (`derive_clock_uncertainty`). Each generated external clock (for example the SDRAM one) gets its `create_generated_clock` and the input and output delays from the chip datasheet.

### 10.3. Compile and program

```bash
quartus_sh -t src/<family>/<platform>/<platform>_synth.tcl && src/<family>/<platform>/<platform>_program.sh
```

Both commands must run in the same shell (`&&`). The [placa.md](placa.md) guide explains the rule and what to do when the board does not respond.

### 10.4. Programs and certification on the board

```bash
riscv-tools --config tools/riscv_build/config.<platform>.yaml run --skip-reconfigure --skip-recompile --only arithmetic-add
```

`certify-board` runs the ACT4 of the chosen profile on the board, with the `config.flash-board-<profile>.yaml` configuration of the `Certification` repository.

### 10.5. Timing report

After compilation, the Timing Analyzer report is at `output_files/<platform>.sta.rpt`. The numbers of interest are the Fmax of each clock and the worst setup and hold slack. A negative setup slack indicates a path longer than the clock period. To list the critical paths, use `riscv-tools timing-paths`.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
