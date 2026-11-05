# The `de0-cv` platform: the FLASH as a chip behind the caches

## 1. What it is

The core keeps only the BOOT_ROM. The FLASH (program and constants) and the SDRAM (data) live outside it, as in a real SoC, and the core reaches them through an instruction cache and a data cache. Each cache miss becomes a four-word line request, which a region router takes to the FLASH chip model, through an arbiter, or to the SDRAM controller.

```
            core (BOOT_ROM only)
              |                |
        instruction          data cache
        cache                (write-through)
              |                |
        router I            router D
         |        \          /      |  \
         |         FLASH arbiter      |
         |              |             |
         |         FLASH chip         |
         |         (storage)          |
         +------------+---------------+
                      |
              SDRAM (bridge, arbiter, controller)
```

## 2. Memory map

| Region | Base | Size | Access |
| :--- | :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | 4 KiB | Fetch and read, direct, uncached |
| FLASH | `0x00001000` | 252 KiB window, up to `0x00040000` | Fetch and read through the caches, read-only |
| SDRAM | `0x40000000` | 64 MB | Fetch, read and write through the caches |
| Peripherals | `0x80000000` | 256 MB windows | Read and write, uncached |

The top 4 KB of the SDRAM hold the words the host writes behind the caches (`tohost`, `fromhost` and the `stdout` buffer). The data cache ignores them, so a load goes to memory as a word, without bringing a line, and a store is only forwarded.

## 3. Behavior

1. **Fetch.** The PC feeds only the instruction cache and the BOOT_ROM. The cache tag carries the region bit, which separates the FLASH lines from the SDRAM ones; the FLASH region is the range `[4 KiB, 256 KiB)` of the core address.
2. **Data.** Loads and stores to the FLASH and the SDRAM go through the data cache, with 16-byte lines and 4 KB direct mapping. A store to the FLASH never changes the cache and the router completes it with no effect, like a write-protected chip.
3. **FLASH.** The chip serves line or word requests with two latency parameters, edges up to the first word and edges between the following words. Outside the chip window a read returns zero.
4. **Restart.** The boot ROM executes `fence.i` before jumping to the FLASH. The instruction invalidates the instruction cache and the data cache, so the new program the host wrote does not find lines of the previous one.
5. **Host.** The host writes the FLASH image through the Quartus in-system memory (instance 0) and the data through the SDRAM debug port, with the core parked in the boot ROM restart loop. It restarts the core by writing a non-zero value to `fromhost`.

## 4. Sizes and latencies

| Item | Simulation | Board |
| :--- | :--- | :--- |
| FLASH chip window | 256 KB (`size_bytes` equal to 262144), of which the FLASH takes the 252 KiB after the BOOT_ROM | The same |
| FLASH storage | 256 KB array | 256 KB in RAM blocks, rewritable over JTAG |
| Chip latency | 24 edges to the first word and 4 between the following ones (default) | The same |

The storage has 256 KB because the largest ACT4 test (`I-jal-00`) takes 131,872 bytes and the first 4 KB of the array stand for the BOOT_ROM, which the FLASH program does not use. A 1 MB array does not run in GHDL.

## 5. How to run

| Goal | Command |
| :--- | :--- |
| Simulation of the existing programs | `riscv-tools --config tools/riscv_build/config.sdram-flash-regression.yaml compile --emit hex`, then `sim --exclude uart-echo,uart-tx,uart-errors` (in the Tests repository) |
| Simulation of the SDRAM and FLASH programs | `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit hex`, then `sim --exclude cpi-kernels,hex-id` |
| Chip latency | The `config.sdram-flash-lat2.yaml`, `-lat20.yaml` and `-lat60.yaml` configurations, and the `-regression-lat*` ones |
| Compile the board | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl` (synthesis only, with the `map` argument) |
| Program the board | `src/cyclone-v/de0-cv/de0-cv_program.sh`, in the same shell as the compile (`&&`) |
| Programs on the board | `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml run --skip-reconfigure --skip-recompile` |
| ACT4 on the board | `certify-board --skip-build` with the `config.flash-board-<profile>.yaml` configuration of the Certification repository |

The `platform.yaml` is the only source of the map. `riscv-tools generate-memory-map` (`make generate`) writes from it the `de0_cv_map_pkg.vhd` package, which the board top, the simulation top and the Quartus project (`de0-cv.qsf`) use for the limits of the regions, the size of the FLASH chip and the page of the SDRAM that the host shares with the program, plus the link flags, the linker script of the boot ROM and the `memory_map.h` with the addresses of `tohost`, `fromhost`, `stdout` and the UART for the runtime. The package also carries `NUM_REGS` and the `HAS_*` of the platform profile, `BOOT_ROM_BITS` (12) and `ROM_STORAGE_BYTES` (262144). `config.yaml` declares `memory_map: platform.yaml` and receives from the map the bases, the words, `tohost`, `fromhost` and the address width of the simulation memories. The `check-memory-map` checker covers only what is left written by hand: the boot ROM, the VHDL of the core and the header of the programs.

The peripherals take the upper 2 GiB of the address space (bit 31 set), with one 256 MiB window per peripheral chosen by bits 30:28: the JTAG UART at id 4 (`0xC0000000`) and the seven-segment display at id 5 (`0xD0000000`). The BOOT_ROM, the FLASH and the SDRAM sit in the lower 2 GiB.

## 6. ACT4

The ACT4 ELFs have code and constants in the FLASH and data, stack and the HTIF words in the SDRAM. The `Zifencei-fence.i-00` test rewrites its own code, and the FLASH ignores stores, so it uses a variant of the target where the test body sits in the SDRAM and only the entry, the model macros and the constants stay in the FLASH.

## 7. Simulation top test

The catalog `tests/python/tests.json` has the entry `De0CvSimTop`, which runs the top `rv32im_sdram_flash_sim_test` with a minimal program in each region. The BOOT_ROM stores a mark in the SDRAM and jumps to the FLASH, the FLASH stores another mark, writes to the display and jumps to the code the SDRAM has held since time zero (`SDRAM_FILE`), and that code stores the third mark and writes `tohost`. The test reads the SDRAM through the debug port of the chip and checks the three marks, `tohost` and the display value. The images come from `tests/python/gen_de0_cv_images.py`, built from `platform.yaml`.
