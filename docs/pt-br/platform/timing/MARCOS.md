# Marcos M1 e M2 da frente de 100 MHz na `de0-cv`

🌐 [Português](MARCOS.md) · [English](../../../en/platform/timing/MARCOS.md)

## 1. Escopo

Este documento mede a `de0-cv` com o núcleo final (Core `8a828cc`, que já traz os passos F.P1 a F.P3) nos relógios dos marcos M1 (50 MHz) e M2 (66,7 MHz) da frente F, e compara com a linha de base de [README.md](README.md). A referência é o pior cenário do Quartus: modelo lento a 85 °C no setup, modelo rápido a 0 °C no hold, pior das sementes 1 a 5.

## 2. Condições da medição

| Item | Valor |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, na workstation PC1 |
| Dispositivo | 5CEBA4F23C7 (Cyclone V) |
| Fontes | Insper-RISC-V `224a762`, Core `8a828cc`, Memory `1160ae1`, Peripherals `d7253f6`, Common-Components `9aa6a75`; resumo SHA-256 dos arquivos de código e de projeto `65eff664dceb14fa` |
| Topo e projeto | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, `.sdc` versionado |
| Modo | `HIGH PERFORMANCE EFFORT`, sementes 1 a 5, pelo `de0-cv_synth.tcl` |
| Relógios | Saídas 2 e 3 da PLL na frequência do marco (50 ou 66,666667 MHz) e fase da saída 3 (relógio do núcleo) indicada em cada tabela; só a cópia de trabalho do Quartus muda, o repositório não |
| Contagem do tick do `time` | 50 ciclos nas duas frequências, o que não altera o tempo da compilação |

As folgas de cada semente estão em `dados/marcos/tabela-sementes.tsv` (seção 7). Os relatórios completos e logs do Quartus não são versionados; regere-os com `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <semente>` sobre a compilação da semente pedida, que deixa o `.sta.rpt` e o `.fit.rpt` em `output_files/`.

## 3. Marco M1: 50 MHz

### 3.1. Com a fase versionada (6625 ps)

| Domínio | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo | -0,729 | -1,345 | -0,350 | -0,560 | -1,001 | -1,345 |
| Busca | 3,582 | 5,406 | 3,403 | 4,491 | 4,160 | 3,403 |
| Controlador da SDRAM | -0,744 | -0,255 | -0,208 | -0,173 | -0,713 | -0,744 |
| `DRAM_CLK` | 0,428 | -0,127 | -0,042 | -0,078 | 0,394 | -0,127 |
| JTAG | 10,433 | 7,612 | 9,873 | 10,824 | 11,068 | 7,612 |
| Fmax do núcleo (MHz) | 65,07 | 65,58 | 62,44 | 62,23 | 67,32 | 62,23 |
| Menor hold, modelo rápido a 0 °C | 0,142 | 0,149 | 0,125 | 0,002 | 0,142 | 0,002 |

### 3.2. Com a fase do núcleo em 8250 ps

| Domínio | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo | 0,666 | 0,188 | 1,386 | 0,649 | 0,570 | 0,188 |
| Busca | 3,804 | 3,781 | 3,031 | 2,944 | 4,179 | 2,944 |
| Controlador da SDRAM | -0,745 | -0,255 | -0,205 | -0,173 | -0,713 | -0,745 |
| `DRAM_CLK` | 0,429 | -0,127 | -0,046 | -0,078 | 0,394 | -0,127 |
| JTAG | 11,376 | 11,303 | 10,683 | 9,034 | 10,683 | 9,034 |
| Fmax do núcleo (MHz) | 64,67 | 66,70 | 65,48 | 65,09 | 64,28 | 64,28 |
| Menor hold, modelo rápido a 0 °C | 0,130 | 0,131 | 0,065 | 0,122 | 0,126 | 0,065 |

### 3.3. Leitura

| Item | Resultado |
| :--- | :--- |
| Núcleo e busca | Folga não negativa nas cinco sementes com a fase de 8250 ps (pior folga do núcleo 0,188 ns); com 6625 ps a folga do núcleo é negativa em todas as sementes (pior -1,345 ns) |
| Controlador da SDRAM e `DRAM_CLK` | Continuam negativos (-0,745 e -0,127 ns) e iguais à linha de base, porque não dependem da fase do núcleo |
| Hold | Positivo em todos os domínios e sementes (mínimo 0,002 ns com 6625 ps e 0,065 ns com 8250 ps) |
| Veredito | M1 não fecha: faltam os dois domínios da SDRAM, que são o passo F.P6 |

A fase de 8250 ps desloca a borda do relógio do núcleo 1625 ps para depois da versionada. O laço que passa pela cache de instruções (PC, etiqueta, PC) fica entre os dois relógios, e a fase reparte os 20 ns entre as duas travessias; a fase versionada deixa a travessia de busca para núcleo com 6,6 ns e ela precisa de perto de 8,0 ns.

## 4. Marco M2: 66,7 MHz

### 4.1. Folga do pior caminho de cada par de relógios

A tabela dá a pior folga (ns, modelo lento a 85 °C) das cinco sementes para cada par e cada fase.

| Núcleo | Fase | núcleo para núcleo | núcleo para busca | busca para núcleo |
| :--- | ---: | ---: | ---: | ---: |
| 50 MHz | 6625 | 3,931 | 3,403 | -1,345 |
| 50 MHz | 8250 | 4,443 | 2,944 | 0,188 |
| 66,7 MHz | 7500 | 1,593 | 0,494 | -1,699 |
| 66,7 MHz | 8000 | 1,135 | 0,400 | -0,907 |
| 66,7 MHz | 8500 | 1,318 | 0,032 | -0,290 |
| 66,7 MHz | 9000 | 1,490 | -0,339 | -0,223 |

### 4.2. Folga por domínio com a melhor fase (8500 ps)

| Domínio | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo | -0,084 | -0,290 | 0,508 | 0,359 | 0,265 | -0,290 |
| Busca | 0,851 | 0,853 | 0,247 | 0,032 | 0,445 | 0,032 |
| Controlador da SDRAM | -0,744 | -0,255 | -0,205 | -0,173 | -0,713 | -0,744 |
| `DRAM_CLK` | 0,428 | -0,127 | -0,046 | -0,078 | 0,394 | -0,127 |
| JTAG | 11,109 | 10,010 | 9,087 | 10,058 | 11,238 | 9,087 |
| Fmax do núcleo (MHz) | 75,42 | 76,32 | 73,09 | 74,47 | 73,10 | 73,09 |
| Menor hold, modelo rápido a 0 °C | 0,121 | 0,043 | 0,139 | 0,125 | 0,019 | 0,019 |

### 4.3. Leitura

| Item | Resultado |
| :--- | :--- |
| Laço do núcleo | Folga de +1,1 a +1,6 ns em todas as fases, ou seja, os passos F.P1 a F.P3 fecham o laço do núcleo a 66,7 MHz |
| Laço da cache de instruções | Soma das duas travessias perto de 0 ns de folga: busca para núcleo -0,290 ns e núcleo para busca +0,032 ns com 8500 ps; nenhuma fase leva os dois a folga não negativa nas cinco sementes |
| Controlador da SDRAM e `DRAM_CLK` | Iguais à linha de base (-0,744 e -0,127 ns) |
| Fmax do domínio do núcleo | 74,59 a 77,92 MHz com 7500 ps, contra 62,23 a 67,32 MHz a 50 MHz |
| Veredito | M2 não fecha: faltam o laço da cache de instruções (passo F.P5, etiqueta registrada) e o controlador da SDRAM (F.P6) |

## 5. Os passos F.P1 a F.P3

Os três passos já estão no RTL medido, então o Fmax e a folga por domínio dos três são os das seções 3 e 4; o documento de cada passo no Core (`docs/pt-br/timing/P1_*.md`, `P2_*.md` e `P3_*.md`) traz o caminho antes e depois. Os piores caminhos restantes do núcleo para o núcleo são a leitura de CSR realimentando a escrita de CSR (de `ID/EX r_imm` por 9 níveis de lógica, pelo multiplexador de 29 contadores, até `mepc`, `mtval` e os contadores) e a decisão de exceção de MEM chegando ao PC e aos contadores.

## 6. Como reproduzir

| Objetivo | Comando |
| :--- | :--- |
| Compilar uma semente | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <semente>`, numa cópia do repositório |
| Mudar frequência e fase | Editar `output_clock_frequency2`, `output_clock_frequency3` e `phase_shift3` de `src/cyclone-v/de0-cv/pll/sdram_platform_pll.v` na cópia |
| Folga por domínio | `output_files/de0-cv.sta.summary` e `output_files/de0-cv.sta.rpt` |
| Caminhos por par de relógios | `quartus_sta -t docs/pt-br/platform/timing/dados/pares-de-dominios.tcl de0-cv 300 slow` na pasta do projeto compilado |

## 7. Tabelas por semente

Os valores vêm de `dados/marcos/tabela-sementes.tsv`, gerado por `dados/tabelar_resumos.py` a partir dos `.sta.summary` do Timing Analyzer (modelo lento, 1100 mV, 85 °C). Cada tabela lista, por semente, o pior setup, o pior hold e o domínio em que cada um ocorre. Os domínios são `core` (saída 3 da PLL), `fetch` (saída 2), `mem` (saída 0, controlador da SDRAM), `DRAM_CLK` (pino) e `jtag`; no topo `core_fpga_test` as saídas da PLL aparecem como `pll_c0` e `pll_c1`, e `pll_dram_clk` e `pll_vco` só têm largura mínima de pulso. O TSV traz também TNS, recovery, removal, largura mínima de pulso e o pior valor entre os quatro modelos de temperatura e tensão.

As medições descrevem a plataforma congelada em 76,923077 MHz e os experimentos listados. Um novo ataque de frequência regera a tabela com `python3 dados/tabelar_resumos.py gerar dados/marcos` sobre os `.resumo.txt` das sementes novas (o `.sta.summary` e o `.fit.summary` do Quartus renomeados), e `--check` confere o TSV contra eles. Os resumos brutos não são versionados, e as tabelas são a referência de partida para a próxima rodada.

### 7.1. `50mhz-fase6625`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,744 | mem | 0,295 | core |
| 2 | -1,345 | core | 0,317 | core |
| 3 | -0,350 | core | 0,306 | core |
| 4 | -0,560 | core | 0,141 | jtag |
| 5 | -1,001 | core | 0,280 | core |

### 7.2. `50mhz-fase8250`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,745 | mem | 0,293 | core |
| 2 | -0,255 | mem | 0,271 | core |
| 3 | -0,205 | mem | 0,276 | core |
| 4 | -0,173 | mem | 0,269 | core |
| 5 | -0,713 | mem | 0,265 | core |

### 7.3. `66mhz-fase7500`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -1,699 | core | 0,313 | core |
| 2 | -1,380 | core | 0,268 | core |
| 3 | -0,204 | mem | 0,268 | core |
| 4 | -0,173 | mem | 0,279 | core |
| 5 | -1,674 | core | 0,303 | core |

### 7.4. `66mhz-fase8000`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,744 | mem | 0,267 | core |
| 2 | -0,882 | core | 0,304 | core |
| 3 | -0,204 | mem | 0,267 | core |
| 4 | -0,191 | mem | 0,261 | core |
| 5 | -0,907 | core | 0,265 | core |

### 7.5. `66mhz-fase8500`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,744 | mem | 0,306 | core |
| 2 | -0,290 | core | 0,270 | core |
| 3 | -0,205 | mem | 0,271 | core |
| 4 | -0,173 | mem | 0,291 | core |
| 5 | -0,713 | mem | 0,158 | jtag |

### 7.6. `66mhz-fase9000`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,745 | mem | 0,267 | core |
| 2 | -0,255 | mem | 0,283 | core |
| 3 | -0,339 | fetch | 0,279 | core |
| 4 | -0,173 | mem | 0,277 | core |
| 5 | -0,713 | mem | 0,258 | core |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
