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

The per-seed summaries and the scripts are in `dados/frente-f-onda2/`. The full Quartus reports and logs are not versioned; regenerate them with `dados/frente-f-onda2/run-sementes.sh` on the build of seed N, and `pior_por_par.py` extracts the worst path per domain pair.

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

## 8. The 100 MHz: five seeds, the gap and the gain of each step

### 8.1. Conditions

Insper-RISC-V tree `8e05f01` (Core `9deecac`, Memory `768e81e`, Peripherals `ef0e3d6`, Common-Components `56c293e`), measured with the RTL before the last two changes of table 8.4, with the SDRAM controller and `DRAM_CLK` at 100 MHz of front F.P6, core and fetch at 100 MHz, core phase 6000 ps, `HIGH PERFORMANCE EFFORT`, seeds 1 to 5, slow model at 85 °C. A phase of 5000 ps gives an identical result in the core domain (the fitter does not change the placement because the pairs between the fetch and core clocks have slack).

| Seed | Core (ns) | Data of the worst path (ns) | Fetch | SDRAM controller (ns) | `DRAM_CLK` (ns) | ALMs |
| ---: | ---: | ---: | :--- | ---: | ---: | ---: |
| 1 | -1.418 | 11.3 | positive slack | +2.048 | +1.156 | 10,905 |
| 2 | -1.647 | 11.4 | positive slack | +2.099 | +0.670 | 10,916 |
| 3 | -1.220 | 11.1 | positive slack | +1.792 | +0.660 | 10,887 |
| 4 | -2.300 | 12.1 | positive slack | +1.214 | +1.200 | 10,890 |
| 5 | -1.687 | 11.5 | positive slack | +1.587 | +1.116 | 10,885 |
| Worst | -2.300 | 12.1 | | +1.214 | +0.660 | 10,916 |

The real gap to 100 MHz is the worst core slack: 2.30 ns are missing in the worst seed and 1.22 ns in the best. The pairs with the fetch clock close in every seed, as do the SDRAM controller and `DRAM_CLK`.

### 8.2. Paths above 10 ns of data

The core destinations whose worst path exceeds 10 ns of data are 906 in seed 4 and 476 in seed 1 (of 20,000 destinations analyzed), concentrated in `ID/EX` (212 and 170), the Zihpm bank (178 and 37), `csr_file` (122 and 32), `EX/MEM` (121 and 111), `IF/ID` (97 and 70) and `dcache` (40 and 36).

### 8.3. List by logic levels (seed 4)

| Levels | Data (ns) | Slack (ns) | Endpoints | Source | Destination |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 10 | 11.73 | -1.969 | 1 | `u_reg_mem_wb/r_we_ok` | `u_reg_ex_mem/r_same` |
| 10 | 10.15 | -0.362 | 32 | `u_reg_ex_mem/r_in_main` | `INTERCONNECT/pending[#]` |
| 9 | 12.08 | -2.300 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_rs2_val[#]` |
| 9 | 11.79 | -2.019 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_alu_out[#]` |
| 9 | 11.76 | -1.995 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_rs1_val[#]` |
| 9 | 11.73 | -1.943 | 3 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_ext_ram_op[#]` |
| 9 | 11.69 | -1.930 | 43 | `plic:\PLIC/priorities[#]` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 9 | 11.68 | -1.895 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_valid` |
| 9 | 11.68 | -1.895 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_we_ram` |
| 9 | 11.63 | -1.856 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_pc[#]` |
| 9 | 11.62 | -1.846 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_re_ram` |
| 9 | 11.62 | -1.846 | 3 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_funct#[#]` |
| 9 | 11.62 | -1.846 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_en_ram` |
| 9 | 11.59 | -1.815 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_store_data[#]` |
| 9 | 11.58 | -1.806 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_ok_wr` |
| 9 | 11.57 | -1.800 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_pc#[#]` |
| 9 | 11.53 | -1.795 | 32 | `u_reg_ex_mem/r_in_main` | `DCACHE/pend[#]` |
| 9 | 11.53 | -1.790 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_is_csr` |
| 9 | 11.56 | -1.781 | 4 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_byte_mask[#]` |
| 9 | 11.56 | -1.781 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_imm[#]` |
| 9 | 11.49 | -1.756 | 32 | `plic:\PLIC/priorities[#]` | `u_reg_if_id/r_pc[#]` |
| 9 | 11.46 | -1.737 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_illegal` |
| 9 | 11.47 | -1.735 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_is_muldiv` |
| 9 | 11.47 | -1.734 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_wb_sel[#]` |
| 9 | 11.47 | -1.729 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_sel_pc4_alu` |
| 9 | 11.41 | -1.664 | 3 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_funct#[#]` |
| 9 | 11.39 | -1.652 | 30 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_pc[#]` |
| 9 | 11.39 | -1.649 | 5 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_rd[#]` |
| 9 | 11.41 | -1.634 | 1 | `plic:\PLIC/priorities[#]` | `u_reg_ex_mem/r_in_main` |
| 9 | 11.37 | -1.626 | 8 | `plic:\PLIC/priorities[#]` | `u_reg_id_ex/r_alu_sel[#]` |

| Domain | Destination module | Endpoints | >= 6 levels | >= 8 levels | >= 10 levels | Max levels | Max delay (ns) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| c3 | EX/MEM | 121 | 121 | 121 | 1 | 10 | 11.79 |
| c3 | ext_interconnect INT | 66 | 34 | 32 | 1 | 10 | 10.49 |
| c3 | Zihpm banco | 4079 | 278 | 165 | 0 | 9 | 11.34 |
| c3 | dcache | 740 | 322 | 61 | 0 | 9 | 12.20 |
| c3 | csr_file | 718 | 222 | 124 | 0 | 9 | 11.69 |
| c3 | PC | 393 | 74 | 13 | 0 | 9 | 11.16 |
| c3 | ID/EX | 214 | 214 | 214 | 0 | 9 | 12.08 |
| c3 | clint g_irq CLINT | 155 | 152 | 2 | 0 | 9 | 10.26 |
| c3 | IF/ID | 97 | 97 | 97 | 0 | 9 | 11.49 |
| c3 | IF | 1 | 1 | 1 | 0 | 9 | 11.14 |
| c3 | EX | 465 | 284 | 1 | 0 | 8 | 10.47 |
| c3 | generic_register u_w | 91 | 66 | 8 | 0 | 8 | 10.95 |
| c3 | plic g_irq PLIC | 31 | 25 | 3 | 0 | 8 | 9.56 |
| c3 | seg_display_shell DI | 25 | 25 | 12 | 0 | 8 | 9.26 |
| c3 | trap_seen | 1 | 1 | 1 | 0 | 8 | 10.72 |
| c3 | jtag_uart_shell JTAG | 608 | 497 | 0 | 0 | 7 | 9.95 |
| c3 | flash_cmd_port FLASH | 194 | 100 | 0 | 0 | 7 | 9.52 |
| c3 | icache | 175 | 29 | 0 | 0 | 7 | 8.63 |
| c3 | flash_controller FLA | 80 | 43 | 0 | 0 | 7 | 10.36 |
| c3 | MEM/WB | 46 | 46 | 0 | 0 | 7 | 9.24 |
| c3 | flash_chip FLASH_CHI | 176 | 1 | 0 | 0 | 6 | 9.62 |
| c3 | desalinhado | 34 | 2 | 0 | 0 | 6 | 8.96 |

### 8.4. Gain of each step (core to core at 100 MHz)

| Step | Measured effect |
| :--- | :--- |
| F.P4 (registered address class) | core to core at 83.3 MHz from -0.64 to -0.29 ns; at 100 MHz the path `r_we_ok` to `r_same` becomes one of the worst (11.1 to 11.7 ns) |
| F.P5 (valid bit in RAM, select from the registered address, PC enable one gate from `i_ic_ready`) | takes the fetch loop off the worst list: the fetch to core and core to fetch pairs have positive slack at 100 MHz |
| F.P6c (registered Zihpm read) | at 100 MHz, phase 6000, seed 1: from -2.55 to -1.39 ns |
| IF replay (the PC moves on without waiting for the cache) | closes the `c2>c3` pair; the instruction cache stops limiting the frequency |
| Registered fill writes of the icache and `check_addr` off | take `d_addr_i` and `addr_q` off the lists |
| Interrupt lines through a register at the core input | takes the PLIC `priorities` out of first place (seed 4: from -2.30 to -2.24, the next path is `r_we_ok` to the PC) |
| `maxfan` on `r_we_ok` and on the forwarding selects, and the same-region flag computed in MEM from two registers | no gain in the worst seed (-2.30 to -2.48 against -2.24 to -2.28: within the ±0.5 ns spread between seeds) |
| `counter64` in blocks | not done: after F.P6c the counter no longer appears among the worst paths |

### 8.5. What is missing

The limit is the loop of stage EX: `r_we_ok` or `r_fwd_match_rs*` (forwarding select, fan-out 98), the operand A multiplexer, the ALU (four LUT levels) and, after it, the address class, the branch decision, the clear of `IF/ID`, `ID/EX` and `EX/MEM` and the PC enable, with 11.1 to 12.1 ns of data. A registered branch redirect does not cut the stretch that ends in `r_alu_out` (11.0 to 11.5 ns) and only gains on the clear destinations, so by itself it does not close the 2.3 ns. The candidates left, in order of expected gain:

1. Forwarding to the ALU only from registers (the EX result is registered and used in the next cycle), which takes the forwarding select and multiplexer out of the loop at the cost of one cycle on every immediate data dependency; it fits the five stages.
2. The registered branch and JALR redirect, which cuts the clear destinations (`r_pc`, `r_inst`, `r_valid`, writes), at one more cycle per taken branch.
3. The address class computed from `rs1` and `imm` in parallel with the sum.
4. A LogicLock region for the EX loop, justified only if it measures a routing gain (1.3 to 1.9 ns between levels on the longest paths).

## 9. Closed milestone: 76.923 MHz

The highest frequency that the 1000 MHz PLL delivers and that closes the setup in the slow model at 85 °C and the hold in the fast model at 0 °C in every domain of the five seeds is 1000 / 13 = 76.923077 MHz, with the core phase at 7500 ps. It passes milestone M2 (66.7 MHz) and stays below M3 (80 MHz), which the PLL does not produce (80 MHz needs divider 12.5). The 83.333 MHz frequency (divider 12) does not close.

Insper-RISC-V tree `a612e9c` (Core `2ed0117`, Memory `768e81e`, Peripherals `ef0e3d6`, Common-Components `56c293e`), `HIGH PERFORMANCE EFFORT`.

| Seed | Core (ns) | Fetch to core (ns) | Core to fetch (ns) | Core to core (ns) | SDRAM controller (ns) | `DRAM_CLK` (ns) | JTAG (ns) | Lowest hold (ns) | ALMs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | +0.692 | +0.752 | +0.474 | +0.692 | +3.360 | +1.679 | +11.684 | +0.093 | 10,374 |
| 2 | +0.657 | +0.657 | +0.686 | +0.908 | +3.714 | +1.123 | +9.145 | +0.066 | 10,355 |
| 3 | +0.634 | +1.311 | +0.225 | +0.634 | +3.910 | +1.204 | +10.564 | +0.092 | 10,322 |
| 4 | +0.562 | +1.479 | +0.427 | +0.562 | +3.063 | +1.172 | +9.932 | +0.100 | 10,341 |
| 5 | +0.707 | +0.707 | +0.710 | +1.063 | +4.022 | +1.660 | +10.494 | +0.108 | 10,333 |
| Worst | +0.562 | +0.657 | +0.225 | +0.562 | +3.063 | +1.123 | +9.145 | +0.066 | 10,374 |

At 83.333 MHz (phase 7000 ps, same tree) the core closes in four of the five seeds (worst -0.771 ns, seed 4, 12.6 ns of data) and the core to fetch pair fails in four (worst -1.268 ns). The frequency, the phase and the tick rounding are in `platform.yaml` (`pll.core_clock_hz`, `pll.core_phase_ps`, `interrupts.clock_hz`) and in the PLL file, which `check-memory-map` verifies.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
