# How a new program starts running: FLASH rewrite and boot handoff

Changing the test on the board combines two distinct mechanisms. One is generic, from `riscv-tools` itself (rewriting a memory over JTAG without recompiling or reprogramming the whole FPGA). The other is specific to this project (how control gets from the fixed BOOT_ROM to the program just written into the FLASH). The second is the same problem any remote firmware update system has to solve (see "What the BOOT_ROM and the program agree on" below). The side receiving the update is already running code compiled **before** the update existed, so both sides (the one that updates and the one that is updated) must agree beforehand on where everything lives.

## 1. The full sequence

1. **Initial programming (once)**: `quartus_sh --flow compile` and `quartus_pgm` load the whole bitstream, including the initial content of the BOOT_ROM (`src/simulation/internal-mem/runtime/boot_rom.S`) and of the first FLASH and RAM. The BOOT_ROM is never touched again after that.
2. **Test change (fast path)**: `riscv-tools run` rewrites the FLASH (both physical copies, `FLASH` and `FLASH_MEM`, see `quartus.rom_mem_instances`) over JTAG (In-System Memory Content Editor), without recompiling or reprogramming the FPGA. Then it writes `1` to `fromhost_addr`.
3. **The core, from the inside**: between one test and the next, the core is parked in `rv32_wait_restart` (fixed address `0x100` in the BOOT_ROM), in a loop that only does `lw` from `fromhost_addr` until it reads non-zero.
4. On seeing `fromhost` different from zero, `rv32_wait_restart` jumps to `_reset` (fixed address `0x0`). The previous test already wrote its result to `tohost` before getting there.
5. `_reset` zeroes `tohost`, `fromhost` and the `stdout` header (so neither the result nor the output of the previous test leaks) and jumps to `FLASH_BASE` (`0x00001000`).
6. At `0x1000` is the `_start` of the picolibc `crt0`, inside the test image. It sets `sp` and `gp`, copies `.data` from the FLASH to the RAM, zeroes `.bss`, prepares TLS and calls `main`, see [boot.md](boot.md).
7. When it ends, the test writes `tohost` (`RV32_PASS()` or `RV32_FAIL(code)` in `rv32_test.h`, or the return of `main` through `_exit`) and calls `rv32_wait_restart`, going back to step 3.

The only contact between the BOOT_ROM and the FLASH is the jump of step 5 (BOOT_ROM to the FLASH) and the jump of step 7 (program to `0x100`). The BOOT_ROM reads nothing from the FLASH.

## 2. Why the BOOT_ROM is never rewritten per test

`_reset` and `rv32_wait_restart` are fixed addresses (`0x0`, `0x100`, see `src/simulation/internal-mem/runtime/boot_rom.ld`), resolved in the **single, separate** link of `src/simulation/internal-mem/runtime/boot_rom.S`, not in the link of each test. If the BOOT_ROM were rewritten per test as the FLASH is, each new compilation could move those offsets, and every test that already has those same fixed addresses embedded in its own binary (through `--defsym=rv32_wait_restart=0x100` in `rv32im-fpga.specs`) would call a wrong address with no link error warning, since both sides are compiled and linked completely separately. Keeping the BOOT_ROM frozen after the initial programming is that. Without it fixed, there would be no stable address for the handoff to work.

`rv32_wait_restart` also cannot live in the FLASH. The core waits in it while the host rewrites the FLASH, so it must be in a memory nobody rewrites, otherwise the core would execute instructions from a memory being rewritten.

## 3. What the BOOT_ROM and the program agree on

`src/simulation/internal-mem/runtime/boot_rom.S` is compiled and linked **before** any test exists, and its binary cannot contain anything of a specific test. This is the problem any remote firmware update faces, a fixed bootloader that cannot be rewritten remotely (the risk of bricking the device is too high) receiving an application image that can. Both sides must agree beforehand on the minimum, and here that minimum is:

| Agreement | Value | Who uses it |
| :--- | :--- | :--- |
| Program entry | `0x1000`, the picolibc `_start` (`picolibc.ld` puts `.init` at the beginning of the FLASH) | The BOOT_ROM jumps there |
| `rv32_wait_restart` | `0x100` | The program jumps there when it ends |
| Words at the top of the RAM | `fromhost` `0x2FFF0`, `tohost` `0x2FFE8`, `stdout` header `0x2FBE0` (generated from `platform.yaml` into `memory_map.h`) | The BOOT_ROM zeroes them, the program and the host use them |

Everything else (where `.data`, `.bss`, heap and stack live, the size of each section) is decided in the link of each test by the toolchain linker script, from the addresses in `rv32im-fpga.specs`. The BOOT_ROM knows nothing of this, because whoever copies `.data` and zeroes `.bss` is the `crt0` of the program itself. That is why the image of a test carries everything that varies in it.

The MEM stage of this core does have a read path to the FLASH (the second physical port, `FLASH_MEM`, see [memoria.md](memoria.md#2-the-flash-needs-a-second-read-port-the-quartus-lite-limit)). That is how the `crt0` reads the initial `.data` from the FLASH to copy it to the RAM, and how `.rodata` can stay resident in the FLASH (never copied to the RAM, see [memoria.md](memoria.md)).

A real difference from a true remote update (over radio, for example) is that nothing here verifies the integrity of the image before jumping to it (checksum, signature). JTAG is a local, physical, trusted link, so that verification was never needed here. A system receiving updates over an untrusted link would need it.

## 4. The slow path: recompile and reprogram

If a test does not answer within the timeout (`quartus.default_timeout_s`), the `orchestrator` of `riscv-tools` falls back to progressively more expensive tiers up to a full recompile and reprogram. The `orchestrator` module of Tools has the details of when each tier fires, and [placa.md](../guide/placa.md) gives the rule for compiling and programming without breaking the JTAG session.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
