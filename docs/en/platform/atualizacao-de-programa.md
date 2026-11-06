# How a new program starts running: FLASH rewrite and boot handoff

Changing the test on the board combines two distinct mechanisms. One is generic, from `riscv-tools` itself (rewriting a memory over JTAG without recompiling or reprogramming the whole FPGA). The other is specific to this project (how control gets from the fixed BOOT_MEMORY to the program just written into the FLASH). The second is the same problem any remote firmware update system has to solve (see "What the BOOT_MEMORY and the program agree on" below). The side receiving the update is already running code compiled **before** the update existed, so both sides (the one that updates and the one that is updated) must agree beforehand on where everything lives.

## 1. The full sequence

1. **Initial programming (once)**: `quartus_sh --flow compile` and `quartus_pgm` load the whole bitstream, including the initial content of the BOOT_MEMORY (`src/simulation/internal-mem/runtime/boot_memory.S`) and of the first FLASH and RAM. The BOOT_MEMORY is never touched again after that.
2. **Test change (fast path)**: `riscv-tools run` rewrites the FLASH, which has a single copy, through the JTAG loader (`quartus.rom_write_method: jtag_loader`). It halts the core, writes the image, checks the count and the checksum and releases the core, which restarts from the BOOT_MEMORY in step 5, without recompiling or reprogramming the FPGA and without writing `fromhost`.
3. **The core, from the inside**: between one test and the next, the core is parked in `rv32_wait_restart` (fixed address `0x100` in the BOOT_MEMORY), in a loop that only does `lw` from `fromhost_addr` until it reads non-zero.
4. On seeing `fromhost` different from zero, `rv32_wait_restart` jumps to `_reset` (fixed address `0x0`). The previous test already wrote its result to `tohost` before getting there.
5. `_reset` zeroes `tohost`, `fromhost` and the `stdout` header (so neither the result nor the output of the previous test leaks) and jumps to `FLASH_BASE` (`0x00001000`). On `de0-cv`, which has two banks, the BOOT_MEMORY first checks the header and the CRC-32 of each bank and jumps to the program start of the valid bank with the larger version (section 5).
6. At the program start (`0x1000` on platforms without banks, `0x1100` in bank A of `de0-cv`) is the `_start` of the picolibc `crt0`, inside the test image. It sets `sp` and `gp`, copies `.data` from the FLASH to the RAM, zeroes `.bss`, prepares TLS and calls `main`, see [boot.md](boot.md).
7. When it ends, the test writes `tohost` (`RV32_PASS()` or `RV32_FAIL(code)` in `rv32_test.h`, or the return of `main` through `_exit`) and calls `rv32_wait_restart`, going back to step 3.

The contact between the BOOT_MEMORY and the FLASH is the jump of step 5 (BOOT_MEMORY to the FLASH) and the jump of step 7 (program to `0x100`). On platforms without banks the BOOT_MEMORY reads nothing from the FLASH. On `de0-cv` it reads the header and the payload of both banks to check the CRC-32s before the jump.

## 2. Why the BOOT_MEMORY is never rewritten per test

`_reset` and `rv32_wait_restart` are fixed addresses (`0x0`, `0x100`, see `src/simulation/internal-mem/runtime/boot_memory.ld`), resolved in the **single, separate** link of `src/simulation/internal-mem/runtime/boot_memory.S`, not in the link of each test. If the BOOT_MEMORY were rewritten per test as the FLASH is, each new compilation could move those offsets, and every test that already has those same fixed addresses embedded in its own binary (through `--defsym=rv32_wait_restart=0x100` in `rv32im-fpga.specs`) would call a wrong address with no link error warning, since both sides are compiled and linked completely separately. Keeping the BOOT_MEMORY frozen after the initial programming is that. Without it fixed, there would be no stable address for the handoff to work.

The choice of the bank by its header (section 5) enters the BOOT_MEMORY of `de0-cv` in a single rewrite, together with the bitstream of a full Quartus compile. After it the BOOT_MEMORY is frozen again, which is why the whole policy fits in it: the update in the field only changes the content of the banks.

`rv32_wait_restart` also cannot live in the FLASH. The core waits in it while the host rewrites the FLASH, so it must be in a memory nobody rewrites, otherwise the core would execute instructions from a memory being rewritten.

## 3. What the BOOT_MEMORY and the program agree on

`src/simulation/internal-mem/runtime/boot_memory.S` is compiled and linked **before** any test exists, and its binary cannot contain anything of a specific test. This is the problem any remote firmware update faces, a fixed bootloader that cannot be rewritten remotely (the risk of bricking the device is too high) receiving an application image that can. Both sides must agree beforehand on the minimum, and here that minimum is:

| Agreement | Value | Who uses it |
| :--- | :--- | :--- |
| Program entry | `0x1000`, the picolibc `_start` (`picolibc.ld` puts `.init` at the beginning of the FLASH); on `de0-cv`, `0x1100` or `0x20100`, the program start of each bank | The BOOT_MEMORY jumps there |
| `rv32_wait_restart` | `0x100` | The program jumps there when it ends |
| Words at the top of the RAM | `fromhost` `0x2FFF0`, `tohost` `0x2FFE8`, `stdout` header `0x2FBE0` (generated from `platform.yaml` into `memory_map.h`) | The BOOT_MEMORY zeroes them, the program and the host use them |

Everything else (where `.data`, `.bss`, heap and stack live, the size of each section) is decided in the link of each test by the toolchain linker script, from the addresses in `rv32im-fpga.specs`. The BOOT_MEMORY knows nothing of this, because whoever copies `.data` and zeroes `.bss` is the `crt0` of the program itself. That is why the image of a test carries everything that varies in it.

The MEM stage of this core does have a read path to the FLASH (port B of the FLASH, see [memoria.md](memoria.md#12-flash-the-firmware-of-each-test)). That is how the `crt0` reads the initial `.data` from the FLASH to copy it to the RAM, and how `.rodata` can stay resident in the FLASH (never copied to the RAM, see [memoria.md](memoria.md)).

On platforms without banks nothing checks the integrity of the image before the jump, because JTAG is a local, physical and trusted link. On `de0-cv` the BOOT_MEMORY checks the magic, both CRC-32s and the size of each bank (section 5), as a system that receives updates over an untrusted link has to do. A signature stays out of scope, since the CRC-32 detects an interrupted or corrupted image, not a forged one.

## 4. The slow path: recompile and reprogram

If a test does not answer within the timeout (`quartus.default_timeout_s`), the `orchestrator` of `riscv-tools` falls back to progressively more expensive tiers up to a full recompile and reprogram. The `orchestrator` module of Tools has the details of when each tier fires, and [placa.md](../guide/placa.md) gives the rule for compiling and programming without breaking the JTAG session.

## 5. The FLASH banks and the image

The FLASH of the `de0-cv` has two banks for the program update in the field, declared in `flash.banks` of the `platform.yaml`.

| Bank | Start | Size | Program start |
| :--- | :--- | :--- | :--- |
| A | `0x00001000` | 124 KiB | `0x00001100` |
| B | `0x00020000` | 128 KiB | `0x00020100` |

Each bank starts with a 256-byte header page (magic, size, CRC-32 of the payload, version and header CRC; the format is in the `flash_image` module of Tools), and the program follows it. The update routine writes the payload first and the header last, so a valid header marks a bank whose update finished. The boot memory checks the header and the CRC-32 of the payload of each bank and jumps to the valid one with the larger version, bank A winning a tie and the core waiting in `rv32_wait_restart` when none is valid. The policy and the cost of the check are in the [entry contract](contrato-de-entrada.md), section 6.6.

`make generate` writes the files below from the banks.

| File | Content |
| :--- | :--- |
| `runtime/rv32im-fpga-bank-a.specs` and `runtime/rv32im-fpga-bank-b.specs` | Linker flags of a program for each bank, with `__flash` at the start of the program and `__flash_size` without the header page |
| `runtime/flash_banks.h` | Image magic, size of the header page and, for each bank, `RV32_BANK_<NAME>_BASE`, `_SIZE` and `_ENTRY`, for the boot memory and the update routine |

A program for bank B is compiled with `--specs` pointing at its specs file, and `riscv-tools flash-image pack program.bin --output image.bin --version N --platform src/cyclone-v/de0-cv/platform.yaml --bank B` builds the image and checks that it fits. `riscv-tools check-memory-map` validates the banks (aligned to the 4 KiB sector, inside the FLASH, not overlapping).

## 6. The update protocol in the firmware

The host packs the program with `riscv-tools flash-image pack` and sends it over the JTAG UART with `riscv-tools flash-image send image.bin --config <config>`; `flash-image verify` checks an image without sending it. The UART stream is the image with no framing, the 256-byte header page first and then as many payload bytes as the size field of the header says. The firmware of one bank receives the image and updates the other bank in six steps.

| Step | What happens |
| :--- | :--- |
| 1 | Reads the 256 header bytes and checks the magic, the header CRC-32 and the size, before keeping any payload |
| 2 | Reads the payload, as many bytes as the header says, and checks its CRC-32. A stream that was cut or damaged stops here, without touching the FLASH |
| 3 | Copies the update routine to the SDRAM and runs `fence.i`, because the code that erases the FLASH must not depend on a region of it |
| 4 | For each sector of the destination bank, enables the write, erases and waits for the chip to be free |
| 5 | Programs the payload pages, one of 256 bytes at a time through the buffer of the controller, and the header page last |
| 6 | Reads the bank back, compares it with the received image and restarts through the BOOT_MEMORY, which chooses the image with the larger version |

The FLASH controller ([flash_controller](https://github.com/insper-riscv/Peripherals/blob/main/docs/en/flash-controller/flash_controller.md)) sits in the `FLASH_CTRL` peripheral of `platform.yaml`, and the routine reads the chip status before each command because the chip ignores a command that arrives while busy. A refusal by the chip (protected sector, address outside the window) ends the routine with an error code. The caches receive from the chip the invalidation pulse of the changed region, so the read back already sees the new FLASH.

An update interrupted before step 5 ends leaves the header of the bank erased, and the BOOT_MEMORY ignores the bank. The firmware can simulate that cut with the option of not writing the header, which the interrupted-update test uses.

## 7. The tests

| Test | Where | What it proves |
| :--- | :--- | :--- |
| Bank choice | `tests/python/unittests/rtl/de0_cv_boot_banks.py`, entry `De0CvBootBanks` | With the real `boot_memory.S`, the newer bank runs, a corrupted payload or an erased, tampered or absurdly sized header makes the BOOT_MEMORY fall back to the other bank, and with no valid bank the core stays in `rv32_wait_restart`. The registers `a0` and `a1` arrive at `0` |
| Change through the loader | `tests/python/unittests/rtl/external_data_flash_update.py`, entry `ExternalDataFlashUpdate` | The sequence of section 6.2 of the contract: halt, write through the STREAM, checksum check, release, and the new program running after the `_reset` that zeroed `tohost` |
| Complete update | `c-sdram-update/flash-update` of the Tests repository | The program of bank A receives the image of bank B, updates, restarts and the BOOT_MEMORY runs bank B |
| Interrupted update | `c-sdram-update/flash-update-interrupted` | The header of bank B is not written and the BOOT_MEMORY returns to bank A |

The update programs run on the simulation top of `de0-cv` with `HAS_FLASH_CONTROLLER`, which adds the controller, the two-port storage and the command chip, with the erase and program waits in the generics `FLASH_ERASE_LATENCY` and `FLASH_PROGRAM_LATENCY`. The Tests repository runs them with a fast chip and with a slow one.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
