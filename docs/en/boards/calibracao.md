# Fit calibration

## 1. What is measured

The calibration measures, per family, the logic cost of each block of the profile with the synthesis only (`quartus_map`), and the estimator of the Tools (`fit_estimate`) adds those costs to say whether a profile fits a board. The device is measured, not the board, and each family has its own unit (ALM on the Cyclone V; LE on the others).

| File | Contents |
| :--- | :--- |
| `boards/calibration/profiles/<family>.yaml` | List of the measured profiles, what changes in the `platform.yaml` and the generics of each |
| `boards/calibration/raw/<family>/<profile>.yaml` | Raw data of one synthesis, with seed, hash of the sources, Quartus version and commits of the project and the submodules |
| `boards/calibration/<family>.yaml` | Fitted table, with the recorded error and the residual of each profile |

## 2. Cyclone V (DE0-CV, 5CEBA4)

Calibrated core: commit `1057cbcc67ac3a82af4d314489e1eb840b84e12c` of the Core, with 24 profiles in the fit and 4 for validation. Tool: Quartus 25.1std.0 Build 1129 10/21/2025 SC Lite Edition. The F front changes the core, and the core term of the calibration (one profile per family) is redone after the F front gate.

The top of the DE0-CV is fixed: the SDRAM, the FLASH, the display, the JTAG UART and the FLASH controller exist in every profile and are inside the core term (`absorbed` in the table file). The terms of each peripheral and of the 16-bit SDRAM controller are zero for that reason. The `sdram_32`, `nor` and `sram` controllers have no measurement and stay `null`, which makes the estimator emit V18 when a profile asks for them. Each cache has the term $c_0 = -32\,c_1$, because the 32 kbit size is already in the core.

| Coefficient | ALMs |
| :--- | ---: |
| `core.rv32i` | 5134,00 |
| `core.rv32e` | 4796,00 |
| `extensions.M` | 260,00 |
| `extensions.Zicclsm` | 42,25 |
| `extensions.Zicntr` | 316,75 |
| `extensions.Zicond` | 8,07 |
| `extensions.Zicsr` | 213,00 |
| `extensions.Zifencei` | 114,00 |
| `extensions.Zimop` | 25,07 |
| `extensions.Zmmul` | 222,00 |
| `extras.Interrupts` | 230,07 |
| `extras.Sscofpmf` | 274,00 |
| `extras.Zihintntl` | -2,93 |
| `extras.Zihintpause` | -1,93 |
| `zihpm.a0` | -34,17 |
| `zihpm.a1` | -0,06 |
| `zihpm.a2` | 1,51 |
| `cache.icache.c0` | -5,95 |
| `cache.icache.c1` | 0,19 |
| `cache.dcache.c0` | -639,52 |
| `cache.dcache.c1` | 19,98 |

The data cache costs about 19,98 ALMs per kbit, against 0,19 for the instruction cache, because the byte array of the data cache is synthesized in registers.

## 3. Error and the GMC gate

| Measure | Value |
| :--- | ---: |
| Root mean square error in the fit | 0,29 % |
| Largest error in the fit | 0,94 % |
| Largest error in the validation profiles | 1,23 % |

The maximum validation error is below 10 %, so the Cyclone V enables the logic error (V12).

The synthesis estimate of the full profile is 9569 ALMs, against the range of 8058 to 8095 ALMs known after the fit, so the ratio fit over synthesis is 0.8421 to 0.846 (`map_to_fit_ratio` = 0.844). The estimator multiplies the sum by the ratio to compare it with the capacity of the fit. The ratio comes from a single point, measured on an earlier version of the core, and a Quartus fit of the full profile should confirm it.

## 4. Residuals by profile

| Profile | Measured | Predicted | Error (%) | Validation |
| :--- | ---: | ---: | ---: | :--- |
| `p1_rv32i` | 5134 | 5134,00 | 0,00 | no |
| `p1_rv32e` | 4796 | 4796,00 | 0,00 | no |
| `p2_rv32im` | 5616 | 5616,00 | 0,00 | no |
| `p2_rv32i_zmmul` | 5356 | 5356,00 | 0,00 | no |
| `p3_zicsr` | 5829 | 5829,00 | 0,00 | no |
| `p3_zicsr_zifencei` | 5943 | 5943,00 | 0,00 | no |
| `p3_zicntr_zifencei` | 6259 | 6259,70 | 0,01 | no |
| `p3_zicclsm_zicntr_zifencei` | 6302 | 6302,00 | 0,00 | no |
| `p4_hpm_4x40` | 6506 | 6508,70 | 0,04 | no |
| `p4_hpm_4x64` | 6655 | 6653,40 | -0,02 | no |
| `p4_hpm_29x40` | 8038 | 8014,10 | -0,30 | no |
| `p4_hpm_0x64` | 6314 | 6267,80 | -0,73 | no |
| `p4_hpm_8x32` | 6591 | 6653,10 | 0,94 | no |
| `p4_hpm_16x52` | 7614 | 7520,70 | -1,23 | yes |
| `p5_base` | 9058 | 9063,00 | 0,06 | no |
| `p5_full` | 9569 | 9595,40 | 0,28 | yes |
| `p6_zimop` | 9089 | 9088,10 | -0,01 | no |
| `p6_zicond` | 9072 | 9071,10 | -0,01 | no |
| `p6_zihintntl` | 9061 | 9060,10 | -0,01 | no |
| `p6_zihintpause` | 9062 | 9061,10 | -0,01 | no |
| `p6_interrupts` | 9294 | 9293,10 | -0,01 | no |
| `p6_interrupts_sscofpmf` | 9568 | 9567,10 | -0,01 | no |
| `p7_ic8` | 6225 | 6255,30 | 0,49 | no |
| `p7_ic128` | 6270 | 6277,60 | 0,12 | no |
| `p7_dc8` | 5811 | 5780,10 | -0,53 | no |
| `p7_dc128` | 8186 | 8178,30 | -0,09 | no |
| `p7_ic64` | 6264 | 6265,70 | 0,03 | yes |
| `p7_dc64` | 6917 | 6899,30 | -0,26 | yes |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
