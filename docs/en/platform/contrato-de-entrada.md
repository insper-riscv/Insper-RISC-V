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
| Program counter | `boot.entry` |
| Interrupts | Off, because the BOOT_ROM writes no CSR and the reset value of `mstatus`, `mie` and `mip` holds |
| CSRs | All at their reset value |
| Instruction cache | Free of lines from the previous program, through the `fence.i` executed before the jump |
| Shared words at the top of the RAM (`stdout`, `tohost` and `fromhost`) | Zeroed |
| Rest of the RAM | Undefined |
| `x0` | `0`, always |
| Other registers (`x1` to `x31`) | Undefined, including `sp`, `gp`, `tp`, `a0` and `a1` |

No entry register is defined, so the firmware receives neither the hart identifier nor a pointer to the platform description. The core has a single hart, and the description is obtained at build time (section 4).

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

`boot.entry` is the only value that the BOOT_ROM and the firmware linker both repeat. The BOOT_ROM reads it from `RV32_BOOT_ENTRY` and the linker receives it from `rv32im-fpga.specs`, both generated from the same `platform.yaml`, and `riscv-tools check-memory-map` checks that the hand-written copies match it.

## 6. Restart by the test environment

`rv32_wait_restart`, fixed at `boot.wait_restart` (`0x100`), is the routine where a test program ends. It parks the core until the host has rewritten the FLASH and written `fromhost`, and then starts over at `_reset`. It belongs to the test environment, and a firmware that is not a test program does not reference it. The full protocol is in [atualizacao-de-programa.md](atualizacao-de-programa.md).

## 7. Platforms

The same contract holds on the three platforms, and only the values that come from `platform.yaml` change.

| Platform | `boot.entry` | Firmware region |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `0x1000` | FLASH, 252 KiB |
| [internal-mem](internal-mem.md) | `0x1000` | FLASH, 28 KiB |
| [modular](modular.md) | `0x1000` | According to the chosen memory model |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
