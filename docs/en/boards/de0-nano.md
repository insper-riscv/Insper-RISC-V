# DE0-Nano

This page describes the `de0-nano` platform, the Terasic DE0-Nano (Cyclone IV E, EP4CE22F17C6) with the reduced profile, and what was measured on it. The package of the board is in `boards/de0-nano/` and the platform in `src/cyclone-iv-e/de0-nano/`.

## 1. Profile and memory map

The device has 22,320 LEs and 608 kbit of M9K. The full profile of the DE0-CV does not fit, so the platform turns on only RV32I with the Zicsr and Zifencei extensions, with no counters, multiplier or interrupts. The Zifencei is there because the boot memory executes `fence.i` at every reset, and without it the core takes the instruction as illegal and traps back to the reset forever.

| Region | Base | Size | Realization |
| :--- | :--- | ---: | :--- |
| `BOOT_MEMORY` | `0x00000000` | 4 KiB | M9K, inside the core |
| `FLASH` | `0x00001000` | 28 KiB | Emulated in M9K, behind the caches, with 24 cycles for the first word of a burst and 4 for the following ones |
| `RAM` | `0x40000000` | 32 MiB | SDRAM of the board, behind the caches |

The FLASH is 28 KiB because the block store takes the power of two that the address asks for (32 KiB with the `BOOT_MEMORY` in front), and the next one, 64 KiB, would take more than 85 % of the blocks. The banks of the program updater are A (`0x1000`, 12 KiB) and B (`0x4000`, 16 KiB). The instruction and data caches have 8 kbit each. The core clock is 50 MHz and the SDRAM controller clock is 100 MHz.

## 2. What the board offers and what the platform leaves out

| Role | Use |
| :--- | :--- |
| `leds` | 8 LEDs, required |
| `switches` and `keys` | Left out of the platform |
| `display` | The board has none |
| Console | JTAG UART, no pin |
| Reset | `KEY[0]` |

The polarity of `KEY[0]` (active low) is inferred from the Terasic button convention. Check in the board schematic that the button has a pull-up and closes to ground before relying on the reset.

The four `DIP` switches and `KEY[1]` sit on pins that the Quartus accepts only as inputs, and the GPIO cell of the SoC is bidirectional (error 169009 in the fit). The platform therefore does not ask for the `switches` and `keys` roles.

## 3. SDRAM

The chip is the ISSI IS42S16160B-7 (256 Mbit, 16M x 16, 143 MHz, CL3), in the catalog `Memory/chips/IS42S16160B-7.yaml`. The timings are those of the `-7` column of the ISSI datasheet (tRCD and tRP of 20 ns, tRAS of 45 ns, tRC of 67.5 ns, tDPL of 14 ns). The manual of the board does not name the chip, and the name comes from a third-party VHDL port, so the identification remains inferred. The organization (13 row bits, 9 column bits, 4 banks) gives the 32 MiB, and the controller is the one of the DE0-CV with these values in its generics.

The phase of `DRAM_CLK` is 7000 ps (the -3 ns shift of the Terasic demonstration for 100 MHz), and the memory tests on the board passed with it.

## 4. Fit

The estimator runs in `board generate` and in `check-memory-map` and writes `capacity.json` in the project.

| Resource | Estimated | Quartus fit | Capacity |
| :--- | ---: | ---: | ---: |
| Logic elements | 7,465 | 8,992 | 22,320 |
| RAM blocks | 35 | 316,096 bits | 66 blocks, 608,256 bits |
| PLLs | 1 | 1 | 4 |
| Pins | | 49 | 154 |

The estimate is 17 % below the fit, because the fit over synthesis ratio of the Cyclone IV E table is inverted for the LE unit. The full profile of the DE0-CV on this board is refused with error V11: it needs 240 RAM blocks, and the board has 66.

## 5. Timing

The core runs 8250 ps behind the fetch clock, as on the DE2-115 and on the DE0-CV, because the instruction memories read on the fetch clock one cycle ahead of the core, and without the phase the core skips instructions. With seed 5 and the core at 50 MHz, the smallest setup slack is 1.09 ns (85 C, fetch clock) and the smallest hold slack is 0.17 ns, both positive.

## 6. On the board

The bitstream comes out of `program` with the boot memory embedded, and `board_run.py --stages de0-nano-regression de0-nano-sdram` runs the programs of Tests that the profile can run (those whose `RV32_EXT` header has only Zicsr and Zifencei).

| Stage | Programs | Result |
| :--- | ---: | :--- |
| `de0-nano-regression` | 71 | 71 pass |
| `de0-nano-sdram` | 7 | 7 pass |

Left out are `code-sweep` (17 KiB, more than the 12 KiB bank A), `flash-const` (it asks for the access fault, an extra that the platform does not turn on), `monitor` and `hex-id` (they need a person), and the three UART-on-pins programs (the board has no UART). The address bus test of `sdram-memtest` stops before the end of the 32 MiB RAM, and the SDRAM test window is 8 MiB, from 8 MiB above the base.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
