# Entry contract between the BOOT_ROM and the firmware

The BOOT_ROM wakes the board up and hands control to the firmware without knowing which firmware is in the FLASH. This document defines what the BOOT_ROM guarantees at the moment of the handoff and what is left to the firmware, so that a program in C, Rust or assembly, with its own `_start`, boots on any platform of this repository. The sequence of the picolibc `crt0`, used by the test programs, is in [boot.md](boot.md).

## 1. Roles

| Role | Who | Where |
| :--- | :--- | :--- |
| Leave the board in a known initial state and jump to the firmware | `boot_rom.S` | BOOT_ROM, `0x0`, programmed once in the bitstream |
| Initialize the program environment (stack, `gp`, `.data`, `.bss`, TLS, constructors) | `_start` of the firmware | FLASH, at `boot.entry` |
| Be the BIOS, the RTOS or the program | Firmware | FLASH |

The stack and `gp` stay out of the BOOT_ROM because a Rust firmware or an RTOS brings its own `_start` and sets the stack through its own linker. Fixing those values in the ROM would force the firmware to accept them or overwrite them.

## 2. State guaranteed at firmware entry

The firmware starts executing at the `boot.entry` address of `platform.yaml`, with the following state.

| Item | State at entry |
| :--- | :--- |
| Program counter | `boot.entry`; on `de0-cv`, the start of the program of the chosen bank (section 6.6) |
| Interrupts | Off, because the BOOT_ROM writes no CSR and the reset value of `mstatus`, `mie` and `mip` holds |
| CSRs | All at their reset value |
| Instruction cache | Free of lines from the previous program, through the `fence.i` executed before the jump |
| Shared words at the top of the RAM (`stdout`, `tohost` and `fromhost`) | Zeroed |
| Rest of the RAM | Undefined |
| `x0` | `0`, always |
| `a0` | `0`, the hart identifier |
| `a1` | `0` |
| Other registers (`x1` to `x31`) | Undefined, including `sp`, `gp` and `tp` |

The entry registers follow the RISC-V convention. `a0` carries the hart identifier, always `0` because the core has a single hart, and `a1` carries `0` in place of the pointer to the platform description, which the firmware obtains at build time (section 4). A firmware that does not need them ignores them, and `sp`, `gp` and `tp` remain its own business.

## 3. What the firmware does on its own

| Responsibility | Note |
| :--- | :--- |
| Set `sp` and `gp` | From the symbols of its own linker script, before any call |
| Copy `.data` and `.tdata` from the FLASH to the RAM and zero `.bss` | The FLASH is read through the data port, see [memoria.md](memoria.md) |
| Prepare TLS and run the constructors | When the language uses them |
| Configure `mtvec` and enable interrupts | Only after having a valid stack |
| Respect the reserved words at the top of the RAM | The firmware linker limits the RAM to the start of `stdout` |

## 4. Platform description

There is a single description, and it comes from `platform.yaml`, the source of truth of the platform. `riscv-tools generate-memory-map` writes it to `memory_map.h` for C and assembly, with the constants below, and the firmware includes that header instead of copying addresses by hand.

| Constant | Meaning |
| :--- | :--- |
| `RV32_BOOT_ENTRY` | Address where the firmware starts |
| `RV32_RAM_END` | End of the RAM |
| `RV32_STDOUT_BASE` | Start of the `stdout` region, the upper limit of the firmware RAM |
| `RV32_TOHOST_ADDR` and `RV32_FROMHOST_ADDR` | Words of the protocol with the test host |
| `RV32_UART_BASE`, `RV32_DISPLAY_BASE` | Base of each peripheral present on the platform |

There is no description table in the BOOT_ROM, because the memory map is fixed per platform and known when the firmware is built.

## 5. Shared entry point

`boot.entry` is the only value that the BOOT_ROM and the firmware linker both repeat. The BOOT_ROM reads it from `RV32_BOOT_ENTRY` and the linker receives it from `rv32im-fpga.specs`, both generated from the same `platform.yaml`, and `riscv-tools check-memory-map` checks that the hand-written copies match it. On `de0-cv` the BOOT_ROM reads instead the base, the size and the program start of each bank in `flash_banks.h`, and the linker of each bank receives `rv32im-fpga-bank-a.specs` or `rv32im-fpga-bank-b.specs`, all generated from the same `flash.banks`.

## 6. How the core reaches the FLASH

There are two jump policies, depending on whether the platform has banks in the FLASH. On platforms without banks the `_reset` of the BOOT_ROM always jumps to `boot.entry`, and the guarantee that the FLASH is complete at that moment comes from the hardware that writes it and from the order in which the host uses it. On `de0-cv`, which declares `flash.banks`, the BOOT_ROM checks both banks and jumps only to a valid image (section 6.6). As for writing the FLASH, there are two mechanisms.

| Mechanism | Platforms | Who keeps the core out of the FLASH during the write |
| :--- | :--- | :--- |
| FLASH loader | Internal two-port FLASH, rewritten over JTAG ([internal-mem](internal-mem.md)) | The hardware: the halt output of the loader holds the core in reset |
| Write with the core parked | FLASH chip behind the caches, written through the Quartus in-system memory ([de0-cv](de0-cv.md)) | The protocol: the core waits in `rv32_wait_restart`, in the BOOT_ROM, and leaves only when the host writes `fromhost` |

### 6.1. Cold start

1. The FPGA is programmed with the `.sof`, which already carries the BOOT_ROM and the initial image of the FLASH.
2. When the PLL locks, the core reset is released. The core reset combines the unlocked PLL, the board button and, where there is a loader, its halt output.
3. The loader leaves reset with the halt off, so the core is not held.
4. The core fetches address `0x0`, runs `_reset`, zeroes `fromhost`, `tohost` and the `stdout` header, runs `fence.i` where there are caches and jumps to `boot.entry`.
5. What the core finds at `boot.entry` is the initial image of the `.sof`. On `internal-mem` it is a test program. On `de0-cv` the initial FLASH has no valid image header, so the BOOT_ROM jumps to no bank and parks the core in `rv32_wait_restart` until the host writes an image.

On platforms without banks no step of the cold start checks the FLASH before the jump. On `de0-cv` step 4 includes the choice of the bank.

### 6.2. Test change with the FLASH loader

1. The host zeroes `tohost` through the RAM access port, so the result of the previous test is not mistaken for the new one.
2. It sends the halt command. The halt output rises, the core enters reset wherever it was, and port B of the FLASH becomes the loader's.
3. It sets the cursor and sends the image in one `STREAM` scan. A write reaches the memory only while the core is halted.
4. It reads the count and the checksum from the loader and compares them with those of the image. If they differ, the change is aborted and the core stays halted.
5. It sends the release command. The core reset falls and the core starts from address `0x0`.
6. `_reset` zeroes the shared words and jumps to `boot.entry`, which is now the complete, checked image.

The host does not write `fromhost` on this path. The restart comes from releasing the reset, not from the `rv32_wait_restart` loop.

### 6.3. Test change with the core parked

1. The host zeroes `tohost` through the SDRAM debug port.
2. It writes the FLASH image through the Quartus in-system memory. The core is in the `rv32_wait_restart` loop, which sits in the BOOT_ROM, uncached, so it executes nothing from the FLASH being rewritten.
3. It writes a nonzero value to `fromhost`.
4. The loop reads `fromhost`, exits and jumps to `_reset`, which zeroes the shared words, runs `fence.i` to drop the lines of the previous program and jumps to `boot.entry`, or, on `de0-cv`, to the bank that section 6.6 chooses.

### 6.4. End of a test

1. The program writes the result to `tohost` (`1` for a pass, `(code << 1) | 1` for a failure).
2. It jumps to `rv32_wait_restart`, which sits in the BOOT_ROM and is therefore never rewritten.
3. The host reads `tohost` at intervals and, when bit 0 is `1`, records the verdict.
4. The core stays in the loop until the next change. With the loader, the next halt takes it out of the loop through the reset. With the core parked, `fromhost` takes it out.

### 6.5. Hardware guarantees

| Guarantee | FLASH loader | FLASH chip with caches |
| :--- | :--- | :--- |
| Write to the FLASH while the core runs | Impossible: the write enable of port B is the loader pulse combined with the halt state, and a write or read request outside the halt is refused and flagged in the status | Not prevented by the hardware, the parked-core protocol holds |
| Core executing the FLASH while it is written | No, the core is in reset | No, as long as it is in `rv32_wait_restart`, so the host must wait for the end of the previous test |
| Image checked before execution | Count and checksum read from the loader before the release, by the host | The BOOT_ROM checks the CRC-32 of each bank before the jump (section 6.6) |
| Cache lines of the previous program | The platform has no instruction cache, and the core reset restarts whatever caches exist | The `fence.i` of `_reset` drops them |
| State of the rest of the platform on a change | RAM and peripherals keep their content, and only the shared words are zeroed by `_reset` | The same |
| Effect of the reset button | Restarts the core through `_reset` with whatever FLASH is written. The button does not reset the loader, so a halt in progress continues | Restarts the core through `_reset` with whatever FLASH is written |

### 6.6. Choice of the bank on `de0-cv`

The BOOT_ROM reads the 256-byte header at the start of each bank, in the format of the `flash_image` module of Tools.

| Offset | Field | Content |
| ---: | :--- | :--- |
| 0 | Magic | `0x52564946` |
| 4 | Size | Bytes of the payload, a multiple of 4 and inside the bank |
| 8 | Payload CRC | CRC-32 (IEEE 802.3) of the payload |
| 12 | Version | The newest image has the larger version |
| 16 | Header CRC | CRC-32 of the first 16 bytes of the header |

A bank is valid when the magic matches, the header CRC matches, the size is a nonzero multiple of 4 that fits in the bank and the CRC-32 of the payload read from the FLASH matches. The choice follows three rules.

1. It jumps to the valid bank with the larger version, and bank A wins a tie.
2. A bank that is not valid is ignored, so an update that failed leaves the system on the other bank.
3. With no valid bank, the BOOT_ROM parks the core in `rv32_wait_restart`, where the host can write an image and write `fromhost` to start over.

The jump hands the firmware the state of section 2, with `a0` and `a1` at `0`, and the address is the start of the program of the bank, `base + 0x100`. The update writes the header last, so a bank interrupted in the middle of the write is never valid, and the CRC-32 of the payload also refuses a bank corrupted after it was written.

The check is a bitwise CRC-32, with no table and no stack, one 32-bit word at a time, with the 32 bit steps unrolled in sequence (the BOOT_ROM only fetches instructions, so there is no table to read). The BOOT_ROM executes about 166 instructions per word of the payload, with a single taken branch per word, which is about 0.11 s for a full 128 KiB bank at 50 MHz, and the whole code, together with `_reset` and `rv32_wait_restart`, is 940 bytes of instructions that end at address `0x480` of the 4 KiB. It uses only the registers of RV32E, and `sp`, `gp` and `tp` are scratch because the `_start` of the program sets them.

## 7. Restart by the test environment

`rv32_wait_restart`, fixed at `boot.wait_restart` (`0x100`), is the routine where a test program ends. It parks the core until the host has rewritten the FLASH and written `fromhost`, and then starts over at `_reset`. It belongs to the test environment, and a firmware that is not a test program does not reference it. The full protocol is in [atualizacao-de-programa.md](atualizacao-de-programa.md).

## 8. Platforms

The same state and register contract holds on every platform, and only the values that come from `platform.yaml` change. The choice of the bank of section 6.6 exists where `platform.yaml` declares `flash.banks`.

| Platform | `boot.entry` | Firmware region |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `0x1000` | FLASH, 252 KiB |
| [internal-mem](internal-mem.md) | `0x1000` | FLASH, 28 KiB |
| [modular](modular.md) | `0x1000` | According to the chosen memory model |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
