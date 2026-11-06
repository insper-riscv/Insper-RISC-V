# Full Quartus compile of the new Core on the DE0-CV tops

🌐 [Português](../../../pt-br/platform/timing/core-novo.md) · [English](core-novo.md)

## 1. Scope

This document records the full Quartus compile of the three Insper-RISC-V tops with the new Core (Zimop and Zicond as `extras:`, Zihintntl, Zihintpause and interrupts with `has_interrupts`, default `false`) and the cost of the interrupt mechanism enabled on the `de0-cv`. It complements the [baseline](README.md), which measured the full profile before these features, and is the area and Fmax reference ahead of any decision about 100 MHz. No RTL file was changed.

## 2. Measurement conditions

| Item | Value |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, on workstation PC1 (seeds 1 and 2) and on the laptop (seeds 3 to 5 and the experiment with inputs tied to `0`) |
| Device | 5CEBA4F23C7 (Cyclone V) |
| Sources | Insper-RISC-V `224a762` (`main`, after the `Onda-0` tag), Common-Components `9aa6a75`, Core `8a828cc`, Memory `1160ae1`, Peripherals `d7253f6`; tree hash (`git ls-files -s` of the top and the four submodules) `8576b682405b711e` |
| Mode | `HIGH PERFORMANCE EFFORT`, seeds 1 to 5, through the `de0-cv_synth.tcl`, `external-data_synth.tcl` and `dados/core-novo/core_fpga_test_synth.tcl` scripts |
| Clocks | 50 MHz for core and fetch (core phase as versioned), 142.857 MHz for the SDRAM controller and `DRAM_CLK` on the tops with SDRAM |
| Profile | That of each `platform.yaml`: `rv32im_zicclsm_zicntr_zihpm_zifencei` with `extras: [Zimop, Zicond]`, 29 64-bit Zihpm counters |
| Setup slack | Slow model at 85 °C, slack of the destination clock domain |
| Hold slack | Fast model at 0 °C, smallest value across the domains |

The same seeds give the same result on both machines: `de0-cv` seed 5 (8,095 ALMs and 67.32 MHz) and `external-data` seed 5 (8,227 ALMs and 63.54 MHz) match the compiles done earlier on PC1.

## 3. Results per top

The domains are core (`clk_idexmem`), fetch (`clk_if`), SDRAM controller, `DRAM_CLK` and JTAG; `core_fpga_test` has only core, fetch, the input clock and JTAG. Slacks are in ns. The "Worst" row gives the largest resource use and the smallest Fmax and slack of the five seeds.

#### `de0-cv`

| Seed | ALMs | Registers | M10K | Core Fmax (MHz) | setup core | setup fetch | setup SDRAM | setup `DRAM_CLK` | setup JTAG | minimum hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,058 | 9,227 | 271 | 65.07 | -0.729 | 3.582 | -0.744 | 0.428 | 10.433 | 0.142 |
| 2 | 8,091 | 9,267 | 271 | 65.58 | -1.345 | 5.406 | -0.255 | -0.127 | 7.612 | 0.149 |
| 3 | 8,084 | 9,222 | 271 | 62.44 | -0.350 | 3.403 | -0.208 | -0.042 | 9.873 | 0.125 |
| 4 | 8,082 | 9,222 | 271 | 62.23 | -0.560 | 4.491 | -0.173 | -0.078 | 10.824 | 0.002 |
| 5 | 8,095 | 9,172 | 271 | 67.32 | -1.001 | 4.160 | -0.713 | 0.394 | 11.068 | 0.142 |
| Worst | 8,095 | 9,267 | 271 | 62.23 | -1.345 | 3.403 | -0.744 | -0.127 | 7.612 | 0.002 |
| Mean | 8,082 | 9,222 | 271 | 64.53 |  |  |  |  |  | |

#### `external-data`

| Seed | ALMs | Registers | M10K | Core Fmax (MHz) | setup core | setup fetch | setup SDRAM | setup `DRAM_CLK` | setup JTAG | minimum hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,225 | 8,452 | 234 | 64.51 | 0.033 | 5.158 | -0.731 | 0.416 | 10.039 | 0.126 |
| 2 | 8,215 | 8,461 | 234 | 63.56 | 0.129 | 4.703 | -0.203 | -0.048 | 10.878 | 0.121 |
| 3 | 8,201 | 8,564 | 234 | 65.38 | 0.308 | 4.210 | -0.730 | 0.413 | 9.335 | 0.039 |
| 4 | 8,190 | 8,448 | 234 | 62.25 | 0.665 | 4.956 | -0.191 | -0.061 | 10.339 | 0.107 |
| 5 | 8,227 | 8,480 | 234 | 63.54 | -0.204 | 4.126 | -0.743 | 0.427 | 9.142 | 0.099 |
| Worst | 8,227 | 8,564 | 234 | 62.25 | -0.204 | 4.126 | -0.743 | -0.061 | 9.142 | 0.039 |
| Mean | 8,212 | 8,481 | 234 | 63.85 |  |  |  |  |  | |

#### `core_fpga_test`

| Seed | ALMs | Registers | M10K | Core Fmax (MHz) | setup core | setup fetch | setup `i_clock_50` | setup JTAG | minimum hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7,172 | 7,987 | 288 | 66.98 | 1.412 | 3.272 | 16.116 | 10.705 | 0.124 |
| 2 | 7,173 | 8,005 | 288 | 66.18 | 1.212 | 3.071 | 16.097 | 10.722 | 0.113 |
| 3 | 7,163 | 7,821 | 288 | 66.70 | 1.140 | 4.200 | 15.883 | 11.476 | 0.120 |
| 4 | 7,103 | 7,804 | 288 | 67.80 | 1.320 | 3.935 | 16.108 | 9.675 | 0.128 |
| 5 | 7,142 | 8,019 | 288 | 64.15 | 1.122 | 3.000 | 16.080 | 10.595 | 0.118 |
| Worst | 7,173 | 8,019 | 288 | 64.15 | 1.122 | 3.000 | 15.883 | 9.675 | 0.113 |
| Mean | 7,151 | 7,927 | 288 | 66.36 |  |  |  |  | |

#### `de0-cv` with `has_interrupts`

| Seed | ALMs | Registers | M10K | Core Fmax (MHz) | setup core | setup fetch | setup SDRAM | setup `DRAM_CLK` | setup JTAG | minimum hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8,060 | 9,298 | 271 | 64.56 | -0.918 | 3.946 | -0.744 | 0.428 | 10.144 | 0.010 |
| 2 | 8,078 | 9,245 | 271 | 63.02 | -1.702 | 3.237 | -0.255 | -0.127 | 9.465 | 0.051 |
| 3 | 8,078 | 9,272 | 271 | 65.53 | -0.237 | 3.893 | -0.204 | -0.047 | 9.596 | 0.148 |
| 4 | 8,098 | 9,180 | 271 | 66.45 | -0.380 | 4.189 | -0.191 | -0.060 | 10.191 | 0.124 |
| 5 | 8,078 | 9,271 | 271 | 65.58 | -0.649 | 4.500 | -0.728 | 0.410 | 10.860 | 0.123 |
| Worst | 8,098 | 9,298 | 271 | 63.02 | -1.702 | 3.237 | -0.744 | -0.127 | 9.465 | 0.010 |
| Mean | 8,078 | 9,253 | 271 | 65.03 |  |  |  |  |  | |

#### `de0-cv` with `has_interrupts` and the inputs tied to `0`

| Seed | ALMs | Registers | M10K | Core Fmax (MHz) | setup core | setup fetch | setup SDRAM | setup `DRAM_CLK` | setup JTAG | minimum hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 8,069 | 9,190 | 271 | 65.07 | -1.229 | 4.772 | -0.713 | 0.394 | 11.045 | 0.139 |

## 4. Cost of the interrupt mechanism

The `de0-cv` variant with `has_interrupts => true` wires `i_irq_software`, `i_irq_timer` and `i_irq_external` to three `sdram_rdata` bits registered on the core clock, because the CLINT and the external controller are not yet wired to the top and constant inputs would let Quartus prune `mip`. The control variant ties the three inputs to `0` (seed 5). The diffs of the two throwaway copies are in `dados/core-novo/experimento-interrupcoes/`.

| Measure (mean of seeds 1 to 5) | `de0-cv` | with `has_interrupts` | Difference |
| :--- | ---: | ---: | ---: |
| ALMs | 8,082 | 8,078 | -4 |
| Registers | 9,222 | 9,253 | +31 |
| M10K | 271 | 271 | 0 |
| Core Fmax (MHz) | 64.53 | 65.03 | +0.50 |
| Worst core setup slack (ns) | -1.345 | -1.702 | -0.357 |

On seed 5, inputs tied to `0` give 8,069 ALMs and 9,190 registers, against 8,078 and 9,271 with live inputs and 8,095 and 9,172 without the mechanism.

## 5. Reading the numbers

1. **Area.** The three tops use 7,100 to 8,230 ALMs (38 to 45 % of 18,480). The `de0-cv` stayed between 8,058 and 8,095 ALMs, the same range as the baseline (8,037 to 8,090), so the new Core has no measurable area cost there. `external-data` uses about 130 ALMs more than the `de0-cv` and 740 fewer registers, and frees 37 of the 271 M10K (234 of 308, 76 %). `core_fpga_test` (internal memories) uses 7,103 to 7,173 ALMs and 288 M10K (94 %).
2. **Fmax.** The core domain closes at 62.23 to 67.32 MHz on the `de0-cv`, 62.25 to 65.38 MHz on `external-data` and 64.15 to 67.80 MHz on `core_fpga_test`. The `de0-cv` worst value (62.23 MHz) is 2 MHz below the baseline worst (64.30 MHz), within the seed spread of about 5 MHz. No top comes close to 100 MHz, and the structural conclusion of front F does not change.
3. **Slack at 50 MHz.** On the `de0-cv` the core fails in every seed (worst -1.345 ns), against -1.604 ns in the baseline, and the SDRAM controller and `DRAM_CLK` keep the known small violation (worst -0.744 and -0.127 ns). On `external-data` the core closes in four seeds (worst -0.204 ns on seed 5) and the remaining violations are the SDRAM controller (worst -0.743 ns) and `DRAM_CLK` (worst -0.061 ns). `core_fpga_test` closes setup in every seed (smallest slack 1.122 ns).
4. **Hold.** Hold slack in the fast 0 °C model is positive on every top and seed; the smallest value is 0.002 ns (JTAG, `de0-cv`, seed 4), and on the core and fetch clocks the smallest is 0.039 ns (`external-data` core, seed 3).
5. **Interrupts.** The mechanism costs less than the seed spread: the ALM difference (-4) and the Fmax difference (+0.50 MHz) are within it, and the 31 extra registers correspond to `mie`, the `mstatus` bits and the input capture point. Core setup slacks with `has_interrupts` (-0.237 to -1.702 ns) cover the same range as without it (-0.350 to -1.345 ns).

## 6. How to reproduce

| Goal | Command |
| :--- | :--- |
| `de0-cv` and `external-data` | `quartus_sh -t src/cyclone-v/<platform>/<platform>_synth.tcl <seed>`, on a copy of the repository |
| `core_fpga_test` | Copy `dados/core-novo/core_fpga_test_synth.tcl` to `src/simulation/internal-mem/quartus/` and run `quartus_sh -t core_fpga_test_synth.tcl <seed>` there |
| Interrupt variant | Apply `dados/core-novo/experimento-interrupcoes/irq.patch` (or `irq0.patch`) to `src/cyclone-v/de0-cv/de0-cv_top.vhd` on the copy |
| Slacks and Fmax | `output_files/<project>.sta.summary` and `output_files/<project>.sta.rpt` |

## 7. Raw data

In `dados/core-novo/`, for each compile `<top>-semente-<n>`: `.quartus.log` (flow log, local paths replaced by `<caminho-local>`), `.sta.relatorio.txt` (the `.sta.rpt`), `.sta.resumo.txt` (the `.sta.summary`) and `.fit.resumo.txt` (the `.fit.summary`). The tops are `de0-cv`, `external-data`, `core_fpga_test`, `irq` (`de0-cv` with `has_interrupts`, seeds 1 to 5) and `irq0` (inputs tied to `0`, seed 5). The `.rpt` and `.summary` extensions were changed to `.txt` because `.gitignore` ignores them.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
