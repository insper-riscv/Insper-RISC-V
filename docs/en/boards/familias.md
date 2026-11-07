# Device families

## 1. Purpose

The `boards/families/<family>.yaml` file keeps what holds for every device of a family, so the `board.yaml` of each board cites only the family and the device. The Tools reads the files with the `board_schema` module and checks them with the `check-boards` command.

## 2. Fields

| Field | Meaning |
| :--- | :--- |
| `family` | Identifier, equal to the file name |
| `quartus_family` | Name of the family in Quartus |
| `logic_unit` | `alm` or `le` |
| `pll` | `ip` (`altera_pll` or `altpll`), `vco_mhz` (lowest and highest oscillator frequency), `clock_node_pattern` (name of the internal PLL nodes) and `outputs_max` |
| `block_ram` | Kind and bits of a memory block |
| `memory_ip` | IP that infers the memories |
| `virtual_jtag` | Whether the family has the Virtual JTAG node |
| `onchip_flash` | IP of the internal FLASH, or `null` |
| `fmax.core_mhz_by_grade` | Core frequency measured for each grade, `null` without a measure |
| `calibration` | Calibration file of the estimator, relative to `boards/`, or `null` |
| `slew_rate` | Whether the fitter accepts `SLEW_RATE` on 3.3-V LVTTL pins; absent means `true`, and `cyclone-iv-e`, `max-10` and `cyclone-10-lp` refuse it (`false`) |
| `qsf` | Lines that the `.qsf` of every project of the family gets, or absent; the `max-10` asks for the configuration mode of the memories with an initial content |

## 3. Families

| Family | Logic | PLL | RAM block | Internal FLASH |
| :--- | :--- | :--- | :--- | :--- |
| `cyclone-v` | ALM | `altera_pll`, 18 outputs | M10K of 10240 bits | no |
| `cyclone-v-soc` | ALM | `altera_pll`, 18 outputs | M10K of 10240 bits | no |
| `cyclone-iv-e` | LE | `altpll`, 5 outputs | M9K of 9216 bits | no |
| `max-10` | LE | `altpll`, 5 outputs | M9K of 9216 bits | `altera_onchip_flash` |
| `cyclone-10-lp` | LE | `altpll`, 5 outputs | M9K of 9216 bits | no |

The only measured Fmax is the `cyclone-v` one in grade `C7`. Each family has its calibration table in `calibration/<family>.yaml`, described in [calibracao.md](calibracao.md), and the validator warns when it is missing (rule V18).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
