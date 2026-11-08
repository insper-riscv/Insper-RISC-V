# Milestones M1 and M2 of the 100 MHz front on the `de0-cv`

🌐 [Português](../../../pt-br/platform/timing/MARCOS.md) · [English](MARCOS.md)

## 1. Scope

This document measures the `de0-cv` with the final core (Core `8a828cc`, which already carries steps F.P1 to F.P3) at the clocks of milestones M1 (50 MHz) and M2 (66.7 MHz) of front F, and compares it with the baseline of [README.md](README.md). The reference is the Quartus worst case: slow model at 85 degrees C for setup, fast model at 0 degrees C for hold, worst of seeds 1 to 5.

## 2. Measurement conditions

| Item | Value |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, on workstation PC1 |
| Device | 5CEBA4F23C7 (Cyclone V) |
| Sources | Insper-RISC-V `224a762`, Core `8a828cc`, Memory `1160ae1`, Peripherals `d7253f6`, Common-Components `9aa6a75`; SHA-256 digest of the code and project files `65eff664dceb14fa` |
| Top and project | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, versioned `.sdc` |
| Mode | `HIGH PERFORMANCE EFFORT`, seeds 1 to 5, through `de0-cv_synth.tcl` |
| Clocks | PLL outputs 2 and 3 at the milestone frequency (50 or 66.666667 MHz) and the phase of output 3 (core clock) given in each table; only the Quartus working copy changes, not the repository |
| `time` tick count | 50 cycles at both frequencies, which does not change the build timing |

The slacks of each seed are in `dados/marcos/tabela-sementes.tsv` (section 7). The full Quartus reports and logs are not versioned; regenerate them with `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <seed>` on the build of the requested seed, which leaves the `.sta.rpt` and `.fit.rpt` in `output_files/`.

## 3. Milestone M1: 50 MHz

### 3.1. With the versioned phase (6625 ps)

| Domain | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | -0.729 | -1.345 | -0.350 | -0.560 | -1.001 | -1.345 |
| Fetch | 3.582 | 5.406 | 3.403 | 4.491 | 4.160 | 3.403 |
| SDRAM controller | -0.744 | -0.255 | -0.208 | -0.173 | -0.713 | -0.744 |
| `DRAM_CLK` | 0.428 | -0.127 | -0.042 | -0.078 | 0.394 | -0.127 |
| JTAG | 10.433 | 7.612 | 9.873 | 10.824 | 11.068 | 7.612 |
| Core Fmax (MHz) | 65.07 | 65.58 | 62.44 | 62.23 | 67.32 | 62.23 |
| Lowest hold, fast model at 0 degrees C | 0.142 | 0.149 | 0.125 | 0.002 | 0.142 | 0.002 |

### 3.2. With the core phase at 8250 ps

| Domain | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | 0.666 | 0.188 | 1.386 | 0.649 | 0.570 | 0.188 |
| Fetch | 3.804 | 3.781 | 3.031 | 2.944 | 4.179 | 2.944 |
| SDRAM controller | -0.745 | -0.255 | -0.205 | -0.173 | -0.713 | -0.745 |
| `DRAM_CLK` | 0.429 | -0.127 | -0.046 | -0.078 | 0.394 | -0.127 |
| JTAG | 11.376 | 11.303 | 10.683 | 9.034 | 10.683 | 9.034 |
| Core Fmax (MHz) | 64.67 | 66.70 | 65.48 | 65.09 | 64.28 | 64.28 |
| Lowest hold, fast model at 0 degrees C | 0.130 | 0.131 | 0.065 | 0.122 | 0.126 | 0.065 |

### 3.3. Reading

| Item | Result |
| :--- | :--- |
| Core and fetch | Non-negative slack in all five seeds with the 8250 ps phase (worst core slack 0.188 ns); with 6625 ps the core slack is negative in all seeds (worst -1.345 ns) |
| SDRAM controller and `DRAM_CLK` | Still negative (-0.745 and -0.127 ns) and equal to the baseline, because they do not depend on the core phase |
| Hold | Positive in all domains and seeds (minimum 0.002 ns with 6625 ps and 0.065 ns with 8250 ps) |
| Verdict | M1 does not close: the two SDRAM domains are missing, which is step F.P6 |

The 8250 ps phase moves the core clock edge 1625 ps after the versioned one. The loop through the instruction cache (PC, tag, PC) lies between the two clocks, and the phase splits the 20 ns between the two crossings; the versioned phase leaves the fetch-to-core crossing with 6.6 ns and it needs close to 8.0 ns.

## 4. Milestone M2: 66.7 MHz

### 4.1. Slack of the worst path of each clock pair

The table gives the worst slack (ns, slow model at 85 degrees C) of the five seeds for each pair and each phase.

| Core | Phase | core to core | core to fetch | fetch to core |
| :--- | ---: | ---: | ---: | ---: |
| 50 MHz | 6625 | 3.931 | 3.403 | -1.345 |
| 50 MHz | 8250 | 4.443 | 2.944 | 0.188 |
| 66.7 MHz | 7500 | 1.593 | 0.494 | -1.699 |
| 66.7 MHz | 8000 | 1.135 | 0.400 | -0.907 |
| 66.7 MHz | 8500 | 1.318 | 0.032 | -0.290 |
| 66.7 MHz | 9000 | 1.490 | -0.339 | -0.223 |

### 4.2. Slack per domain with the best phase (8500 ps)

| Domain | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core | -0.084 | -0.290 | 0.508 | 0.359 | 0.265 | -0.290 |
| Fetch | 0.851 | 0.853 | 0.247 | 0.032 | 0.445 | 0.032 |
| SDRAM controller | -0.744 | -0.255 | -0.205 | -0.173 | -0.713 | -0.744 |
| `DRAM_CLK` | 0.428 | -0.127 | -0.046 | -0.078 | 0.394 | -0.127 |
| JTAG | 11.109 | 10.010 | 9.087 | 10.058 | 11.238 | 9.087 |
| Core Fmax (MHz) | 75.42 | 76.32 | 73.09 | 74.47 | 73.10 | 73.09 |
| Lowest hold, fast model at 0 degrees C | 0.121 | 0.043 | 0.139 | 0.125 | 0.019 | 0.019 |

### 4.3. Reading

| Item | Result |
| :--- | :--- |
| Core loop | Slack of +1.1 to +1.6 ns in all phases, so steps F.P1 to F.P3 close the core loop at 66.7 MHz |
| Instruction cache loop | The sum of the two crossings sits near 0 ns of slack: fetch to core -0.290 ns and core to fetch +0.032 ns with 8500 ps; no phase takes both to non-negative slack in the five seeds |
| SDRAM controller and `DRAM_CLK` | Equal to the baseline (-0.744 and -0.127 ns) |
| Core domain Fmax | 74.59 to 77.92 MHz with 7500 ps, against 62.23 to 67.32 MHz at 50 MHz |
| Verdict | M2 does not close: the instruction cache loop (step F.P5, registered tag) and the SDRAM controller (F.P6) are missing |

## 5. Steps F.P1 to F.P3

The three steps are already in the measured RTL, so the Fmax and the slack per domain of the three are those of sections 3 and 4; the document of each step in the Core (`docs/en/timing/P1_*.md`, `P2_*.md` and `P3_*.md`) gives the path before and after. The remaining worst core-to-core paths are the CSR read feeding the CSR write (from `ID/EX r_imm` through 9 logic levels, the 29-counter multiplexer, to `mepc`, `mtval` and the counters) and the MEM exception decision reaching the PC and the counters.

## 6. How to reproduce

| Goal | Command |
| :--- | :--- |
| Build one seed | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <seed>`, in a copy of the repository |
| Change frequency and phase | Edit `output_clock_frequency2`, `output_clock_frequency3` and `phase_shift3` of `src/cyclone-v/de0-cv/pll/sdram_platform_pll.v` in the copy |
| Slack per domain | `output_files/de0-cv.sta.summary` and `output_files/de0-cv.sta.rpt` |
| Paths per clock pair | `quartus_sta -t docs/pt-br/platform/timing/dados/pares-de-dominios.tcl de0-cv 300 slow` in the folder of the built project |

## 7. Per-seed tables

The values come from `dados/marcos/tabela-sementes.tsv`, generated by `dados/tabelar_resumos.py` from the Timing Analyzer `.sta.summary` files (slow model, 1100 mV, 85 °C). Each table lists, per seed, the worst setup, the worst hold and the domain where each occurs. The domains are `core` (PLL output 3), `fetch` (output 2), `mem` (output 0, the SDRAM controller), `DRAM_CLK` (pin) and `jtag`; in the `core_fpga_test` top the PLL outputs appear as `pll_c0` and `pll_c1`, and `pll_dram_clk` and `pll_vco` only have minimum pulse width. The TSV also carries TNS, recovery, removal, minimum pulse width and the worst value among the four temperature and voltage models.

The measurements describe the platform frozen at 76.923077 MHz and the listed experiments. A new frequency attack regenerates the table with `python3 dados/tabelar_resumos.py gerar dados/marcos` over the `.resumo.txt` files of the new seeds (the Quartus `.sta.summary` and `.fit.summary`, renamed), and `--check` compares the TSV against them. The raw summaries are not versioned, and the tables are the starting reference for the next round.

### 7.1. `50mhz-fase6625`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0.744 | mem | 0.295 | core |
| 2 | -1.345 | core | 0.317 | core |
| 3 | -0.350 | core | 0.306 | core |
| 4 | -0.560 | core | 0.141 | jtag |
| 5 | -1.001 | core | 0.280 | core |

### 7.2. `50mhz-fase8250`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0.745 | mem | 0.293 | core |
| 2 | -0.255 | mem | 0.271 | core |
| 3 | -0.205 | mem | 0.276 | core |
| 4 | -0.173 | mem | 0.269 | core |
| 5 | -0.713 | mem | 0.265 | core |

### 7.3. `66mhz-fase7500`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -1.699 | core | 0.313 | core |
| 2 | -1.380 | core | 0.268 | core |
| 3 | -0.204 | mem | 0.268 | core |
| 4 | -0.173 | mem | 0.279 | core |
| 5 | -1.674 | core | 0.303 | core |

### 7.4. `66mhz-fase8000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0.744 | mem | 0.267 | core |
| 2 | -0.882 | core | 0.304 | core |
| 3 | -0.204 | mem | 0.267 | core |
| 4 | -0.191 | mem | 0.261 | core |
| 5 | -0.907 | core | 0.265 | core |

### 7.5. `66mhz-fase8500`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0.744 | mem | 0.306 | core |
| 2 | -0.290 | core | 0.270 | core |
| 3 | -0.205 | mem | 0.271 | core |
| 4 | -0.173 | mem | 0.291 | core |
| 5 | -0.713 | mem | 0.158 | jtag |

### 7.6. `66mhz-fase9000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0.745 | mem | 0.267 | core |
| 2 | -0.255 | mem | 0.283 | core |
| 3 | -0.339 | fetch | 0.279 | core |
| 4 | -0.173 | mem | 0.277 | core |
| 5 | -0.713 | mem | 0.258 | core |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
