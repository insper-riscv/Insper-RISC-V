# Compile and program a board

## 1. The rule: compile and program in the same shell

`quartus_sh --flow compile` and `quartus_pgm` run chained in the same shell (`cmd1 && cmd2`). Launching them as two Python `subprocess.run()` calls in sequence makes `quartus_pgm` fail with `Can't scan JTAG chain. Error code 87`, and after that `jtagconfig` stops seeing the board until it is power-cycled.

| How compile and program were launched | Result |
| :--- | :--- |
| Two Python `subprocess.run()` calls in sequence | 4 failures out of 4 |
| Two separate shell commands, one per tool | 2 successes out of 2 |
| A single `bash -c "cmd1 && cmd2"` | 2 successes out of 2, even with 1 s between them |

The wait between the two is not the variable. The mechanical cause was not confirmed, and the Intel community research points out that the Quartus command-line tools sometimes do not initialize the JTAG environment the way the graphical interface does. `riscv-tools` (`quartus_program/core.py` in [Tools](https://github.com/insper-riscv/Tools/blob/main/src/riscv_tools/quartus_program/core.py)) already builds the chain as a single shell string.

## 2. Compile and program a board

The Quartus project is not a versioned file: `program` writes it from the `platform.yaml` and the board package (`boards/<board>`) and compiles it in a build folder. A single command writes, compiles and programs.

```bash
uv run riscv-tools --config src/<family>/<platform>/config.yaml --board <board> program <image.mif>
```

| Board | Platform | `--config` |
| :--- | :--- | :--- |
| `de0-cv` | `de0-cv` | `src/cyclone-v/de0-cv/config.yaml` |
| `de2-115` | `de2-115` (N4), `de2-115-n2` (N2) | `src/cyclone-iv-e/de2-115/config.yaml`, `src/cyclone-iv-e/de2-115-n2/config.yaml` |
| `de0-nano` | `de0-nano` | `src/cyclone-iv-e/de0-nano/config.yaml` |
| `de10-lite` | `de10-lite` | `src/max-10/de10-lite/config.yaml` |

| Option | What it does |
| :--- | :--- |
| `--board NAME` | Picks the board by identification, in place of the `board` field of the platform |
| `--board-id ID`, `--cable NAME` | Pick an inventory entry or force the cable ([../boards/identificacao-jtag.md](../boards/identificacao-jtag.md)) |
| `--seed N` | Placement seed (default 5), with the `HIGH PERFORMANCE EFFORT` mode fixed |
| `--stop-after map\|fit\|sta` | Stops after the stage and does not program; `map` is enough to check paths and entities |
| `--compile-only` | Compiles without programming the board and without needing the image |
| `--generic NAME=VALUE` | Changes a top generic for this compile only (`HPM_COUNTERS=4 HPM_WIDTH=40` compiles the reduced Zihpm) |

The command `riscv-tools --board <board> board generate --platform <platform>.yaml --out build` writes only the project (`build/<platform>-<board>/`) and the memory map files, and with `--check` it compares them without writing. The core frequency changes in `clocks.core.mhz` of the `platform.yaml`, and the PLL, the `.sdc` and the map package follow from it.

With more than one board connected, take the board lock before programming.

```bash
riscv-tools board lock --board <board> --wait -- \
  riscv-tools --config src/<family>/<platform>/config.yaml --board <board> program <image.mif>
```

The bench cable of the DE0-CV shows up as `USB-Blaster [3-6]`, with the device `5CE(BA4|FA4)`. A new board follows [adicionar-placa.md](adicionar-placa.md).

## 3. Run programs on the board

With the bitstream already programmed, the `riscv-tools` of the test project ([Tests](https://github.com/insper-riscv/Tests)) writes each program into the BOOT_MEMORY, the FLASH and the RAM over JTAG and checks the result, without recompiling the FPGA. The DE0-CV uses the `sdram-flash` configurations; the other boards use the `<board>-*` stages of `tools/board/board_run.py`.

```bash
cd Tests
riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit mif --only conformance-fencei
riscv-tools --config tools/riscv_build/config.sdram-flash.yaml run --skip-reconfigure --skip-recompile --only conformance-fencei
```

Without `--skip-reconfigure`, `run` compiles and programs first, through the chain of section 1. Replacing one program with another is described in [atualizacao-de-programa.md](../platform/atualizacao-de-programa.md).

## 4. If the board does not respond

| Symptom | What to check |
| :--- | :--- |
| `jtagconfig` does not list the cable | USB cable, board power and, if the chain shows as broken, a power cycle |
| `jtagconfig` lists the board, but reads and writes through the JTAG hang | The PLL lost lock and the core stayed in reset. Only a power cycle recovers it |
| `quartus_pgm` fails right after a compile | The rule of section 1 was broken |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
