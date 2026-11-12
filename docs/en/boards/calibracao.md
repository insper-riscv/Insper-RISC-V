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
| `boards/calibration/profiles/sdram-cost-max-10.yaml` | Profiles of the cost of the 16-bit SDRAM controller, on the `src/calibration/de10-lite-emulated` platform |
| `boards/calibration/verification/<board>.yaml` | Comparison of the family table with those profiles |
| `boards/calibration/cyclone-v-manual.yaml` and `raw/cyclone-v-manual/` | Measurements of the hand-written DE0-CV top, with the known point of 8058 to 8095 ALMs |

## 2. Calibration platform

Each family is measured on its reference board with the same calibration platform, which changes the profile, the extras, the caches and the Zihpm generics at each measurement. The platform has the 4 KiB BOOT_MEMORY, the emulated FLASH (28 KiB, or 12 KiB on the Vidor) with loader and JTAG, the console through the JTAG UART, the display and the FLASH controller. These blocks exist in every profile and stay inside the core term, so the term of each peripheral is zero (`absorbed` in the table). Some coefficients of small extensions come out negative (for example `extensions.Zimop` on the Cyclone IV E and `extras.Sscofpmf` on the Cyclone 10 LP), because the synthesis reorganizes the logic when the extension turns on and the profile with it comes out smaller than the base. The coefficient keeps the measured difference, and the estimator adds it with the sign it has. The RAM is what changes from one board to the other, and on the Vidor the memories stay inside the 504 kbit of the 10CL016, because above that the synthesis converts the RAM into logic and the cost of the 64 and 128 kbit caches stops being the cost of the cache.

| Family | Measuring board | Device | Unit | Platform RAM |
| :--- | :--- | :--- | :--- | :--- |
| Cyclone V | DE0-CV | 5CEBA4 | ALM | 16-bit SDRAM, with the controller inside the core term |
| Cyclone IV E | DE2-115 | EP4CE115 | LE | emulated in 64 KiB blocks, so the top is the same as the DE0-Nano and the Vidor |
| MAX 10 | DE10-Lite | 10M50DA | LE | 16-bit SDRAM, with the controller inside the core term |
| Cyclone 10 LP | MKR Vidor 4000 | 10CL016 | LE | emulated in 8 KiB blocks, because the SDRAM controller of the Memory has a 13-bit row address and the board SDRAM has 12 |

The terms `backends.sdram_32`, `backends.nor` and `backends.sram` have no measurement and stay `null`, which makes the estimator emit V18 when a profile asks for them. The term `backends.sdram_16` is zero in the families whose platform has the SDRAM and stays `null` in the others. Each cache has the term $c_0 = -32\,c_1$, because the 32 kbit size is already in the core.

Each calibration platform lives in `src/calibration/<board>/` with its generated memory map package, and its `top` field names the `cal_<board>_board` component of `paths.yaml`, whose closure of `requires` is the list of sources of the project that `board generate` writes.

The Quartus is 25.1std.0 Build 1129 Lite Edition, the seed is 5 and the core is commit `451f5fcceb4bd2aef6cf4f9046a59d30961d40a0` of the Core. The 128 kbit data cache (`p7_dc128`) is measured and left out of the fit and of the errors (`outside`), because the synthesis turns it into registers and the cost stops being linear: the tables hold up to 64 kbit of data cache.

## 3. Cyclone V (DE0-CV, 5CEBA4)

| Coefficient | ALMs |
| :--- | ---: |
| `cache.dcache.c0` | -351.46 |
| `cache.dcache.c1` | 10.98 |
| `cache.icache.c0` | -4.10 |
| `cache.icache.c1` | 0.13 |
| `core.rv32e` | 3,965.00 |
| `core.rv32i` | 4,343.00 |
| `extensions.M` | 148.00 |
| `extensions.Zicclsm` | 84.41 |
| `extensions.Zicntr` | 304.60 |
| `extensions.Zicond` | 5.00 |
| `extensions.Zicsr` | 166.00 |
| `extensions.Zifencei` | 137.00 |
| `extensions.Zimop` | 87.00 |
| `extensions.Zmmul` | 166.00 |
| `extras.Interrupts` | 104.00 |
| `extras.Sscofpmf` | 236.00 |
| `extras.Zihintntl` | 1.00 |
| `extras.Zihintpause` | -1.00 |
| `zihpm.a0` | -11.76 |
| `zihpm.a1` | -10.58 |
| `zihpm.a2` | 1.70 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.18 % |
| Largest error of the fit | 0.73 % |
| Largest error of the validation profiles | 0.97 % |
| Fit over synthesis ratio | 0.9642 |

Residuals of the validation profiles (the other profiles are in `boards/calibration/cyclone-v.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 6,597 | 6,579.9 | -0.26 |
| `p5_full` | 8,532 | 8,612.2 | 0.94 |
| `p7_ic64` | 5,273 | 5,268.7 | -0.08 |
| `p7_dc64` | 5,671 | 5,616.1 | -0.97 |

## 4. Cyclone IV E (DE2-115, EP4CE115)

| Coefficient | LEs |
| :--- | ---: |
| `backends.sdram_16` | 1,185.30 |
| `cache.dcache.c0` | -860.00 |
| `cache.dcache.c1` | 26.88 |
| `cache.icache.c0` | -5.34 |
| `cache.icache.c1` | 0.17 |
| `core.rv32e` | 8,401.00 |
| `core.rv32i` | 9,726.00 |
| `extensions.M` | 386.00 |
| `extensions.Zicclsm` | 306.00 |
| `extensions.Zicntr` | 711.00 |
| `extensions.Zicond` | -80.25 |
| `extensions.Zicsr` | 610.00 |
| `extensions.Zifencei` | 199.00 |
| `extensions.Zimop` | -66.25 |
| `extensions.Zmmul` | 434.00 |
| `extras.Interrupts` | 352.75 |
| `extras.Sscofpmf` | 601.00 |
| `extras.Zihintntl` | -60.26 |
| `extras.Zihintpause` | -94.25 |
| `zihpm.a0` | -29.18 |
| `zihpm.a1` | -57.06 |
| `zihpm.a2` | 4.50 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.38 % |
| Largest error of the fit | 1.10 % |
| Largest error of the validation profiles | 3.39 % |
| Fit over synthesis ratio | 0.8418 |

Residuals of the validation profiles (the other profiles are in `boards/calibration/cyclone-iv-e.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 15,192 | 15,170.6 | -0.14 |
| `p5_full` | 20,015 | 19,685.5 | -1.65 |
| `p7_ic64` | 12,094 | 12,071.3 | -0.19 |
| `p7_dc64` | 13,379 | 12,926.0 | -3.39 |

## 5. MAX 10 (DE10-Lite, 10M50DA)

| Coefficient | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -884.22 |
| `cache.dcache.c1` | 27.63 |
| `cache.icache.c0` | -14.02 |
| `cache.icache.c1` | 0.44 |
| `core.rv32e` | 9,929.00 |
| `core.rv32i` | 11,194.00 |
| `extensions.M` | 383.00 |
| `extensions.Zicclsm` | 415.83 |
| `extensions.Zicntr` | 674.17 |
| `extensions.Zicond` | 34.76 |
| `extensions.Zicsr` | 573.00 |
| `extensions.Zifencei` | -87.00 |
| `extensions.Zimop` | -11.24 |
| `extensions.Zmmul` | 639.00 |
| `extras.Interrupts` | 498.76 |
| `extras.Sscofpmf` | 414.00 |
| `extras.Zihintntl` | -14.24 |
| `extras.Zihintpause` | -32.24 |
| `zihpm.a0` | 62.33 |
| `zihpm.a1` | -30.06 |
| `zihpm.a2` | 3.37 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.31 % |
| Largest error of the fit | 0.96 % |
| Largest error of the validation profiles | 2.80 % |
| Fit over synthesis ratio | 0.8797 |

Residuals of the validation profiles (the other profiles are in `boards/calibration/max-10.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 16,213 | 16,175.5 | -0.23 |
| `p5_full` | 20,262 | 20,123.4 | -0.68 |
| `p7_ic64` | 13,422 | 13,390.2 | -0.24 |
| `p7_dc64` | 14,671 | 14,260.4 | -2.80 |

## 6. Cyclone 10 LP (MKR Vidor 4000, 10CL016)

| Coefficient | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -820.26 |
| `cache.dcache.c1` | 25.63 |
| `cache.icache.c0` | -5.54 |
| `cache.icache.c1` | 0.17 |
| `core.rv32e` | 8,032.00 |
| `core.rv32i` | 9,296.00 |
| `extensions.M` | 375.00 |
| `extensions.Zicclsm` | 256.81 |
| `extensions.Zicntr` | 736.19 |
| `extensions.Zicond` | -25.52 |
| `extensions.Zicsr` | 478.00 |
| `extensions.Zifencei` | 185.00 |
| `extensions.Zimop` | -58.52 |
| `extensions.Zmmul` | 635.00 |
| `extras.Interrupts` | -833.52 |
| `extras.Sscofpmf` | 535.00 |
| `extras.Zihintntl` | -66.52 |
| `extras.Zihintpause` | -13.52 |
| `zihpm.a0` | 67.76 |
| `zihpm.a1` | -49.81 |
| `zihpm.a2` | 4.25 |

| Measure | Value |
| :--- | ---: |
| Root mean square error of the fit | 0.20 % |
| Largest error of the fit | 0.81 % |
| Largest error of the validation profiles | 3.76 % |
| Fit over synthesis ratio | 0.8390 |

Residuals of the validation profiles (the other profiles are in `boards/calibration/cyclone-10-lp.yaml`):

| Profile | Measured | Predicted | Error (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 14,857 | 14,771.3 | -0.58 |
| `p5_full` | 18,220 | 18,016.2 | -1.12 |
| `p7_ic64` | 11,714 | 11,710.7 | -0.03 |
| `p7_dc64` | 13,015 | 12,525.4 | -3.76 |

## 7. Fit over synthesis ratio

The estimator adds the terms of the table, which are `quartus_map` estimates, and multiplies the sum by the `map_to_fit_ratio` ratio to reach the logic the fitter (`quartus_fit`) uses. The ratio of each family is the mean of `fit_result.logic` over `result.logic` of a few profiles run up to the fitter (`calibrate run --stop-after fit`), and the fitter packs the logic better in the larger profiles, so the ratio grows with the profile. The last two columns show the error of the table sum times the ratio against the fitter logic, which stays below 10 % in every profile that ran.

| Family | Profile | Synthesis | Fit | Fit over synthesis | Table times ratio | Error (%) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| Cyclone V | `p1_rv32i` | 4,343 | 4,087 | 0.9411 | 4,188 | 2.5 |
| Cyclone V | `p3_zicntr_zifencei` | 5,269 | 5,072 | 0.9626 | 5,076 | 0.1 |
| Cyclone V | `p5_base` | 8,177 | 7,944 | 0.9715 | 7,887 | -0.7 |
| Cyclone V | `p5_full` | 8,532 | 8,373 | 0.9814 | 8,304 | -0.8 |
| Cyclone IV E | `p1_rv32i` | 9,726 | 7,958 | 0.8182 | 8,187 | 2.9 |
| Cyclone IV E | `p3_zicntr_zifencei` | 12,076 | 10,255 | 0.8492 | 10,157 | -1.0 |
| Cyclone IV E | `p5_base` | 19,006 | 16,059 | 0.8449 | 16,022 | -0.2 |
| Cyclone IV E | `p5_full` | 20,015 | 17,111 | 0.8549 | 16,571 | -3.2 |
| MAX 10 | `p1_rv32i` | 11,194 | 9,400 | 0.8397 | 9,847 | 4.8 |
| MAX 10 | `p3_zicntr_zifencei` | 13,352 | 11,587 | 0.8678 | 11,767 | 1.6 |
| MAX 10 | `p5_base` | 19,201 | 17,377 | 0.9050 | 16,920 | -2.6 |
| MAX 10 | `p5_full` | 20,262 | 18,365 | 0.9064 | 17,703 | -3.6 |
| Cyclone 10 LP | `p1_rv32i` | 9,296 | 7,599 | 0.8174 | 7,799 | 2.6 |
| Cyclone 10 LP | `p2_rv32im` | 10,306 | 8,638 | 0.8382 | 8,647 | 0.1 |
| Cyclone 10 LP | `p3_zicntr_zifencei` | 11,709 | 9,855 | 0.8417 | 9,821 | -0.3 |
| Cyclone 10 LP | `p4_hpm_4x40` | 12,562 | 10,786 | 0.8586 | 10,497 | -2.7 |

| Family | Ratio used | Lowest | Highest |
| :--- | ---: | ---: | ---: |
| Cyclone V | 0.9642 | 0.9411 | 0.9814 |
| Cyclone IV E | 0.8418 | 0.8182 | 0.8549 |
| MAX 10 | 0.8797 | 0.8397 | 0.9064 |
| Cyclone 10 LP | 0.8390 | 0.8174 | 0.8586 |

On the Vidor the fitted profiles go up to `p4_hpm_4x40`, because the larger profiles exceed the 15408 LEs of the 10CL016.

## 8. Cross verification

The verification measures 14 profiles (12 on the DE0-Nano, without the 64 kbit caches, which do not fit its blocks) on another device of the same family and compares them with the table, using `riscv-tools calibrate verify`. The top of each board differs from the top of the measuring board (the DE10-Nano has emulated RAM and the DE0-Nano has smaller memories), so the comparison has two columns. The first uses the table as it is. The second moves the core term by the difference measured on profile `p1_rv32i`, so the part of the top that changes leaves the account and the increments of the extensions and the caches remain, which is what the table must get right on another device.

| Board | Family | Device | Core shift | Largest error | Largest shifted error | Shifted root mean square error |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| DE10-Nano | Cyclone V | 5CSEBA6 | -633 | 18.64 % | 4.63 % | 3.20 % |
| DE0-Nano | Cyclone IV E | EP4CE22 | -436 | 4.50 % | 2.02 % | 1.11 % |

The DE10-Nano shift (-633 ALMs) is what the DE0-CV top carries in addition, with the 16-bit SDRAM controller, and the DE0-Nano shift (-436 LEs) comes from the smaller memories of its platform (12 KiB FLASH and 8 KiB RAM, which fit the 66 blocks of the EP4CE22). Both tables hold on another device of the family with an error below 10 % after the core term shift.

### DE10-Nano

| Profile | Measured | Predicted | Error (%) | Shifted prediction | Shifted error (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 3,710 | 4,343.0 | 17.06 | 3,710.0 | 0.00 |
| `p1_rv32e` | 3,342 | 3,965.0 | 18.64 | 3,332.0 | -0.30 |
| `p2_rv32im` | 4,137 | 4,657.0 | 12.57 | 4,024.0 | -2.73 |
| `p3_zicntr_zifencei` | 4,806 | 5,264.6 | 9.54 | 4,631.6 | -3.63 |
| `p3_zicclsm_zicntr_zifencei` | 4,921 | 5,349.0 | 8.70 | 4,716.0 | -4.17 |
| `p4_hpm_4x40` | 5,144 | 5,566.5 | 8.21 | 4,933.5 | -4.09 |
| `p4_hpm_16x52` | 6,162 | 6,579.9 | 6.78 | 5,946.9 | -3.49 |
| `p5_base` | 7,735 | 8,180.2 | 5.75 | 7,547.2 | -2.43 |
| `p5_full` | 8,045 | 8,612.2 | 7.05 | 7,979.2 | -0.82 |
| `p6_interrupts` | 7,786 | 8,284.2 | 6.40 | 7,651.2 | -1.73 |
| `p7_ic8` | 4,798 | 5,261.5 | 9.66 | 4,628.5 | -3.53 |
| `p7_dc8` | 4,506 | 5,001.0 | 10.98 | 4,368.0 | -3.06 |
| `p7_ic64` | 4,812 | 5,268.7 | 9.49 | 4,635.7 | -3.66 |
| `p7_dc64` | 5,225 | 5,616.1 | 7.48 | 4,983.1 | -4.63 |

### DE0-Nano

| Profile | Measured | Predicted | Error (%) | Shifted prediction | Shifted error (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 9,290 | 9,726.0 | 4.69 | 9,290.0 | 0.00 |
| `p1_rv32e` | 8,039 | 8,401.0 | 4.50 | 7,965.0 | -0.92 |
| `p2_rv32im` | 10,318 | 10,546.0 | 2.21 | 10,110.0 | -2.02 |
| `p3_zicntr_zifencei` | 11,723 | 12,066.0 | 2.93 | 11,630.0 | -0.79 |
| `p3_zicclsm_zicntr_zifencei` | 11,992 | 12,372.0 | 3.17 | 11,936.0 | -0.47 |
| `p4_hpm_4x40` | 12,544 | 12,834.0 | 2.31 | 12,398.0 | -1.16 |
| `p4_hpm_16x52` | 14,852 | 15,170.6 | 2.15 | 14,734.6 | -0.79 |
| `p5_base` | 18,613 | 19,032.8 | 2.25 | 18,596.8 | -0.09 |
| `p5_full` | 19,615 | 19,685.5 | 0.36 | 19,249.5 | -1.86 |
| `p6_interrupts` | 18,792 | 19,385.5 | 3.16 | 18,949.5 | 0.84 |
| `p7_ic8` | 11,712 | 12,062.0 | 2.99 | 11,626.0 | -0.73 |
| `p7_dc8` | 11,096 | 11,421.0 | 2.93 | 10,985.0 | -1.00 |

## 9. How to redo it

Each family runs in the Tools, under the `flock` of the machine with the Quartus, and the table comes from the fit of the records. The profiles of one family run in sequence, and the Cyclone V runs on the laptop or on PC1, while the other families run only on PC1.

```bash
flock /tmp/quartus-<machine>.lock riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --lock <own-file>
riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --stop-after fit --only p1_rv32i,p3_zicntr_zifencei,p5_base,p5_full
riscv-tools --root <Insper-RISC-V> calibrate fit --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --table boards/calibration/max-10.yaml
riscv-tools --root <Insper-RISC-V> calibrate verify --profiles boards/calibration/profiles/verify-de0-nano.yaml --raw boards/calibration/raw/verify-de0-nano --table boards/calibration/cyclone-iv-e.yaml --output boards/calibration/verification/de0-nano.yaml
```

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
