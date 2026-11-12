# How to add a new board

This guide takes a Quartus board the repository does not know to the point of running programs on it. Each step cites the boards already done as examples: `de0-cv`, `de2-115`, `de0-nano`, `de10-lite`, `de10-nano`, `de0-nano-soc` and `mkr-vidor-4000`. What each board offered and the level it reached are in [../boards/placas.md](../boards/placas.md). The commands run at the root of `Insper-RISC-V`, in the `dev_tools` image or on a machine with `riscv-tools` installed; steps 8 to 10 need Quartus.

## 1. Support levels

The levels are cumulative, and each board declares in `target_level` what it aims to reach.

| Level | Meaning | Proof |
| :--- | :--- | :--- |
| N0 | Project generated and synthesized | `quartus_map` without error |
| N1 | Fit and timing | `quartus_fit` and `quartus_sta` without error, with the numbers recorded on the board page |
| N2 | Live board | Bitstream programmed, the BOOT_MEMORY runs and a minimal program answers on the console |
| N3 | Hardware suite | The programs of the Tests repository pass on the board |
| N4 | Conformance | The ACT4 of the profile that fits passes on the board |

A board without a cable at hand stays at N0 or N1; the package enters with the note that it was not validated on hardware, like `de10-nano` and `mkr-vidor-4000`.

## 2. Research sheet

The sheet is the research section of the page of the board, `docs/en/boards/<board>.md` with its mirror in `docs/pt-br/boards/<board>.md`, which gathers the facts before any data file. Each fact carries its source and a certainty seal.

| Seal | Meaning |
| :--- | :--- |
| `manual` | Read in the board manual or schematic |
| `repo` | Read in a project file of the repository (for example a `.qsf`) |
| `inferido` | Deduced from third-party sources, such as a VHDL port or a forum |
| `measured` | Read from a real cable (`jtagconfig`, `lsusb`) |

The sections of the sheet, in this order, are the same as in the boards already done.

| Section | Content | Example |
| :--- | :--- | :--- |
| Identification | Board, full device, grade, measured IDCODE | `de0-nano`: IDCODE `020F30DD` belongs to three devices, and the identification closes by the board name and the cable |
| FPGA resources | Logic, RAM blocks, multipliers, PLLs, user pins | `de10-lite`: 49,760 LEs and 182 M9K blocks |
| Clocks and reset | Oscillators, reset pin and polarity | `de0-nano`: no reset button, the reset is `KEY[0]` |
| Input and output | LEDs, switches, keys, displays, UART and their polarities | `de2-115`: 18 red LEDs plus 9 green |
| Memories | Chip, organization and timing of each external memory | `mkr-vidor-4000`: AS4C4M16SA SDRAM with 12 row bits |
| Configuration and JTAG | Cable, USB IDs, chain | `de10-nano`: chain with the HPS and the FPGA |
| Pitfalls | Jumpers, voltage banks, input-only pins | `de2-115`: KEY, SW and part of the HEX follow jumper JP7 |
| Map for the project | What the `board.yaml` and the platform will declare | |

A fact without a source does not enter the `board.yaml`. A value the manual lacks (such as the SDRAM chip name of the `de0-nano`) enters with the `inferido` seal, and the sheet says how to confirm it.

## 3. The `pins.yaml`

The `pins.yaml` lists each signal of the board with pin, I/O standard, direction, source and seal, in the format of [../boards/formato.md](../boards/formato.md). The pin tables of the manual are the source; the schematic settles doubts.

1. Create `boards/<board>/pins.yaml` with `board` and `device`.
2. One entry per signal, with indexed buses (`LEDR[3]`, `DRAM_ADDR[12]`). The name is the manual's, because the `board.yaml` cites signals by name only.
3. Write in `conflicts` each pin assigned to more than one signal. The `mkr-vidor-4000` had seven duplicated pins in the official `.qsf`, settled by the schematic; the `de2-115` keeps the reserved-pin aliases.
4. Mark `inferred` what came from third parties. The Tools refuses to build with such a pin without `--accept-inferred-pins`, and the refusal protects the hardware from a wrong pin.

## 4. The `board.yaml`

Create `boards/<board>/board.yaml` with the fields of [../boards/formato.md](../boards/formato.md). The file cites the family, the chips and the signals by name, and never repeats a pin number, a chip timing or a family parameter.

| Field | How to fill | Example |
| :--- | :--- | :--- |
| `family`, `device`, `speed_grade` | Family from the catalog (step 5), full device and grade | `cyclone-iv-e`, `EP4CE22F17C6`, `C6` |
| `target_level` | The level of step 1 the board aims at | `N3` on the `de0-nano` |
| `jtag` | Cable, chain with the IDCODE of each device, USB IDs (step 9) | `usb-blaster-ii` on the `de10-nano` |
| `resources` | Device totals in the unit of the family (`alm` or `le`); `null` where the capacity is unknown | `logic: {unit: le, total: 22320}` |
| `clocks` | Inputs, the PLL reference and the reset with polarity | `reset: {signal: "KEY[0]", active: low}` |
| `io` | One role (`leds`, `switches`, `keys`, `display`) per signal group, with the polarity | `leds: {signals: "LED[7:0]", active: high}` |
| `memories` | One block per external memory, with the catalog chip and the signal prefix | `sdram: {chip: IS42S16160B-7, chips: 1, signals: DRAM, clk_phase_ps: 7000}` |
| `console` | `default: jtag`; `uart` only when the board has a UART on pins | `de2-115` |
| `notes` | The pitfalls of the sheet | |

Roles the board lacks stay out (the `de0-nano` has no `display`), and the validator treats the absence by rules V5 and V6 of step 7. The command `riscv-tools --root . check-boards` reads the package and points out unknown fields, signals missing from the `pins.yaml` and repeated pins outside `conflicts`.

## 5. Family and chips

### 5.1. Family

If the family of the device is already in `boards/families/`, the board only cites it: `cyclone-v`, `cyclone-v-soc`, `cyclone-iv-e`, `max-10` and `cyclone-10-lp` cover the seven boards. A new family gets `boards/families/<family>.yaml` with the fields of [../boards/familias.md](../boards/familias.md). Three fields need care.

| Field | Care |
| :--- | :--- |
| `pll.ip` | The Tools writes `altera_pll` and `altpll`. Measure which one Quartus accepts in the family: `altera_pll` only synthesizes on Cyclone V. Another primitive needs a new writer in the PLL generator |
| `pll.vco_mhz` and `clock_node_pattern` | The oscillator range comes from the family manual; the node name pattern comes from the report of a generated project and feeds the `.sdc` |
| `slew_rate` and `qsf` | What the Quartus fitter refuses or requires in the family: `max-10` refuses `SLEW_RATE` and asks for the single-image mode in the configuration |

### 5.2. Chips

Each external memory cites a chip of `Memory/chips/<chip>.yaml`, in the format of [../boards/plataforma-e-placa.md](../boards/plataforma-e-placa.md). The file carries organization, datasheet timing and `max_mhz`, with `source: datasheet` or `source: inferido`. A chip of the same series inherits from another with `extends` and writes only what changes: the `IS42S16320B-7` of the `de2-115` inherits everything from the `IS42S16320D-7` of the `de0-cv`.

The SDRAM controller reads width and row, column and bank bits from the chip, and two chips side by side form the 32-bit bus of the `de2-115`. The 8-bit NOR FLASH has its own controller. A memory without a controller (the SRAM) generates no instance in the top, and the region stays idle.

## 6. The platform

The platform says what the SoC asks for, and the board what exists. Copy the closest platform and edit its `platform.yaml`: `de0-nano` for a small board, `de0-cv` for one that holds the full profile.

1. Create `src/<family>/<board>/` by copying the folder of the starting platform, and rename the memory-map package.
2. In `platform.yaml`, adjust the field `platform`, `board: auto`, `boards: [<board>]`, `profile` and `regions`. The new fields, with their rules, are in [../boards/plataforma-e-placa.md](../boards/plataforma-e-placa.md).
3. Choose the backend of each external region. An `emulado` region consumes RAM blocks of the board, and a `dispositivo` one consumes the chip. On the `de0-nano` the FLASH has 28 KiB, because the next power of two would pass 85 % of the blocks.
4. Choose the core clock and the controller clock in `clocks`, and the I/O roles in `io` with `need: required` or `optional`.
5. In `paths.yaml`, declare the map package (`<board>_map`) and the component `<board>_board`, whose closure of `requires` is the source list of the project; the `top` field of the platform points to it. A board with 16-bit SDRAM uses `requires: [sdram_board, <board>_map]`.
6. Adapt the `config.yaml` of the platform (`extends` the starting platform, `memory_map: platform.yaml`, the `quartus` block with `generate`, `project_dir`, `project_name` and `sof_file`) and the `runtime/` folder.
7. Generate the map files and check them.

```bash
riscv-tools --root . generate-memory-map --platform src/<family>/<board>/platform.yaml
riscv-tools --root . generate-memory-map --platform src/<family>/<board>/platform.yaml --check
make sources-check
```

The platform also enters the `Makefile` lists that run `generate` and `generate-check`.

## 7. The validator

The validator compares what the platform requires with what the board offers and runs in `check-memory-map`, in `board generate` and before compiling.

```bash
riscv-tools --root . check-memory-map --platform src/<family>/<board>/platform.yaml
```

Each difference is an error (`E`) or a warning (`W`) with a code from V1 to V19, listed in [../boards/plataforma-e-placa.md](../boards/plataforma-e-placa.md). The most common errors on a new board are the following.

| Rule | Typical cause | Fix |
| :--- | :--- | :--- |
| V2, V3 | The platform asks for a device the board lacks | Switch the backend to `emulado`, as the `de0-nano` does with the FLASH |
| V5 | `required` role missing | Mark it `optional` or drop the role from the platform |
| V9 | FLASH bank not a multiple of the sector | Move the bank; on the `de2-115` bank B sits at `0x81000` because of the 64 KiB sector |
| V11, V12 | The profile does not fit the blocks or the logic | Reduce the profile, the caches or the emulated memory; the `de0-nano` uses RV32I with Zicsr |
| V16 | `inferred` pin in use | Confirm the pin at the source, or pass `--accept-inferred-pins` aware of the risk |

## 8. Estimator and calibration

The estimator tells whether the profile fits without running Quartus, using the calibration table of the family ([../boards/cabimento.md](../boards/cabimento.md)). A board of an already calibrated family needs nothing in this step: `check-memory-map` and `board generate` already estimate and write `capacity.json` in the project.

A new family needs its own table, measured on its reference board.

1. Create `src/calibration/<board>/platform.yaml`, the measurement platform, and the component `cal_<board>_board` in `paths.yaml`.
2. Create `boards/calibration/profiles/<family>.yaml`, the list of profiles to measure, and point `calibration` of the family to `calibration/<family>.yaml`.
3. Measure, fit and, when there is a second device of the family, verify.

```bash
riscv-tools --root . calibrate run --profiles boards/calibration/profiles/<family>.yaml --raw boards/calibration/raw/<family>
riscv-tools --root . calibrate fit --profiles boards/calibration/profiles/<family>.yaml --raw boards/calibration/raw/<family> --table boards/calibration/<family>.yaml
riscv-tools --root . calibrate verify --profiles boards/calibration/profiles/verify-<board>.yaml --raw boards/calibration/raw/verify-<board> --table boards/calibration/<family>.yaml --output boards/calibration/verification/<board>.yaml
```

`calibrate run` runs `quartus_map` profile by profile, under the machine lock. Without the table the validator emits V18 and only the Quartus fit decides the fit.

## 9. JTAG identification

`riscv-tools` finds the board by the IDCODE of the chain and the USB port of the cable ([../boards/identificacao-jtag.md](../boards/identificacao-jtag.md)). What the package must declare:

1. `jtag.chain` with the `name` that `jtagconfig` prints and the 8-hexadecimal-digit `idcode`, the FPGA's with `fpga: true`. Read both with the board powered.
2. `jtag.cable` with the cable type. Boards with an on-board USB-Blaster use `usb-blaster`; `de10-nano` and `de0-nano-soc` use `usb-blaster-ii` and declare the HPS as the first item of the chain (`hps: true`); `mkr-vidor-4000` uses `samd21-usbblaster`.
3. `jtag.usb` with the USB IDs when the cable only shows up before there is a chain. `board scan` recognizes the board by them, with no new code.

With the board connected, register the cable in the host inventory.

```bash
riscv-tools board scan
riscv-tools board scan --save
riscv-tools board doctor
```

An IDCODE shared among devices (the `020F70DD` of the `de2-115` serves the 10CL120 and the EP3C120) leaves more than one candidate board. Two equal boards on the same host are only told apart by the inventory, and `--board`, `--board-id` and `--cable` break the tie per run.

## 10. Levels in practice

### 10.1. N0 and N1

```bash
riscv-tools --root . --board <board> board generate --platform src/<family>/<board>/platform.yaml --out build
riscv-tools --config src/<family>/<board>/config.yaml --board <board> program --stop-after map
riscv-tools --config src/<family>/<board>/config.yaml --board <board> program --stop-after sta
```

`board generate` writes the project in `build/<platform>-<board>/`, and `--stop-after` compiles up to `map` (N0) or `sta` (N1) without programming. `--accept-inferred-pins` goes on the first line while any pin is inferred. Record on the board page (`docs/en/boards/<board>.md`) the logic and memory use, the PLLs, the pins and the smallest setup and hold slack of each clock, as `de0-nano.md` and `de10-lite.md` do. If the fitter refuses something of the family, the fix goes into the family (`slew_rate`, `qsf`) and not into the board.

### 10.2. N2

With the board connected and free, take the lock and program.

```bash
riscv-tools board lock --board <board> --wait -- \
  riscv-tools --config src/<family>/<board>/config.yaml --board <board> program <image.mif>
```

`program` compiles and programs in the same shell, which avoids the chain failure described in [placa.md](placa.md). The criterion is a minimal program that writes to the JTAG console and ends. A board whose cable does not enumerate stays at N1.

### 10.3. N3 and N4

N3 runs the programs of the Tests repository through the `<board>-*` stages of `tools/board/board_run.py` ([Tests](https://github.com/insper-riscv/Tests)), which compile only the programs whose extensions the profile of the platform turns on. N4 runs the ACT4 of the profile that fits through the Certification repository. Each new stage enters the runner with the board, the configuration and the justified exclusions (for example, UART-on-pins programs on a board without a UART).

## 11. Tests and checks

| Where | Command | What it proves |
| :--- | :--- | :--- |
| Insper-RISC-V | `make paths` | Paths of `paths.yaml`, tree shape and the board catalog (`check-boards`) |
| Insper-RISC-V | `make generate-check` and `make sources-check` | The generated files and the source lists are up to date |
| Insper-RISC-V | `riscv-tools --root . board generate --platform ... --check` | The project on disk is what the generator would write |
| Tools | `uv run pytest tests/test_board_scan_select.py tests/test_board_special.py` | Board selection with `jtagconfig` and `lsusb` fixtures of the new board, without hardware |

For the selection, copy a `jtagconfig` fixture of the powered board to `tests/fixtures/jtagconfig` of the Tools and the board package to `tests/fixtures/boards`, and add the case to the selection tests.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
