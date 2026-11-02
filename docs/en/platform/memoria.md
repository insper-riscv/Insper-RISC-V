# Memory architecture: BOOT_ROM + FLASH + RAM (modified Harvard)

This document describes the memory of the `internal-mem` platform. The one of `de0-cv`, with the FLASH and the SDRAM behind the caches, is in [de0-cv.md](de0-cv.md).

## Summary

The core (`rv32im_pipeline_core`) models the memory hierarchy of a real SoC with **3 logical roles**, implemented in **4 physical memory instances**:

| Role | Physical instance(s) | Rewritten over JTAG? | Who accesses it |
| :--- | :--- | :--- | :--- |
| BOOT_ROM | `BOOT_ROM` | No, only at the initial compile | Instruction fetch only (IF) |
| FLASH | `FLASH` and `FLASH_MEM` | Yes, at each test change | `FLASH`: IF. `FLASH_MEM`: MEM |
| RAM | `RAM` | No (JTAG only reads and writes data) | IF never. MEM always |

This is called **modified Harvard**. A "true" Harvard would have fully independent instruction and data buses, with no overlap. Here, IF fetches instructions from the BOOT_ROM and the FLASH (never from the RAM), and the MEM stage (load and store) only touches the RAM, **except** for one deliberate opening. The MEM stage can also read `FLASH_MEM` (the second physical copy of the FLASH), only so the bootloader copies `.data` from the FLASH to the RAM at boot. This is the only exception to the instruction and data separation, see [the FLASH needs a second read port](#2-the-flash-needs-a-second-read-port-the-quartus-lite-limit) below.

## 1. The three roles in detail

### 1.1. BOOT_ROM: the fixed bootloader

Programmed **once**, as part of the initial full Quartus compile (`quartus_sh --flow compile` and `quartus_pgm`), and never rewritten over JTAG afterwards, unlike the FLASH. It holds `boot_rom.S` (`src/simulation/internal-mem/runtime/boot_rom.S`). That is the reset vector, which clears tohost, fromhost and the `stdout` header and jumps to the FLASH, and the wait and restart loop (`rv32_wait_restart`) that lets `riscv-tools run` change tests without reprogramming the whole FPGA. See [atualizacao-de-programa.md](atualizacao-de-programa.md) for the full flow of that change.

It is generic on purpose and knows nothing about a test. The picolibc `crt0`, inside the image of each test (starting at `0x800`), copies `.data`, zeroes `.bss` and calls `main`. What the BOOT_ROM and the program agree on is only the entry point, the address of `rv32_wait_restart` and the words at the top of the RAM. See [runtime.md](runtime.md) and [atualizacao-de-programa.md](atualizacao-de-programa.md).

### 1.2. FLASH: the "firmware" of each test

The real program of each test (`.init`, `.text` and `.rodata`, plus the initial image of `.data`), rewritten over JTAG (In-System Memory Content Editor) every time a test changes. Physically it is a RAM-type `altsyncram` (not a real flash), but architecturally it represents the non-volatile storage. It is only rewritten explicitly between runs, never by the CPU at run time.

### 1.3. RAM: the real data

`.data`, `.sdata`, `.sbss`, `.bss`, stack and heap. It is the only memory the MEM stage (load and store) always reaches for writing. `.rodata` (large constants) stays resident in the FLASH and is never copied here. The last 1056 bytes of the physical space of the IP are reserved (outside the `__ram_size` that `rv32im-fpga.specs` gives the test) for tohost and fromhost (4 words, HTIF convention, with 2 free words) and the `stdout` buffer (1032 bytes, see [runtime.md](runtime.md)).

## 2. The FLASH needs a second read port: the Quartus Lite limit

The MEM stage needs to read the FLASH as data specifically for the `.data` copy loop in `boot_rom.S` (`lw a0, 0(t1)`, where `t1` points into the FLASH, the LMA of `.data`).

The obvious solution, giving the `FLASH` a second read port (a `DUAL_PORT` `altsyncram` IP), **does not compile in Quartus Prime Lite**. An `altsyncram` with `operation_mode => DUAL_PORT` **and** `lpm_hint => "ENABLE_RUNTIME_MOD=YES"` at the same time fails to compile in that edition (confirmed empirically by running `quartus_map` alone on that IP). `ENABLE_RUNTIME_MOD` is mandatory because it is what lets the JTAG In-System Memory Content Editor rewrite the FLASH at each test.

Instead of a dual-port FLASH, there are **two identical physical instances**, single-port each:

- `FLASH` (`ips/FLASH1PORT/flash1port.vhd`): the instruction fetch port (IF), `INSTANCE_NAME=FLASH`.
- `FLASH_MEM` (`ips/FLASH_MEM1PORT/flash_mem1port.vhd`): the data read port for the MEM stage, `INSTANCE_NAME=FLASH_MEM`. Same clock as the RAM (`pll_clk_idexmem`), since the MEM stage consumes both.

The different `INSTANCE_NAME` is what makes the JTAG In-System Memory Content Editor treat them as two independent taps. `riscv_tools` (tohost and rom_writer) writes the **same content** to both every time a test changes. In `config.yaml`, `quartus.rom_mem_instances: [1, 3]` is a list with both JTAG indexes, not a single one.

The BOOT_ROM never needs a second port, since it has no `.data` of its own, and `boot_rom.S` only uses fixed immediates.

## 3. Memory map

| Region | Base | Size | Words | widthad |
| :--- | :--- | :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | 2K | 512 | 9 |
| FLASH and FLASH_MEM | `0x00000800` | 30K | 7680 | 13 |
| RAM (physical space) | `0x00008000` | 160K | 40960 | 16 |
| RAM (usable, `rv32im-fpga.specs`) | `0x00008000` | 160K minus 24 minus 1032 bytes | N/A | N/A |
| `stdout` (header and data) | `0x0002FBE0` | 1032 bytes | N/A | N/A |
| fromhost | `0x0002FFF0` | 2 words | N/A | N/A |
| tohost | `0x0002FFE8` | 2 words | N/A | N/A |
| `__stack` (initial sp) | `0x0002FBE0` | N/A | N/A | N/A |

The FLASH is **30K**, not the obvious round 32K, for a specific reason. The top of the RAM (`ram_base + ram_words*4 = 0x30000`) must fall on a 4096-byte aligned address, because the boot ROM builds the end of the RAM with `lui t0, 0x30` (with no `addi` after). `lui` only zeroes the low 12 bits, so it only works if those 12 bits are already zero in the real value. `0x800 (FLASH_BASE) + FLASH_SIZE` only falls on a multiple of 4096 if `FLASH_SIZE` is an odd multiple of 2048 (30K = 30720 = 15x2048 works, 32K = 32768 = 16x2048 does not).

### 3.1. The RAM block limit

The Cyclone V 5CEBA4F23 has 308 M10K blocks of 10 Kbit, a limit on the number of blocks as well as on total bits. The duplicated FLASH (`FLASH` and `FLASH_MEM`) counts twice, and the current map uses about 178 blocks (58 % of the ceiling).

## 4. JTAG indexes (`config.yaml: quartus:`)

The instantiation order in `core_fpga_test.vhd` is the order the In-System Memory Content Editor uses to number the instances:

0. `BOOT_ROM` has no usable index in `config.yaml` on purpose, since it is never rewritten at run time, only at the initial compile.
1. `FLASH` is `quartus.rom_mem_instances[0]`.
2. `RAM` is `quartus.ram_mem_instance` (`tohost` and `fromhost` live inside the RAM, so they share its index).
3. `FLASH_MEM` is `quartus.rom_mem_instances[1]`. It is instantiated **after** the RAM on purpose, so index 2, which the RAM already has, does not shift.

## 5. LEDs (`core_fpga_test.vhd`)

| LED | Signal | Meaning |
| :--- | :--- | :--- |
| LEDR(0) | `Blinky` | Blinks straight from `CLOCK_50`, unrelated to the core, "board alive" |
| LEDR(1) | `pll_locked` | Should stay **always on** after the FPGA is configured. Off means the PLL never locked |
| LEDR(2) | `FPGA_RESET_N` | On means the physical reset button is **released**. Off means it is pressed |
| LEDR(3) | `not core_reset` | On means the core is out of reset and running. Off means the core is in reset (PLL without lock, or button pressed) |
| LEDR(4-9) | (unused) | Free |

As a quick diagnostic without opening a JTAG session, if LEDR(1) or LEDR(3) is off, the problem is **before** the core (PLL or reset) and no test will run. If both are on and a test still does not pass, the problem is in the software or the core logic, not in the board configuration.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
