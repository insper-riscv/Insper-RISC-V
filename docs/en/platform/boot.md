# The reference boot state of this bare-metal RISC-V

Booting on this core goes through two sides. The BOOT_MEMORY (`src/boot/boot_core.S`, included by the `boot_memory.S` of each platform) is fixed and shared, programmed once and never rewritten by a test. The picolibc `crt0` goes inside the image of each test in the FLASH. This project has no `crt0` or linker script of its own, see [runtime.md](runtime.md) for where they come from and how to use them. See [atualizacao-de-programa.md](atualizacao-de-programa.md) for how control passes from one side to the other at each test change.

This document describes, register by register and section by section, exactly what state exists at the instant `main()` is called and, just as important, what is **not** done. The state follows the official RISC-V ABI ([riscv-elf-psabi-doc](https://github.com/riscv-non-isa/riscv-elf-psabi-doc)).

## 1. The common BOOT_MEMORY

Every platform builds the same BOOT, the common `boot_core.S` (`src/boot/boot_core.S`). The `boot_memory.S` of each platform is only a wrapper that includes the headers `riscv-tools generate-memory-map` writes from `platform.yaml` and, last, `boot_core.S`.

| Part | Role |
| :--- | :--- |
| `runtime/memory_map.h` | The addresses of `tohost`, `fromhost`, `stdout` and `RV32_BOOT_ENTRY` |
| `runtime/flash_banks.h` | The two FLASH banks and the image format (only on platforms with banks) |
| `runtime/boot_config.h` | One `RV32_HAS_<EXTENSION>` per extension and extra of the `core` block, `RV32_IS_E` and `RV32_TEST_WAIT`, through the `generate.boot_config_h` key |
| `Core/src/<Extension>/boot.inc` | The fragment of each extension, which `boot_core.S` includes and which switches itself off with `#if RV32_HAS_<EXTENSION>` |

### 1.1. The two switches

| Switch | Origin | Effect |
| :--- | :--- | :--- |
| `RV32_TEST_WAIT` | The `boot.wait_restart` key of `platform.yaml` | Present, the BOOT is the test one. `_reset` clears `tohost`, `fromhost` and the `stdout` header, and `rv32_wait_restart` is fixed at `0x100`. Absent, the BOOT is the application one, none of that exists and the symbol is not exported |
| `RV32_BANK_A_BASE` | `flash_banks.h` | Present, the BOOT chooses between FLASH banks A and B. Absent, it jumps straight to `RV32_BOOT_ENTRY` |

The `de2-115` platform also defines `RV32_BOOT_RAM_MAGIC` in its wrapper, and so accepts a program the host left in the RAM.

### 1.2. The state the BOOT hands the core over in

1. Only in the test BOOT, `tohost`, `fromhost` and the `stdout` header are zeroed.
2. `x1` to `x31` are zero (`x1` to `x15` on RV32E).
3. The Core fragments always run in this order: Zicsr, Zicntr, Zihpm, Sscofpmf and Zifencei. Each one uses only `t0`, `t1` and `t2`, and the `fence.i` of the Zifencei fragment exists only with Zifencei.
4. With banks, the BOOT validates both and jumps to the one with the larger version with `a0 = 0` and `a1 = 0`. With no valid bank it waits reading `fromhost` and starts over at `_reset`. This safeguard exists in both builds, and `fromhost` is only the doorbell, never the jump address.

The BOOT does not prepare `sp`, `gp`, `tp`, `.data` or `.bss`, which belong to the `crt0` of the program. The `rv32_boot_trap` symbol, the safe handler the Zicsr fragment writes to `mtvec`, stops the core in a loop instead of restarting forever.

### 1.3. Layout

`_reset` is alone in `.text.reset`, with a branch to the rest, which lives in `.text.wait_restart`. In the test BOOT that section starts at `0x100`, with `rv32_wait_restart` at the first instruction, as the generated `boot_memory.ld` pins it. The size depends on the extensions that are on, and the linker rejects a BOOT that goes past the size of the BOOT_MEMORY.

### 1.4. Verification

| Proof | Where |
| :--- | :--- |
| On every platform the BOOT assembles, has `fence.i` only with Zifencei and exports `rv32_wait_restart` only with `RV32_TEST_WAIT`. It also assembles on the minimal core with no CSR instruction, on the complete core, on RV32E and in the application version | `tests/python/check_boot_contract.py` |
| The real BOOT images that the simulation tests load are up to date with the sources | `tests/python/gen_de0_cv_boot_images.py --check` and `tests/python/gen_real_boot_images.py --check` |
| The real BOOT starts the program on the minimal core (`rv32i`), on a core with Zicsr and interrupts and on the complete one, and chooses the right bank in 13 cases | The `TemplateRealBoot`, `ModularRealBoot`, `De0CvBootBanks` and `ExternalDataFlashUpdate` tests of `tests.json` |


## 2. The boot sequence

1. Reset enters `_reset` (`0x0`, in the BOOT_MEMORY) and the BOOT does what section 1.2 describes. It jumps to `0x1000` (`RV32_BOOT_ENTRY`) or, on platforms with banks, to the program start of the valid bank with the larger version (`0x1100` or `0x20100` on `de0-cv`), and hands over `a0` and `a1` at `0`. It does not initialize `sp` or `gp` and copies nothing.
2. At `0x1000` is the `_start` of the picolibc `crt0-hosted`. It sets `sp` (from `__stack`) and `gp` (from `__global_pointer$`) and calls `_cstart`.
3. `_cstart` copies `.data` and `.tdata` from the FLASH to the RAM (with `memcpy`), zeroes `.bss` (with `memset`), prepares TLS (`_set_tls`) and runs the constructors (`__libc_init_array`).
4. It calls `main(0, 0)` with `jal`, and whatever `main` returns goes to `exit`, which calls the project `_exit` (`src/simulation/internal-mem/runtime/_exit.c`). A test that ends with `RV32_PASS()` or `RV32_FAIL()` writes `tohost` and jumps straight to `rv32_wait_restart`, without going through `_exit`.

## 3. General-purpose registers when `main()` runs

| Register | ABI name | State in `main()` | Why |
| :--- | :--- | :--- | :--- |
| `x0` | `zero` | `0`, always | Fixed in silicon |
| `x1` | `ra` | Return address into `_cstart` | `main` is called with `jal`, and the return lands in `exit` |
| `x2` | `sp` | `__stack` (`0x0002FBE0`) | Set by `_start` from the linker script |
| `x3` | `gp` | `__global_pointer$` (depends on the size of the regular `.data`, `0x8800` when it is empty) | Set by `_start` (`auipc` and `addi`, PC-relative). Needed for any `gp`-relative access to `.sdata` and `.sbss` |
| `x4` | `tp` | TLS block in the RAM | Set by `_set_tls` |
| `x10`, `x11` | `a0`, `a1` | `0`, `0` | `argc` and `argv` of `main`, with no command line |
| other `x5` to `x9`, `x12` to `x17`, `x18` to `x31` | `t`, `s`, `a` | **Not guaranteed** | Leftovers of the startup itself, and a correct program never depends on the initial value of one of them |

## 4. CSRs (control and status registers)

`crt0-hosted` and `libc.a` touch no CSR, which was checked in the object code (no `csr*`, `ecall`, `ebreak` or `mret` instruction). What leaves the machine state known is the BOOT, through the fragments of the extensions of the core. With Zicsr, `mstatus`, `mie`, `mscratch` (and `mip`, with interrupts) come out zeroed and `mtvec` points to `rv32_boot_trap`. With Zicntr the cycle and instruction counters come out zeroed and counting, and with Zihpm and Sscofpmf the event counters come out zeroed. A program that needs interrupts or another handler configures them on its own before using them.

## 5. Memory sections

The addresses come from `picolibc.ld` and `rv32im-fpga.specs`, which `riscv-tools generate-memory-map` writes from `platform.yaml` (FLASH from `0x1000`, 28 KB, RAM from `0x8000`, minus the reserved regions at the top). There is no fixed budget per section. Each one takes what the program needs, and the linker refuses what does not fit.

| Section | Region | State before `main()` |
| :--- | :--- | :--- |
| `.init` | FLASH, `0x1000` | The `_start` and what picolibc puts at the beginning |
| `.text`, `.rodata` (includes `.srodata`) | FLASH | Already there, loaded over JTAG. `.rodata` is never copied to the RAM, and a `lw` reaches it through the second FLASH read port (see [memoria.md](memoria.md)) |
| `.data` (includes `.sdata`), `.tdata` | RAM, from `0x8000`, LMA in the FLASH | Copied from the FLASH by `_cstart` |
| `.bss` (includes `.sbss`), `.tbss` | RAM, after `.data` | Zeroed by `_cstart` |
| heap | RAM, from `_end` to `__heap_end` | Managed by the picolibc `malloc`, through `sbrk` |
| Stack | RAM, top at `0x0002FBE0` | Only the pointer (`sp`) is set, with 4 KB reserved |
| `stdout` | RAM, `0x0002FBE0` to `0x0002FFE7` | Header zeroed by the BOOT_MEMORY (see [runtime.md](runtime.md)) |
| `tohost` (`0x0002FFE8`) and `fromhost` (`0x0002FFF0`) | RAM | Zeroed on every entry to `_reset`, cold boot or restart, so the result of the previous test never leaks. HTIF convention, and only Spike uses it |

## 6. What this boot sequence deliberately does NOT do

- **Handling of `ecall` and interrupts.** The BOOT only points `mtvec` to the safe handler that stops the core, and the program installs its own before depending on a trap.
- **Multi-hart support.** It assumes a single hart, with no `mhartid`, and the core is single-hart.
- **Data input.** There is no input device, and `stdin` returns end of file.
- **PMP (Physical Memory Protection) and isolation.** The core does not implement PMP.
- **Zeroed registers in `main()`.** The BOOT zeroes `x1` to `x31` on entry, but the bank selection and the `crt0` reuse them, so only the ones listed in section 3 have a defined value in `main()`.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
