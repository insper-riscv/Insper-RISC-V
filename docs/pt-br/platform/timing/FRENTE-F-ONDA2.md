# Frente F na Onda 2: passos F.P4 e F.P5 e o marco M3

🌐 [Português](FRENTE-F-ONDA2.md) · [English](../../../en/platform/timing/FRENTE-F-ONDA2.md)

## 1. Escopo

Este documento mede a `de0-cv` com os passos F.P4 (classificação do endereço registrada em EX/MEM) e F.P5 (laço da busca e cache de instruções) e confere o marco M3 (relógio do núcleo entre 80 e 100 MHz). Os passos estão descritos em `Core/docs/pt-br/timing/P4_*.md` e `P5_*.md` e em `Memory/docs/pt-br/cache/icache.md`. A referência é o pior cenário do Quartus: modelo lento a 85 °C no setup, modelo rápido a 0 °C no hold.

## 2. Condições da medição

| Item | Valor |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, na workstation PC1 |
| Dispositivo | 5CEBA4F23C7 (Cyclone V) |
| Topo e projeto | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, `.sdc` versionado |
| Modo | `HIGH PERFORMANCE EFFORT`, pelo `de0-cv_synth.tcl` |
| Relógios | Saídas 2 (busca, fase 0) e 3 (núcleo, fase indicada) da PLL na frequência indicada; o controlador da SDRAM e `DRAM_CLK` ficam em 142,857 MHz; só a cópia de trabalho muda, o repositório não |
| Frequência do marco | 83,333 MHz (divisor 12 do VCO de 1000 MHz), a menor frequência realizável pela PLL acima de 80 MHz |
| Pares de relógios | `c3` é o relógio do núcleo, `c2` o da busca; `c2>c3` é o caminho da cache de instruções ao PC, `c3>c2` o do PC à cache |

Os resumos e os piores caminhos por par estão em `dados/frente-f-onda2/`.

## 3. Resultado a 83,333 MHz, fase do núcleo em 6000 ps, sementes 1 a 5

| Domínio | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo (`c3`) | -0,698 | -1,786 | -0,475 | -0,086 | -1,322 | -1,786 |
| Busca (`c2`) | 0,003 | 0,266 | -0,294 | -0,762 | -0,186 | -0,762 |
| Controlador da SDRAM | -0,742 | -0,255 | -0,205 | -0,173 | -0,728 | -0,742 |
| `DRAM_CLK` | 0,426 | -0,127 | -0,046 | -0,078 | 0,410 | -0,127 |
| JTAG | 9,990 | 10,658 | 8,803 | 9,898 | 8,300 | 8,300 |
| Menor hold, modelo rápido a 0 °C | 0,123 | 0,130 | 0,136 | 0,086 | 0,102 | 0,086 |
| ALMs | 8 940 | 8 947 | 9 159 | 9 162 | 8 941 | 9 162 |

O M3 não fecha: o núcleo e a busca ficam negativos em todas as sementes menos uma, e o controlador da SDRAM e `DRAM_CLK` (passo F.P6, outra trilha) continuam negativos.

## 4. Antes e depois dos passos, semente 1

| Medida | Antes (Core `8a828cc`, Memory `1160ae1`) | Depois |
| :--- | ---: | ---: |
| 83,333 MHz, fase 6000: pior par | -1,039 ns (`c3>c2`, PC até o bit de validade) | -0,698 ns (`c2>c3`, tag até o PC) |
| 83,333 MHz, fase 6000: núcleo para núcleo | -0,639 ns | -0,289 ns |
| 100 MHz, fase 5000: núcleo para núcleo | -2,453 ns (12,2 ns de dados) | -2,687 ns (12,5 ns de dados) |
| 100 MHz: PC até a cache | -2,610 ns (7,1 ns de dados) | fora dos 400 piores caminhos |
| ALMs a 100 MHz (fase 5000) | 9 636 | 9 281 |

## 5. O que limita o resto

| Caminho (modelo lento, 100 MHz) | Dados | Leitura |
| :--- | ---: | :--- |
| Leitura de CSR realimentando a escrita de CSR: contador do Zihpm, multiplexador de 29 contadores, `csr_file`, contador de destino | 12,3 ns | Nove níveis de lógica com roteamento de 1,3 a 1,9 ns entre os níveis; o laço é um `csrrs`, `csrrc` ou `csrrw` sobre um contador |
| `r_we_ok`, `r_fwd_match_rs*` e `r_imm` até os registradores de contagem e o PC | 12,0 a 12,4 ns | A confirmação da instrução em EX chega a todos os contadores |
| Tag da cache de instruções até a habilitação do PC | 4,2 a 5,0 ns | 2,5 ns são da saída da RAM de tag, o resto é o acerto e a habilitação do PC |

Nenhum desses é um passo pequeno: o primeiro exige tirar a escrita dos contadores do mesmo ciclo da leitura (com adiantamento ou parada para o `csr` seguinte), e o último exige que a cache de instruções entregue o acerto já registrado, o que muda o contrato de busca e coloca a leitura da cache num estágio próprio.

## 6. Veredito

| Marco | Resultado |
| :--- | :--- |
| M3 (80 MHz) | Não fecha. Pior folga do núcleo -1,786 ns e da busca -0,762 ns em 83,333 MHz; SDRAM e `DRAM_CLK` também negativos |
| M4 (100 MHz) | Não fecha. O laço do núcleo tem perto de 12,3 ns de dados contra os 10 ns do período |

O último marco com o núcleo fechado continua sendo o M1 de [MARCOS.md](MARCOS.md) (50 MHz com a fase do núcleo em 8250 ps); o que impede o M1 de fechar é só o controlador da SDRAM.

## 7. Leitura registrada do Zihpm (passo F.P6c)

O passo F.P6c (`Core/docs/pt-br/timing/P6_LEITURA_REGISTRADA_DO_ZIHPM.md`) tira o multiplexador dos 29 contadores do laço leitura-escrita de CSR. A tabela dá a semente 1 a 100 MHz e as cinco sementes a 83,333 MHz (fase 6000 ps); a lista de caminhos por número de níveis está em [CAMINHOS-POR-NIVEIS.md](CAMINHOS-POR-NIVEIS.md).

| Medida | Antes de F.P6c | Depois |
| :--- | ---: | ---: |
| 100 MHz, fase 5000, núcleo para núcleo | -2,687 ns | -2,053 ns |
| 100 MHz, fase 6000, núcleo para núcleo | -2,549 ns | -1,393 ns (11,2 ns de dados) |
| Níveis de lógica do banco do Zihpm (máximo) | 10 | 8 |

| Domínio a 83,333 MHz | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo (`c3`) | -0,549 | -1,837 | -0,275 | -0,439 | -0,825 | -1,837 |
| Busca (`c2`) | 0,118 | -0,087 | -0,308 | -0,333 | -0,035 | -0,333 |
| Controlador da SDRAM | -0,745 | -0,255 | -0,204 | -0,173 | -0,713 | -0,745 |
| `DRAM_CLK` | 0,429 | -0,127 | -0,047 | -0,078 | 0,394 | -0,127 |
| Menor hold, modelo rápido | 0,009 | 0,092 | 0,089 | 0,056 | 0,118 | 0,009 |
| ALMs | 9 067 | 9 062 | 9 062 | 9 005 | 9 045 | 9 067 |

O M3 continua aberto: o pior caminho do núcleo a 83,333 MHz passa a ser o da tag da cache de instruções até o PC (4,0 a 4,2 ns de dados mais 2,4 ns de defasagem do relógio da RAM), seguido pelo contador do Zihpm somando a si mesmo e pela confirmação da instrução (`r_we_ok`) que chega aos contadores, ao PC e à classificação do endereço. O custo do passo é um ciclo por instrução CSR que acessa o banco do Zihpm.

## 8. Os 100 MHz: cinco sementes, o gap e o ganho de cada passo

### 8.1. Condições

Árvore Insper-RISC-V `8e05f01` (Core `9deecac`, Memory `768e81e`, Peripherals `ef0e3d6`, Common-Components `56c293e`), medida com o RTL anterior às duas últimas alterações da tabela 8.4, com o controlador da SDRAM e o `DRAM_CLK` em 100 MHz da frente F.P6, núcleo e busca em 100 MHz, fase do núcleo 6000 ps, `HIGH PERFORMANCE EFFORT`, sementes 1 a 5, modelo lento a 85 °C. A fase de 5000 ps dá resultado idêntico no domínio do núcleo (o fitter não muda o posicionamento porque os pares entre os relógios de busca e núcleo têm folga).

| Semente | Núcleo (ns) | Dados do pior caminho (ns) | Busca | Controlador da SDRAM (ns) | `DRAM_CLK` (ns) | ALMs |
| ---: | ---: | ---: | :--- | ---: | ---: | ---: |
| 1 | -1,418 | 11,3 | folga positiva | +2,048 | +1,156 | 10 905 |
| 2 | -1,647 | 11,4 | folga positiva | +2,099 | +0,670 | 10 916 |
| 3 | -1,220 | 11,1 | folga positiva | +1,792 | +0,660 | 10 887 |
| 4 | -2,300 | 12,1 | folga positiva | +1,214 | +1,200 | 10 890 |
| 5 | -1,687 | 11,5 | folga positiva | +1,587 | +1,116 | 10 885 |
| Pior | -2,300 | 12,1 | | +1,214 | +0,660 | 10 916 |

O gap real para os 100 MHz é a pior folga do núcleo: faltam 2,30 ns na pior semente e 1,22 ns na melhor. Os pares com o relógio de busca fecham em todas as sementes, assim como o controlador da SDRAM e o `DRAM_CLK`.

### 8.2. Caminhos acima de 10 ns de dados

Os destinos do núcleo cujo pior caminho passa de 10 ns de dados são 906 na semente 4 e 476 na semente 1 (de 20 000 destinos analisados), concentrados em:

| Módulo de destino | Semente 4 | Semente 1 |
| :--- | ---: | ---: |
| `ID/EX` | 212 | 170 |
| Banco do Zihpm | 178 | 37 |
| `csr_file` | 122 | 32 |
| `EX/MEM` | 121 | 111 |
| `IF/ID` | 97 | 70 |
| `dcache` | 40 | 36 |

### 8.3. Lista por níveis de lógica (semente 4)

| Níveis | Dados (ns) | Folga (ns) | Endpoints | Origem | Destino |
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

| Domínio | Módulo de destino | Endpoints | >= 6 níveis | >= 8 níveis | >= 10 níveis | Máx. de níveis | Máx. de atraso (ns) |
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

### 8.4. Ganho de cada passo (núcleo para núcleo a 100 MHz)

| Passo | Efeito medido |
| :--- | :--- |
| F.P4 (classificação do endereço registrada) | núcleo para núcleo a 83,3 MHz de -0,64 para -0,29 ns; a 100 MHz o caminho `r_we_ok` até `r_same` passa a ser um dos piores (11,1 a 11,7 ns) |
| F.P5 (validade em RAM, seleção pelo endereço registrado, habilitação do PC a uma porta de `i_ic_ready`) | tira o laço da busca da lista de piores: o par busca para núcleo e o par núcleo para busca ficam com folga positiva a 100 MHz |
| F.P6c (leitura registrada do Zihpm) | a 100 MHz, fase 6000, semente 1: de -2,55 para -1,39 ns |
| Replay de IF (o PC segue sem esperar a cache) | fecha o par `c2>c3`; a cache de instruções deixa de limitar a frequência |
| Escritas de preenchimento da icache registradas e `check_addr` desligado | tiram `d_addr_i` e `addr_q` das listas |
| Linhas de interrupção por registrador na entrada do núcleo | tira o `priorities` do PLIC do primeiro lugar (semente 4: de -2,30 para -2,24, o próximo caminho é `r_we_ok` até o PC) |
| `maxfan` em `r_we_ok` e nos seletores do adiantamento, e `r_same` calculado em MEM a partir de dois registradores | sem ganho na pior semente (de -2,30 a -2,48 contra -2,24 a -2,28: dentro da dispersão de ±0,5 ns entre sementes) |
| `counter64` em blocos | não feito: depois de F.P6c o contador deixou de aparecer entre os piores caminhos |

### 8.5. O que falta

O limite é o laço do estágio EX: `r_we_ok` ou `r_fwd_match_rs*` (seleção do adiantamento, fan-out 98), multiplexador do operando A, ULA (quatro níveis de LUT) e, depois dela, a classificação do endereço, a decisão de desvio, a limpeza de `IF/ID`, `ID/EX` e `EX/MEM` e a habilitação do PC, com 11,1 a 12,1 ns de dados. O redirecionamento de desvio registrado não corta o trecho que termina em `r_alu_out` (11,0 a 11,5 ns) e só ganha nos destinos de limpeza, então por si só não fecha os 2,3 ns. Os candidatos que sobram, em ordem de ganho esperado:

1. Adiantar para a ULA só a partir de registradores (o resultado de EX é registrado e usado no ciclo seguinte), o que tira o seletor e o multiplexador do adiantamento do laço ao custo de um ciclo em cada dependência de dado imediata; cabe nos cinco estágios.
2. O redirecionamento de desvio e JALR registrado, que corta os destinos de limpeza (`r_pc`, `r_inst`, `r_valid`, escritas), a um ciclo a mais por desvio tomado.
3. A classificação do endereço calculada de `rs1` e `imm` em paralelo com a soma.
4. Região LogicLock para o laço do estágio EX, que só se justifica se medir ganho de roteamento (1,3 a 1,9 ns entre níveis nos caminhos mais longos).

## 9. Marco fechado: 76,923 MHz

A frequência mais alta que a PLL de 1000 MHz entrega e que fecha o setup no modelo lento a 85 °C e o hold no modelo rápido a 0 °C em todos os domínios das cinco sementes é 1000 / 13 = 76,923077 MHz, com a fase do núcleo em 7500 ps. Ela passa o marco M2 (66,7 MHz) e fica abaixo do M3 (80 MHz), que a PLL não produz (80 MHz pede o divisor 12,5). A frequência de 83,333 MHz (divisor 12) não fecha.

Árvore Insper-RISC-V `a612e9c` (Core `2ed0117`, Memory `768e81e`, Peripherals `ef0e3d6`, Common-Components `56c293e`), `HIGH PERFORMANCE EFFORT`.

| Semente | Núcleo (ns) | Busca para núcleo (ns) | Núcleo para busca (ns) | Núcleo para núcleo (ns) | Controlador da SDRAM (ns) | `DRAM_CLK` (ns) | JTAG (ns) | Hold mínimo (ns) | ALMs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | +0,692 | +0,752 | +0,474 | +0,692 | +3,360 | +1,679 | +11,684 | +0,093 | 10 374 |
| 2 | +0,657 | +0,657 | +0,686 | +0,908 | +3,714 | +1,123 | +9,145 | +0,066 | 10 355 |
| 3 | +0,634 | +1,311 | +0,225 | +0,634 | +3,910 | +1,204 | +10,564 | +0,092 | 10 322 |
| 4 | +0,562 | +1,479 | +0,427 | +0,562 | +3,063 | +1,172 | +9,932 | +0,100 | 10 341 |
| 5 | +0,707 | +0,707 | +0,710 | +1,063 | +4,022 | +1,660 | +10,494 | +0,108 | 10 333 |
| Pior | +0,562 | +0,657 | +0,225 | +0,562 | +3,063 | +1,123 | +9,145 | +0,066 | 10 374 |

A 83,333 MHz (fase 7000 ps, mesma árvore) o núcleo fecha em quatro das cinco sementes (pior -0,771 ns, semente 4, 12,6 ns de dados) e o par núcleo para busca falha em quatro (pior -1,268 ns). A frequência, a fase e o arredondamento do tick estão em `platform.yaml` (`pll.core_clock_hz`, `pll.core_phase_ps`, `interrupts.clock_hz`) e no arquivo da PLL, que o `check-memory-map` confere.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
