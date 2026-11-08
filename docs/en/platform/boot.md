# The reference boot state of this bare-metal RISC-V

Booting on this core goes through two sides. The BOOT_MEMORY (`src/simulation/internal-mem/runtime/boot_memory.S`) is fixed and shared, programmed once and never rewritten by a test. The picolibc `crt0` goes inside the image of each test in the FLASH. This project has no `crt0` or linker script of its own, see [runtime.md](runtime.md) for where they come from and how to use them. See [atualizacao-de-programa.md](atualizacao-de-programa.md) for how control passes from one side to the other at each test change.

This document describes, register by register and section by section, exactly what state exists at the instant `main()` is called and, just as important, what is **not** done. The state follows the official RISC-V ABI ([riscv-elf-psabi-doc](https://github.com/riscv-non-isa/riscv-elf-psabi-doc)).

## 1. The boot sequence

1. Reset enters `_reset` (`0x0`, in the BOOT_MEMORY). It clears `tohost`, `fromhost` and the `stdout` header, and jumps to `0x1000` (`RV32_BOOT_ENTRY`) or, on `de0-cv`, to the program start of the valid bank with the larger version (`0x1100` or `0x20100`). It hands over `a0` and `a1` at `0`. It does not initialize `sp` or `gp` and copies nothing.
2. At `0x1000` is the `_start` of the picolibc `crt0-hosted`. It sets `sp` (from `__stack`) and `gp` (from `__global_pointer$`) and calls `_cstart`.
3. `_cstart` copies `.data` and `.tdata` from the FLASH to the RAM (with `memcpy`), zeroes `.bss` (with `memset`), prepares TLS (`_set_tls`) and runs the constructors (`__libc_init_array`).
4. It calls `main(0, 0)` with `jal`, and whatever `main` returns goes to `exit`, which calls the project `_exit` (`src/simulation/internal-mem/runtime/_exit.c`). A test that ends with `RV32_PASS()` or `RV32_FAIL()` writes `tohost` and jumps straight to `rv32_wait_restart`, without going through `_exit`.

## 2. General-purpose registers when `main()` runs

| Register | ABI name | State in `main()` | Why |
| :--- | :--- | :--- | :--- |
| `x0` | `zero` | `0`, always | Fixed in silicon |
| `x1` | `ra` | Return address into `_cstart` | `main` is called with `jal`, and the return lands in `exit` |
| `x2` | `sp` | `__stack` (`0x0002FBE0`) | Set by `_start` from the linker script |
| `x3` | `gp` | `__global_pointer$` (depends on the size of the regular `.data`, `0x8800` when it is empty) | Set by `_start` (`auipc` and `addi`, PC-relative). Needed for any `gp`-relative access to `.sdata` and `.sbss` |
| `x4` | `tp` | TLS block in the RAM | Set by `_set_tls` |
| `x10`, `x11` | `a0`, `a1` | `0`, `0` | `argc` and `argv` of `main`, with no command line |
| other `x5` to `x9`, `x12` to `x17`, `x18` to `x31` | `t`, `s`, `a` | **Not guaranteed** | Leftovers of the startup itself, and a correct program never depends on the initial value of one of them |

## 3. CSRs (control and status registers)

**No CSR is touched** by `crt0-hosted` or by `libc.a`, neither `mstatus`, `mtvec`, `mepc` nor `mie` and `mip`. This was checked in the object code (no `csr*`, `ecall`, `ebreak` or `mret` instruction). The core implements Zicsr and the trap unit, so a program that needs `mtvec` or interrupts configures them on its own before using them.

## 4. Memory sections

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

## 5. What this boot sequence deliberately does NOT do

- **Trap vector (`mtvec`) and handling of `ecall` and interrupts.** The startup does not configure `mtvec`, and a trap before the program configures it uses the reset value of `mtvec`.
- **Multi-hart support.** It assumes a single hart, with no `mhartid`, and the core is single-hart.
- **Data input.** There is no input device, and `stdin` returns end of file.
- **PMP (Physical Memory Protection) and isolation.** The core does not implement PMP.
- **Clearing registers before `main()`.** Only the ones listed above have a defined value.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
