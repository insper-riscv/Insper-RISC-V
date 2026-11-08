# Quartus completo do Core novo nos topos da DE0-CV

🌐 [Português](core-novo.md) · [English](../../../en/platform/timing/core-novo.md)

## 1. Escopo

Este documento registra a compilação completa no Quartus dos três topos do Insper-RISC-V com o Core novo (Zimop e Zicond como `extras:`, Zihintntl, Zihintpause e interrupções com `has_interrupts`, padrão `false`) e o custo do mecanismo de interrupções ligado na `de0-cv`. Ele complementa a [linha de base](README.md), que mediu o perfil completo antes desses recursos, e é a referência de área e de Fmax anterior a qualquer decisão sobre os 100 MHz. Nenhum arquivo de RTL foi alterado.

## 2. Condições da medição

| Item | Valor |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, na workstation PC1 (sementes 1 e 2) e no notebook (sementes 3 a 5 e o experimento com as entradas em `0`) |
| Dispositivo | 5CEBA4F23C7 (Cyclone V) |
| Fontes | Insper-RISC-V `224a762` (`main`, posterior à tag `Onda-0`), Common-Components `9aa6a75`, Core `8a828cc`, Memory `1160ae1`, Peripherals `d7253f6`; hash da árvore (`git ls-files -s` do topo e dos quatro submódulos) `8576b682405b711e` |
| Modo | `HIGH PERFORMANCE EFFORT`, sementes 1 a 5, pelos roteiros `de0-cv_synth.tcl`, `external-data_synth.tcl` e `dados/core-novo/core_fpga_test_synth.tcl` |
| Relógios | 50 MHz no núcleo e na busca (fase do núcleo como versionada), 142,857 MHz no controlador da SDRAM e em `DRAM_CLK` nos topos com SDRAM |
| Perfil | O de cada `platform.yaml`: `rv32im_zicclsm_zicntr_zihpm_zifencei` com `extras: [Zimop, Zicond]`, 29 contadores de 64 bits do Zihpm |
| Folga de setup | Modelo lento a 85 °C, folga do domínio de relógio de destino |
| Folga de hold | Modelo rápido a 0 °C, menor valor entre os domínios |

As mesmas sementes dão o mesmo resultado nas duas máquinas: a `de0-cv` na semente 5 (8 095 ALMs e 67,32 MHz) e o `external-data` na semente 5 (8 227 ALMs e 63,54 MHz) coincidem com as compilações feitas antes na PC1.

## 3. Resultados por topo

Os domínios são o do núcleo (`clk_idexmem`), o de busca (`clk_if`), o do controlador da SDRAM, `DRAM_CLK` e o JTAG; no `core_fpga_test` há só núcleo, busca, o relógio de entrada e o JTAG. As folgas estão em ns. A coluna "Pior" traz o maior uso de recursos e a menor Fmax e folga das cinco sementes.

#### `de0-cv`

| Semente | ALMs | Registradores | M10K | Fmax do núcleo (MHz) | setup núcleo | setup busca | setup SDRAM | setup `DRAM_CLK` | setup JTAG | hold mínimo |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 058 | 9 227 | 271 | 65,07 | -0,729 | 3,582 | -0,744 | 0,428 | 10,433 | 0,142 |
| 2 | 8 091 | 9 267 | 271 | 65,58 | -1,345 | 5,406 | -0,255 | -0,127 | 7,612 | 0,149 |
| 3 | 8 084 | 9 222 | 271 | 62,44 | -0,350 | 3,403 | -0,208 | -0,042 | 9,873 | 0,125 |
| 4 | 8 082 | 9 222 | 271 | 62,23 | -0,560 | 4,491 | -0,173 | -0,078 | 10,824 | 0,002 |
| 5 | 8 095 | 9 172 | 271 | 67,32 | -1,001 | 4,160 | -0,713 | 0,394 | 11,068 | 0,142 |
| Pior | 8 095 | 9 267 | 271 | 62,23 | -1,345 | 3,403 | -0,744 | -0,127 | 7,612 | 0,002 |
| Média | 8 082 | 9 222 | 271 | 64,53 |  |  |  |  |  | |

#### `external-data`

| Semente | ALMs | Registradores | M10K | Fmax do núcleo (MHz) | setup núcleo | setup busca | setup SDRAM | setup `DRAM_CLK` | setup JTAG | hold mínimo |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 225 | 8 452 | 234 | 64,51 | 0,033 | 5,158 | -0,731 | 0,416 | 10,039 | 0,126 |
| 2 | 8 215 | 8 461 | 234 | 63,56 | 0,129 | 4,703 | -0,203 | -0,048 | 10,878 | 0,121 |
| 3 | 8 201 | 8 564 | 234 | 65,38 | 0,308 | 4,210 | -0,730 | 0,413 | 9,335 | 0,039 |
| 4 | 8 190 | 8 448 | 234 | 62,25 | 0,665 | 4,956 | -0,191 | -0,061 | 10,339 | 0,107 |
| 5 | 8 227 | 8 480 | 234 | 63,54 | -0,204 | 4,126 | -0,743 | 0,427 | 9,142 | 0,099 |
| Pior | 8 227 | 8 564 | 234 | 62,25 | -0,204 | 4,126 | -0,743 | -0,061 | 9,142 | 0,039 |
| Média | 8 212 | 8 481 | 234 | 63,85 |  |  |  |  |  | |

#### `core_fpga_test`

| Semente | ALMs | Registradores | M10K | Fmax do núcleo (MHz) | setup núcleo | setup busca | setup `i_clock_50` | setup JTAG | hold mínimo |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7 172 | 7 987 | 288 | 66,98 | 1,412 | 3,272 | 16,116 | 10,705 | 0,124 |
| 2 | 7 173 | 8 005 | 288 | 66,18 | 1,212 | 3,071 | 16,097 | 10,722 | 0,113 |
| 3 | 7 163 | 7 821 | 288 | 66,70 | 1,140 | 4,200 | 15,883 | 11,476 | 0,120 |
| 4 | 7 103 | 7 804 | 288 | 67,80 | 1,320 | 3,935 | 16,108 | 9,675 | 0,128 |
| 5 | 7 142 | 8 019 | 288 | 64,15 | 1,122 | 3,000 | 16,080 | 10,595 | 0,118 |
| Pior | 7 173 | 8 019 | 288 | 64,15 | 1,122 | 3,000 | 15,883 | 9,675 | 0,113 |
| Média | 7 151 | 7 927 | 288 | 66,36 |  |  |  |  | |

#### `de0-cv` com `has_interrupts`

| Semente | ALMs | Registradores | M10K | Fmax do núcleo (MHz) | setup núcleo | setup busca | setup SDRAM | setup `DRAM_CLK` | setup JTAG | hold mínimo |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8 060 | 9 298 | 271 | 64,56 | -0,918 | 3,946 | -0,744 | 0,428 | 10,144 | 0,010 |
| 2 | 8 078 | 9 245 | 271 | 63,02 | -1,702 | 3,237 | -0,255 | -0,127 | 9,465 | 0,051 |
| 3 | 8 078 | 9 272 | 271 | 65,53 | -0,237 | 3,893 | -0,204 | -0,047 | 9,596 | 0,148 |
| 4 | 8 098 | 9 180 | 271 | 66,45 | -0,380 | 4,189 | -0,191 | -0,060 | 10,191 | 0,124 |
| 5 | 8 078 | 9 271 | 271 | 65,58 | -0,649 | 4,500 | -0,728 | 0,410 | 10,860 | 0,123 |
| Pior | 8 098 | 9 298 | 271 | 63,02 | -1,702 | 3,237 | -0,744 | -0,127 | 9,465 | 0,010 |
| Média | 8 078 | 9 253 | 271 | 65,03 |  |  |  |  |  | |

#### `de0-cv` com `has_interrupts` e as entradas em `0`

| Semente | ALMs | Registradores | M10K | Fmax do núcleo (MHz) | setup núcleo | setup busca | setup SDRAM | setup `DRAM_CLK` | setup JTAG | hold mínimo |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 8 069 | 9 190 | 271 | 65,07 | -1,229 | 4,772 | -0,713 | 0,394 | 11,045 | 0,139 |

## 4. Custo do mecanismo de interrupções

A variante `de0-cv` com `has_interrupts => true` liga `i_irq_software`, `i_irq_timer` e `i_irq_external` a três bits de `sdram_rdata` registrados no relógio do núcleo, porque o CLINT e o controlador externo ainda não estão ligados ao topo e entradas constantes deixariam o Quartus podar o `mip`. A variante de controle prende as três entradas a `0` (semente 5). Os `diff` das duas cópias descartáveis estão em `dados/core-novo/experimento-interrupcoes/`.

| Medida (média das sementes 1 a 5) | `de0-cv` | com `has_interrupts` | Diferença |
| :--- | ---: | ---: | ---: |
| ALMs | 8 082 | 8 078 | -4 |
| Registradores | 9 222 | 9 253 | +31 |
| M10K | 271 | 271 | 0 |
| Fmax do núcleo (MHz) | 64,53 | 65,03 | +0,50 |
| Pior folga de setup do núcleo (ns) | -1,345 | -1,702 | -0,357 |

Na semente 5, as entradas presas a `0` dão 8 069 ALMs e 9 190 registradores, contra 8 078 e 9 271 com as entradas vivas e 8 095 e 9 172 sem o mecanismo.

## 5. Leitura dos números

1. **Área.** Os três topos ocupam 7 100 a 8 230 ALMs (38 a 45 % das 18 480). A `de0-cv` ficou entre 8 058 e 8 095 ALMs, no mesmo intervalo da linha de base (8 037 a 8 090), então o Core novo não custa área mensurável nela. O `external-data` usa cerca de 130 ALMs a mais que a `de0-cv` e 740 registradores a menos, e libera 37 dos 271 M10K (234 de 308, 76 %). O `core_fpga_test` (memórias internas) usa 7 103 a 7 173 ALMs e 288 M10K (94 %).
2. **Fmax.** O domínio do núcleo fecha em 62,23 a 67,32 MHz na `de0-cv`, 62,25 a 65,38 MHz no `external-data` e 64,15 a 67,80 MHz no `core_fpga_test`. O pior valor da `de0-cv` (62,23 MHz) é 2 MHz abaixo do pior da linha de base (64,30 MHz), dentro da dispersão entre sementes de cerca de 5 MHz. Nenhum topo chega perto de 100 MHz, e a conclusão estrutural da frente F não muda.
3. **Folga a 50 MHz.** Na `de0-cv` o núcleo falha em todas as sementes (pior -1,345 ns), contra -1,604 ns da linha de base, e o controlador da SDRAM e `DRAM_CLK` mantêm a violação pequena já conhecida (pior -0,744 e -0,127 ns). No `external-data` o núcleo fecha em quatro sementes (pior -0,204 ns na semente 5) e a violação restante é a do controlador da SDRAM (pior -0,743 ns) e de `DRAM_CLK` (pior -0,061 ns). O `core_fpga_test` fecha o setup em todas as sementes (menor folga 1,122 ns).
4. **Hold.** A folga de hold no modelo rápido a 0 °C é positiva em todos os topos e sementes; o menor valor é 0,002 ns (JTAG, `de0-cv`, semente 4), e nos relógios do núcleo e da busca o menor é 0,039 ns (núcleo do `external-data`, semente 3).
5. **Interrupções.** O mecanismo custa menos que a dispersão entre sementes: a diferença de ALMs (-4) e a de Fmax (+0,50 MHz) estão dentro dela, e os 31 registradores a mais correspondem ao `mie`, aos bits de `mstatus` e ao ponto de captura das entradas. As folgas de setup do núcleo com `has_interrupts` (-0,237 a -1,702 ns) cobrem a mesma faixa que sem ele (-0,350 a -1,345 ns).

## 6. Como reproduzir

| Objetivo | Comando |
| :--- | :--- |
| `de0-cv` e `external-data` | `quartus_sh -t src/cyclone-v/<plataforma>/<plataforma>_synth.tcl <semente>`, numa cópia do repositório |
| `core_fpga_test` | Copiar `dados/core-novo/core_fpga_test_synth.tcl` para `src/simulation/internal-mem/quartus/` e rodar `quartus_sh -t core_fpga_test_synth.tcl <semente>` ali |
| Variante com interrupções | Aplicar `dados/core-novo/experimento-interrupcoes/irq.patch` (ou `irq0.patch`) a `src/cyclone-v/de0-cv/de0-cv_top.vhd` na cópia |
| Folgas e Fmax | `output_files/<projeto>.sta.summary` e `output_files/<projeto>.sta.rpt` |

## 7. Dados brutos

Em `dados/core-novo/` ficam `tabela-sementes.tsv` (o `.sta.summary` de cada compilação `<topo>-semente-<n>`) e `tabela-ocupacao.tsv` (o `.fit.summary`). Os topos são `de0-cv`, `external-data`, `core_fpga_test`, `irq` (`de0-cv` com `has_interrupts`, sementes 1 a 5) e `irq0` (entradas em `0`, semente 5). As extensões `.rpt` e `.summary` foram trocadas por `.txt` porque o `.gitignore` as ignora. Os relatórios completos e logs do Quartus não são versionados; regere-os com `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <semente>` sobre a compilação da semente pedida, que deixa o `.sta.rpt` e o `.fit.rpt` em `output_files/`.

## 8. Tabelas por semente

Os valores vêm de `dados/core-novo/tabela-sementes.tsv`, gerado por `dados/tabelar_resumos.py` a partir dos `.sta.summary` do Timing Analyzer (modelo lento, 1100 mV, 85 °C). Cada tabela lista, por semente, o pior setup, o pior hold e o domínio em que cada um ocorre. Os domínios são `core` (saída 3 da PLL), `fetch` (saída 2), `mem` (saída 0, controlador da SDRAM), `DRAM_CLK` (pino) e `jtag`; no topo `core_fpga_test` as saídas da PLL aparecem como `pll_c0` e `pll_c1`, e `pll_dram_clk` e `pll_vco` só têm largura mínima de pulso. O TSV traz também TNS, recovery, removal, largura mínima de pulso e o pior valor entre os quatro modelos de temperatura e tensão. A ocupação por semente está em `dados/core-novo/tabela-ocupacao.tsv`.

As medições descrevem a plataforma congelada em 76,923077 MHz e os experimentos listados. Um novo ataque de frequência regera a tabela com `python3 dados/tabelar_resumos.py gerar dados/core-novo` sobre os `.resumo.txt` das sementes novas (o `.sta.summary` e o `.fit.summary` do Quartus renomeados), e `--check` confere o TSV contra eles. Os resumos brutos não são versionados, e as tabelas são a referência de partida para a próxima rodada.

### 8.1. `de0-cv`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,744 | mem | 0,295 | core |
| 2 | -1,345 | core | 0,317 | core |
| 3 | -0,350 | core | 0,306 | core |
| 4 | -0,560 | core | 0,141 | jtag |
| 5 | -1,001 | core | 0,280 | core |

| Semente | ALMs | Registradores | Pinos | Blocos de RAM |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 8,058 / 18,480 ( 44 % ) | 9227 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 2 | 8,091 / 18,480 ( 44 % ) | 9267 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 3 | 8,084 / 18,480 ( 44 % ) | 9222 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 4 | 8,082 / 18,480 ( 44 % ) | 9222 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 5 | 8,095 / 18,480 ( 44 % ) | 9172 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |

### 8.2. `external-data`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,731 | mem | 0,267 | core |
| 2 | -0,203 | mem | 0,255 | core |
| 3 | -0,730 | mem | 0,253 | core |
| 4 | -0,191 | mem | 0,264 | core |
| 5 | -0,743 | mem | 0,292 | core |

| Semente | ALMs | Registradores | Pinos | Blocos de RAM |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 8,225 / 18,480 ( 45 % ) | 8452 | 93 / 224 ( 42 % ) | 234 / 308 ( 76 % ) |
| 2 | 8,215 / 18,480 ( 44 % ) | 8461 | 93 / 224 ( 42 % ) | 234 / 308 ( 76 % ) |
| 3 | 8,201 / 18,480 ( 44 % ) | 8564 | 93 / 224 ( 42 % ) | 234 / 308 ( 76 % ) |
| 4 | 8,190 / 18,480 ( 44 % ) | 8448 | 93 / 224 ( 42 % ) | 234 / 308 ( 76 % ) |
| 5 | 8,227 / 18,480 ( 45 % ) | 8480 | 93 / 224 ( 42 % ) | 234 / 308 ( 76 % ) |

### 8.3. `core_fpga_test`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | 1,412 | pll_c1 | 0,266 | pll_c1 |
| 2 | 1,212 | pll_c1 | 0,304 | pll_c1 |
| 3 | 1,140 | pll_c1 | 0,257 | pll_c1 |
| 4 | 1,320 | pll_c1 | 0,351 | pll_c1 |
| 5 | 1,122 | pll_c1 | 0,257 | pll_c1 |

| Semente | ALMs | Registradores | Pinos | Blocos de RAM |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 7,172 / 18,480 ( 39 % ) | 7987 | 14 / 224 ( 6 % ) | 288 / 308 ( 94 % ) |
| 2 | 7,173 / 18,480 ( 39 % ) | 8005 | 14 / 224 ( 6 % ) | 288 / 308 ( 94 % ) |
| 3 | 7,163 / 18,480 ( 39 % ) | 7821 | 14 / 224 ( 6 % ) | 288 / 308 ( 94 % ) |
| 4 | 7,103 / 18,480 ( 38 % ) | 7804 | 14 / 224 ( 6 % ) | 288 / 308 ( 94 % ) |
| 5 | 7,142 / 18,480 ( 39 % ) | 8019 | 14 / 224 ( 6 % ) | 288 / 308 ( 94 % ) |

### 8.4. `irq`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 1 | -0,918 | core | 0,150 | jtag |
| 2 | -1,702 | core | 0,266 | core |
| 3 | -0,237 | core | 0,310 | core |
| 4 | -0,380 | core | 0,318 | core |
| 5 | -0,728 | mem | 0,301 | core |

| Semente | ALMs | Registradores | Pinos | Blocos de RAM |
| :--- | ---: | ---: | ---: | ---: |
| 1 | 8,060 / 18,480 ( 44 % ) | 9298 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 2 | 8,078 / 18,480 ( 44 % ) | 9245 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 3 | 8,078 / 18,480 ( 44 % ) | 9272 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 4 | 8,098 / 18,480 ( 44 % ) | 9180 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |
| 5 | 8,078 / 18,480 ( 44 % ) | 9271 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |

### 8.5. `irq0`

| Semente | Pior setup (ns) | Domínio | Pior hold (ns) | Domínio |
| :--- | ---: | :--- | ---: | :--- |
| 5 | -1,229 | core | 0,273 | core |

| Semente | ALMs | Registradores | Pinos | Blocos de RAM |
| :--- | ---: | ---: | ---: | ---: |
| 5 | 8,069 / 18,480 ( 44 % ) | 9190 | 93 / 224 ( 42 % ) | 271 / 308 ( 88 % ) |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
