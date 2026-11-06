# The `external-data` platform: the two-port FLASH inside the FPGA and the SDRAM behind the data cache

## 1. What it is

The core holds the BOOT_MEMORY and the FLASH, and only the RAM sits outside it. The FLASH is a single copy of a true dual-port memory inside the FPGA, the same one as in [internal-mem](internal-mem.md), and the RAM is the board's SDRAM, reached through a write-through data cache. There is no instruction cache and no FLASH chip, because the instruction fetch reads the FLASH directly.

```
                     core
        fetch (IF)             MEM stage
            |                   |        |
         port A              port B     data cache
            |                   |        (write-through)
            |         FLASH loader           |
            |     (port B is free only       |
            |      while the core is stopped)|
            +--------- FLASH ---------+      |
                  (a single copy)        SDRAM (bridge, arbiter, controller)
```

## 2. Memory map

| Region | Base | Size | Access |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Fetch and read, direct |
| FLASH | `0x00001000` | 252 KiB window, up to `0x00040000` | Fetch through port A and data read through port B, read only for the core |
| SDRAM | `0x40000000` | 64 MB | Data read and write through the data cache; there is no instruction fetch |
| Peripherals | `0x80000000` | 256 MB windows | Read and write, uncached |

Because the instruction fetch does not reach the SDRAM, no code runs from it. The top 4 KB of the SDRAM hold the words that the host writes behind the cache (`tohost`, `fromhost` and the `stdout` buffer), and the data cache ignores them.

## 3. Behaviour

1. **FLASH.** Port A is read by the fetch stage and port B by the MEM stage, when a load falls in the FLASH region. Both reads hit the same block, with no second copy.
2. **Rewrite.** The host writes the FLASH through the loader of the Memory repository, which talks to the Virtual JTAG (instance 0). The loader stops the core, writes the image through port B, checks the count and the checksum, and releases the core, which restarts from the BOOT_MEMORY. While the core runs, port B belongs to the MEM stage and the write is refused in hardware.
3. **SDRAM.** The host reads and writes the SDRAM through the debug port, a second master of the controller (Virtual JTAG instance 3). The JTAG UART and the display use instances 1 and 2.
4. **Restart.** The BOOT_MEMORY executes `fence.i` before jumping to the FLASH, and the instruction flushes the data cache.
5. **Misaligned access.** A load that crosses two words of the FLASH (Zicclsm) does not complete on this platform; the same access in the SDRAM and an aligned word of the FLASH work.
6. **Trap and loader.** `LEDR1` lights when the core pulses `o_trap`, and `LEDR2` lights while the loader holds the core stopped.

## 4. Sizes

| Item | Value |
| :--- | :--- |
| FLASH storage | 256 KB, which the fetch decoder requires (it does not subtract the FLASH base) |
| Data cache | 4 KiB, 16-byte lines, direct mapped |
| Initial image | `init.mif` (FLASH) and `boot_memory_init.mif` (BOOT_MEMORY) |

## 5. How to run

| Goal | Command |
| :--- | :--- |
| Compile the board | `quartus_sh -t src/cyclone-v/external-data/external-data_synth.tcl` |
| Program the board | `src/cyclone-v/external-data/external-data_program.sh`, in the same shell as the compilation (`&&`) |
| Simulate the programs | `riscv-tools --config tools/riscv_build/config.sdram-external-data.yaml compile --emit hex`, then `sim` (in the Tests repository) |
| Programs on the board | `riscv-tools --config tools/riscv_build/config.sdram-external-data.yaml run --skip-reconfigure --skip-recompile` |
| Simulation top test | `make test TEST=ExternalDataSimTop` |

The `platform.yaml` is the single source of the map, and `make generate` writes from it the `external_data_map_pkg.vhd` package, the link flags, the BOOT_MEMORY linker script and `memory_map.h`. The `config.yaml` holds `quartus.sdram_debug_instance`, the Virtual JTAG index of the SDRAM debug port, which `riscv-tools` passes to the port script.

## 6. Simulation top test

The `ExternalDataSimTop` entry of `tests/python/tests.json` runs the `rv32im_external_data_sim_test` top with a minimal program. The BOOT_MEMORY stores a mark in the SDRAM and jumps to the FLASH. The FLASH stores another mark, reads as data a word that it holds itself, copies that word to the SDRAM, writes to the display, stores the third mark and writes `tohost`. The test reads the SDRAM through the chip's debug port and checks the marks, the word read from the FLASH, `tohost` and the display value. The images come from `tests/python/gen_external_data_images.py`.

## 7. Compilation measurements

Cyclone V 5CEBA4F23, Quartus Prime 25.1 Lite, `HIGH PERFORMANCE EFFORT` mode and seed 5.

| Resource | Use |
| :--- | :--- |
| ALMs | 8227 of 18480 (45 %) |
| Registers | 8480 |
| M10K RAM blocks | 234 of 308 (76 %) |
| Core domain Fmax (slow model at 85 °C) | 63.54 MHz |
| Core setup slack | -0.204 ns |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
