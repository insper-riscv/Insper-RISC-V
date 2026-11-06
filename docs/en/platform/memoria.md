# Memory architecture: BOOT_MEMORY + FLASH + RAM (modified Harvard)

This document describes the memory of the `internal-mem` platform. The one of `de0-cv`, with the FLASH and the SDRAM behind the caches, is in [de0-cv.md](de0-cv.md).

## Summary

The core (`rv32im_pipeline_core`) models the memory hierarchy of a real SoC with **3 logical roles**, implemented in **3 physical memory instances**:

| Role | Physical instance | Rewritten over JTAG? | Who accesses it |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `BOOT_MEMORY` | No, only at the initial compile | Instruction fetch only (IF) |
| FLASH | `FLASH` | Yes, at each test change, by the JTAG loader | Port A: IF. Port B: MEM and the loader |
| RAM | `RAM` | No (JTAG only reads and writes data) | IF never. MEM always |

This is called **modified Harvard**. A "true" Harvard would have fully independent instruction and data buses, with no overlap. Here, IF fetches instructions from the BOOT_MEMORY and the FLASH (never from the RAM), and the MEM stage (load and store) only touches the RAM, **except** for one deliberate opening. The MEM stage can also read the FLASH through its port B, only so the bootloader copies `.data` from the FLASH to the RAM at boot. This is the only exception to the instruction and data separation, see [FLASH: the firmware of each test](#12-flash-the-firmware-of-each-test) below.

## 1. The three roles in detail

### 1.1. BOOT_MEMORY: the fixed bootloader

Programmed **once**, as part of the initial full Quartus compile (`quartus_sh --flow compile` and `quartus_pgm`), and never rewritten over JTAG afterwards, unlike the FLASH. It holds `boot_memory.S` (`src/simulation/internal-mem/runtime/boot_memory.S`). That is the reset vector, which clears tohost, fromhost and the `stdout` header and jumps to the FLASH, and the wait and restart loop (`rv32_wait_restart`) that lets `riscv-tools run` change tests without reprogramming the whole FPGA. See [atualizacao-de-programa.md](atualizacao-de-programa.md) for the full flow of that change.

It is generic on purpose and knows nothing about a test. The picolibc `crt0`, inside the image of each test (starting at `0x1000`), copies `.data`, zeroes `.bss` and calls `main`. What the BOOT_MEMORY and the program agree on is only the entry point, the address of `rv32_wait_restart` and the words at the top of the RAM. See [runtime.md](runtime.md) and [atualizacao-de-programa.md](atualizacao-de-programa.md).

### 1.2. FLASH: the "firmware" of each test

The real program of each test (`.init`, `.text` and `.rodata`, plus the initial image of `.data`), rewritten by the JTAG loader (`flash_loader`, from Memory) every time a test changes. Physically it is a true dual-port `altsyncram` (not a real flash), **a single copy**, but architecturally it represents the non-volatile storage. It is only rewritten explicitly between runs, never by the CPU at run time.

Port A is the instruction fetch (IF) and port B is the data read of the MEM stage, which the `.data` copy loop of `boot_memory.S` uses (`lw a0, 0(t1)`, where `t1` points into the FLASH, the LMA of `.data`). The loader halts the core (its halt output feeds `core_reset`), writes the image through port B and releases the core, which restarts from the BOOT_MEMORY. With the core running the write enable is forced to `'0'` in hardware, and the core only reads. The protocol is in the Memory documentation (`flash_loader`), and the host picks this path with `quartus.rom_write_method: jtag_loader`.

### 1.3. RAM: the real data

`.data`, `.sdata`, `.sbss`, `.bss`, stack and heap. It is the only memory the MEM stage (load and store) always reaches for writing. `.rodata` (large constants) stays resident in the FLASH and is never copied here. The last 1056 bytes of the physical space of the IP are reserved (outside the `__ram_size` that `rv32im-fpga.specs` gives the test) for tohost and fromhost (4 words, HTIF convention, with 2 free words) and the `stdout` buffer (1032 bytes, see [runtime.md](runtime.md)).

## 2. Memory map

| Region | Base | Size | Words | widthad |
| :--- | :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4K | 1024 | 10 |
| FLASH | `0x00001000` | 28K | 7168 | 13 |
| RAM (physical space) | `0x00008000` | 160K | 40960 | 16 |
| RAM (usable, `rv32im-fpga.specs`) | `0x00008000` | 160K minus 24 minus 1032 bytes | N/A | N/A |
| `stdout` (header and data) | `0x0002FBE0` | 1032 bytes | N/A | N/A |
| fromhost | `0x0002FFF0` | 2 words | N/A | N/A |
| tohost | `0x0002FFE8` | 2 words | N/A | N/A |
| `__stack` (initial sp) | `0x0002FBE0` | N/A | N/A | N/A |

The FLASH takes `0x00001000` to `0x00008000` (**28K**), where the RAM starts. The top of the RAM (`ram_base + ram_words*4 = 0x30000`) and its base must fall on multiples of 4096 bytes, because the boot memory builds the end of the RAM with `lui t0, 0x30` (with no `addi` after), and `lui` only zeroes the low 12 bits. Since the FLASH starts at `0x1000`, its end must also be a multiple of 4096:

$$0x1000 + \text{FLASH\_SIZE} \equiv 0 \pmod{4096}$$

This requires `FLASH_SIZE` to be a multiple of 4096, and 28K ($7 \times 4096 = 28672$) works and ends exactly at the base of the RAM.

### 2.1. The RAM block limit

The Cyclone V 5CEBA4F23 has 308 M10K blocks of 10 Kbit, a limit on the number of blocks as well as on total bits. The Fitter report of the current map records the usage below, 288 blocks (94 % of the ceiling).

| Memory | M10K blocks |
| :--- | ---: |
| `BOOT_MEMORY` | 4 |
| `FLASH` | 28 |
| `RAM` | 256 |
| **Total** | **288 of 308** |

## 3. JTAG indexes (`config.yaml: quartus:`)

Only the `RAM` declares `ENABLE_RUNTIME_MOD`, so it is the only In-System Memory Content Editor instance and has index 0 (`quartus.ram_mem_instance`; `tohost` and `fromhost` live inside the RAM, so they share its index). The `BOOT_MEMORY` is written only at the initial compile, and the `FLASH`, rewritten by the loader, has no index (`quartus.rom_mem_instances: []`).

## 4. LEDs (`core_fpga_test.vhd`)

| LED | Signal | Meaning |
| :--- | :--- | :--- |
| o_ledr(0) | `Blinky` | Blinks straight from `i_clock_50`, unrelated to the core, "board alive" |
| o_ledr(1) | `pll_locked` | Should stay **always on** after the FPGA is configured. Off means the PLL never locked |
| o_ledr(2) | `i_fpga_reset_n` | On means the physical reset button is **released**. Off means it is pressed |
| o_ledr(3) | `not core_reset` | On means the core is out of reset and running. Off means the core is in reset (PLL without lock, or button pressed) |
| o_ledr(4) | `flash_halt` | Lit = core halted by the FLASH loader (reset held while the image is written) |
| o_ledr(5-9) | (unused) | Free |

As a quick diagnostic without opening a JTAG session, if o_ledr(1) or o_ledr(3) is off, the problem is **before** the core (PLL or reset) and no test will run. If both are on and a test still does not pass, the problem is in the software or the core logic, not in the board configuration.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
