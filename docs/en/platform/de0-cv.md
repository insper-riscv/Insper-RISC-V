# The `de0-cv` platform: the SDRAM split into FLASH and RAM

## 1. What it is

The core holds only the BOOT_MEMORY. The SDRAM chip of the board (64 MB, one controller) is split into two windows, the FLASH (instructions and constants, read only for the core) and the RAM (data). The core reaches them through an instruction cache and a data cache. Each cache miss becomes a request for a line of four words, which a region router takes to the chip through the instruction port (FLASH) or the data port (RAM) of the controller.

```
   instruction cache            data cache (write-through)
            |                              |
       router I                        router D
        |       \                      /      |  \
        |        FLASH arbiter -------+       |   absorber of stores to the FLASH
        |              |                      |
   execution from RAM  |                      |
        |              |                      |
        +--- 2:1 arbiter ---> bridge I        +--> bridge A
                              |                     |
                              +----> arbiter (A, I, B) ----> controller ----> DRAM_* pins
JTAG (debug port, master B) -----------------------------^
```

## 2. Memory map

The sizes and the bases come from `platform.yaml`, and the default of the board splits the chip into two halves of 32 MiB. Any other division in which the FLASH and the RAM fit in the chip is valid: change `size` of the two regions.

| Region | Base | Size | Access |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Fetch and read, direct, uncached |
| FLASH | `0x00001000` | up to `0x02000000` (32 MiB minus 4 KiB) | Fetch and read through the caches, read only for the core |
| RAM | `0x40000000` | 32 MiB | Fetch, read and write through the caches |
| Peripherals | `0x80000000` | windows of 256 MB | Read and write, uncached |

In the chip, the FLASH occupies the start with the address of the SoC, without subtraction, and the RAM starts right after the end of the FLASH. With 32 MiB and 32 MiB, bit 25 of the byte address picks the half of the chip (0 in the FLASH, 1 in the RAM). The 4 KB at the top of the RAM hold the words the host writes behind the caches (`tohost`, `fromhost` and the `stdout` buffer). The data cache ignores them: a load goes to memory as a word, without bringing a line, and a store is only passed on.

Both regions use `on_bus: true`, that is, the CPU reaches them through the bus (external memory). Only the BOOT_MEMORY, onchip, is read directly from the CPU port.

## 3. Behavior

1. **Fetch.** The PC feeds only the instruction cache and the BOOT_MEMORY. The tag of the cache carries the region bit, which separates the FLASH lines from the RAM lines. Code that runs from the RAM uses the same instruction port of the chip, behind a second arbiter with the FLASH face.
2. **Data.** Loads and stores to the FLASH and the RAM go through the data cache, with 16-byte lines and direct mapping, of the size of `cache.size_bits` in `platform.yaml` (4 KiB). A store to the FLASH never changes the cache.
3. **FLASH protection.** The core only reads the FLASH, through three independent layers. With `AccessFaults`, a store to it is the exception of cause 7 (store access fault) with `mtval` equal to the address. Without `AccessFaults`, the router completes the store with no effect, like a write-protected chip. By construction, the instruction port of the chip never writes, and the data port only reaches the RAM.
4. **Read window.** The router serves the read of the FLASH up to its end (`FLASH_END` of the map package), and returns zero above it. The window comes from the map, not from a fixed value.
5. **Restart.** The boot memory runs `fence.i` before reading the FLASH. The instruction invalidates the instruction cache and the data cache, so the check of the banks and the new program the host wrote do not find lines of the previous one. The FLASH has two banks, and the boot memory jumps to the one with the highest version whose header and CRC-32 match ([entry contract](contrato-de-entrada.md), section 6.6); without a valid bank the core waits in the restart loop.
6. **Host.** Only the JTAG writes the FLASH: the host uses the debug port of the SDRAM (instance 3 of the Virtual JTAG), which is a master of the controller arbiter. The platform has no FLASH controller and no PLIC line 6.
7. **Trap.** The `LEDR1` of the top lights when the core pulses `o_trap_take` and stays lit until the next reset, including the one of the `KEY4` button (`FPGA_RESET_N`), which restarts only the core and not the SDRAM controller, so the content of the FLASH survives.

## 4. Sizes and latencies

| Item | Simulation | Board |
| :--- | :--- | :--- |
| SDRAM chip | 64 MiB model (13 row bits, 2 bank bits, 10 column bits) | IS42S16320D, 64 MB |
| FLASH and RAM | Two windows of the same model | Two windows of the same controller |
| Latency | That of the controller and of the chip model | That of the controller at 100 MHz |

The chip model is a sparse table, so the simulation image only needs the words the program uses. The RAM needs no image: the program copies what it needs from the FLASH.

## 5. How to run

| Goal | Command |
| :--- | :--- |
| Simulation top test | `make test TEST=De0CvSimTop` |
| Bank choice by the boot memory | `make test TEST=De0CvBootBanks` |
| Build the board | `riscv-tools --config src/cyclone-v/de0-cv/config.yaml program --compile-only --stop-after map` (synthesis only) |
| Program the board | `riscv-tools --config src/cyclone-v/de0-cv/config.yaml program <image.mif>` |

`platform.yaml` is the single source of the map. `riscv-tools generate-memory-map` (`make generate`) writes from it the package `de0_cv_map_pkg.vhd`, which the generated board top, the simulation top and the generated Quartus project use for the region limits and the page of the RAM the host shares with the program, besides the link flags, the linker script of the boot memory and `memory_map.h`. The `config.yaml` declares `memory_map: platform.yaml` and receives the bases, the words and `tohost` from the map. The verifier `check-memory-map` checks only what is left written by hand: the boot memory, the VHDL of the core and the header of the programs.

The peripherals occupy the upper 2 GiB of the address space (bit 31 set), one window per peripheral, with base and size given by the `peripherals` list of `platform.yaml` and decoded by the table of the map package: the JTAG UART (index 0, `0xC0000000`), the 7-segment display (index 1, `0xD0000000`), the CLINT (index 2, `0xE0000000`, 64 KiB window) and the external interrupt controller (index 3, `0xF0000000`). An access to an address with no window ends in an access fault. The MTIP, MSIP and MEIP lines reach the core (see the [interconnect](../interconnect/ext_interconnect.md)).

## 6. ACT4

The ACT4 ELFs have the code and constants in the FLASH and the data, the stack and the HTIF words in the RAM. The test `Zifencei-fence.i-00` rewrites its own code, and the FLASH ignores stores, so it uses a variant of the target in which the body of the test is in the RAM and only the entry, the macros of the model and the constants are in the FLASH.

## 7. Simulation top test

The catalog `tests/python/tests.json` has the entries `De0CvBootBanks` (the real boot memory choosing the bank, one simulation per case, see [atualizacao-de-programa.md](atualizacao-de-programa.md)) and `De0CvSimTop`, which runs the top `rv32im_sdram_flash_sim_test`. The chip image (`SDRAM_FILE`) has only the FLASH, from word 0. The BOOT_MEMORY stores a mark in the RAM and jumps to the FLASH. The FLASH stores another mark, writes to the display, installs an exception handler and tries to write to itself. The test checks the access fault of cause 7, `mtval` with the address and the word intact in the chip. Then the FLASH copies a piece of code to the RAM and jumps to it, and that code stores the third mark and writes `tohost`. The test reads the chip through the debug port of the model and checks the marks, `tohost` and the display value. The images come from `tests/python/gen_de0_cv_images.py`, built from `platform.yaml`.

The program simulation testbench (`testbench/test_c_program.py`) starts the UART console only at the first access of the core to the UART window (`UART_START_ON_ACCESS` and `UART_INDEX` in `config.yaml`, the latter equal to the index of the UART in the window table), because the boot memory checks the banks and the startup of the program takes much longer than the 64-byte receive queue holds what the host sends. `UART_SCANS_PER_BYTE` sets how many scans separate two bytes sent.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
