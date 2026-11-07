# DE10-Lite

This page describes the `de10-lite` platform, the Terasic DE10-Lite (MAX 10, 10M50DAF484C7G) with the full profile of the DE0-CV, and what was measured on it. The package of the board is in `boards/de10-lite/` and the platform in `src/max-10/de10-lite/`.

## 1. Profile and memory map

The device has 49,760 LEs and 182 M9K blocks (1,677,312 bits), enough for the `rv32im_zicclsm_zicntr_zihpm_zifencei` profile with the extras of the DE0-CV (Zimop, Zicond, Zihintntl, Zihintpause, interrupts and Sscofpmf).

| Region | Base | Size | Realization |
| :--- | :--- | ---: | :--- |
| `BOOT_MEMORY` | `0x00000000` | 4 KiB | M9K, inside the core |
| `FLASH` | `0x00001000` | 124 KiB | Emulated in M9K, behind the caches, with 24 cycles for the first word of a burst and 4 for the following ones |
| `RAM` | `0x40000000` | 64 MiB | SDRAM of the board, behind the caches |

The FLASH is 124 KiB because the block store takes the power of two that the address asks for (128 KiB with the `BOOT_MEMORY` in front). The banks of the program updater are A (`0x1000`, 60 KiB) and B (`0x10000`, 64 KiB). Each cache has 32 kbit. The core clock is 50 MHz and the SDRAM controller clock is 100 MHz. The board has no external FLASH, and the internal FLASH (UFM) is left to a separate backend.

## 2. Input and output roles

| Role | Use |
| :--- | :--- |
| `leds` | 10 LEDs, required |
| `switches` | 10 switches |
| `keys` | 2 buttons, and `KEY[0]` is also the reset |
| `display` | 6 seven-segment digits |
| Console | JTAG UART, no pin |

## 3. SDRAM

The chip is the ISSI IS42S16320D-7 (512 Mbit, 32M x 16), the same as the DE0-CV, in the catalog `Memory/chips/IS42S16320D-7.yaml`. The manual of the board does not name the chip, so the identification on this board is a hypothesis of the IS42S16320 family. The phase of `DRAM_CLK` is 7000 ps.

## 4. MAX 10 configuration

The Quartus only assembles the programming file of a MAX 10 with memories that have an initial content (the `BOOT_MEMORY` and the emulated FLASH) in the single-image mode with the configuration RAM. The `max-10` family asks for that mode in the `qsf` key of `boards/families/max-10.yaml`, and the generated project carries it. The fitter also refuses `SLEW_RATE` on 3.3-V LVTTL pins, which the `slew_rate: false` key of the family handles.

## 5. Fit

| Resource | Quartus fit | Capacity |
| :--- | ---: | ---: |
| Logic elements | 22,751 | 49,760 (46 %) |
| Memory bits | 1,155,328 | 1,677,312 (69 %) |
| RAM blocks estimated | 126 | 182 |
| PLLs | 1 | 4 |
| Pins | 104 | 360 |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
