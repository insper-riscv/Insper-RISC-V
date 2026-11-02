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
| BOOT_ROM | `0x00000000` | 2 KB | Fetch and read, direct, uncached |
| FLASH | `0x20000000` | 1 MB window | Fetch and read through the caches, read-only |
| SDRAM | `0x40000000` | 64 MB | Fetch, read and write through the caches |
| Peripherals | `0x80000000` | 256 MB windows | Read and write, uncached |

The top 4 KB of the SDRAM hold the words the host writes behind the caches (`tohost`, `fromhost` and the `stdout` buffer). The data cache ignores them, so a load goes to memory as a word, without bringing a line, and a store is only forwarded.

## 3. Behavior

1. **Fetch.** The PC feeds only the instruction cache and the BOOT_ROM. The cache tag carries address bit 29, which separates the FLASH lines from the SDRAM ones.
2. **Data.** Loads and stores to the FLASH and the SDRAM go through the data cache, with 16-byte lines and 4 KB direct mapping. A store to the FLASH never changes the cache and the router completes it with no effect, like a write-protected chip.
3. **FLASH.** The chip serves line or word requests with two latency parameters, edges up to the first word and edges between the following words. Outside the chip window a read returns zero.
4. **Restart.** The boot ROM executes `fence.i` before jumping to the FLASH. The instruction invalidates the instruction cache and the data cache, so the new program the host wrote does not find lines of the previous one.
5. **Host.** The host writes the FLASH image through the Quartus in-system memory (instance 1) and the data through the SDRAM debug port, with the core parked in the boot ROM restart loop. It restarts the core by writing a non-zero value to `fromhost`.

## 4. Sizes and latencies

| Item | Simulation | Board |
| :--- | :--- | :--- |
| FLASH chip window | 1 MB (`window_bits` equal to 20) | 256 KB (`window_bits` equal to 18) |
| FLASH storage | 256 KB array | 132 KB in RAM blocks, rewritable over JTAG |
| Chip latency | 24 edges to the first word and 4 between the following ones (default) | The same |

The board storage has 132 KB because the largest ACT4 test (`I-jal-00`) takes 131,872 bytes. The simulation array has 256 KB because a 1 MB array does not run in GHDL.

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

The map checker (`check-memory-map`) checks the platform `platform.yaml` against `config.yaml`, the link flags, the boot ROM, the runtime, the core constants and the program header.

## 6. ACT4

The ACT4 ELFs have code and constants in the FLASH and data, stack and the HTIF words in the SDRAM. The `Zifencei-fence.i-00` test rewrites its own code, and the FLASH ignores stores, so it uses a variant of the target where the test body sits in the SDRAM and only the entry, the model macros and the constants stay in the FLASH.
