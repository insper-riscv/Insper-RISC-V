# Timing and cycles-per-instruction baseline of the `de0-cv` platform

🌐 [Português](../../../pt-br/platform/timing/README.md) · [English](README.md)

## 1. Scope

This document records the measurement of the `de0-cv` platform with the `rv32im_zicclsm_zicntr_zihpm_zifencei` profile (29 event counters of 64 bits) before any structural step of the 100 MHz front. It gives the Fmax and the critical paths of the bitstream (section 3), the cycles per instruction of the reference programs in simulation (section 4), and the review of the clock domain crossings and of the `.sdc` (section 5). The reference for the 100 MHz closure criterion is the Quartus worst case (slow model at 85 °C for setup, fast model at 0 °C for hold), recorded as the worst of seeds 1 to 5. The full compile of the new Core on the three tops and the cost of interrupts are in [core-novo.md](core-novo.md).

## 2. Measurement conditions

| Item | Value |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, on the PC1 workstation |
| Device | 5CEBA4F23C7 (Cyclone V) |
| Sources | Insper-RISC-V `4daff3e`, Core `a5f6920`, Memory `743f095`, Peripherals `f773791`, Common-Components `ddbfdcb` |
| Top and project | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, the `.sdc` of section 5 |
| Mode | `HIGH PERFORMANCE EFFORT`, seeds 1 to 5, through `de0-cv_synth.tcl` |
| Clocks at 50 MHz | The PLL as versioned (core and fetch at 50 MHz, core phase 6625 ps, controller and `DRAM_CLK` at 142.857 MHz) |
| Clocks at 100 MHz | The same PLL with outputs 2 and 3 at 100 MHz and the core phase at 3125 ps; only the Quartus working copy changes, the repository does not |
| `time` tick count | 50 cycles in both builds, which does not change the timing |

The per-domain slacks of each seed are in `dados/tabela-sementes.tsv` (section 7). The full Quartus reports and logs are not versioned; regenerate them with `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <seed>` on the build of the requested seed, which leaves the `.sta.rpt` and `.fit.rpt` in `output_files/`. The script `dados/pares-de-dominios.tcl` extracts the paths by pair of source and destination clocks.

## 3. Fmax and critical path

### 3.1. Slack per domain

The domains are the core (clock `clk_idexmem`), the fetch (`clk_if`), the SDRAM controller (142.857 MHz), `DRAM_CLK` and the JTAG. The table gives the setup slack in the slow model at 85 °C (ns) for each seed and the worst of the five.

| Core clock | Domain | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 MHz | Core | -1.103 | -1.604 | -0.224 | -0.388 | -0.783 | -1.604 |
| 50 MHz | Fetch | 4.743 | 5.233 | 4.327 | 4.636 | 3.649 | 3.649 |
| 50 MHz | SDRAM controller | -0.745 | -0.255 | -0.205 | -0.173 | -0.713 | -0.745 |
| 50 MHz | `DRAM_CLK` | 0.429 | -0.127 | -0.046 | -0.078 | 0.394 | -0.127 |
| 50 MHz | JTAG | 10.814 | 9.048 | 10.578 | 10.455 | 9.746 | 9.048 |
| 100 MHz | Core | -5.022 | -5.848 | -4.058 | -4.816 | -3.713 | -5.848 |
| 100 MHz | Fetch | -0.453 | 0.016 | -1.051 | -1.036 | -0.264 | -1.051 |
| 100 MHz | SDRAM controller | -0.744 | -0.220 | -0.205 | -0.173 | -0.713 | -0.744 |
| 100 MHz | `DRAM_CLK` | 0.428 | -0.162 | -0.046 | -0.078 | 0.394 | -0.162 |
| 100 MHz | JTAG | 10.215 | 10.647 | 10.661 | 10.781 | 10.459 | 10.215 |

The hold slack in the fast model at 0 °C is positive in every domain and seed. The worst value is 0.087 ns (JTAG, 100 MHz, seed 3); in the core it is 0.121 ns (100 MHz) and 0.132 ns (50 MHz).

The core-domain Fmax that Quartus reports (only paths between registers of the same clock, slow model at 85 °C) is in the table below.

| Core clock | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 MHz | 65.73 | 66.92 | 64.30 | 65.98 | 66.15 | 64.30 MHz |
| 100 MHz | 79.35 | 83.14 | 81.73 | 81.40 | 81.32 | 79.35 MHz |

The Fmax rises with the constraint because the fitter works harder when the requested clock is higher. The 50 MHz value is that of the project as delivered (about 64 to 67 MHz); the 100 MHz value shows what the fitter gets out of the same RTL under pressure.

### 3.2. Critical paths by pair of clocks

The slack that Quartus assigns to a destination clock mixes paths between different clocks, because the fetch and the core have the same frequency with different phases. The table separates the pairs (slack and data delay, in ns, of the worst path of each pair, slow model at 85 °C).

| Core clock | Source to destination pair | S1 | S2 | S3 | S4 | S5 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 50 MHz | core to core | 4.787 (15.01) | 5.057 (14.72) | 4.448 (15.28) | 4.844 (15.83) | 4.882 (14.89) |
| 50 MHz | core to fetch | 4.743 (8.12) | 5.233 (8.08) | 4.327 (7.96) | 4.636 (7.69) | 3.649 (9.18) |
| 50 MHz | fetch to core | -1.103 (5.25) | -1.604 (5.21) | -0.224 (4.85) | -0.388 (5.02) | -0.783 (4.92) |
| 100 MHz | core to core | -2.602 (12.38) | -2.028 (11.85) | -2.236 (12.04) | -2.285 (12.01) | -2.297 (12.09) |
| 100 MHz | core to fetch | -0.453 (6.77) | 0.016 (6.79) | -1.051 (6.83) | -1.036 (6.81) | -0.264 (6.60) |
| 100 MHz | fetch to core | -5.022 (5.71) | -5.848 (5.94) | -4.058 (5.20) | -4.816 (5.96) | -3.713 (4.35) |

The three pairs correspond to three different loops.

| Pair | Worst-case path | Reading |
| :--- | :--- | :--- |
| core to core | `EX/MEM r_alu_out` and `EX/MEM r_we_ok` (ALU result and the decision to commit the instruction) to the PC, `IF/ID`, `mtval`, the RAM write and the `counter64` registers of the event counters | About 12 ns of data at 100 MHz and 15 ns at 50 MHz. The exception and discard decision, taken in EX with the ALU, reaches all these destinations; the counters are destinations of the same signal, not the origin of the delay |
| fetch to core | The instruction cache tag RAM (`tag_ram`, in the fetch clock) to the PC register (`u_pc_fetch`, in the core clock) | 4.4 to 6.0 ns of data in a 3.125 ns window at 100 MHz (6.625 ns at 50 MHz). It is the worst path of the bitstream in every seed |
| core to fetch | The PC (`u_pc_reg`) to the address and `valid_rd` of the instruction cache | 6.6 to 6.8 ns of data at 100 MHz in a 6.875 ns window |

The loop through the instruction cache (PC, tag, PC) adds up to about 12 ns of data (6.8 ns from the PC to the cache plus 4.4 to 6.0 ns from the tag to the PC), so no phase between the two clocks closes 10 ns. Section 5.3 shows the phase sweep that confirms it.

### 3.3. Resource count

| Core clock | ALMs (of 18 480) | Registers | RAM blocks |
| :--- | ---: | ---: | ---: |
| 50 MHz | 8 037 to 8 090 (44 %) | 9 142 to 9 241 | 271 of 308 (88 %) |
| 100 MHz | 9 174 to 9 270 (50 %) | 10 769 to 10 852 | 271 of 308 (88 %) |

The difference of about 1 200 ALMs between the two frequencies is the register duplication that the fitter does to shorten the paths.

### 3.4. Cost of the event counters at 100 MHz

The same 100 MHz compilation with `HPM_COUNTERS` at 29, 4 and 0 (width 64), changed only in the default value of the generic of the working copy, in seeds 3 and 5.

| Counters | ALMs (S3 and S5) | Registers (S3 and S5) | core to core (S3 and S5) | fetch to core (S3 and S5) |
| ---: | :--- | :--- | :--- | :--- |
| 29 | 9 270 and 9 174 | 10 769 and 10 784 | -2.236 and -2.297 | -4.058 and -3.713 |
| 4 | 6 263 and 6 259 | 8 143 and 8 180 | -2.218 and -2.193 | -3.669 and -3.975 |
| 0 | 5 872 and 5 836 | 7 534 and 7 537 | -1.953 and -2.091 | -4.232 and -3.802 |

The 29 counters cost about 3 000 ALMs more than 4, and 4 counters cost about 400 ALMs more than none. The slack of the core loop varies by less than 0.35 ns among the three cases, within the variation between seeds, so the counters do not limit the core loop; they show up in the report only as destinations of the instruction commit signal.

## 4. Cycles per instruction in simulation

### 4.1. Method

The programs `cpi-core`, `cpi-data` and `cpi-fetch` (sources in `dados/programas/`, with the header `rv32_cpi.h`, under `docs/pt-br/platform/timing/`) run, copied into `c-sdram/` and `tools/riscv_build/include-sdram/` of the Tests repository, in the `de0-cv` simulation (top `rv32im_sdram_flash_sim_test`, FLASH with 24 edges to the first word and 4 between the following ones, 4 KiB caches with 16-byte lines). Each kernel runs twice between reads of `cycle`, `instret` and eight Zihpm event counters; the first pass starts with cold caches and the second with the caches the first one left. The cost of an empty window is subtracted. The counts are deterministic and equal on the board and in simulation. The raw values are in `dados/cpi-simulacao.txt`.

The counted events are

| Column | Event | Meaning |
| :--- | :--- | :--- |
| e1 | 1 | Multiply or divide stall cycles |
| e2 | 2 | External memory wait cycles |
| e3 | 3 | Taken branches or jumps |
| e5 | 5 | Instruction cache misses |
| e6 | 6 | Data cache misses |
| e7 | 7 | FLASH wait cycles |
| e8 | 8 | Load-use stall cycles |
| e9 | 9 | Fused multiply or divide operations |

### 4.2. Result

The table shows the warm pass with its events; the miss and FLASH wait columns of the cold pass are in 4.3.

| Kernel | Instructions | Cycles | CPI | e1 | e2 | e3 | e5 | e6 | e7 | e8 | e9 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `int-loop` (256 rounds of add, xor and shift) | 1285 | 1805 | 1.40 | 0 | 10 | 255 | 0 | 0 | 8 | 0 | 0 |
| `branches` (256 rounds, half taken) | 1157 | 1932 | 1.67 | 0 | 9 | 383 | 0 | 0 | 0 | 0 | 0 |
| `mul` (128 independent MUL) | 645 | 5388 | 8.35 | 4480 | 9 | 127 | 0 | 0 | 0 | 0 | 0 |
| `mulh-mul-fused` (64 MULH, MUL pairs with the same operands) | 392 | 2960 | 7.55 | 2432 | 10 | 63 | 0 | 0 | 0 | 0 | 64 |
| `mulh-mul-plain` (64 pairs with different operands) | 458 | 5074 | 11.08 | 4480 | 10 | 63 | 0 | 0 | 0 | 0 | 0 |
| `div-rem-fused` (32 DIV, REM pairs with the same operands) | 198 | 1550 | 7.83 | 1280 | 10 | 31 | 0 | 0 | 0 | 0 | 32 |
| `div-div-plain` (32 DIV, DIV pairs with different operands) | 231 | 2671 | 11.56 | 2368 | 10 | 31 | 0 | 0 | 0 | 0 | 0 |
| `sdram-load-use` (256 loads of 1 KiB of SDRAM, used at once) | 1029 | 2315 | 2.25 | 0 | 520 | 255 | 0 | 0 | 0 | 256 | 0 |
| `sdram-stream` (2048 loads sweeping 8 KiB of SDRAM) | 8197 | 26705 | 3.26 | 0 | 12366 | 2047 | 0 | 512 | 0 | 2048 | 0 |
| `sdram-store` (256 word stores) | 1283 | 4303 | 3.35 | 0 | 2510 | 255 | 0 | 0 | 0 | 0 | 0 |
| `flash-small` (256 loads of 1 KiB of FLASH constants) | 1030 | 2321 | 2.25 | 0 | 525 | 255 | 0 | 0 | 0 | 256 | 0 |
| `flash-stream` (2048 loads sweeping 8 KiB of FLASH) | 8199 | 41997 | 5.12 | 0 | 27656 | 2047 | 0 | 512 | 18432 | 2048 | 0 |
| `fetch-straight` (2048 straight-line instructions, 8 KiB) | 2048 | 25364 | 12.38 | 0 | -1 | 0 | 519 | 0 | 18682 | 0 | 0 |
| `fetch-loop` (1024 rounds of 4 instructions) | 4097 | 6143 | 1.50 | 0 | 0 | 1023 | 0 | 0 | -2 | 0 | 0 |

The values -1 and -2 come from the subtraction of the empty window and mean zero.

### 4.3. Cold pass

| Kernel | Cold cycles | Cold CPI | e5 | e6 | e7 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `int-loop` | 1894 | 1.47 | 3 | 0 | 88 |
| `branches` | 2137 | 1.85 | 9 | 0 | 324 |
| `mul` | 5558 | 8.62 | 8 | 0 | 288 |
| `mulh-mul-fused` | 3289 | 8.39 | 10 | 0 | 360 |
| `mulh-mul-plain` | 5333 | 11.64 | 11 | 0 | 396 |
| `div-rem-fused` | 1806 | 9.12 | 10 | 0 | 360 |
| `div-div-plain` | 2883 | 12.48 | 10 | 0 | 360 |
| `sdram-load-use` | 3385 | 3.29 | 3 | 64 | 87 |
| `sdram-stream` | 26993 | 3.29 | 8 | 512 | 288 |
| `sdram-store` | 4558 | 3.55 | 7 | 0 | 252 |
| `flash-small` | 5554 | 5.39 | 8 | 64 | 2592 |
| `flash-stream` | 39536 | 4.82 | 8 | 452 | 16560 |
| `fetch-straight` | 25132 | 12.27 | 514 | 0 | 18538 |
| `fetch-loop` | 6347 | 1.55 | 6 | 0 | 214 |

### 4.4. Reading the numbers

| Quantity | Value | How it comes out |
| :--- | ---: | :--- |
| Taken branch penalty | 2 cycles | `int-loop`: (1805 - 1285) / 255 rounds |
| Cost of a MUL | 35 stall cycles | `mul`: 4480 / 128 |
| Cost of a fused MULH and MUL pair | 46 cycles | `mulh-mul-fused`: 2960 / 64; without fusion it is 79 cycles (`mulh-mul-plain`) |
| Cost of a fused DIV and REM pair | 48 cycles | `div-rem-fused`: 1550 / 32; without fusion it is 83 cycles (`div-div-plain`) |
| SDRAM load that hits the data cache | 9 cycles per round of 4 instructions | `sdram-load-use`: 2315 / 256, with 2 of external wait, 1 of load-use and 2 of branch |
| SDRAM load that misses the data cache | 13 cycles per load | `sdram-stream`: 26705 / 2048, one miss in every four loads |
| FLASH load that misses the data cache | 20.5 cycles per load | `flash-stream`: 41997 / 2048 |
| FLASH instruction fetch miss | about 49 cycles per line of four instructions | `fetch-straight`: 25364 / 512 lines, against 4 ideal |
| SDRAM word store | 17 cycles per round | `sdram-store`: 4303 / 256, with 10 of external wait per store (write-through cache) |

Multiplication and division dominate the CPI of the kernels that use them: the MUL costs 35 stall cycles per operation and fusion cuts the pair to about 58 percent of the unfused cost (a 42 percent saving). The acceptance criterion of each structural step of the front (frequency divided by CPI) uses this table as its reference.

## 5. Clock domain crossings and `.sdc`

### 5.1. Crossings of the bitstream

The bitstream has five clocks: the core and the fetch (the same frequency, different phases), the SDRAM controller, `DRAM_CLK` and the JTAG. The crossings and the constraint of each one are

| Crossing | Mechanism in the RTL | Constraint in the `.sdc` | Situation at 100 MHz |
| :--- | :--- | :--- | :--- |
| Core and fetch to the controller, and back (SDRAM bridge) | Request, answer and initialization toggles through a two flip-flop synchronizer; buses held until the answer | `set_max_delay` of 10 ns and `set_min_delay` of -10 ns in both directions | The 10 ns bound is below two edges of the controller (20 ns at 100 MHz) and of the core (20 ns), so it holds from 50 to 100 MHz |
| JTAG to the controller (SDRAM debug port) | Command toggle and initialization flag through a two flip-flop synchronizer | The same pair of bounds, between the controller and the JTAG | Holds |
| Core to the JTAG (UART and display) | Command, answer and write toggles through a two flip-flop synchronizer; byte and value held until the toggle | The same pair of bounds, between the core and the JTAG | Holds |
| Fetch to the core and back | Same frequency with a fixed phase; the PC feeds the cache and the tag returns to the PC | No exception: Quartus times it as a synchronous path with the phase difference | Worst path of the bitstream (section 3.2) |
| Controller to the SDRAM pins | Output and input registers of the controller | `set_output_delay`, `set_input_delay` and a 2-cycle multicycle path on `DRAM_CLK_pin` | Slack from +1.123 to +4.0 ns in the five seeds with the controller at 100 MHz, on the `DRAM_DQ` pin (input) and on `o_dram_dq_oe` (output); see [sdram-100mhz.md](sdram-100mhz.md) |
| Reset button | `FPGA_RESET_N` and the PLL lock form `core_reset` | `set_false_path` from `FPGA_RESET_N` | The controller reset goes through a two flip-flop synchronizer (`rst_sr`); the core and the fetch use `core_reset` directly, with no deassertion synchronizer |

Quartus reports 88 synchronizer chains (MTBF above 10^9 years), which covers the two flip-flop synchronizers of `Common-Components` and the chains of the JTAG hub itself.

### 5.2. Review of the `.sdc`

The `.sdc` does not depend on the core frequency: the only clock created is the 50 MHz board clock, and the derived PLL brings the other frequencies. The review for 100 MHz changes two things.

| Change | Reason |
| :--- | :--- |
| `set_false_path -to` on the outputs `HEX0` to `HEX5` | The display register is written by the core and drives the pins directly, with no timing requirement; the 42 outputs showed up unconstrained in the report |
| Comment that gives the 10 ns bound against the synchronizer latency | Records that the value holds from 50 to 100 MHz of the core |

After the review, the unconstrained paths report drops from 43 outputs to 1 (the `altera_reserved_tdo` of the JTAG hub, from Quartus itself) and from 173 to 5 output paths; no slack changes, because the paths that gained the exception had no requirement.

Two design points stay outside the `.sdc` and matter for the 100 MHz front.

| Point | Effect |
| :--- | :--- |
| The `tick_cycles` of the top is 50 | The Zicntr `time` tick is 1 MHz only with the core at 50 MHz; at 100 MHz the value becomes 100 |
| The core and fetch resets have no deassertion synchronizer | The deassertion edge of `core_reset` comes from the button and the PLL lock, with no phase relation to the core and fetch clocks; the metastability report does not cover this path |

### 5.3. Core clock phase sweep at 100 MHz

The phase of the core clock relative to the fetch clock (125 ps step of the 1000 MHz VCO) splits the 10 ns between the fetch-to-core and core-to-fetch paths. The table gives the worst path of each pair (slack in ns, slow model at 85 °C) for three phases.

| Phase | Seed | core to core | core to fetch | fetch to core |
| :--- | :--- | ---: | ---: | ---: |
| 3125 ps | 3 | -2.236 | -1.051 | -4.058 |
| 3125 ps | 5 | -2.297 | -0.264 | -3.713 |
| 5000 ps | 3 | -2.002 | -2.862 | -1.939 |
| 5000 ps | 5 | -2.460 | -2.614 | -2.018 |
| 6250 ps | 5 | -2.438 | -3.531 | -1.863 |

No phase takes the three pairs to non-negative slack. The 5000 ps phase balances the two crossings at about -2 ns, the same value as the core's own loop; closing at 100 MHz requires shortening the core loop (exception decision in MEM, registered load data) and the loop through the instruction cache (registered tag), not only adjusting the phase.

## 6. How to reproduce

| Goal | Command |
| :--- | :--- |
| Compile one seed | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <seed>`, on a copy of the repository |
| Change the frequency | Edit `output_clock_frequency2`, `output_clock_frequency3` and `phase_shift3` of `src/cyclone-v/de0-cv/pll/sdram_platform_pll.v` in the copy |
| Slack per domain | `output_files/de0-cv.sta.summary` and `output_files/de0-cv.sta.rpt` |
| Paths by register | `riscv-tools timing-paths --npaths 300` on the compiled project |
| Paths by pair of clocks | `quartus_sta -t docs/pt-br/platform/timing/dados/pares-de-dominios.tcl de0-cv 400 slow` in the compiled project folder |
| Cycles per instruction | In the Tests repository, after copying `dados/programas/cpi-<name>.c` to `c-sdram/cpi-<name>/src.c` and `rv32_cpi.h` to `tools/riscv_build/include-sdram/`, `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit hex` and then `sim --only cpi-core,cpi-data,cpi-fetch` |

## 7. Per-seed tables

The values come from `dados/tabela-sementes.tsv`, generated by `dados/tabelar_resumos.py` from the Timing Analyzer `.sta.summary` files (slow model, 1100 mV, 85 °C). Each table lists, per seed, the worst setup, the worst hold and the domain where each occurs. The domains are `core` (PLL output 3), `fetch` (output 2), `mem` (output 0, the SDRAM controller), `DRAM_CLK` (pin) and `jtag`; in the `core_fpga_test` top the PLL outputs appear as `pll_c0` and `pll_c1`, and `pll_dram_clk` and `pll_vco` only have minimum pulse width. The TSV also carries TNS, recovery, removal, minimum pulse width and the worst value among the four temperature and voltage models.

The measurements describe the platform frozen at 76.923077 MHz and the listed experiments. A new frequency attack regenerates the table with `python3 dados/tabelar_resumos.py gerar dados` over the `.resumo.txt` files of the new seeds (the Quartus `.sta.summary` and `.fit.summary`, renamed), and `--check` compares the TSV against them. The raw summaries are not versioned, and the tables are the starting reference for the next round.

### 7.1. `50mhz`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -1.103 | core | 0.293 | core |
| 2 | -1.604 | core | 0.307 | core |
| 3 | -0.224 | core | 0.271 | core |
| 4 | -0.388 | core | 0.267 | core |
| 5 | -0.783 | core | 0.267 | core |

### 7.2. `100mhz`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -5.022 | core | 0.261 | core |
| 2 | -5.848 | core | 0.254 | core |
| 3 | -4.058 | core | 0.268 | core |
| 4 | -4.816 | core | 0.266 | core |
| 5 | -3.713 | core | 0.267 | core |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
