# Caminhos mais longos por número de níveis de lógica

🌐 [Português](CAMINHOS-POR-NIVEIS.md) · [English](../../../en/platform/timing/CAMINHOS-POR-NIVEIS.md)

## 1. Escopo

Este documento ordena os caminhos de setup da `de0-cv` pelo número de níveis de lógica (LUTs entre dois registradores), e não pelo atraso. Ele usa o banco do Quartus de dois bitstreams de 100 MHz, sem compilação nova.

| Banco | Estado do RTL | Fase do núcleo |
| :--- | :--- | ---: |
| A | Depois dos passos F.P4 e F.P5 (Core `a826b68`, Memory `1052bc3`) | 5000 ps |
| B | A mais o passo F.P6c, a leitura registrada do Zihpm (Core `63a316e`) | 6000 ps |

Condições: Quartus Prime 25.1std Lite, `HIGH PERFORMANCE EFFORT`, semente 1, modelo lento a 85 °C, relógio de busca e do núcleo em 100 MHz, `get_timing_paths -setup -nworst 1 -npaths 20000` por domínio de destino (um caminho por registrador de destino) e `get_path_info -num_logic_levels`. O script é `levels.tcl`, em `dados/frente-f-onda2/`, e `niveis_resumo.py` gera as tabelas a partir da saída dele. Os caminhos brutos e as tabelas geradas não são versionados; regere-os com `levels.tcl` sobre a compilação da semente 1 e `niveis_resumo.py` sobre a saída. Os nomes estão abreviados: `#` troca os números de índice, e os contadores do Zihpm aparecem como `counter#`.

## 2. Banco A: os caminhos com mais níveis

### 2.1. Núcleo (`c3`, 13 258 destinos)

| Níveis | Dados (ns) | Folga (ns) | Endpoints | Origem | Destino |
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

### 2.2. Busca (`c2`, 279 destinos)

| Níveis | Dados (ns) | Folga (ns) | Endpoints | Origem | Destino |
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

### 2.3. Controlador da SDRAM (142,857 MHz, 1 129 destinos)

| Níveis | Dados (ns) | Folga (ns) | Endpoints | Origem | Destino |
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

### 2.4. `DRAM_CLK` (36 destinos, todos com zero níveis: saída direta do registrador para o pino)

| Níveis | Dados (ns) | Folga (ns) | Endpoints | Origem | Destino |
| ---: | ---: | ---: | ---: | :--- | :--- |
| 0 | 3.09 | 0.428 | 15 | `SDRAM_CTRL/o_dram_dq_oe~_Duplicate_#` | `DRAM_DQ[#]` |
| 0 | 3.06 | 0.516 | 1 | `SDRAM_CTRL/o_dram_dq_oe` | `DRAM_DQ[#]` |
| 0 | 3.18 | 0.533 | 2 | `SDRAM_CTRL/o_dram_ba[#]` | `DRAM_BA[#]` |
| 0 | 3.18 | 0.589 | 13 | `SDRAM_CTRL/o_dram_addr[#]` | `DRAM_ADDR[#]` |
| 0 | 3.19 | 0.592 | 1 | `SDRAM_CTRL/o_dram_we_n` | `DRAM_WE_N` |
| 0 | 3.16 | 0.606 | 1 | `SDRAM_CTRL/o_dram_cas_n` | `DRAM_CAS_N` |
| 0 | 3.15 | 0.636 | 1 | `SDRAM_CTRL/o_dram_ras_n` | `DRAM_RAS_N` |
| 0 | 3.02 | 0.693 | 1 | `SDRAM_CTRL/o_dram_dqm[#]` | `DRAM_UDQM` |

## 3. Banco A: tabela agregada por módulo de destino

A coluna de níveis conta os destinos do módulo cujo pior caminho tem pelo menos N níveis.

| Domínio | Módulo de destino | Endpoints | >= 6 níveis | >= 8 níveis | >= 10 níveis | Máx. de níveis | Máx. de atraso (ns) |
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

## 4. Níveis contra atraso (banco A, núcleo)

Atraso médio de dados por número de níveis:

| Níveis | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Atraso médio de dados (ns) | 3.6 | 3.0 | 4.6 | 5.9 | 7.0 | 8.0 | 8.3 | 9.3 | 10.8 | 11.0 | 11.6 |
| Endpoints | 3563 | 2301 | 2359 | 855 | 239 | 339 | 890 | 218 | 1128 | 622 | 744 |

O atraso cresce com os níveis, mas de 8 níveis em diante satura perto de 11 ns: o roteamento, e não a lógica, passa a dominar.

### 4.1. Muitos níveis e atraso baixo (lógica profunda, bem posicionada)

| Níveis | Dados (ns) | Folga (ns) | Origem | Destino |
| ---: | ---: | ---: | :--- | :--- |
| 9 | 7.87 | 1.954 | `u_mtime/u_lo/o_d[#]` | `clint:\CLINT/u_mtip/o_d` |
| 9 | 9.84 | -0.069 | `u_reg_ex_mem/r_alu_out[#]` | `u_mtime/u_hi/o_d[#]` |
| 9 | 9.84 | -0.066 | `u_reg_ex_mem/r_alu_out[#]` | `u_mtime/u_hi/o_d[#]` |
| 9 | 9.98 | -0.226 | `u_reg_ex_mem/r_alu_out[#]` | `INTERCONNECT/pending[#]` |
| 9 | 9.99 | -0.202 | `u_reg_ex_mem/r_alu_out[#]` | `DISPLAY/u_display/tog_seen` |
| 9 | 10.02 | -0.243 | `u_reg_id_ex/r_fwd_match_rs#[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |

### 4.2. Poucos níveis e atraso alto (roteamento ruim)

| Níveis | Dados (ns) | Folga (ns) | Origem | Destino |
| ---: | ---: | ---: | :--- | :--- |
| 6 | 11.35 | -1.521 | `counter#:\u_counter/u_lo/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.89 | -1.085 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.89 | -1.091 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.81 | -1.017 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |
| 6 | 10.61 | -0.807 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/u_lo/o_d[#]` |
| 6 | 10.55 | -0.738 | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` | `counter#:\u_counter/generic_register:\u_hi/o_d[#]` |

## 5. Banco B (depois da leitura registrada do Zihpm)

### 5.1. Núcleo, maiores níveis

| Níveis | Dados (ns) | Folga (ns) | Endpoints | Origem | Destino |
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

### 5.2. Agregado por módulo

| Domínio | Módulo de destino | Endpoints | >= 6 níveis | >= 8 níveis | >= 10 níveis | Máx. de níveis | Máx. de atraso (ns) |
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

### 5.3. Atraso por nível

Atraso médio de dados por número de níveis:

| Níveis | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Atraso médio de dados (ns) | 3.7 | 3.2 | 4.3 | 5.6 | 6.9 | 7.3 | 8.3 | 9.3 | 9.8 | 10.1 | 10.1 | 11.0 |
| Endpoints | 3575 | 2335 | 3083 | 1613 | 483 | 748 | 484 | 1290 | 232 | 67 | 1 | 1 |

## 6. Leitura

| Observação | O que sugere |
| :--- | :--- |
| No banco A os caminhos com 9 e 10 níveis são os de leitura de CSR realimentando a escrita dos contadores do Zihpm (691 destinos do banco com 10 níveis ou mais); no banco B esses caminhos somem e o máximo cai para 11 níveis em um único destino (`r_same`) e 9 nos demais | A leitura registrada cortou a lógica profunda real do laço do Zihpm |
| O contador do Zihpm somando a si mesmo (`counter# -> counter#`) tem só 6 níveis e 10,6 a 11,4 ns de dados, mais que muitos caminhos de 9 níveis | O incrementador de 64 bits está mal posicionado ou mal mapeado (cada nível custa perto de 1,8 ns): é roteamento, e a correção é estrutural (dividir o contador em partes registradas com propagação de transporte atrasada, ou posicionar os 29 contadores perto do multiplexador) |
| Na busca (`c2`) os caminhos têm no máximo 6 níveis e 5,0 ns, mas a folga é negativa por causa da janela de 5 ns e da saída lenta das RAMs (2,5 ns) | O limite da busca é a topologia do laço entre os dois relógios, e não a quantidade de lógica |
| No controlador da SDRAM o máximo é 4 níveis e os 20 caminhos de mais níveis têm folga positiva (as folgas negativas do domínio vêm de outros caminhos, de menos níveis, ligados ao cruzamento com `DRAM_CLK`) | A lógica do controlador é rasa; o problema é de fase e de entrada e saída, ou seja, o passo F.P6 |
| `DRAM_CLK` tem zero níveis | O domínio é só de pinos e depende da fase da PLL |
| Os destinos `r_same`, `r_is_sdram`, `r_in_main` (classificação de F.P4) chegam a 10 e 11 níveis no banco B, vindos de `r_we_ok` da MEM/WB | O adiantamento do resultado de WB para a ULA e para a decodificação do endereço soma à cadeia; vale classificar o endereço só nos bits altos antes da soma completa |

## 7. Tabelas por semente

Os valores vêm de `dados/frente-f-onda2/tabela-sementes.tsv`, gerado por `dados/tabelar_resumos.py` a partir dos `.sta.summary` do Timing Analyzer (modelo lento, 1100 mV, 85 °C). Cada tabela lista, por semente, o pior setup, o pior hold e o domínio em que cada um ocorre. Os domínios são `core` (saída 3 da PLL), `fetch` (saída 2), `mem` (saída 0, controlador da SDRAM), `DRAM_CLK` (pino) e `jtag`; no topo `core_fpga_test` as saídas da PLL aparecem como `pll_c0` e `pll_c1`, e `pll_dram_clk` e `pll_vco` só têm largura mínima de pulso. O TSV traz também TNS, recovery, removal, largura mínima de pulso e o pior valor entre os quatro modelos de temperatura e tensão.

As medições descrevem a plataforma congelada em 76,923077 MHz e os experimentos listados. Um novo ataque de frequência regera a tabela com `python3 dados/tabelar_resumos.py gerar dados/frente-f-onda2` sobre os `.resumo.txt` das sementes novas (o `.sta.summary` e o `.fit.summary` do Quartus renomeados), e `--check` confere o TSV contra eles. Os resumos brutos não são versionados, e as tabelas são a referência de partida para a próxima rodada.

### 7.1. `b100p5000`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| - | -2,610 | fetch | 0,148 | jtag |

### 7.2. `b83p6000`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| - | -1,039 | fetch | 0,266 | core |

### 7.3. `p45c100p5000`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| - | -2,687 | core | 0,267 | core |

### 7.4. `p45c100p6000`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| - | -2,549 | core | 0,270 | core |

### 7.5. `p45c83p6500`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| - | -0,744 | mem | 0,286 | core |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
