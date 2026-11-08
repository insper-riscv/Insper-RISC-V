# Fit of the profile on the board

## 1. Two stages

The Tools checks whether the chosen profile, with the backends, caches and peripherals requested, fits the board. The fast estimator runs without Quartus, and the authoritative confirmation reads the summaries Quartus itself writes.

| Stage | Input | Runs in |
| :--- | :--- | :--- |
| Estimator | `platform.yaml`, resolved profile and the calibration table of the family | `check-memory-map`, `board generate` and before `program` and `run`; also in the CI without Quartus |
| Authoritative | Fit summaries (`*.fit.summary`) | After the compilation of `program`, and `check-fit` over a folder of reports |

## 2. Capacities

The capacities of the board are in `resources` of the `board.yaml`.

| Resource | Field | Unit |
| :--- | :--- | :--- |
| Logic | `resources.logic.total` | ALM (Cyclone V) or LUT4 LE (other families); no unit converts into the other by a fixed factor |
| Internal RAM | `resources.block_ram` | Blocks and bits per block |
| Multipliers | `resources.multipliers` | Device elements, in the Quartus unit |
| PLLs | `resources.plls` | Count |
| Pins | `resources.user_pins` | User pins of the package |

A `null` capacity is unknown, and the estimator skips it with warning V18.

## 3. Estimate

The estimator sums the cost of each block of the profile with the calibration table of the family. With $\hat{L}$ the logic estimated in the unit of the family and $r$ the ratio between fit and synthesis,

$$ \hat{L} = r \left( L_{core} + \sum_{e} L_e + L_{hpm}(n, w) + \sum_{c \in \{i, d\}} L_c(s_c) + \sum_{p} L_p + \sum_{b} L_b \right) $$

| Term | Meaning | Cost form |
| :--- | :--- | :--- |
| $L_{core}$ | Base core (`rv32i` or `rv32e`) | Constant per family and per base |
| $L_e$ | Extension or extra (M, Zmmul, Zicsr, Zicntr, Zifencei, Zicclsm, Zimop, Zicond, Zihintntl, Zihintpause, interrupts, Sscofpmf) | Constant per extension |
| $L_{hpm}$ | Zihpm with $n$ counters of $w$ bits | $a_0 + a_1 n + a_2 n w$ |
| $L_c$ | Instruction or data cache of $s_c$ kbit | $c_0 + c_1 s_c$ |
| $L_p$ | Peripheral | Constant per peripheral, which stays inside the core term when the measurement platform includes it in every measurement |
| $L_b$ | Device backend controller | Constant per type and width |

The ISA implications hold in the estimate: Zicntr and Zihpm imply Zicsr, M implies Zmmul, and Sscofpmf requires Zihpm and interrupts. The emulated memory costs blocks, not logic, and the number of blocks is the one in section 6 of [arquitetura.md](arquitetura.md).

The calibration table is measured and not written by hand, and each family has its own in `boards/calibration/<family>.yaml` ([calibracao.md](calibracao.md)): the unit, the coefficients, the error and the Fmax per grade. A `null` coefficient is a measurement not yet made and makes the estimator emit V18. The keys of extensions, extras, peripherals and controllers come from the catalogs of the Core and the `platform.yaml`, and a key outside them is refused.

## 4. Policy

Let $u$ be the utilization of a resource, the estimate over the total.

| Utilization | Result | Reason |
| :--- | :--- | :--- |
| $u \le 0.85$ | Pass | Margin above the expected error |
| $0.85 < u \le 1.00$ | Warning | The estimator errs by a few percentage points; only the fit decides |
| $u > 1.00$ | Error | Exceeds the capacity even with a favorable error |

The thresholds are Tools constants and hold for RAM blocks, logic, multipliers, PLLs and pins, in both stages; there is no option to force the result. The estimated logic only fails when the family is validated, that is, the maximum validation error of the table is up to 10 %. Before that the warning V18 applies, and the fit decides. The frequency warning (V8) compares `clocks.core.mhz` with the measured Fmax of the family and never fails.

## 5. Rules

| Rule | Origin | Severity |
| :--- | :--- | :--- |
| V11 | RAM blocks of the emulated memory and the caches | Error; warning between 85 % and 100 % |
| V12 | Estimated logic above the capacity | Error |
| V13 | Estimated logic between 85 % and 100 % | Warning |
| V14 | The fit report exceeds resources; all are listed at once | Error; warning in the 85 % to 100 % range |
| V18 | Family without calibration, `null` capacity or `null` coefficient | Warning |

## 6. Command

```bash
riscv-tools --root . check-fit --reports <folder with *.fit.summary> --board boards/<board>/board.yaml
```

The command lists all resources that exceed the capacity and exits with status 1 when there is an error. The `fit_estimate` module of the [Tools](https://github.com/insper-riscv/Tools) carries the functions and tests.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
