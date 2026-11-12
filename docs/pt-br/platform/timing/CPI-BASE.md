# Ciclos por instrução de base da `de0-cv` a 76,923 MHz

🌐 [Português](CPI-BASE.md) · [English](../../../en/platform/timing/CPI-BASE.md)

## 1. Escopo

Este documento registra os ciclos por instrução dos programas de medida do repositório Tests na simulação da `de0-cv` com o RTL congelado (Insper-RISC-V `a612e9c`: Core `2ed0117`, Memory `768e81e`), e o custo, em ciclos, de cada passo da frente de frequência. Os números são o ponto de partida para qualquer mudança futura de pipeline.

## 2. Condições

| Item | Valor |
| :--- | :--- |
| Programa | `c-sdram/cpi-kernels` do Tests (`Tests` `c1fcead`) |
| Simulação | Topo `rv32im_sdram_flash_sim_test` no GHDL, imagem `ci-elf`, `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml sim --only cpi-kernels` |
| Plataforma | `de0-cv` com caches de 4 KiB, FLASH atrás das caches, perfil `rv32im_zicclsm_zicntr_zihpm_zifencei` com `extras` do `platform.yaml` |
| Medida | `cycle` e `instret` lidos antes e depois de cada núcleo de cálculo, as contagens são determinísticas |

## 3. Resultado

| Núcleo de cálculo | Ciclos | Instruções | Ciclos por instrução |
| :--- | ---: | ---: | ---: |
| Laço de inteiros | 2173 | 1300 | 1,67 |
| Multiplicação | 2920 | 275 | 10,62 |
| Divisão | 3075 | 276 | 11,14 |
| Leitura da SDRAM | 3757 | 1043 | 3,60 |
| Escrita de byte na SDRAM | 4166 | 786 | 5,30 |

## 4. Custo, em ciclos, de cada mudança da frente de frequência

| Mudança | Custo | Como foi medido |
| :--- | :--- | :--- |
| Leitura registrada do Zihpm (F.P6c) | Um ciclo por instrução CSR que acessa `mcountinhibit`, `mhpmeventK`, `mhpmcounterK` ou `mhpmcounterKh` | Teste de núcleo `test_a_bank_read_costs_one_cycle`: 16 leituras a mais custam 16 ciclos |
| Replay da busca (F.P5) | Zero nos acertos da cache de instruções; em cada falha, o PC volta à instrução depois de um ciclo e a busca só confirma a cada dois ciclos | Fórmula da `icache` (`Memory/docs/pt-br/cache/icache.md`): falha de $9 + k$ ciclos, antes $7 + k$ |
| Linhas de interrupção registradas | Um ciclo a mais entre o evento (MSIP, MTIP, MEIP) e o `mip` | Programa `clint-mtip` ajustado para esperar o `mip` |
| Invalidação da cache de instruções por varredura (F.P5) | $L + 4$ ciclos de busca na cache em cada `fence.i` e em cada invalidação por região, com $L$ linhas (256 na cache de 4 KiB) | Fórmula da `icache` |
| Classificação do endereço registrada (F.P4) | Zero | Mesmo ciclo da exceção e do stall |

## 5. O que não foi medido

Não há medida dos mesmos programas no RTL anterior à frente (a árvore anterior não roda com as ferramentas atuais do Tests). O CPI de comparação do início da frente está em [README.md](README.md), seção 3, medido com outros núcleos de cálculo (`cpi-core`, `cpi-data` e `cpi-fetch`).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
