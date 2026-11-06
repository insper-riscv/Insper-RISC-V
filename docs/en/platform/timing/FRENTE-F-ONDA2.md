# Front F in Wave 2: steps F.P4 and F.P5 and milestone M3

🌐 [Português](../../../pt-br/platform/timing/FRENTE-F-ONDA2.md) · [English](FRENTE-F-ONDA2.md)

## 1. Scope

This document measures the `de0-cv` with steps F.P4 (address class registered in EX/MEM) and F.P5 (fetch loop and instruction cache) and checks milestone M3 (core clock between 80 and 100 MHz). The steps are described in `Core/docs/en/timing/P4_*.md` and `P5_*.md` and in `Memory/docs/en/cache/icache.md`. The reference is the Quartus worst case: slow model at 85 °C for setup, fast model at 0 °C for hold.

## 2. Measurement conditions

| Item | Value |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, on workstation PC1 |
| Device | 5CEBA4F23C7 (Cyclone V) |
| Top and project | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, versioned `.sdc` |
| Mode | `HIGH PERFORMANCE EFFORT`, through `de0-cv_synth.tcl` |
| Clocks | PLL outputs 2 (fetch, phase 0) and 3 (core, indicated phase) at the indicated frequency; the SDRAM controller and `DRAM_CLK` stay at 142.857 MHz; only the working copy changes, not the repository |
| Milestone frequency | 83.333 MHz (divider 12 of the 1000 MHz VCO), the lowest frequency the PLL can make above 80 MHz |
| Clock pairs | `c3` is the core clock, `c2` the fetch clock; `c2>c3` is the path from the instruction cache to the PC, `c3>c2` from the PC to the cache |

The summaries and the worst paths per pair are in `dados/frente-f-onda2/`.

## 3. Result at 83.333 MHz, core phase at 6000 ps, seeds 1 to 5

| Domain | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core (`c3`) | -0.698 | -1.786 | -0.475 | -0.086 | -1.322 | -1.786 |
| Fetch (`c2`) | 0.003 | 0.266 | -0.294 | -0.762 | -0.186 | -0.762 |
| SDRAM controller | -0.742 | -0.255 | -0.205 | -0.173 | -0.728 | -0.742 |
| `DRAM_CLK` | 0.426 | -0.127 | -0.046 | -0.078 | 0.410 | -0.127 |
| JTAG | 9.990 | 10.658 | 8.803 | 9.898 | 8.300 | 8.300 |
| Lowest hold, fast model at 0 °C | 0.123 | 0.130 | 0.136 | 0.086 | 0.102 | 0.086 |
| ALMs | 8,940 | 8 947 | 9 159 | 9 162 | 8 941 | 9 162 |

M3 does not close: the core and the fetch are negative in all seeds but one, and the SDRAM controller and `DRAM_CLK` (step F.P6, another track) stay negative.

## 4. Before and after the steps, seed 1

| Measure | Before (Core `8a828cc`, Memory `1160ae1`) | After |
| :--- | ---: | ---: |
| 83.333 MHz, phase 6000: worst pair | -1.039 ns (`c3>c2`, PC to the valid bit) | -0.698 ns (`c2>c3`, tag to the PC) |
| 83.333 MHz, phase 6000: core to core | -0.639 ns | -0.289 ns |
| 100 MHz, phase 5000: core to core | -2.453 ns (12.2 ns of data) | -2.687 ns (12.5 ns of data) |
| 100 MHz: PC to the cache | -2.610 ns (7.1 ns of data) | outside the 400 worst paths |
| ALMs at 100 MHz (phase 5000) | 9 636 | 9 281 |

## 5. What limits the rest

| Path (slow model, 100 MHz) | Data | Reading |
| :--- | ---: | :--- |
| CSR read feeding the CSR write: Zihpm counter, 29-counter multiplexer, `csr_file`, destination counter | 12.3 ns | Nine logic levels with 1.3 to 1.9 ns of routing between levels; the loop is a `csrrs`, `csrrc` or `csrrw` on a counter |
| `r_we_ok`, `r_fwd_match_rs*` and `r_imm` to the counter registers and the PC | 12.0 to 12.4 ns | The confirmation of the EX instruction reaches every counter |
| Instruction-cache tag to the PC enable | 4.2 to 5.0 ns | 2.5 ns are the tag RAM output, the rest is the hit and the PC enable |

None of these is a small step: the first needs the counter write moved out of the cycle of the read (with forwarding or a stall for the next `csr`), and the last needs the instruction cache to deliver the hit already registered, which changes the fetch contract and puts the cache read in a stage of its own.

## 6. Verdict

| Milestone | Result |
| :--- | :--- |
| M3 (80 MHz) | Does not close. Worst core slack -1.786 ns and fetch slack -0.762 ns at 83.333 MHz; SDRAM and `DRAM_CLK` also negative |
| M4 (100 MHz) | Does not close. The core loop has about 12.3 ns of data against the 10 ns period |

The last milestone with the core closed is still M1 of [MARCOS.md](MARCOS.md) (50 MHz with the core phase at 8250 ps); what keeps M1 from closing is only the SDRAM controller.

## 7. Registered Zihpm read (step F.P6c)

Step F.P6c (`Core/docs/en/timing/P6_LEITURA_REGISTRADA_DO_ZIHPM.md`) takes the 29-counter multiplexer out of the CSR read-write loop. The table gives seed 1 at 100 MHz and the five seeds at 83.333 MHz (phase 6000 ps); the list of paths by number of levels is in [CAMINHOS-POR-NIVEIS.md](CAMINHOS-POR-NIVEIS.md).

| Measure | Before F.P6c | After |
| :--- | ---: | ---: |
| 100 MHz, phase 5000, core to core | -2.687 ns | -2.053 ns |
| 100 MHz, phase 6000, core to core | -2.549 ns | -1.393 ns (11.2 ns of data) |
| Logic levels of the Zihpm bank (maximum) | 10 | 8 |

| Domain at 83.333 MHz | S1 | S2 | S3 | S4 | S5 | Worst |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core (`c3`) | -0.549 | -1.837 | -0.275 | -0.439 | -0.825 | -1.837 |
| Fetch (`c2`) | 0.118 | -0.087 | -0.308 | -0.333 | -0.035 | -0.333 |
| SDRAM controller | -0.745 | -0.255 | -0.204 | -0.173 | -0.713 | -0.745 |
| `DRAM_CLK` | 0.429 | -0.127 | -0.047 | -0.078 | 0.394 | -0.127 |
| Lowest hold, fast model | 0.009 | 0.092 | 0.089 | 0.056 | 0.118 | 0.009 |
| ALMs | 9,067 | 9,062 | 9,062 | 9,005 | 9,045 | 9,067 |

M3 stays open: the worst core path at 83.333 MHz becomes the one from the instruction-cache tag to the PC (4.0 to 4.2 ns of data plus 2.4 ns of RAM clock skew), followed by the Zihpm counter adding to itself and by the instruction confirmation (`r_we_ok`) that reaches the counters, the PC and the address class. The cost of the step is one cycle per CSR instruction that accesses the Zihpm bank.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
