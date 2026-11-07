# Calibração do cabimento

## 1. O que é medido

A calibração mede, por família, o custo em lógica de cada bloco do perfil com a síntese apenas (`quartus_map`), e o estimador do Tools (`fit_estimate`) soma esses custos para dizer se um perfil cabe numa placa. O dispositivo é medido, não a placa, e cada família tem a sua unidade (ALM na Cyclone V; LE nas demais).

| Arquivo | Conteúdo |
| :--- | :--- |
| `boards/calibration/profiles/<família>.yaml` | Lista dos perfis medidos, o que muda no `platform.yaml` e os generics de cada um |
| `boards/calibration/raw/<família>/<perfil>.yaml` | Dado bruto de uma síntese, com semente, hash das fontes, versão do Quartus e commits do projeto e dos submódulos |
| `boards/calibration/<família>.yaml` | Tabela ajustada, com o erro registrado e os resíduos de cada perfil |

## 2. Cyclone V (DE0-CV, 5CEBA4)

Núcleo calibrado: commit `1057cbcc67ac3a82af4d314489e1eb840b84e12c` do Core, com 24 perfis no ajuste e 4 de validação. Ferramenta: Quartus 25.1std.0 Build 1129 10/21/2025 SC Lite Edition. A frente F muda o núcleo, e a calibração do termo do núcleo (um perfil por família) é refeita depois do portão da frente F.

O topo da DE0-CV é fixo: a SDRAM, a FLASH, o display, a JTAG UART e o controlador de FLASH existem em todos os perfis e estão dentro do termo do núcleo (`absorbed` no arquivo da tabela). Os termos de cada periférico e do controlador de SDRAM de 16 bits valem zero por isso. Os controladores `sdram_32`, `nor` e `sram` não têm medida e continuam `null`, o que faz o estimador emitir V18 quando um perfil os pede. Cada cache tem o termo $c_0 = -32\,c_1$, porque o tamanho de 32 kbit já está no núcleo.

| Coeficiente | ALMs |
| :--- | ---: |
| `core.rv32i` | 5134,00 |
| `core.rv32e` | 4796,00 |
| `extensions.M` | 260,00 |
| `extensions.Zicclsm` | 42,25 |
| `extensions.Zicntr` | 316,75 |
| `extensions.Zicond` | 8,07 |
| `extensions.Zicsr` | 213,00 |
| `extensions.Zifencei` | 114,00 |
| `extensions.Zimop` | 25,07 |
| `extensions.Zmmul` | 222,00 |
| `extras.Interrupts` | 230,07 |
| `extras.Sscofpmf` | 274,00 |
| `extras.Zihintntl` | -2,93 |
| `extras.Zihintpause` | -1,93 |
| `zihpm.a0` | -34,17 |
| `zihpm.a1` | -0,06 |
| `zihpm.a2` | 1,51 |
| `cache.icache.c0` | -5,95 |
| `cache.icache.c1` | 0,19 |
| `cache.dcache.c0` | -639,52 |
| `cache.dcache.c1` | 19,98 |

A cache de dados custa cerca de 19,98 ALMs por kbit, contra 0,19 da cache de instruções, porque o arranjo de bytes da cache de dados é sintetizado em registradores.

## 3. Erro e portão GMC

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,29 % |
| Maior erro no ajuste | 0,94 % |
| Maior erro nos perfis de validação | 1,23 % |

O erro máximo de validação fica abaixo de 10 %, então a Cyclone V habilita o erro de lógica (V12).

A estimativa da síntese do perfil completo é de 9569 ALMs, contra a faixa de 8058 a 8095 ALMs conhecida depois do ajuste, de modo que a razão ajuste sobre síntese é de 0,8421 a 0,846 (`map_to_fit_ratio` = 0,844). O estimador multiplica a soma pela razão para comparar com a capacidade do ajuste. A razão sai de um único ponto, medido numa versão anterior do núcleo, e um ajuste do perfil completo do Quartus deve confirmá-la.

## 4. Resíduos por perfil

| Perfil | Medido | Previsto | Erro (%) | Validação |
| :--- | ---: | ---: | ---: | :--- |
| `p1_rv32i` | 5134 | 5134,00 | 0,00 | não |
| `p1_rv32e` | 4796 | 4796,00 | 0,00 | não |
| `p2_rv32im` | 5616 | 5616,00 | 0,00 | não |
| `p2_rv32i_zmmul` | 5356 | 5356,00 | 0,00 | não |
| `p3_zicsr` | 5829 | 5829,00 | 0,00 | não |
| `p3_zicsr_zifencei` | 5943 | 5943,00 | 0,00 | não |
| `p3_zicntr_zifencei` | 6259 | 6259,70 | 0,01 | não |
| `p3_zicclsm_zicntr_zifencei` | 6302 | 6302,00 | 0,00 | não |
| `p4_hpm_4x40` | 6506 | 6508,70 | 0,04 | não |
| `p4_hpm_4x64` | 6655 | 6653,40 | -0,02 | não |
| `p4_hpm_29x40` | 8038 | 8014,10 | -0,30 | não |
| `p4_hpm_0x64` | 6314 | 6267,80 | -0,73 | não |
| `p4_hpm_8x32` | 6591 | 6653,10 | 0,94 | não |
| `p4_hpm_16x52` | 7614 | 7520,70 | -1,23 | sim |
| `p5_base` | 9058 | 9063,00 | 0,06 | não |
| `p5_full` | 9569 | 9595,40 | 0,28 | sim |
| `p6_zimop` | 9089 | 9088,10 | -0,01 | não |
| `p6_zicond` | 9072 | 9071,10 | -0,01 | não |
| `p6_zihintntl` | 9061 | 9060,10 | -0,01 | não |
| `p6_zihintpause` | 9062 | 9061,10 | -0,01 | não |
| `p6_interrupts` | 9294 | 9293,10 | -0,01 | não |
| `p6_interrupts_sscofpmf` | 9568 | 9567,10 | -0,01 | não |
| `p7_ic8` | 6225 | 6255,30 | 0,49 | não |
| `p7_ic128` | 6270 | 6277,60 | 0,12 | não |
| `p7_dc8` | 5811 | 5780,10 | -0,53 | não |
| `p7_dc128` | 8186 | 8178,30 | -0,09 | não |
| `p7_ic64` | 6264 | 6265,70 | 0,03 | sim |
| `p7_dc64` | 6917 | 6899,30 | -0,26 | sim |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
