# Longest paths by number of logic levels

🌐 [Português](../../../pt-br/platform/timing/CAMINHOS-POR-NIVEIS.md) · [English](CAMINHOS-POR-NIVEIS.md)

## 1. Scope

This document orders the setup paths of the `de0-cv` by the number of logic levels (LUTs between two registers), not by delay. It uses the Quartus database of two 100 MHz bitstreams, with no new compilation.

| Database | RTL state | Core phase |
| :--- | :--- | ---: |
| A | After steps F.P4 and F.P5 (Core `a826b68`, Memory `1052bc3`) | 5000 ps |
| B | A plus step F.P6c, the registered Zihpm read (Core `63a316e`) | 6000 ps |

Conditions: Quartus Prime 25.1std Lite, `HIGH PERFORMANCE EFFORT`, seed 1, slow model at 85 °C, fetch and core clocks at 100 MHz, `get_timing_paths -setup -nworst 1 -npaths 20000` per destination domain (one path per destination register) and `get_path_info -num_logic_levels`. The script is `levels.tcl`, in `dados/frente-f-onda2/`, and `niveis_resumo.py` builds the tables from its output. The raw paths and the generated tables are not versioned; regenerate them with `levels.tcl` on the build of seed 1 and `niveis_resumo.py` on the output. Names are abbreviated: `#` replaces index numbers, and the Zihpm counters appear as `counter#`.

## 2. Database A: the paths with the most levels

### 2.1. Core (`c3`, 13,258 destinations)

| Levels | Data (ns) | Slack (ns) | Endpoints | Source | Destination |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 10 | 12.23 | -2.453 | 716 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 10 | 12.06 | -2.314 | 86 | `counter#:\u_counter/flip_flop:\u_carry/o_d` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 10 | 12.05 | -2.258 | 5 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_hpm_bank/counter#:\u_counter/carry_nxt` |
| 10 | 11.90 | -2.105 | 30 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 10 | 11.83 | -2.054 | 29 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `counter#:\u_minstret/u_lo/o_d[#]` |
| 10 | 11.71 | -1.956 | 12 | `counter#:\u_counter/flip_flop:\u_carry/o_d` | `counter#:\u_minstret/u_lo/o_d[#]` |
| 10 | 11.68 | -1.876 | 1 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_same` |
| 10 | 11.59 | -1.805 | 50 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_hpm_bank/generic_register:\u_event_code/o_d[#]` |
| 10 | 10.98 | -1.233 | 7 | `counter#:\u_counter/flip_flop:\u_carry/o_d` | `u_reg_ex_mem/r_alu_out[#]` |
| 10 | 10.35 | -0.595 | 14 | `counter#:\u_counter/flip_flop:\u_carry/o_d` | `u_csr_file/u_mepc_reg/o_d[#]` |
| 9 | 12.29 | -2.500 | 87 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `counter#:\u_counter/flip_flop:\u_carry/o_d` |
| 9 | 12.02 | -2.219 | 14 | `u_csr_file/u_mscratch_reg/o_d[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 9 | 11.84 | -2.084 | 32 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_if_id/r_pc[#]` |
| 9 | 11.85 | -2.084 | 32 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_if_id/r_pc#[#]` |
| 9 | 11.86 | -2.083 | 1 | `u_csr_file/u_mscratch_reg/o_d[#]` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 9 | 11.88 | -2.069 | 148 | `counter#:\u_counter/u_lo/o_d[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 9 | 11.69 | -1.934 | 3 | `counter#:\u_counter/flip_flop:\u_carry/o_d` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 9 | 11.67 | -1.927 | 32 | `u_reg_ex_mem/r_alu_out[#]` | `DCACHE/pend[#]` |
| 9 | 11.71 | -1.895 | 8 | `counter#:\u_counter/u_lo/o_d[#]` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 9 | 11.64 | -1.880 | 32 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_if_id/r_inst[#]` |
| 9 | 11.63 | -1.844 | 32 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_id_ex/r_pc[#]` |
| 9 | 11.57 | -1.815 | 32 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_id_ex/r_pc#[#]` |
| 9 | 11.52 | -1.754 | 1 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_id_ex/r_sel_pc4_alu` |
| 9 | 11.46 | -1.672 | 6 | `u_reg_id_ex/r_imm[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 9 | 11.43 | -1.651 | 77 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_csr_file/u_mtval_reg/o_d[#]` |
| 9 | 11.33 | -1.593 | 2 | `u_reg_ex_mem/r_alu_out[#]` | `DCACHE/cnt[#]` |
| 9 | 12.19 | -1.576 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\1:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 9 | 12.15 | -1.538 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\3:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 9 | 11.33 | -1.534 | 3 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_ext_ram_op[#]` |
| 9 | 11.35 | -1.532 | 10 | `counter#:\u_counter/flip_flop:\u_carry/o_d` | `u_hpm_bank/generic_register:\u_event_code/o_d[#]` |
| 9 | 11.28 | -1.506 | 13 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_alu_out[#]` |
| 9 | 11.32 | -1.506 | 1 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_id_ex/r_sel_pc_rs#` |
| 9 | 11.30 | -1.492 | 5 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_id_ex/r_rd[#]` |
| 9 | 11.27 | -1.480 | 30 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_pc[#]` |
| 9 | 11.26 | -1.479 | 1 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_in_main` |
| 9 | 11.23 | -1.424 | 3 | `counter#:\u_counter/u_lo/o_d[#]` | `counter#:\u_minstret/u_lo/o_d[#]` |
| 9 | 11.19 | -1.394 | 1 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_is_sdram` |
| 9 | 11.14 | -1.349 | 32 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_ex_mem/r_store_data[#]` |
| 9 | 11.12 | -1.334 | 5 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `u_reg_id_ex/r_rs#[#]` |
| 9 | 11.90 | -1.287 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\2:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |

### 2.2. Fetch (`c2`, 279 destinations)

| Levels | Data (ns) | Slack (ns) | Endpoints | Source | Destination |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 6 | 5.02 | -0.635 | 28 | `ICACHE/d_addr_i[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~PORT_A_DATA_IN_#` |
| 6 | 5.03 | -0.594 | 28 | `ICACHE/d_addr_i[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~porta_datain_reg#` |
| 4 | 5.23 | -0.806 | 18 | `u_csr_file/u_mcause_reg/o_d[#]` | `ICACHE/addr_q[#]` |
| 4 | 4.92 | -0.490 | 15 | `u_pc_fetch/u_pc_reg/o_d[#]_REG432` | `ICACHE/addr_q[#]` |
| 4 | 4.91 | -0.455 | 4 | `ICACHE/cnt[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~porta_datain_reg#` |
| 4 | 4.90 | -0.450 | 4 | `ICACHE/cnt[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~PORT_A_DATA_IN_#` |
| 3 | 5.54 | -1.091 | 5 | `u_csr_file/u_mepc_reg/o_d[#]` | `ICACHE/addr_q[#]` |
| 3 | 5.40 | -1.042 | 16 | `u_csr_file/u_mcause_reg/o_d[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 5.34 | -0.940 | 17 | `u_csr_file/u_mcause_reg/o_d[#]` | `u_altsyncram/auto_generated/ram_block1a#~porta_address_reg#` |
| 3 | 5.37 | -0.938 | 2 | `u_pc_fetch/u_pc_reg/o_d[#]` | `ICACHE/addr_q[#]` |
| 3 | 5.30 | -0.884 | 3 | `u_csr_file/u_mcause_reg/o_d[#]` | `valid_ram[#]__#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 5.26 | -0.845 | 3 | `u_csr_file/u_mcause_reg/o_d[#]` | `tag_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 5.21 | -0.802 | 4 | `u_pc_fetch/u_pc_reg/o_d[#]_REG432` | `valid_ram[#]__#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 5.18 | -0.790 | 16 | `u_pc_fetch/u_pc_reg/o_d[#]_REG432` | `u_altsyncram/auto_generated/ram_block1a#~porta_address_reg#` |
| 3 | 5.09 | -0.679 | 4 | `u_csr_file/u_mepc_reg/o_d[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 5.00 | -0.598 | 3 | `u_csr_file/u_mepc_reg/o_d[#]` | `u_altsyncram/auto_generated/ram_block1a#~porta_address_reg#` |
| 3 | 4.97 | -0.579 | 4 | `u_pc_fetch/u_pc_reg/o_d[#]_REG432` | `tag_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 4.97 | -0.578 | 16 | `u_pc_fetch/u_pc_reg/o_d[#]_REG432` | `data_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 4.49 | -0.081 | 1 | `u_csr_file/u_mepc_reg/o_d[#]` | `tag_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 3 | 4.43 | -0.018 | 1 | `u_csr_file/u_mepc_reg/o_d[#]` | `valid_ram[#]__#/auto_generated/ram_block1a#~portb_address_reg#` |
| 2 | 5.12 | -0.664 | 4 | `u_pc_fetch/u_pc_reg/o_d[#]_REG614` | `u_altsyncram/auto_generated/ram_block1a#~porta_address_reg#` |
| 2 | 4.96 | -0.534 | 1 | `u_pc_fetch/u_pc_reg/o_d[#]_REG614` | `ICACHE/addr_q[#]` |
| 2 | 4.85 | -0.399 | 4 | `u_pc_fetch/u_pc_reg/o_d[#]_REG614` | `data_ram_rtl_#/auto_generated/ram_block1a#~portb_address_reg#` |
| 2 | 5.88 | 0.223 | 1 | `ICACHE/cnt[#]` | `valid_ram[#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 1 | 3.82 | 0.563 | 8 | `ICACHE/sw_idx[#]` | `valid_ram[#]__#/auto_generated/ram_block1a#~porta_address_reg#` |
| 1 | 5.31 | 0.783 | 1 | `ICACHE/cnt[#]` | `tag_ram_rtl_#/auto_generated/ram_block1a#~porta_we_reg` |
| 1 | 2.18 | 2.277 | 1 | `ICACHE/st.S_SWEEP` | `valid_ram[#]__#/auto_generated/ram_block1a#~porta_datain_reg#` |
| 0 | 2.63 | 1.812 | 8 | `ICACHE/cnt[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~porta_address_reg#` |
| 0 | 2.54 | 1.918 | 15 | `ICACHE/fill_tag[#]` | `tag_ram_rtl_#/auto_generated/ram_block1a#~porta_datain_reg#` |
| 0 | 2.35 | 2.043 | 32 | `ICACHE/fill_idx[#]` | `data_ram_rtl_#/auto_generated/ram_block1a#~porta_address_reg#` |

### 2.3. SDRAM controller (142.857 MHz, 1,129 destinations)

| Levels | Data (ns) | Slack (ns) | Endpoints | Source | Destination |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 4 | 5.45 | 1.322 | 25 | `SDRAM_DEBUG/left[#]` | `SDRAM_DEBUG/left[#]` |
| 4 | 5.15 | 1.652 | 17 | `SDRAM_DEBUG/count[#]` | `SDRAM_DEBUG/wcnt[#]` |
| 4 | 5.12 | 1.661 | 24 | `SDRAM_DEBUG/left[#]` | `SDRAM_DEBUG/o_b_addr[#]` |
| 4 | 5.12 | 1.690 | 1 | `SDRAM_DEBUG/count[#]` | `SDRAM_DEBUG/st.ST_WAIT` |
| 4 | 5.05 | 1.738 | 4 | `SDRAM_DEBUG/left[#]` | `SDRAM_DEBUG/o_b_be[#]` |
| 4 | 5.04 | 1.745 | 32 | `SDRAM_DEBUG/left[#]` | `SDRAM_DEBUG/o_b_wdata[#]` |
| 4 | 4.84 | 1.964 | 1 | `SDRAM_DEBUG/count[#]` | `SDRAM_DEBUG/st.ST_IDLE` |
| 4 | 4.68 | 2.143 | 1 | `SDRAM_DEBUG/count[#]` | `SDRAM_DEBUG/done_i` |
| 4 | 4.35 | 2.458 | 1 | `SDRAM_DEBUG/left[#]` | `SDRAM_DEBUG/req_i` |
| 4 | 4.32 | 2.494 | 1 | `SDRAM_DEBUG/left[#]` | `SDRAM_DEBUG/o_b_we` |
| 4 | 4.08 | 2.750 | 2 | `SDRAM_CTRL/st.ST_WAIT` | `SDRAM_CTRL/st.ST_READ` |
| 3 | 5.02 | 1.797 | 25 | `SDRAM_DEBUG/req_i` | `SDRAM_ARBITER/o_c_addr[#]` |
| 3 | 5.51 | 1.976 | 11 | `SDRAM_CTRL/act_cnt[#]` | `SDRAM_CTRL/o_dram_addr[#]` |
| 3 | 4.54 | 2.275 | 19 | `SDRAM_CTRL/wcnt[#]` | `SDRAM_CTRL/wcnt[#]` |
| 3 | 4.28 | 2.528 | 2 | `SDRAM_CTRL/act_cnt[#]` | `SDRAM_CTRL/st.ST_IDLE` |
| 3 | 4.07 | 2.745 | 1 | `SDRAM_ARBITER/ins_s[#]` | `SDRAM_ARBITER/o_c_we` |
| 3 | 4.05 | 2.751 | 1 | `SDRAM_CTRL/act_cnt[#]` | `SDRAM_CTRL/st.ST_INIT_WAIT` |
| 3 | 4.04 | 2.763 | 2 | `SDRAM_CTRL/line_l` | `SDRAM_CTRL/st.ST_INIT_REF` |
| 3 | 4.03 | 2.780 | 1 | `SDRAM_CTRL/line_l` | `SDRAM_CTRL/st.ST_INIT_PRE` |
| 3 | 4.02 | 2.787 | 1 | `SDRAM_CTRL/line_l` | `SDRAM_CTRL/st.ST_INIT_MRS` |

### 2.4. `DRAM_CLK` (36 destinations, all with zero levels: register straight to the pin)

| Levels | Data (ns) | Slack (ns) | Endpoints | Source | Destination |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 0 | 3.09 | 0.428 | 15 | `SDRAM_CTRL/o_dram_dq_oe~_Duplicate_#` | `DRAM_DQ[#]` |
| 0 | 3.06 | 0.516 | 1 | `SDRAM_CTRL/o_dram_dq_oe` | `DRAM_DQ[#]` |
| 0 | 3.18 | 0.533 | 2 | `SDRAM_CTRL/o_dram_ba[#]` | `DRAM_BA[#]` |
| 0 | 3.18 | 0.589 | 13 | `SDRAM_CTRL/o_dram_addr[#]` | `DRAM_ADDR[#]` |
| 0 | 3.19 | 0.592 | 1 | `SDRAM_CTRL/o_dram_we_n` | `DRAM_WE_N` |
| 0 | 3.16 | 0.606 | 1 | `SDRAM_CTRL/o_dram_cas_n` | `DRAM_CAS_N` |
| 0 | 3.15 | 0.636 | 1 | `SDRAM_CTRL/o_dram_ras_n` | `DRAM_RAS_N` |
| 0 | 3.02 | 0.693 | 1 | `SDRAM_CTRL/o_dram_dqm[#]` | `DRAM_UDQM` |

## 3. Database A: table aggregated by destination module

Each level column counts the destinations of the module whose worst path has at least N levels.

| Domain | Destination module | Endpoints | >= 6 levels | >= 8 levels | >= 10 levels | Max levels | Max delay (ns) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| c3 | Zihpm banco | 3520 | 1088 | 1037 | 691 | 10 | 12.45 |
| c3 | csr_file | 1063 | 319 | 224 | 51 | 10 | 11.90 |
| c3 | EX/MEM | 119 | 119 | 111 | 2 | 10 | 11.71 |
| c3 | dcache | 725 | 333 | 41 | 0 | 9 | 12.19 |
| c3 | ID/EX | 214 | 214 | 214 | 0 | 9 | 11.87 |
| c3 | clint g_irq CLINT | 214 | 127 | 110 | 0 | 9 | 10.90 |
| c3 | IF/ID | 97 | 97 | 97 | 0 | 9 | 11.85 |
| c3 | ext_interconnect INT | 66 | 33 | 32 | 0 | 9 | 10.76 |
| c3 | seg_display_shell DI | 26 | 25 | 25 | 0 | 9 | 10.82 |
| c3 | jtag_uart_shell JTAG | 614 | 539 | 513 | 0 | 8 | 11.62 |
| c3 | EX | 466 | 239 | 74 | 0 | 8 | 10.33 |
| c3 | PC | 377 | 183 | 14 | 0 | 8 | 10.89 |
| c3 | flash_chip FLASH_CHI | 176 | 48 | 1 | 0 | 8 | 8.75 |
| c3 | trap_seen | 1 | 1 | 1 | 0 | 8 | 10.83 |
| c3 | generic_register u_w | 96 | 73 | 0 | 0 | 7 | 10.05 |
| c3 | MEM/WB | 46 | 1 | 0 | 0 | 7 | 7.54 |
| c3 | desalinhado | 36 | 2 | 0 | 0 | 7 | 7.81 |
| c3 | sdram | 709 | 130 | 0 | 0 | 6 | 8.80 |
| c2 | icache | 239 | 8 | 0 | 0 | 6 | 5.88 |
| c3 | icache | 76 | 19 | 0 | 0 | 6 | 7.86 |
| c3 | ext_irq_controller  | 16 | 8 | 0 | 0 | 6 | 8.74 |
| c3 | flash_arbiter FLASH_ | 4 | 3 | 0 | 0 | 6 | 7.32 |

## 4. Levels against delay (database A, core)

Mean data delay by number of levels:

| Levels | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mean data delay (ns) | 3.6 | 3.0 | 4.6 | 5.9 | 7.0 | 8.0 | 8.3 | 9.3 | 10.8 | 11.0 | 11.6 |
| Endpoints | 3563 | 2301 | 2359 | 855 | 239 | 339 | 890 | 218 | 1128 | 622 | 744 |

The delay grows with the levels but saturates near 11 ns from 8 levels on: routing, not logic, starts to dominate.

### 4.1. Many levels and low delay (deep logic, well placed)

| Levels | Data (ns) | Slack (ns) | Source | Destination |
| ---: | ---: | ---: | :--- | :--- |
| 9 | 7.87 | 1.954 | `u_mtime/u_lo/o_d[#]` | `clint:\CLINT/u_mtip/o_d` |
| 9 | 9.84 | -0.069 | `u_reg_ex_mem/r_alu_out[#]` | `u_mtime/u_hi/o_d[#]` |
| 9 | 9.84 | -0.066 | `u_reg_ex_mem/r_alu_out[#]` | `u_mtime/u_hi/o_d[#]` |
| 9 | 9.98 | -0.226 | `u_reg_ex_mem/r_alu_out[#]` | `INTERCONNECT/pending[#]` |
| 9 | 9.99 | -0.202 | `u_reg_ex_mem/r_alu_out[#]` | `DISPLAY/u_display/tog_seen` |
| 9 | 10.02 | -0.243 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |

### 4.2. Few levels and high delay (bad routing)

| Levels | Data (ns) | Slack (ns) | Source | Destination |
| ---: | ---: | ---: | :--- | :--- |
| 6 | 11.35 | -1.521 | `counter#:\u_counter/u_lo/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.89 | -1.085 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.89 | -1.091 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.81 | -1.017 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 6 | 10.61 | -0.807 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.55 | -0.738 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |

## 5. Database B (after the registered Zihpm read)

### 5.1. Core, most levels

| Levels | Data (ns) | Slack (ns) | Endpoints | Source | Destination |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 11 | 11.02 | -1.218 | 1 | `u_reg_mem_wb/r_we_ok` | `u_reg_ex_mem/r_same` |
| 10 | 10.07 | -0.283 | 1 | `u_reg_mem_wb/r_we_ok` | `u_reg_ex_mem/r_is_sdram` |
| 9 | 10.66 | -0.859 | 32 | `u_reg_ex_mem/r_alu_out[#]` | `DCACHE/pend[#]` |
| 9 | 10.32 | -0.535 | 1 | `u_reg_id_ex/r_imm[#]` | `u_csr_file/u_mstatus_mie_ff/o_d` |
| 9 | 11.15 | -0.487 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\3:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 9 | 10.27 | -0.482 | 17 | `u_reg_mem_wb/r_we_ok` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 9 | 10.22 | -0.427 | 15 | `u_reg_id_ex/r_imm[#]` | `counter#:\u_minstret/generic_register:\u_hi/o_d[#]` |
| 9 | 10.14 | -0.326 | 20 | `u_reg_mem_wb/r_we_ok` | `counter#:\u_minstret/u_lo/o_d[#]` |
| 9 | 10.96 | -0.294 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\2:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 9 | 10.91 | -0.245 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\0:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 9 | 10.02 | -0.238 | 1 | `u_hpm_bank/generic_register:\u_inhibit/o_d[#]` | `counter#:\u_minstret/u_lo/o_d[#]` |
| 9 | 10.02 | -0.216 | 2 | `u_reg_ex_mem/r_alu_out[#]` | `DCACHE/cnt[#]` |
| 9 | 10.73 | -0.063 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `altsyncram:\1:lane[#][#]__#/auto_generated/ram_block1a#~porta_we_reg` |
| 9 | 9.84 | -0.039 | 21 | `u_reg_id_ex/r_imm[#]` | `counter#:\u_minstret/u_lo/o_d[#]` |
| 9 | 9.79 | 0.001 | 1 | `u_reg_mem_wb/r_we_ok` | `u_csr_file/u_mstatus_mie_ff/o_d_REG938` |
| 9 | 9.79 | 0.004 | 1 | `u_reg_mem_wb/r_we_ok` | `u_csr_file/u_mstatus_mie_ff/o_d_REG944` |
| 9 | 9.80 | 0.017 | 4 | `u_reg_mem_wb/r_we_ok` | `u_csr_file/u_mstatus_mie_ff/o_d` |
| 9 | 9.30 | 0.529 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `DCACHE/st.S_FILL_REQ` |
| 9 | 9.29 | 0.530 | 1 | `u_reg_ex_mem/r_alu_out[#]` | `DCACHE/st.S_DONE` |
| 9 | 9.25 | 0.551 | 2 | `u_csr_file/u_mtval_reg/o_d[#]` | `u_csr_file/u_mepc_reg/o_d[#]` |
| 9 | 9.02 | 0.786 | 9 | `u_reg_ex_mem/r_alu_out[#]` | `INTERCONNECT/pending[#]` |
| 9 | 8.57 | 1.244 | 1 | `u_mtime/u_lo/o_d[#]` | `clint:\CLINT/u_mtip/o_d` |
| 8 | 10.81 | -1.055 | 24 | `u_reg_mem_wb/r_we_ok` | `u_reg_ex_mem/r_alu_out[#]` |
| 8 | 10.77 | -0.981 | 18 | `u_reg_mem_wb/r_we_ok` | `u_pc_fetch/u_pc_reg/o_d[#]` |
| 8 | 10.71 | -0.931 | 32 | `u_reg_mem_wb/r_we_ok` | `u_reg_ex_mem/r_store_data[#]` |
| 8 | 10.50 | -0.724 | 28 | `u_reg_mem_wb/r_we_ok` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 8 | 10.15 | -0.369 | 4 | `u_reg_mem_wb/r_we_ok` | `u_reg_ex_mem/r_byte_mask[#]` |
| 8 | 10.05 | -0.240 | 8 | `u_reg_mem_wb/r_we_ok` | `u_csr_file/u_mepc_reg/o_d[#]` |
| 8 | 10.03 | -0.220 | 2 | `u_reg_mem_wb/r_we_ok` | `u_csr_file/u_mcause_reg/o_d[#]` |
| 8 | 9.99 | -0.201 | 2 | `u_reg_mem_wb/r_we_ok` | `counter#:\u_mcycle/generic_register:\u_hi/o_d[#]` |

### 5.2. Aggregated by module

| Domain | Destination module | Endpoints | >= 6 levels | >= 8 levels | >= 10 levels | Max levels | Max delay (ns) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| c3 | EX/MEM | 119 | 119 | 63 | 2 | 11 | 11.02 |
| c3 | csr_file | 1053 | 231 | 73 | 0 | 9 | 10.69 |
| c3 | dcache | 725 | 155 | 42 | 0 | 9 | 11.15 |
| c3 | clint g_irq CLINT | 211 | 49 | 3 | 0 | 9 | 9.41 |
| c3 | ext_interconnect INT | 66 | 33 | 9 | 0 | 9 | 10.00 |
| c3 | Zihpm banco | 4169 | 253 | 92 | 0 | 8 | 10.55 |
| c3 | EX | 465 | 278 | 3 | 0 | 8 | 9.92 |
| c3 | PC | 389 | 47 | 12 | 0 | 8 | 10.79 |
| c3 | ID/EX | 214 | 214 | 2 | 0 | 8 | 11.16 |
| c3 | flash_chip FLASH_CHI | 176 | 48 | 1 | 0 | 8 | 7.73 |
| c3 | plic g_irq PLIC | 29 | 5 | 1 | 0 | 8 | 9.48 |
| c3 | jtag_uart_shell JTAG | 617 | 520 | 0 | 0 | 7 | 9.71 |
| c3 | IF/ID | 97 | 97 | 0 | 0 | 7 | 10.82 |
| c3 | trap_seen | 1 | 1 | 0 | 0 | 7 | 9.56 |
| c2 | icache | 237 | 46 | 0 | 0 | 6 | 5.31 |
| c3 | generic_register u_w | 92 | 19 | 0 | 0 | 6 | 9.24 |
| c3 | MEM/WB | 46 | 1 | 0 | 0 | 6 | 8.26 |
| c3 | desalinhado | 36 | 1 | 0 | 0 | 6 | 8.67 |
| c3 | seg_display_shell DI | 26 | 1 | 0 | 0 | 6 | 9.33 |
| c3 | flash_arbiter FLASH_ | 4 | 3 | 0 | 0 | 6 | 7.53 |
| c3 | sdram | 709 | 0 | 0 | 0 | 5 | 6.81 |
| c3 | icache | 76 | 0 | 0 | 0 | 5 | 7.57 |

### 5.3. Delay by level

Mean data delay by number of levels:

| Levels | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mean data delay (ns) | 3.7 | 3.2 | 4.3 | 5.6 | 6.9 | 7.3 | 8.3 | 9.3 | 9.8 | 10.1 | 10.1 | 11.0 |
| Endpoints | 3575 | 2335 | 3083 | 1613 | 483 | 748 | 484 | 1290 | 232 | 67 | 1 | 1 |

## 6. Reading

| Observation | What it suggests |
| :--- | :--- |
| In database A the 9 and 10 level paths are the CSR read feeding the write of the Zihpm counters (691 bank destinations with 10 levels or more); in database B they disappear and the maximum falls to 11 levels in a single destination (`r_same`) and 9 elsewhere | The registered read removed the real deep logic of the Zihpm loop |
| The Zihpm counter adding to itself (`counter# -> counter#`) has only 6 levels and 10.6 to 11.4 ns of data, more than many 9-level paths | The 64-bit incrementer is badly placed or badly mapped (each level costs near 1.8 ns): it is routing, and the fix is structural (split the counter into registered parts with delayed carry propagation, or place the 29 counters near the multiplexer) |
| In the fetch (`c2`) the paths have at most 6 levels and 5.0 ns, but the slack is negative because of the 5 ns window and the slow RAM output (2.5 ns) | The fetch limit is the topology of the loop between the two clocks, not the amount of logic |
| In the SDRAM controller the maximum is 4 levels and the 20 paths with the most levels have positive slack (the negative slacks of the domain come from other, shallower paths tied to the crossing with `DRAM_CLK`) | The controller logic is shallow; the problem is phase and input and output, that is, step F.P6 |
| `DRAM_CLK` has zero levels | The domain is only pins and depends on the PLL phase |
| The destinations `r_same`, `r_is_sdram`, `r_in_main` (F.P4 class) reach 10 and 11 levels in database B, coming from `r_we_ok` of MEM/WB | Forwarding the WB result into the ALU and into the address decode adds to the chain; it is worth classifying the address on the high bits only before the full sum |

## 7. Per-seed tables

The values come from `dados/frente-f-onda2/tabela-sementes.tsv`, generated by `dados/tabelar_resumos.py` from the Timing Analyzer `.sta.summary` files (slow model, 1100 mV, 85 °C). Each table lists, per seed, the worst setup, the worst hold and the domain where each occurs. The domains are `core` (PLL output 3), `fetch` (output 2), `mem` (output 0, the SDRAM controller), `DRAM_CLK` (pin) and `jtag`; in the `core_fpga_test` top the PLL outputs appear as `pll_c0` and `pll_c1`, and `pll_dram_clk` and `pll_vco` only have minimum pulse width. The TSV also carries TNS, recovery, removal, minimum pulse width and the worst value among the four temperature and voltage models.

The measurements describe the platform frozen at 76.923077 MHz and the listed experiments. A new frequency attack regenerates the table with `python3 dados/tabelar_resumos.py gerar dados/frente-f-onda2` over the `.resumo.txt` files of the new seeds (the Quartus `.sta.summary` and `.fit.summary`, renamed), and `--check` compares the TSV against them. The raw summaries are not versioned, and the tables are the starting reference for the next round.

### 7.1. `b100p5000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| - | -2.610 | fetch | 0.148 | jtag |

### 7.2. `b83p6000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| - | -1.039 | fetch | 0.266 | core |

### 7.3. `p45c100p5000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| - | -2.687 | core | 0.267 | core |

### 7.4. `p45c100p6000`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| - | -2.549 | core | 0.270 | core |

### 7.5. `p45c83p6500`

| Seed | Worst setup (ns) | Domain | Worst hold (ns) | Domain |
| :--- | ---: | :--- | ---: | :--- |
| - | -0.744 | mem | 0.286 | core |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
