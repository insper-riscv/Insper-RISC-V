# DE0-CV

## 1. Reference

The board package is in `boards/de0-cv/`. The format is in [formato.md](formato.md), the table of boards in [placas.md](placas.md) and the platform in [../platform/de0-cv.md](../platform/de0-cv.md). The name and pin of every `pins.yaml` signal were checked against tables 3-2 to 3-7 and 3-10 to 3-13 of the manual, and each carries its table and page.

## 2. Polarities

| Signal | Active level | Manual |
| :--- | :--- | :--- |
| `LEDR[9:0]` | High lights the LED | Section 3.2 |
| `SW[9:0]` | High with the switch up | Section 3.2 |
| `KEY[3:0]` and `FPGA_RESET_N` | Low when pressed | Section 3.2 |
| `HEX[5:0][6:0]` | Low lights the segment | Section 3.3 |

The manual calls the reset button `RESET_N` (table 3-2); the catalog calls it `FPGA_RESET_N`, on the same pin `P22`.

## 3. Expansion pins

The `gpio` role is bidirectional and numbers `GPIO_0` from 0 to 35 and `GPIO_1` from 36 to 71. Each 2x20 header has 36 I/O pins, plus 5 V, 3.3 V and two GND on pins 11, 12, 29 and 30.

| Role | Signals | Pins | Manual | Level |
| :--- | :--- | ---: | :--- | :--- |
| `gpio` | `GPIO_0[35:0]`, `GPIO_1[35:0]` | 72 | 3.5, table 3-7 | 3.3 V |
| `clock_extra` | `CLOCK2_50`, `CLOCK3_50`, `CLOCK4_50` | 3 | 3.4, table 3-6 | 3.3 V |

Only in `pins.yaml`, with no role: the PS/2 (`PS2_CLK`, `PS2_DAT`, `PS2_CLK2` and `PS2_DAT2`, section 3.7, table 3-11), the VGA (section 3.6, table 3-10), the SD card (section 3.8, table 3-12) and the `SPI_FLASH_*`, which exist only in the `.qsf` and coincide with `GPIO_0` pins.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
