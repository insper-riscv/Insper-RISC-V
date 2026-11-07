# Fit calibration

## 1. What is measured

The calibration measures, per family, the logic cost of each block of the profile with the synthesis alone (`quartus_map`), and the `fit_estimate` estimator of the Tools adds these costs to tell whether a profile fits a board. The device is measured, not the board, and each family has its own unit (ALM on the Cyclone V; LE on the others). The project the Quartus reads comes from `board generate`, and the compilation goes through the single `compile.tcl` of `program`, so the four families follow the same path and the same set of sources.

| File | Contents |
| :--- | :--- |
| `src/calibration/<placa>/platform.yaml` | Calibration platform of the measuring board and its memory map package |
| `boards/calibration/profiles/<family>.yaml` | List of the measured profiles, what changes in the `platform.yaml` and the generics of each one |
| `boards/calibration/raw/<family>/<profile>.yaml` | Raw data of one synthesis, with seed, source hash, Quartus version and commits of the project and of the submodules |
| `boards/calibration/<family>.yaml` | Fitted table, with the recorded error and the residual of each profile |
| `boards/calibration/profiles/verify-<board>.yaml` | Profiles measured on another device of the family, for the cross verification |
| `boards/calibration/verification/<board>.yaml` | Comparison of the family table with those profiles |
| `boards/calibration/cyclone-v-manual.yaml` and `raw/cyclone-v-manual/` | Measurements of the hand-written DE0-CV top, with the known point of 8058 to 8095 ALMs |

## 2. Calibration platform

Each family is measured on its reference board with the same calibration platform, which changes the profile, the extras, the caches and the Zihpm generics at each measurement. The platform has the 4 KiB BOOT_MEMORY, the emulated FLASH (28 KiB, or 12 KiB on the Vidor) with loader and JTAG, the console through the JTAG UART, the display and the FLASH controller. These blocks exist in every profile and stay inside the core term, so the term of each peripheral is zero (`absorbed` in the table). Some coefficients of small extensions come out negative (for example `extensions.Zimop` on the Cyclone IV E and `extras.Sscofpmf` on the Cyclone 10 LP), because the synthesis reorganizes the logic when the extension turns on and the profile with it comes out smaller than the base. The coefficient keeps the measured difference, and the estimator adds it with the sign it has. The RAM is what changes from one board to the other, and on the Vidor the memories stay inside the 504 kbit of the 10CL016, because above that the synthesis converts the RAM into logic and the cost of the 64 and 128 kbit caches stops being the cost of the cache.

| Family | Measuring board | Device | Unit | Platform RAM |
| :--- | :--- | :--- | :--- | :--- |
| Cyclone V | DE0-CV | 5CEBA4 | ALM | 16-bit SDRAM, with the controller inside the core term |
| Cyclone IV E | DE2-115 | EP4CE115 | LE | emulated in 64 KiB blocks, because the SDRAM is 32 bits wide and the Memory has no controller of that width |
| MAX 10 | DE10-Lite | 10M50DA | LE | 16-bit SDRAM, with the controller inside the core term |
| Cyclone 10 LP | MKR Vidor 4000 | 10CL016 | LE | emulated in 8 KiB blocks, because the SDRAM controller of the Memory has a 13-bit row address and the board SDRAM has 12 |

The terms `backends.sdram_32`, `backends.nor` and `backends.sram` have no measurement and stay `null`, which makes the estimator emit V18 when a profile asks for them. The term `backends.sdram_16` is zero in the families whose platform has the SDRAM and is 1449 LEs on the Cyclone IV E, the difference measured on the DE0-Nano (cross verification section). Each cache has the term $c_0 = -32\,c_1$, because the 32 kbit size is already in the core.

Each calibration platform lives in `src/calibration/<board>/` with its generated memory map package, and its `top` field names the `cal_<board>_board` component of `paths.yaml`, whose closure of `requires` is the list of sources of the project that `board generate` writes.

The Quartus is 25.1std.0 Build 1129 Lite Edition, the seed is 5 and the core is commit `1057cbcc67ac3a82af4d314489e1eb840b84e12c` of the Core. The F front changes the core, and the core term (one profile per family, `p1_rv32i`) is redone after its gate.

## 3. Cyclone V (DE0-CV, 5CEBA4)

| Coefficient | ALMs |
| :--- | ---: |
| `cache.dcache.c0` | -202.27 |
| `cache.dcache.c1` | 6.32 |
| `cache.icache.c0` | -0.16 |
| `cache.icache.c1` | 0.01 |
| `core.rv32e` | 3,756.00 |
| `core.rv32i` | 4,122.00 |
| `extensions.M` | 153.00 |
| `extensions.Zicclsm` | 114.70 |
| `extensions.Zicntr` | 314.30 |
| `extensions.Zicond` | 6.60 |
| `extensions.Zicsr` | 175.00 |
| `extensions.Zifencei` | 1.00 |
| `extensions.Zimop` | -4.40 |
| `extensions.Zmmul` | 161.00 |
| `extras.Interrupts` | 236.60 |
| `extras.Sscofpmf` | 108.00 |
| `extras.Zihintntl` | -2.40 |
| `extras.Zihintpause` | -1.40 |
| `zihpm.a0` | -15.62 |
| `zihpm.a1` | -9.95 |
| `zihpm.a2` | 1.67 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.18 % |
| Largest error of the fit | 0.68 % |
| Largest error of the validation profiles | 0.27 % |
| Fit over synthesis ratio | 0.9693 |

Residuals of the validation profiles (the other 24 profiles are in `boards/calibration/cyclone-v.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 6,275 | 6,258.1 | -0.27 |
| `p5_full` | 8,199 | 8,185.0 | -0.17 |
| `p7_ic64` | 4,927 | 4,926.5 | -0.01 |
| `p7_dc64` | 5,129 | 5,128.6 | -0.01 |

## 4. Cyclone IV E (DE2-115, EP4CE115)

| Coefficient | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -719.04 |
| `cache.dcache.c1` | 22.47 |
| `cache.icache.c0` | -19.04 |
| `cache.icache.c1` | 0.59 |
| `core.rv32e` | 7,495.00 |
| `core.rv32i` | 8,819.00 |
| `extensions.M` | 346.00 |
| `extensions.Zicclsm` | 123.52 |
| `extensions.Zicntr` | 670.48 |
| `extensions.Zicond` | 5.50 |
| `extensions.Zicsr` | 570.00 |
| `extensions.Zifencei` | 274.00 |
| `extensions.Zimop` | -499.50 |
| `extensions.Zmmul` | 596.00 |
| `extras.Interrupts` | 751.50 |
| `extras.Sscofpmf` | 572.00 |
| `extras.Zihintntl` | -22.50 |
| `extras.Zihintpause` | -12.50 |
| `zihpm.a0` | 31.79 |
| `zihpm.a1` | -45.04 |
| `zihpm.a2` | 4.19 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.35 % |
| Largest error of the fit | 1.39 % |
| Largest error of the validation profiles | 2.62 % |
| Fit over synthesis ratio | 0.8449 |

Residuals of the validation profiles (the other 24 profiles are in `boards/calibration/cyclone-iv-e.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 14,261 | 14,193.7 | -0.47 |
| `p5_full` | 19,193 | 18,690.2 | -2.62 |
| `p7_ic64` | 11,228 | 11,294.5 | 0.59 |
| `p7_dc64` | 12,058 | 11,994.5 | -0.53 |

## 5. MAX 10 (DE10-Lite, 10M50DA)

| Coefficient | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -724.61 |
| `cache.dcache.c1` | 22.64 |
| `cache.icache.c0` | -3.74 |
| `cache.icache.c1` | 0.12 |
| `core.rv32e` | 9,138.00 |
| `core.rv32i` | 10,404.00 |
| `extensions.M` | 387.00 |
| `extensions.Zicclsm` | 245.55 |
| `extensions.Zicntr` | 660.45 |
| `extensions.Zicond` | 57.78 |
| `extensions.Zicsr` | 408.00 |
| `extensions.Zifencei` | 331.00 |
| `extensions.Zimop` | -4.21 |
| `extensions.Zmmul` | 541.00 |
| `extras.Interrupts` | 624.78 |
| `extras.Sscofpmf` | 482.00 |
| `extras.Zihintntl` | -4.21 |
| `extras.Zihintpause` | -6.21 |
| `zihpm.a0` | -17.73 |
| `zihpm.a1` | -23.86 |
| `zihpm.a2` | 3.37 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.14 % |
| Largest error of the fit | 0.60 % |
| Largest error of the validation profiles | 0.63 % |
| Fit over synthesis ratio | 0.8800 |

Residuals of the validation profiles (the other 24 profiles are in `boards/calibration/max-10.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 15,423 | 15,378.1 | -0.29 |
| `p5_full` | 19,662 | 19,664.6 | 0.01 |
| `p7_ic64` | 12,771 | 12,735.2 | -0.28 |
| `p7_dc64` | 13,541 | 13,456.1 | -0.63 |

## 6. Cyclone 10 LP (MKR Vidor 4000, 10CL016)

| Coefficient | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -747.97 |
| `cache.dcache.c1` | 23.37 |
| `cache.icache.c0` | -0.51 |
| `cache.icache.c1` | 0.02 |
| `core.rv32e` | 7,261.00 |
| `core.rv32i` | 8,540.00 |
| `extensions.M` | 386.00 |
| `extensions.Zicclsm` | 327.22 |
| `extensions.Zicntr` | 636.78 |
| `extensions.Zicond` | 193.94 |
| `extensions.Zicsr` | 556.00 |
| `extensions.Zifencei` | 244.00 |
| `extensions.Zimop` | 204.94 |
| `extensions.Zmmul` | 606.00 |
| `extras.Interrupts` | 704.94 |
| `extras.Sscofpmf` | -612.00 |
| `extras.Zihintntl` | 5.94 |
| `extras.Zihintpause` | -206.06 |
| `zihpm.a0` | 54.69 |
| `zihpm.a1` | -81.94 |
| `zihpm.a2` | 4.66 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.35 % |
| Largest error of the fit | 1.14 % |
| Largest error of the validation profiles | 0.95 % |
| Fit over synthesis ratio | 0.8356 |

Residuals of the validation profiles (the other 24 profiles are in `boards/calibration/cyclone-10-lp.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 14,008 | 13,918.5 | -0.64 |
| `p5_full` | 17,750 | 17,918.9 | 0.95 |
| `p7_ic64` | 10,962 | 10,969.3 | 0.07 |
| `p7_dc64` | 11,748 | 11,716.7 | -0.27 |

## 7. Fit over synthesis ratio

The estimator adds the terms of the table, which are `quartus_map` estimates, and multiplies the sum by the `map_to_fit_ratio` ratio to reach the logic the fitter (`quartus_fit`) uses. The ratio of each family is the mean of `fit_result.logic` over `result.logic` of a few profiles run up to the fitter (`calibrate run --stop-after fit`), and the fitter packs the logic better in the larger profiles, so the ratio grows with the profile. The last two columns show the error of the table sum times the ratio against the fitter logic, which stays below 10 % in every profile that ran.

| Family | Profile | Synthesis | Fit | Fit over synthesis | Table times ratio | Error (%) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| Cyclone V | `p1_rv32i` | 4,122 | 3,845 | 0.9328 | 3,995 | 3.9 |
| Cyclone V | `p3_zicntr_zifencei` | 4,926 | 4,832 | 0.9809 | 4,775 | -1.2 |
| Cyclone V | `p5_base` | 7,837 | 7,647 | 0.9758 | 7,601 | -0.6 |
| Cyclone V | `p5_full` | 8,199 | 8,100 | 0.9879 | 7,934 | -2.1 |
| Cyclone IV E | `p1_rv32i` | 8,819 | 7,191 | 0.8154 | 7,451 | 3.6 |
| Cyclone IV E | `p3_zicntr_zifencei` | 11,311 | 9,616 | 0.8501 | 9,527 | -0.9 |
| Cyclone IV E | `p5_base` | 17,869 | 15,290 | 0.8557 | 15,120 | -1.1 |
| Cyclone IV E | `p5_full` | 19,193 | 16,474 | 0.8583 | 15,791 | -4.1 |
| MAX 10 | `p1_rv32i` | 10,404 | 8,709 | 0.8371 | 9,156 | 5.1 |
| MAX 10 | `p3_zicntr_zifencei` | 12,726 | 11,055 | 0.8687 | 11,204 | 1.3 |
| MAX 10 | `p5_base` | 18,502 | 16,760 | 0.9058 | 16,293 | -2.8 |
| MAX 10 | `p5_full` | 19,662 | 17,865 | 0.9086 | 17,305 | -3.1 |
| Cyclone 10 LP | `p1_rv32i` | 8,540 | 6,882 | 0.8059 | 7,136 | 3.7 |
| Cyclone 10 LP | `p2_rv32im` | 9,532 | 7,965 | 0.8356 | 7,965 | -0.0 |
| Cyclone 10 LP | `p3_zicntr_zifencei` | 10,959 | 9,281 | 0.8469 | 9,166 | -1.2 |
| Cyclone 10 LP | `p4_hpm_4x40` | 11,903 | 10,164 | 0.8539 | 9,834 | -3.2 |

| Family | Ratio used | Lowest | Highest |
| :--- | ---: | ---: | ---: |
| Cyclone V | 0.9693 | 0.9328 | 0.9879 |
| Cyclone IV E | 0.8449 | 0.8154 | 0.8583 |
| MAX 10 | 0.8800 | 0.8371 | 0.9086 |
| Cyclone 10 LP | 0.8356 | 0.8059 | 0.8539 |

The full Cyclone V profile (`p5_full`) gives 8100 ALMs in the fit, 5 ALMs from the limit of the 8058 to 8095 ALM range that `core-novo.md` records for the hand-written top. On the Vidor the fitted profiles go up to `p4_hpm_4x40`, because the larger profiles exceed the 15408 LEs of the 10CL016.

## 8. Cross verification

The verification measures 14 profiles on another device of the same family and compares them with the table, using `riscv-tools calibrate verify`. The top of each board differs from the top of the measuring board (the DE10-Nano and the DE2-115 have emulated RAM, the DE0-Nano has the 16-bit SDRAM), so the comparison has two columns. The first uses the table as it is. The second moves the core term by the difference measured on profile `p1_rv32i`, so the part of the top that changes leaves the account and the increments of the extensions and the caches remain, which is what the table must get right on another device.

| Board | Family | Device | Core shift | Largest error | Largest shifted error | Shifted root mean square error |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| DE10-Nano | Cyclone V | 5CSEBA6 | -628 | 20.39 % | 4.04 % | 3.13 % |
| DE0-Nano | Cyclone IV E | EP4CE22 | 1,449 | 16.69 % | 5.52 % | 2.35 % |

The DE10-Nano shift (-628 ALMs) is what the DE0-CV top carries in addition, with the 16-bit SDRAM controller, and the DE0-Nano shift (+1449 LEs) is the cost of that controller on the Cyclone IV E, which the DE2-115 does not have. Both tables hold on another device of the family with an error below 10 % after the core term shift, which is the term that one profile per family redoes.

### DE10-Nano

| Profile | Measured | Predicted | Error (%) | Shifted prediction | Shifted error (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 3,494 | 4,122.0 | 17.97 | 3,494.0 | 0.00 |
| `p1_rv32e` | 3,120 | 3,756.0 | 20.39 | 3,128.0 | 0.26 |
| `p2_rv32im` | 3,909 | 4,436.0 | 13.48 | 3,808.0 | -2.58 |
| `p3_zicntr_zifencei` | 4,464 | 4,926.3 | 10.36 | 4,298.3 | -3.71 |
| `p3_zicclsm_zicntr_zifencei` | 4,588 | 5,041.0 | 9.87 | 4,413.0 | -3.81 |
| `p4_hpm_4x40` | 4,790 | 5,253.3 | 9.67 | 4,625.3 | -3.44 |
| `p4_hpm_16x52` | 5,851 | 6,258.1 | 6.96 | 5,630.1 | -3.77 |
| `p5_base` | 7,420 | 7,842.0 | 5.69 | 7,214.0 | -2.78 |
| `p5_full` | 7,643 | 8,185.0 | 7.09 | 7,557.0 | -1.13 |
| `p6_interrupts` | 7,392 | 8,078.6 | 9.29 | 7,450.6 | 0.79 |
| `p7_ic8` | 4,464 | 4,926.2 | 10.35 | 4,298.2 | -3.71 |
| `p7_dc8` | 4,302 | 4,774.6 | 10.98 | 4,146.6 | -3.61 |
| `p7_ic64` | 4,464 | 4,926.5 | 10.36 | 4,298.5 | -3.71 |
| `p7_dc64` | 4,690 | 5,128.6 | 9.35 | 4,500.6 | -4.04 |

### DE0-Nano

| Profile | Measured | Predicted | Error (%) | Shifted prediction | Shifted error (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 10,268 | 8,819.0 | -14.11 | 10,268.0 | 0.00 |
| `p1_rv32e` | 8,997 | 7,495.0 | -16.69 | 8,944.0 | -0.59 |
| `p2_rv32im` | 11,249 | 9,761.0 | -13.23 | 11,210.0 | -0.35 |
| `p3_zicntr_zifencei` | 12,623 | 11,275.5 | -10.68 | 12,724.5 | 0.80 |
| `p3_zicclsm_zicntr_zifencei` | 12,873 | 11,399.0 | -11.45 | 12,848.0 | -0.19 |
| `p4_hpm_4x40` | 13,314 | 11,920.5 | -10.47 | 13,369.5 | 0.42 |
| `p4_hpm_16x52` | 15,320 | 14,193.7 | -7.35 | 15,642.7 | 2.11 |
| `p5_base` | 18,422 | 17,895.7 | -2.86 | 19,344.7 | 5.01 |
| `p5_full` | 19,585 | 18,690.2 | -4.57 | 20,139.2 | 2.83 |
| `p6_interrupts` | 19,045 | 18,647.2 | -2.09 | 20,096.2 | 5.52 |
| `p7_ic8` | 12,616 | 11,261.2 | -10.74 | 12,710.2 | 0.75 |
| `p7_dc8` | 12,089 | 10,736.2 | -11.19 | 12,185.2 | 0.80 |
| `p7_ic64` | 12,627 | 11,294.5 | -10.55 | 12,743.5 | 0.92 |
| `p7_dc64` | 13,357 | 11,994.5 | -10.20 | 13,443.5 | 0.65 |

## 9. GMC gate

The gate asks for one table per family with the raw data versioned, the recorded error and a maximum validation error up to 10 %. A family above 10 % does not enable the logic error (V12) and stays in warning (V18).

| Family | Measured profiles | Root mean square error | Largest validation error | Fit over synthesis ratio | Logic error enabled |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Cyclone V | 28 | 0.18 % | 0.27 % | 0.9693 | yes |
| Cyclone IV E | 28 | 0.35 % | 2.62 % | 0.8449 | yes |
| MAX 10 | 28 | 0.14 % | 0.63 % | 0.8800 | yes |
| Cyclone 10 LP | 28 | 0.35 % | 0.95 % | 0.8356 | yes |

## 10. How to redo it

Each family runs in the Tools, under the `flock` of the machine with the Quartus, and the table comes from the fit of the records. The profiles of one family run in sequence, and the Cyclone V runs on the laptop or on PC1, while the other families run only on PC1.

```bash
flock /tmp/quartus-<machine>.lock riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --lock <own-file>
riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --stop-after fit --only p1_rv32i,p3_zicntr_zifencei,p5_base,p5_full
riscv-tools --root <Insper-RISC-V> calibrate fit --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --table boards/calibration/max-10.yaml
riscv-tools --root <Insper-RISC-V> calibrate verify --profiles boards/calibration/profiles/verify-de0-nano.yaml --raw boards/calibration/raw/verify-de0-nano --table boards/calibration/cyclone-iv-e.yaml --output boards/calibration/verification/de0-nano.yaml
```

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
