# C runtime: picolibc, crt0 and the toolchain linker script

This project has no `crt0` or linker script of its own. A C (or assembly) program is compiled and linked with what the Infra toolchain already brings, and what belongs to this hardware sits in a single platform file and three code files. This guide says where each piece comes from, how to use it and what the runtime delivers.

## 1. Where the linker script and the crt0 come from

Both are in the toolchain of the `ghcr.io/insper-riscv/ci-elf` image (the same installation as `GCC_SETUP.md` of Infra, in `/opt/riscv-foundation/riscv32-elf`, with the picolibc of `riscv-gnu-toolchain`, whose commit is in the `.tag` of the installation):

| Piece | File in the toolchain | How it reaches the link |
| :--- | :--- | :--- |
| Linker script | `riscv32-unknown-elf/lib/picolibc.ld` | the GCC driver adds it when it sees no `-T` |
| `crt0` | `riscv32-unknown-elf/lib/crt0-hosted.o` | chosen in `rv32im-fpga.specs` |
| C library | `riscv32-unknown-elf/lib/libc.a` | `--specs=picolibc.specs` |

To see the paths on the machine in use:

```bash
riscv32-unknown-elf-gcc -print-file-name=picolibc.ld
riscv32-unknown-elf-gcc --specs=picolibc.specs -print-file-name=crt0-hosted.o
```

## 2. The platform file

`rv32im-fpga.specs`, in `src/simulation/internal-mem/runtime/`, is a GCC specification file, written by `riscv-tools generate-memory-map` from `platform.yaml` (the addresses and sizes are not written by hand). It includes `picolibc.specs` and adds only what belongs to this hardware:

```
%include <picolibc.specs>
%rename link rv32imfpga_picolibc_link

*link:
%(rv32imfpga_picolibc_link) --defsym=__flash=0x1000 --defsym=__flash_size=0x7000 --defsym=__ram=0x8000 --defsym=__ram_size=0x27BE0 %{!DRV32_SPIKE:--defsym=rv32_wait_restart=0x100}

*startfile:
crt0-hosted%O%s
```

| Part | What it does |
| :--- | :--- |
| `__flash`, `__flash_size` | Where `picolibc.ld` puts `.init`, `.text` and `.rodata` (the FLASH, from `0x1000`, 28 KB) |
| `__ram`, `__ram_size` | Where it puts `.data`, `.bss`, the heap and the stack (the RAM, from `0x8000`). The top 1056 bytes stay out, 24 for `tohost`, `fromhost` and 8 free ones, and 1032 for `stdout` (section 5) |
| `rv32_wait_restart=0x100` | The fixed address of the BOOT_ROM routine every test ends in. It leaves the link when compiling with `-DRV32_SPIKE` (section 6) |
| `crt0-hosted` | The picolibc startup, which sets `sp` and `gp`, copies `.data` from the FLASH, zeroes `.bss`, prepares TLS, runs constructors, calls `main` and calls `exit` with what `main` returned |

Outside `riscv-tools`, the same file serves any compilation:

```bash
riscv32-unknown-elf-gcc -march=rv32im -mabi=ilp32 -Os --specs=rv32im-fpga.specs \
    program.c src/simulation/internal-mem/runtime/_exit.c -o program.elf
```

## 3. What the runtime delivers

A program compiled this way is hosted. `main` can return (the return becomes `exit`, and then `_exit`), and the full picolibc libc is available (`string.h`, `stdlib.h`, `malloc`, `free`, `printf`, `errno`, global variables with constructors, and TLS). Measured on an ordinary C program:

| Section | Address |
| :--- | :--- |
| `_start` (entry), `.init` | `0x1000` |
| `.text`, `.rodata` (includes `.srodata`) | in the FLASH, after `.init` |
| `.data` (includes `.sdata`), `.tdata` | VMA `0x8000`, LMA in the FLASH |
| `.bss` | after `.data` |
| heap | from `_end` to `__stack` minus 4 KB |
| `__stack` (initial value of `sp`) | `0x2FBE0` |

`picolibc.ld` reserves 4 KB of stack as a region, and the linker stops with `section .stack will not fit in region "ram"` if the RAM cannot hold data, heap and stack.

The `memcpy` of this picolibc build is byte by byte (`lbu` from the FLASH, `sb` into the RAM), and it is what copies `.data`. Port B of the FLASH serves byte and halfword reads like the RAM. The tests that exercise this are `c/data-init-*`, `c/bss-zero` and `c/struct-init-heap`.

## 4. The project files

In `src/simulation/internal-mem/runtime/`:

| File | Role |
| :--- | :--- |
| `boot_rom.S`, `boot_rom.ld` | The BOOT_ROM, written once. It clears the shared words, jumps to `0x1000` (`RV32_BOOT_ENTRY`) and keeps `rv32_wait_restart` at `0x100` (see [boot.md](boot.md)) |
| `memory_map.h` | Generated from `platform.yaml`: the addresses of `tohost`, `fromhost`, `stdout`, the UART and the boot entry (`RV32_BOOT_ENTRY`, `0x1000`), which the BOOT_ROM, `_exit.c`, `stdio.c` and `spike_exit.S` include |
| `_exit.c` | The `_exit` the `crt0` ends in. Code 0 is PASS (`tohost` `1`), any other is FAIL (`tohost` `(code << 1) | 1`), and then it jumps to `rv32_wait_restart` |
| `stdio.c` | The `stdout` write function (section 5) |
| `spike_exit.S` | The substitute of `rv32_wait_restart` for the Spike ELF (section 6) |

In `config.yaml`, `toolchain.specs` points to `rv32im-fpga.specs`, `paths.sources` lists `_exit.c` and `stdio.c` (compiled in every test), `paths.boot_rom` and `paths.boot_rom_linker_script` point to the BOOT_ROM, and `emulator.sources` and `emulator.gcc_flags` assemble the Spike ELF.

## 5. Data output (`stdout`)

The core has no external output. `stdout` (and `stderr`) is a 1 KB buffer in the RAM, which the host reads over JTAG after the test. The region sits at the top of the RAM, outside the space the linker gives the program:

| Address | Content |
| :--- | :--- |
| `0x0002FBE0` | `length`, the bytes written, at most 1024 |
| `0x0002FBE4` | `truncated`, 1 when some byte did not fit |
| `0x0002FBE8` | `data`, 1024 bytes |

The buffer is linear. When it fills, writing stops and `truncated` stays at 1. The BOOT_ROM zeroes the header at every start. There is no input, and a read returns end of file. `printf`, `puts` and `putchar` work with no change in the C code. The `c/stdout-printf` test checks the content and `c/stdout-truncate` checks the overflow. The host reads this region with `dump-ram`, at address `0x27BE0` relative to the start of the RAM.

The full `printf` (with `double` support) costs about 12 KB of the 28 KB of the FLASH.

## 6. Spike

The program of a test ends in `rv32_wait_restart`, which on the hardware is BOOT_ROM code at a fixed address, and the test image has nothing there. For Spike, the ELF is assembled separately, with `-DRV32_SPIKE` (which removes the fixed address from the link) and with `src/simulation/internal-mem/runtime/spike_exit.S`, which defines `rv32_wait_restart` as ordinary code (a wait, since the test already wrote `tohost`, where Spike stops). `tohost` and `fromhost` are absolute symbols in the reserved words at the top of the RAM, so the file takes no space and every address of the Spike ELF, and therefore of a golden, is the one of the image the hardware loads.

## 7. Known limits

- The ISA is `rv32im`, with no hardware floating point (`float` and `double` run in software, through libgcc). Decide this carefully before porting code that uses them.
- The `crt0` and `libc.a` do not use CSRs, and picolibc does not do semihosting. The core implements Zicsr and traps (see the Core), but the runtime does not configure `mtvec`.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
