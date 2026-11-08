# Base cycles per instruction of the `de0-cv` at 76.923 MHz

🌐 [Português](../../../pt-br/platform/timing/CPI-BASE.md) · [English](CPI-BASE.md)

## 1. Scope

This document records the cycles per instruction of the measurement programs of the Tests repository in the simulation of the `de0-cv` with the frozen RTL (Insper-RISC-V `a612e9c`: Core `2ed0117`, Memory `768e81e`), and the cost in cycles of each step of the frequency front. The numbers are the starting point for any future pipeline change.

## 2. Conditions

| Item | Value |
| :--- | :--- |
| Program | `c-sdram/cpi-kernels` of Tests (`Tests` `c1fcead`) |
| Simulation | Top `rv32im_sdram_flash_sim_test` in GHDL, `ci-elf` image, `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml sim --only cpi-kernels` |
| Platform | `de0-cv` with 4 KiB caches, the FLASH behind the caches, profile `rv32im_zicclsm_zicntr_zihpm_zifencei` with the `extras` of `platform.yaml` |
| Measure | `cycle` and `instret` read before and after each compute kernel; the counts are deterministic |

## 3. Result

| Compute kernel | Cycles | Instructions | Cycles per instruction |
| :--- | ---: | ---: | ---: |
| Integer loop | 2173 | 1300 | 1.67 |
| Multiplication | 2920 | 275 | 10.62 |
| Division | 3075 | 276 | 11.14 |
| SDRAM load | 3757 | 1043 | 3.60 |
| SDRAM byte store | 4166 | 786 | 5.30 |

## 4. Cost in cycles of each change of the frequency front

| Change | Cost | How it was measured |
| :--- | :--- | :--- |
| Registered Zihpm read (F.P6c) | One cycle per CSR instruction that accesses `mcountinhibit`, `mhpmeventK`, `mhpmcounterK` or `mhpmcounterKh` | Core test `test_a_bank_read_costs_one_cycle`: 16 more reads cost 16 cycles |
| Fetch replay (F.P5) | Zero on instruction-cache hits; on each miss the PC returns to the instruction after one cycle and the fetch confirms only every two cycles | `icache` formula (`Memory/docs/en/cache/icache.md`): a miss of $9 + k$ cycles, before $7 + k$ |
| Registered interrupt lines | One more cycle between the event (MSIP, MTIP, MEIP) and `mip` | Program `clint-mtip` adjusted to wait for `mip` |
| Instruction-cache invalidation by sweep (F.P5) | $L + 4$ cache fetch cycles on each `fence.i` and each region invalidation, with $L$ lines (256 in the 4 KiB cache) | `icache` formula |
| Registered address class (F.P4) | Zero | Same cycle of the exception and the stall |

## 5. What was not measured

There is no measurement of the same programs on the RTL before the front (the earlier tree does not run with the current Tests tools). The comparison CPI from the start of the front is in [README.md](README.md), section 3, measured with other kernels (`cpi-core`, `cpi-data` and `cpi-fetch`).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
