# Retomada do clock: do 76,9 MHz aos 100 MHz

🌐 [Português](RETOMADA-DO-CLOCK.md) · [English](../../../en/platform/timing/RETOMADA-DO-CLOCK.md)

## 1. Estado

A plataforma `de0-cv` roda o núcleo e a busca a 76,923077 MHz (1000 MHz dividido por 13), com a fase do núcleo em 7500 ps, valores de `pll.core_clock_hz` e `pll.core_phase_ps` do `platform.yaml`. As cinco sementes fecham o setup no modelo lento a 85 °C e o hold no modelo rápido a 0 °C em todos os domínios, com a pior folga de núcleo de +0,562 ns ([FRENTE-F-ONDA2.md](FRENTE-F-ONDA2.md), seção 9). O controlador da SDRAM e o `DRAM_CLK` fecham a 100 MHz com mais de +1,1 ns. Os 100 MHz faltam no laço do estágio EX.

| Frequência | Núcleo, pior de 5 sementes | Observação |
| :--- | ---: | :--- |
| 76,923 MHz | +0,562 ns | Fecha |
| 83,333 MHz | -0,771 ns | Núcleo para núcleo; o par núcleo para busca falha em quatro sementes (-1,268 ns) |
| 100 MHz | -2,300 ns | Melhor semente -1,220 ns; busca, SDRAM e `DRAM_CLK` fecham |

## 2. O laço de EX

O laço que limita os 100 MHz nasce em `r_we_ok` e `r_fwd_match_rs*` (registradores de `ID/EX` e `EX/MEM`) e atravessa:

| Trecho | Níveis de LUT | Atraso típico (ns) |
| :--- | ---: | ---: |
| Seleção do adiantamento (`forwarding_unit`, fan-out 98) | 1 | 0,9 a 1,3 |
| Multiplexador do operando A (`u_mux_alu_a`) | 2 | 1,6 |
| ULA (somador, deslocador, seleção do resultado) | 4 | 4,5 a 5,0 |
| Classificação do endereço, decisão de desvio, limpeza de `IF/ID`, `ID/EX` e `EX/MEM`, habilitação do PC | 3 a 4 | 3,0 a 3,5 |

A soma dá 11,0 a 11,5 ns de dados contra o período de 10 ns. A causa é estrutural, e não de roteamento isolado: o adiantamento, a ULA e a decisão que limpa o pipeline estão em série dentro de um ciclo. Os destinos do mesmo laço que terminam em `r_alu_out` (11,0 a 11,5 ns) mostram que cortar só a limpeza não basta.

## 3. Como repetir a medição

Os arquivos estão em `dados/frente-f-onda2/` e rodam na PC1, com a trava do Quartus.

```
export TIMING_DIR=/tmp/timing          # contém os .tcl desta pasta
flock /tmp/quartus-workstation.lock \
  printf "6000 1\n6000 2\n6000 3\n6000 4\n6000 5\n" | \
  xargs -P 3 -L 1 bash -c './run-sementes.sh cem_p$0 <copia-do-repositorio> 100.000000 $0 $1'
```

O roteiro `run-sementes.sh` copia o repositório por semente, troca a frequência e a fase das saídas 2 e 3 da PLL na cópia, compila com `de0-cv_synth.tcl` e grava `pares.txt` (os 400 piores caminhos por par de relógios) e `detail-*.rpt`. `agrupa_caminhos.py pares.txt` lista os caminhos por origem e destino, `pior_por_par.py pares.txt` dá a pior folga por par, e `levels.tcl` com `niveis_resumo.py` gera a lista por níveis de lógica. Rode no máximo três sementes ao mesmo tempo na PC1.

## 4. Ideias ainda não tentadas

1. Adiantar para a ULA só a partir de registradores: o resultado de EX é registrado e usado no ciclo seguinte. Tira a seleção e o multiplexador do adiantamento do laço, ao custo de um ciclo em cada dependência de dado imediata (CPI de código com cadeias curtas de dependência sobe). Cabe nos cinco estágios.
2. Calcular a seleção do adiantamento no estágio ID e registrá-la em `ID/EX`, já combinada com a validade das instruções à frente (hoje o `ok` entra por último e tem fan-out 98).
3. Registrar o redirecionamento de desvio e JALR (um ciclo a mais por desvio tomado, com o descarte da instrução que entra em EX). Corta os destinos de limpeza, mas não os que terminam em `r_alu_out`; só vale junto com a ideia 1 ou 2.
4. Calcular a classificação do endereço a partir de `rs1` e `imm` em paralelo com a soma: as três hipóteses do vai-um das páginas de 4 KiB, escolhidas pelo transporte do somador de 12 bits.
5. Região LogicLock para o laço de EX no `.qsf` versionado, só se medir ganho de roteamento (1,3 a 1,9 ns entre níveis nos caminhos mais longos).
6. Replicação manual de `r_we_ok` e dos seletores (o atributo `maxfan` não é aceito pelo GHDL do formal e o Quartus não o aproveitou).
7. Trocar o deslocador por uma versão de dois ciclos só para `sll`, `srl` e `sra` (o deslocamento é o ramo mais longo da ULA depois do somador).

## 5. Critério de pronto dos 100 MHz

| # | Critério | Como se verifica |
| :--- | :--- | :--- |
| 1 | As cinco sementes fecham o setup no modelo lento a 85 °C em todos os domínios (núcleo, busca, SDRAM, `DRAM_CLK`, JTAG) e o hold no modelo rápido a 0 °C | `output_files/de0-cv.sta.summary` de cada semente, tabela em `FRENTE-F-ONDA2.md` |
| 2 | `platform.yaml` traz `pll.core_clock_hz: 100000000`, a fase que fechou e `interrupts.clock_hz` coerente; `make check-memory-map` passa | `riscv-tools check-memory-map` |
| 3 | Todos os programas da placa passam e os ELFs do ACT4 do perfil completo passam, na placa | `tools/board/board_run.py run` e `certify-board` |
| 4 | `make test` e `make formal` do Core, a prova da `icache` e os testes de plataforma passam | CI dos repositórios |
| 5 | O CPI base dos programas do Tests é registrado antes e depois | [CPI-BASE.md](CPI-BASE.md) |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
