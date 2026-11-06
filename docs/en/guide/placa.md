# Compile and program the DE0-CV

## 1. The rule: compile and program in the same shell

`quartus_sh --flow compile` and `quartus_pgm` run chained in the same shell (`cmd1 && cmd2`). Launching them as two Python `subprocess.run()` calls in sequence makes `quartus_pgm` fail with `Can't scan JTAG chain. Error code 87`, and after that `jtagconfig` stops seeing the board until it is power-cycled.

| How compile and program were launched | Result |
| :--- | :--- |
| Two Python `subprocess.run()` calls in sequence | 4 failures out of 4 |
| Two separate shell commands, one per tool | 2 successes out of 2 |
| A single `bash -c "cmd1 && cmd2"` | 2 successes out of 2, even with 1 s between them |

The wait between the two is not the variable. The mechanical cause was not confirmed, and the Intel community research points out that the Quartus command-line tools sometimes do not initialize the JTAG environment the way the graphical interface does. `riscv-tools` (`quartus_program/core.py` in [Tools](https://github.com/insper-riscv/Tools/blob/main/src/riscv_tools/quartus_program/core.py)) already builds the chain as a single shell string.

## 2. Compile and program the de0-cv

From the platform scripts, in a single command.

```bash
quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl && src/cyclone-v/de0-cv/de0-cv_program.sh
```

| Script | What it does |
| :--- | :--- |
| `de0-cv_synth.tcl [seed] [map]` | Fixes the `HIGH PERFORMANCE EFFORT` mode and the seed (default 5) and compiles. With `map` only synthesis runs, which is enough to check paths and entities. It does not write the assignments to the `.qsf` |
| `de0-cv_program.sh [file.sof]` | Programs `output_files/de0-cv.sof` through the first cable `jtagconfig` lists. The `CABLE` variable picks another cable |

The bench cable shows up as `USB-Blaster [3-6]`, with the device `5CE(BA4|FA4)`.

## 3. Run programs on the board

With the bitstream already programmed, the `riscv-tools` of the test project ([Tests](https://github.com/insper-riscv/Tests)) writes each program into the BOOT_MEMORY, the FLASH and the SDRAM over JTAG and checks the result, without recompiling the FPGA.

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
| `jtagconfig` lists the board, but reads and writes through the In-System Memory Content Editor hang | The PLL lost lock and the core stayed in reset. Only a power cycle recovers it |
| `quartus_pgm` fails right after a compile | The rule of section 1 was broken |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
