# SDRAM controller and `DRAM_CLK` at 100 MHz

🌐 [Português](../../../pt-br/platform/timing/sdram-100mhz.md) · [English](sdram-100mhz.md)

## 1. Scope

This document measures step F.P6 of the 100 MHz front: the SDRAM controller and the `DRAM_CLK` pin of the `de0-cv` leave the 142.857 MHz clock and move to 100 MHz, the final core frequency, and it records what this costs in SDRAM throughput. The references are [milestone M1](MARCOS.md) (controller at 142.857 MHz) and the [baseline](README.md).

## 2. Measurement conditions

| Item | Value |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, on the laptop, one compiler at a time |
| Device | 5CEBA4F23C7 (Cyclone V) |
| Sources | Insper-RISC-V `onda2` with step F.P6, Core `7e05744`, Memory `1c4de11`, Peripherals `69abd8b`, Common-Components `56c293e` |
| Mode | `HIGH PERFORMANCE EFFORT`, seeds 1 to 5, through `de0-cv_synth.tcl` |
| Clocks | Controller and `DRAM_CLK` at 100 MHz; core and fetch at 50 MHz, with the core phase at 8250 ps (that of [milestone M1](MARCOS.md)) |
| Setup slack | Slow model at 85 °C, slack of the destination clock domain |
| Hold slack | Fast model at 0 °C, smallest value among the domains |
| Simulation | GHDL and cocotb in the `ci-elf` image, core at 100 MHz (10 ns period) and at 50 MHz, controller at 7 ns and at 10 ns |

## 3. Why the controller at 142.857 MHz does not close

The worst path of the controller domain is the data read: the `DRAM_DQ` pin to the `dq_in` register of the input/output cell. The chip answers a time $t_{AC}$ after the `DRAM_CLK` edge, and Quartus measures the path against the second controller edge after the one that launched the data (multicycle path of 2).

| Term of seed 1 (142.857 MHz, `DRAM_CLK` phase at 2750 ps) | Value (ns) |
| :--- | ---: |
| Relationship between the launch edge and the capture edge | 11.250 |
| Clock delay to the `DRAM_CLK` pin minus the one to the capture register | -4.030 |
| $t_{AC}$ of the chip | 5.400 |
| Pin-to-register delay | 2.425 |
| Clock uncertainty | 0.140 |
| Slack | -0.745 |

The `DRAM_CLK` phase moves the two sides of the account in opposite directions: raising the phase by $\delta$ takes $\delta$ from the read slack and adds $\delta$ to the setup slack of the outputs against `DRAM_CLK`. The sum of the two slacks does not depend on the phase.

| Seed | Controller (read) | `DRAM_CLK` (outputs) | Sum |
| ---: | ---: | ---: | ---: |
| 1 | -0.745 | 0.429 | -0.316 |
| 2 | -0.255 | -0.127 | -0.382 |
| 3 | -0.205 | -0.046 | -0.251 |
| 4 | -0.173 | -0.078 | -0.251 |
| 5 | -0.713 | 0.394 | -0.319 |

The sum is negative in the five seeds, so no phase closes the controller and `DRAM_CLK` together in any of them (values from [milestone M1](MARCOS.md), section 3.2). Fixing the path at 142.857 MHz would take a capture clock of its own with an independent phase and one more clock-domain crossing, with no throughput gain to pay for it.

## 4. The solution: controller at 100 MHz

The controller, the arbiter and the debug master run at 100 MHz, on output 0 of the PLL, and `DRAM_CLK` on output 1, also at 100 MHz. The 1000 MHz internal oscillator of the PLL already gives 100 MHz (divider 10). The SDRAM bridge keeps the toggles and the two flip-flop synchronizers: the crossing to the core holds for any frequency ratio, and the 10 ns limit of the `.sdc` stays below two edges of the controller (20 ns) and of the core (20 ns at 100 MHz).

The relationship of the read path goes from 11.25 ns to $2 T - \varphi = 16.0$ ns with $\varphi$ = 4000 ps, and that of the outputs against `DRAM_CLK` is the phase itself. The chip timings in cycles come from `SDRAM_TCK_PS` (10 000 ps), from the `sdram` section of `platform.yaml`:

| Chip timing | Cycles at 7 ns | Cycles at 10 ns |
| :--- | ---: | ---: |
| tRCD and tRP (15 ns) | 3 | 2 |
| tRC (60 ns) and tRFC (63 ns) | 9 | 6 and 7 |
| Closed-page access, ACTIVE to the next ACTIVE | 10 | 9 |
| Interval between refreshes | 1116 | 782 |

### 4.1. Phase of `DRAM_CLK`

Two phases, five seeds (three for the 4000 ps one), core and fetch as in the rest of this document. With 3000 ps the slack of the outputs is the smallest of the set (0.123 ns), and with 4000 ps the two slacks are 1.1 ns and 4.0 ns; the 4000 ps phase is the versioned one.

3000 ps phase:

| Seed | ALMs | Registers | Core Fmax (MHz) | Controller Fmax (MHz) | core | fetch | controller | `DRAM_CLK` | JTAG | min. hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8297 | 9387 | 67.05 | 154.8 | 0.907 | 3.830 | 3.540 | 0.679 | 10.089 | 0.117 |
| 2 | 8304 | 9368 | 65.54 | 171.03 | 0.343 | 3.552 | 4.153 | 0.123 | 11.044 | 0.019 |
| 3 | 8322 | 9483 | 63.83 | 161.34 | 1.218 | 2.651 | 3.802 | 0.204 | 9.988 | 0.127 |
| 4 | 8297 | 9470 | 65.33 | 145.6 | 1.451 | 3.530 | 3.132 | 0.172 | 10.263 | 0.078 |
| 5 | 8294 | 9395 | 67.02 | 174.52 | 1.010 | 4.166 | 4.270 | 0.660 | 9.601 | 0.145 |
| Worst | 8322 | 9483 | 63.83 | 145.6 | 0.343 | 2.651 | 3.132 | 0.123 | 9.601 | 0.019 |

4000 ps phase (seeds 1 to 3 of this round, with the sources before the `BOOT_MEMORY` rename):

| Seed | ALMs | Registers | Core Fmax (MHz) | Controller Fmax (MHz) | core | fetch | controller | `DRAM_CLK` | JTAG | min. hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8297 | 9375 | 65.29 | 151.91 | 0.873 | 4.009 | 3.417 | 1.679 | 10.145 | 0.129 |
| 2 | 8304 | 9433 | 65.43 | 160.93 | 0.262 | 3.917 | 3.786 | 1.123 | 10.989 | 0.010 |
| 3 | 8322 | 9493 | 63.27 | 166.09 | 1.226 | 2.570 | 3.979 | 1.204 | 10.900 | 0.125 |
| Worst | 8322 | 9493 | 63.27 | 151.91 | 0.262 | 2.570 | 3.417 | 1.123 | 10.145 | 0.010 |

## 5. Result

Controller and `DRAM_CLK` at 100 MHz, 4000 ps phase, core at 50 MHz with the 8250 ps phase. Slacks are in ns and Fmax in MHz.

| Seed | ALMs | Registers | Core Fmax (MHz) | Controller Fmax (MHz) | core | fetch | controller | `DRAM_CLK` | JTAG | min. hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8265 | 9404 | 64.7 | 160.72 | 0.558 | 2.896 | 3.778 | 1.678 | 11.227 | 0.130 |
| 2 | 8329 | 9497 | 64.29 | 157.43 | 0.610 | 4.012 | 3.648 | 1.123 | 10.016 | 0.079 |
| 3 | 8293 | 9451 | 65.79 | 162.79 | 1.449 | 2.189 | 3.857 | 1.203 | 9.027 | 0.092 |
| 4 | 8288 | 9437 | 66.11 | 151.63 | 1.342 | 2.904 | 3.405 | 1.172 | 10.539 | 0.116 |
| 5 | 8319 | 9376 | 67.37 | 156.96 | 1.046 | 3.979 | 3.629 | 1.644 | 10.923 | -0.009 |
| Worst | 8329 | 9497 | 64.29 | 151.63 | 0.558 | 2.189 | 3.405 | 1.123 | 9.027 | -0.009 |

| Item | Result |
| :--- | :--- |
| Controller | Setup slack between +3.405 and +3.857 ns in the five seeds (against -0.745 to -0.173 ns at 142.857 MHz); the worst path became internal to the debug master. The pin read path has +4.0 ns of slack (seed 1) |
| `DRAM_CLK` | Setup slack between +1.123 and +1.678 ns (against -0.127 to +0.429 ns) |
| Core and fetch | Non-negative slack in the five seeds with the 8250 ps phase (worst +0.558 ns in the core and +2.189 ns in fetch) |
| Hold | Positive in all domains and seeds, except the JTAG clock (`altera_reserved_tck`) of seed 5, with -0.009 ns in the fast model at 0 °C. It is in the JTAG hub, not in the SDRAM, and in seeds 1 to 4 the smallest hold is +0.079 ns |
| Area | 8265 to 8329 ALMs. With the same sources and the controller at 142.857 MHz seed 1 uses 8319 ALMs and 9354 registers, against 8265 and 9404 at 100 MHz, so the change does not alter the area measurably |

## 6. SDRAM throughput

The programs `cpi-data`, `sdram-copy`, `sdram-loop`, `cache-sweep`, `code-sweep`, `sdram-memtest`, `sdram-bytes` and `selfmod-repeat` run in simulation in the four scenarios (core at 100 and 50 MHz, controller at 7 and 10 ns) and pass in all of them. The table gives the simulated time to the end of the program, in ns.

| Program | 100 MHz, 7 ns | 100 MHz, 10 ns | Change | 50 MHz, 7 ns | 50 MHz, 10 ns | Change |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sdram-copy` | 2 337 525 | 2 438 111 | +4.3 % | 4 095 855 | 4 169 991 | +1.8 % |
| `sdram-loop` | 1 414 225 | 1 431 631 | +1.2 % | 2 513 295 | 2 529 311 | +0.6 % |
| `cache-sweep` | 6 607 672 | 6 804 571 | +3.0 % | 12 250 680 | 12 434 821 | +1.5 % |
| `code-sweep` | 15 610 561 | 15 611 351 | 0.0 % | 30 969 632 | 30 970 111 | 0.0 % |
| `sdram-memtest` | 3 382 835 | 3 485 251 | +3.0 % | 6 066 922 | 6 180 551 | +1.9 % |
| `sdram-bytes` | 1 253 995 | 1 257 371 | +0.3 % | 2 246 014 | 2 248 771 | +0.1 % |

The Zihpm counters of the `cpi-data` kernels give the bandwidth and the latency the core sees. `sdram-stream` sweeps 8 KiB with 2048 loads and 512 data cache misses; `sdram-store` does 256 word stores through a write-through cache.

| Measure | 100 MHz, 7 ns | 100 MHz, 10 ns | 50 MHz, 7 ns | 50 MHz, 10 ns |
| :--- | ---: | ---: | ---: | ---: |
| `sdram-stream`, core cycles | 31 349 | 33 810 | 27 728 | 29 234 |
| `sdram-stream`, time (µs) | 313.5 | 338.1 | 554.6 | 584.7 |
| Line read bandwidth (MB/s) | 26.1 | 24.2 | 14.8 | 14.0 |
| External wait per line miss (core cycles) | 33.2 | 38.0 | 26.1 | 29.1 |
| External wait per line miss (ns) | 332 | 380 | 523 | 582 |
| `sdram-store`, external wait per store (core cycles) | 14.0 | 15.0 | 10.6 | 11.0 |
| `sdram-store`, core cycles | 5381 | 5640 | 4500 | 4620 |
| `sdram-load-use`, core cycles (hits) | 2318 | 2322 | 2317 | 2318 |

The 10 ns controller costs 4 to 8 % in the time of a program that only sweeps the SDRAM (`sdram-stream`, `sdram-copy`), 3 % in those that use it with reuse (`cache-sweep`, `sdram-memtest`) and nothing in those that stay in the caches (`sdram-load-use`, `code-sweep`). The cycles-per-instruction figures of the programs that do not use the SDRAM do not change. The slacks and the utilization of each seed are in `dados/sdram-100mhz/tabela-sementes.tsv` and `tabela-ocupacao.tsv`. The full Quartus reports and logs are not versioned; regenerate them with `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <seed>` on the build of the requested seed, which leaves the `.sta.rpt` and `.fit.rpt` in `output_files/`.

## 7. Decision

The chosen option is the controller at 100 MHz with the 1 to 1 bridge, not the fix of the path at 142.857 MHz. The evidence for it is that of section 3 (the sum of the slacks is negative in the five seeds, so no phase closes) and that of section 5 (all domains with slack in the five seeds). The lost throughput is that of section 6, at most 8 % of the time of a program dominated by the SDRAM, well below the 30 % the plan foresaw. Since the controller does not depend on the core frequency, the same bitstream holds in milestones M1 to M4.

## 8. How to reproduce

| Goal | Command |
| :--- | :--- |
| Compile a seed | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <seed>`, in a copy of the repository |
| Change the controller clock or phase | Edit `sdram.clock_hz` and `sdram.dram_clk_phase_ps` in `platform.yaml`, and `output_clock_frequency0`, `output_clock_frequency1` and `phase_shift1` in `src/cyclone-v/de0-cv/pll/sdram_platform_pll.v`, then run `riscv-tools generate-memory-map`; `check-memory-map` verifies that both sides agree |
| Simulate with another clock | `SIM_CLOCK_PERIOD_NS` (period of `CLK`, three times the core's) and `SIM_EXTRA_CLOCKS=CLK_MEM:<ns>` with the parameter `SDRAM_TCK_PS=<ps>` of the simulation top |

## 9. Milestones M1 and M2 with the controller at 100 MHz

The sources are those of the merge with the core track of `onda2` (Core `a826b68`, steps F.P4 and F.P5; Memory `8455a20`; Peripherals `6ed5e07`). The `DRAM_CLK` phase is 4000 ps.

### 9.1. Milestone M1: 50 MHz, core phase at 8250 ps

| Seed | ALMs | Registers | Core Fmax (MHz) | Controller Fmax (MHz) | core | fetch | controller | `DRAM_CLK` | JTAG | min. hold |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7948 | 9155 | 63.78 | 157.98 | 0.976 | 3.623 | 3.670 | 1.679 | 10.598 | 0.091 |
| 2 | 7943 | 9214 | 65.41 | 163.85 | 0.048 | 3.964 | 3.897 | 1.123 | 11.051 | 0.052 |
| 3 | 7956 | 9222 | 67.14 | 172.06 | 1.260 | 2.496 | 4.188 | 1.203 | 10.767 | 0.122 |
| 4 | 7978 | 9178 | 66.48 | 154.66 | 0.979 | 3.689 | 3.534 | 1.172 | 11.000 | 0.132 |
| 5 | 7911 | 9221 | 62.9 | 145.82 | 0.953 | 3.194 | 3.142 | 1.644 | 10.720 | 0.118 |
| Worst | 7978 | 9222 | 62.9 | 145.82 | 0.048 | 2.496 | 3.142 | 1.123 | 10.598 | 0.052 |

| Condition | Result |
| :--- | :--- |
| Non-negative setup slack in all domains (core, fetch, controller, `DRAM_CLK`, JTAG) | Met in the five seeds; the smallest is +0.048 ns in the core (seed 2) |
| Non-negative hold slack in the fast model at 0 °C | Met in the five seeds; the smallest is +0.052 ns |
| Hardware suite on the board with the seed 5 bitstream | 127 programs of the regression and 17 programs of `sdram-flash` pass (`sdram-copy`, `sdram-loop`, `cache-sweep`, `code-sweep`, `flash-const`, `sdram-exec-copy`, `selfmod-repeat`, `sdram-memtest`, `sdram-bytes`, `sdram-refresh` and the others); the three UART-on-pins programs are left out because the board has no UART wired |

M1 closes. The 8250 ps phase is versioned in the PLL and in the `pll` section of `platform.yaml` after this board validation.

### 9.2. Milestone M2: 66.667 MHz

Worst of the five seeds (ns) by core phase, with the controller and `DRAM_CLK` as above.

| Core phase | Core | Fetch | Controller | `DRAM_CLK` | Min. hold |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 8500 ps | -0.366 | 0.194 | 3.377 | 1.123 | 0.022 |
| 8625 ps | -0.217 | -0.035 | 3.320 | 1.123 | 0.123 |
| 8875 ps | 0.567 | -0.272 | 3.315 | 1.123 | 0.117 |

M2 does not close: the instruction cache loop (tag to the PC) and the core loop trade slack with the phase, and none of the three phases leaves both with non-negative slack in the five seeds (8500 ps fails in the core of seeds 2 and 5, 8875 ps in the fetch of seeds 3 and 4, and 8625 ps in the core of seed 2, with -0.217 ns, and in the fetch of seeds 3 and 4, with -0.035 ns at worst). The controller and `DRAM_CLK` no longer limit the milestone.

### 9.3. Milestones M3 and M4

[FRENTE-F-ONDA2.md](FRENTE-F-ONDA2.md) measures the core and the fetch at 83.333 MHz and at 100 MHz with steps F.P4 and F.P5: the core is at -0.09 to -1.79 ns at 83.333 MHz and the loop of CSR read feeding the write of the Zihpm counter has 12.3 ns of data against the 10 ns period. The SDRAM controller and `DRAM_CLK` are no longer part of what is missing: at 100 MHz they have 3.1 ns and 1.1 ns of slack (section 5). M3 and M4 do not close, and what is missing is only the core loop.

## 10. Per-seed tables

The values come from `dados/sdram-100mhz/tabela-sementes.tsv`, generated by `dados/tabelar_resumos.py` from the Timing Analyzer `.sta.summary` files (slow model, 1100 mV, 85 °C). Each table lists, per seed, the worst setup, the worst hold and the domain where each occurs. The domains are `core` (PLL output 3), `fetch` (output 2), `mem` (output 0, the SDRAM controller), `DRAM_CLK` (pin) and `jtag`; in the `core_fpga_test` top the PLL outputs appear as `pll_c0` and `pll_c1`, and `pll_dram_clk` and `pll_vco` only have minimum pulse width. The TSV also carries TNS, recovery, removal, minimum pulse width and the worst value among the four temperature and voltage models. The utilization per seed is in `dados/sdram-100mhz/tabela-ocupacao.tsv`.

The measurements describe the platform frozen at 76.923077 MHz and the listed experiments. A new frequency attack regenerates the table with `python3 dados/tabelar_resumos.py gerar dados/sdram-100mhz` over the `.resumo.txt` files of the new seeds (the Quartus `.sta.summary` and `.fit.summary`, renamed), and `--check` compares the TSV against them. The raw summaries are not versioned, and the tables are the starting reference for the next round.

### 10.1. `antes-142mhz`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0.745 | mem | 0.286 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |

### 10.2. `fase3000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.679 | DRAM_CLK | 0.306 | core |
| 2 | 0.123 | DRAM_CLK | 0.181 | jtag |
| 3 | 0.204 | DRAM_CLK | 0.267 | core |
| 4 | 0.172 | DRAM_CLK | 0.300 | core |
| 5 | 0.660 | DRAM_CLK | 0.310 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 8,297 / 18,480 ( 45 % ) | 9387 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 2 | 8,304 / 18,480 ( 45 % ) | 9368 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 3 | 8,322 / 18,480 ( 45 % ) | 9483 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 4 | 8,297 / 18,480 ( 45 % ) | 9470 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 5 | 8,294 / 18,480 ( 45 % ) | 9395 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |

### 10.3. `fase4000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.873 | core | 0.297 | core |
| 2 | 0.262 | core | 0.157 | jtag |
| 3 | 1.204 | DRAM_CLK | 0.268 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 8,297 / 18,480 ( 45 % ) | 9375 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 2 | 8,304 / 18,480 ( 45 % ) | 9433 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 3 | 8,322 / 18,480 ( 45 % ) | 9493 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |

### 10.4. `fase4000-final`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.558 | core | 0.265 | core |
| 2 | 0.610 | core | 0.271 | core |
| 3 | 1.203 | DRAM_CLK | 0.293 | core |
| 4 | 1.172 | DRAM_CLK | 0.289 | core |
| 5 | 1.046 | core | 0.253 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 8,265 / 18,480 ( 45 % ) | 9404 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 2 | 8,329 / 18,480 ( 45 % ) | 9497 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 3 | 8,293 / 18,480 ( 45 % ) | 9451 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 4 | 8,288 / 18,480 ( 45 % ) | 9437 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 5 | 8,319 / 18,480 ( 45 % ) | 9376 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |

### 10.5. `marco-m1-50mhz-fase8250`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.976 | core | 0.290 | core |
| 2 | 0.048 | core | 0.275 | core |
| 3 | 1.203 | DRAM_CLK | 0.262 | core |
| 4 | 0.979 | core | 0.268 | core |
| 5 | 0.953 | core | 0.266 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 7,948 / 18,480 ( 43 % ) | 9155 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 2 | 7,943 / 18,480 ( 43 % ) | 9214 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 3 | 7,956 / 18,480 ( 43 % ) | 9222 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 4 | 7,978 / 18,480 ( 43 % ) | 9178 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 5 | 7,911 / 18,480 ( 43 % ) | 9221 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |

### 10.6. `marco-m2-66mhz-fase8500`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.793 | fetch | 0.266 | core |
| 2 | -0.366 | core | 0.181 | jtag |
| 3 | 0.194 | fetch | 0.289 | core |
| 4 | 0.437 | fetch | 0.269 | core |
| 5 | -0.066 | core | 0.268 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 7,944 / 18,480 ( 43 % ) | 9315 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 2 | 7,965 / 18,480 ( 43 % ) | 9276 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 3 | 7,988 / 18,480 ( 43 % ) | 9301 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 4 | 7,978 / 18,480 ( 43 % ) | 9279 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 5 | 7,980 / 18,480 ( 43 % ) | 9261 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |

### 10.7. `marco-m2-66mhz-fase8625`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.381 | fetch | 0.262 | core |
| 2 | -0.217 | core | 0.262 | core |
| 3 | -0.019 | fetch | 0.261 | core |
| 4 | -0.035 | fetch | 0.270 | core |
| 5 | 0.150 | core | 0.267 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 7,973 / 18,480 ( 43 % ) | 9208 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 2 | 7,961 / 18,480 ( 43 % ) | 9308 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 3 | 7,988 / 18,480 ( 43 % ) | 9300 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 4 | 7,991 / 18,480 ( 43 % ) | 9318 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 5 | 7,961 / 18,480 ( 43 % ) | 9217 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |

### 10.8. `marco-m2-66mhz-fase8875`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 0.202 | fetch | 0.266 | core |
| 2 | 0.539 | fetch | 0.269 | core |
| 3 | -0.160 | fetch | 0.268 | core |
| 4 | -0.272 | fetch | 0.266 | core |
| 5 | 0.477 | fetch | 0.267 | core |

| Seed | ALMs | Registers | Pins | RAM blocks |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 7,969 / 18,480 ( 43 % ) | 9272 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 2 | 7,972 / 18,480 ( 43 % ) | 9257 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 3 | 7,998 / 18,480 ( 43 % ) | 9355 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 4 | 7,966 / 18,480 ( 43 % ) | 9250 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |
| 5 | 7,996 / 18,480 ( 43 % ) | 9302 | 93 / 224 ( 42 % ) | 272 / 308 ( 88 % ) |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
