# Calibração do cabimento

## 1. O que é medido

A calibração mede, por família, o custo em lógica de cada bloco do perfil com a síntese apenas (`quartus_map`), e o estimador do Tools (`fit_estimate`) soma esses custos para dizer se um perfil cabe numa placa. O dispositivo é medido, não a placa, e cada família tem a sua unidade (ALM na Cyclone V; LE nas demais). O projeto que o Quartus lê vem do `board generate`, e a compilação passa pelo `compile.tcl` único do `program`, de modo que as quatro famílias seguem o mesmo caminho e o mesmo conjunto de fontes.

| Arquivo | Conteúdo |
| :--- | :--- |
| `src/calibration/<placa>/platform.yaml` | Plataforma de calibração da placa de medida e o pacote do mapa de memória dela |
| `boards/calibration/profiles/<família>.yaml` | Lista dos perfis medidos, o que muda no `platform.yaml` e os generics de cada um |
| `boards/calibration/raw/<família>/<perfil>.yaml` | Dado bruto de uma síntese, com semente, hash das fontes, versão do Quartus e commits do projeto e dos submódulos |
| `boards/calibration/<família>.yaml` | Tabela ajustada, com o erro registrado e os resíduos de cada perfil |
| `boards/calibration/profiles/verify-<placa>.yaml` | Perfis medidos em outro dispositivo da família, para a verificação cruzada |
| `boards/calibration/verification/<placa>.yaml` | Comparação da tabela da família com esses perfis |
| `boards/calibration/cyclone-v-manual.yaml` e `raw/cyclone-v-manual/` | Medidas do topo da DE0-CV escrito à mão, com o ponto conhecido de 8058 a 8095 ALMs |

## 2. Plataforma de calibração

Cada família é medida na sua placa de referência com a mesma plataforma de calibração, que troca a cada medida o perfil, os extras, as caches e os generics do Zihpm. A plataforma tem a BOOT_MEMORY de 4 KiB, a FLASH emulada (28 KiB, ou 12 KiB na Vidor) com carregador e JTAG, o console pela JTAG UART, o display e o controlador de FLASH. Esses blocos existem em todos os perfis e ficam dentro do termo do núcleo, de modo que os termos de cada periférico valem zero (`absorbed` na tabela). Alguns coeficientes de extensões pequenas saem negativos (por exemplo `extensions.Zimop` na Cyclone IV E e `extras.Sscofpmf` na Cyclone 10 LP), porque a síntese reorganiza a lógica quando a extensão liga e o perfil com ela sai menor que a base. O coeficiente guarda a diferença medida, e o estimador a soma com o sinal que ela tem. A RAM é o que muda de uma placa para outra, e na Vidor as memórias ficam dentro dos 504 kbit do 10CL016, porque acima disso a síntese converte a RAM em lógica e o custo das caches de 64 e 128 kbit deixa de ser o da cache.

| Família | Placa de medida | Dispositivo | Unidade | RAM da plataforma |
| :--- | :--- | :--- | :--- | :--- |
| Cyclone V | DE0-CV | 5CEBA4 | ALM | SDRAM de 16 bits, com o controlador dentro do termo do núcleo |
| Cyclone IV E | DE2-115 | EP4CE115 | LE | emulada em blocos de 64 KiB, porque a SDRAM tem 32 bits e o Memory não tem controlador dessa largura |
| MAX 10 | DE10-Lite | 10M50DA | LE | SDRAM de 16 bits, com o controlador dentro do termo do núcleo |
| Cyclone 10 LP | MKR Vidor 4000 | 10CL016 | LE | emulada em blocos de 8 KiB, porque o controlador de SDRAM do Memory tem endereço de linha de 13 bits e a SDRAM da placa tem 12 |

Os termos `backends.sdram_32`, `backends.nor` e `backends.sram` não têm medida e ficam `null`, o que faz o estimador emitir V18 quando um perfil os pede. O termo `backends.sdram_16` vale zero nas famílias cuja plataforma tem a SDRAM e fica `null` nas outras. Cada cache tem o termo $c_0 = -32\,c_1$, porque o tamanho de 32 kbit já está no núcleo.

Cada plataforma de calibração fica em `src/calibration/<placa>/` com o pacote do mapa de memória gerado, e o campo `top` dela cita o componente `cal_<placa>_board` do `paths.yaml`, cujo fecho de `requires` é a lista de fontes do projeto que o `board generate` escreve.

O Quartus é o 25.1std.0 Build 1129 Lite Edition, a semente é 5 e o núcleo é o commit `1057cbcc67ac3a82af4d314489e1eb840b84e12c` do Core. A frente F muda o núcleo, e o termo do núcleo (um perfil por família, `p1_rv32i`) é refeito depois do portão dela.

## 3. Cyclone V (DE0-CV, 5CEBA4)

| Coeficiente | ALMs |
| :--- | ---: |
| `cache.dcache.c0` | -202,27 |
| `cache.dcache.c1` | 6,32 |
| `cache.icache.c0` | -0,16 |
| `cache.icache.c1` | 0,01 |
| `core.rv32e` | 3.756,00 |
| `core.rv32i` | 4.122,00 |
| `extensions.M` | 153,00 |
| `extensions.Zicclsm` | 114,70 |
| `extensions.Zicntr` | 314,30 |
| `extensions.Zicond` | 6,60 |
| `extensions.Zicsr` | 175,00 |
| `extensions.Zifencei` | 1,00 |
| `extensions.Zimop` | -4,40 |
| `extensions.Zmmul` | 161,00 |
| `extras.Interrupts` | 236,60 |
| `extras.Sscofpmf` | 108,00 |
| `extras.Zihintntl` | -2,40 |
| `extras.Zihintpause` | -1,40 |
| `zihpm.a0` | -15,62 |
| `zihpm.a1` | -9,95 |
| `zihpm.a2` | 1,67 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,18 % |
| Maior erro no ajuste | 0,68 % |
| Maior erro nos perfis de validação | 0,27 % |
| Razão ajuste sobre síntese | 0,9693 |

Resíduos dos perfis de validação (os outros 24 perfis estão em `boards/calibration/cyclone-v.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 6.275 | 6.258,1 | -0,27 |
| `p5_full` | 8.199 | 8.185,0 | -0,17 |
| `p7_ic64` | 4.927 | 4.926,5 | -0,01 |
| `p7_dc64` | 5.129 | 5.128,6 | -0,01 |

## 4. Cyclone IV E (DE2-115, EP4CE115)

| Coeficiente | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -719,04 |
| `cache.dcache.c1` | 22,47 |
| `cache.icache.c0` | -19,04 |
| `cache.icache.c1` | 0,59 |
| `core.rv32e` | 7.495,00 |
| `core.rv32i` | 8.819,00 |
| `extensions.M` | 346,00 |
| `extensions.Zicclsm` | 123,52 |
| `extensions.Zicntr` | 670,48 |
| `extensions.Zicond` | 5,50 |
| `extensions.Zicsr` | 570,00 |
| `extensions.Zifencei` | 274,00 |
| `extensions.Zimop` | -499,50 |
| `extensions.Zmmul` | 596,00 |
| `extras.Interrupts` | 751,50 |
| `extras.Sscofpmf` | 572,00 |
| `extras.Zihintntl` | -22,50 |
| `extras.Zihintpause` | -12,50 |
| `zihpm.a0` | 31,79 |
| `zihpm.a1` | -45,04 |
| `zihpm.a2` | 4,19 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,35 % |
| Maior erro no ajuste | 1,39 % |
| Maior erro nos perfis de validação | 2,62 % |
| Razão ajuste sobre síntese | 0,8449 |

Resíduos dos perfis de validação (os outros 24 perfis estão em `boards/calibration/cyclone-iv-e.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 14.261 | 14.193,7 | -0,47 |
| `p5_full` | 19.193 | 18.690,2 | -2,62 |
| `p7_ic64` | 11.228 | 11.294,5 | 0,59 |
| `p7_dc64` | 12.058 | 11.994,5 | -0,53 |

## 5. MAX 10 (DE10-Lite, 10M50DA)

| Coeficiente | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -724,61 |
| `cache.dcache.c1` | 22,64 |
| `cache.icache.c0` | -3,74 |
| `cache.icache.c1` | 0,12 |
| `core.rv32e` | 9.138,00 |
| `core.rv32i` | 10.404,00 |
| `extensions.M` | 387,00 |
| `extensions.Zicclsm` | 245,55 |
| `extensions.Zicntr` | 660,45 |
| `extensions.Zicond` | 57,78 |
| `extensions.Zicsr` | 408,00 |
| `extensions.Zifencei` | 331,00 |
| `extensions.Zimop` | -4,21 |
| `extensions.Zmmul` | 541,00 |
| `extras.Interrupts` | 624,78 |
| `extras.Sscofpmf` | 482,00 |
| `extras.Zihintntl` | -4,21 |
| `extras.Zihintpause` | -6,21 |
| `zihpm.a0` | -17,73 |
| `zihpm.a1` | -23,86 |
| `zihpm.a2` | 3,37 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,14 % |
| Maior erro no ajuste | 0,60 % |
| Maior erro nos perfis de validação | 0,63 % |
| Razão ajuste sobre síntese | 0,8800 |

Resíduos dos perfis de validação (os outros 24 perfis estão em `boards/calibration/max-10.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 15.423 | 15.378,1 | -0,29 |
| `p5_full` | 19.662 | 19.664,6 | 0,01 |
| `p7_ic64` | 12.771 | 12.735,2 | -0,28 |
| `p7_dc64` | 13.541 | 13.456,1 | -0,63 |

## 6. Cyclone 10 LP (MKR Vidor 4000, 10CL016)

| Coeficiente | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -747,97 |
| `cache.dcache.c1` | 23,37 |
| `cache.icache.c0` | -0,51 |
| `cache.icache.c1` | 0,02 |
| `core.rv32e` | 7.261,00 |
| `core.rv32i` | 8.540,00 |
| `extensions.M` | 386,00 |
| `extensions.Zicclsm` | 327,22 |
| `extensions.Zicntr` | 636,78 |
| `extensions.Zicond` | 193,94 |
| `extensions.Zicsr` | 556,00 |
| `extensions.Zifencei` | 244,00 |
| `extensions.Zimop` | 204,94 |
| `extensions.Zmmul` | 606,00 |
| `extras.Interrupts` | 704,94 |
| `extras.Sscofpmf` | -612,00 |
| `extras.Zihintntl` | 5,94 |
| `extras.Zihintpause` | -206,06 |
| `zihpm.a0` | 54,69 |
| `zihpm.a1` | -81,94 |
| `zihpm.a2` | 4,66 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,35 % |
| Maior erro no ajuste | 1,14 % |
| Maior erro nos perfis de validação | 0,95 % |
| Razão ajuste sobre síntese | 0,8356 |

Resíduos dos perfis de validação (os outros 24 perfis estão em `boards/calibration/cyclone-10-lp.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 14.008 | 13.918,5 | -0,64 |
| `p5_full` | 17.750 | 17.918,9 | 0,95 |
| `p7_ic64` | 10.962 | 10.969,3 | 0,07 |
| `p7_dc64` | 11.748 | 11.716,7 | -0,27 |

## 7. Razão ajuste sobre síntese

O estimador soma os termos da tabela, que são estimativas do `quartus_map`, e multiplica a soma pela razão `map_to_fit_ratio` para chegar à lógica que o ajuste (`quartus_fit`) usa. A razão de cada família é a média de `fit_result.logic` sobre `result.logic` de alguns perfis rodados até o ajuste (`calibrate run --stop-after fit`), e o ajuste empacota a lógica melhor nos perfis maiores, de modo que a razão cresce com o perfil. As duas últimas colunas mostram o erro da soma da tabela vezes a razão contra a lógica do ajuste, que fica abaixo de 10 % em todos os perfis rodados.

| Família | Perfil | Síntese | Ajuste | Ajuste sobre síntese | Tabela vezes razão | Erro (%) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| Cyclone V | `p1_rv32i` | 4.122 | 3.845 | 0,9328 | 3.995 | 3,9 |
| Cyclone V | `p3_zicntr_zifencei` | 4.926 | 4.832 | 0,9809 | 4.775 | -1,2 |
| Cyclone V | `p5_base` | 7.837 | 7.647 | 0,9758 | 7.601 | -0,6 |
| Cyclone V | `p5_full` | 8.199 | 8.100 | 0,9879 | 7.934 | -2,1 |
| Cyclone IV E | `p1_rv32i` | 8.819 | 7.191 | 0,8154 | 7.451 | 3,6 |
| Cyclone IV E | `p3_zicntr_zifencei` | 11.311 | 9.616 | 0,8501 | 9.527 | -0,9 |
| Cyclone IV E | `p5_base` | 17.869 | 15.290 | 0,8557 | 15.120 | -1,1 |
| Cyclone IV E | `p5_full` | 19.193 | 16.474 | 0,8583 | 15.791 | -4,1 |
| MAX 10 | `p1_rv32i` | 10.404 | 8.709 | 0,8371 | 9.156 | 5,1 |
| MAX 10 | `p3_zicntr_zifencei` | 12.726 | 11.055 | 0,8687 | 11.204 | 1,3 |
| MAX 10 | `p5_base` | 18.502 | 16.760 | 0,9058 | 16.293 | -2,8 |
| MAX 10 | `p5_full` | 19.662 | 17.865 | 0,9086 | 17.305 | -3,1 |
| Cyclone 10 LP | `p1_rv32i` | 8.540 | 6.882 | 0,8059 | 7.136 | 3,7 |
| Cyclone 10 LP | `p2_rv32im` | 9.532 | 7.965 | 0,8356 | 7.965 | -0,0 |
| Cyclone 10 LP | `p3_zicntr_zifencei` | 10.959 | 9.281 | 0,8469 | 9.166 | -1,2 |
| Cyclone 10 LP | `p4_hpm_4x40` | 11.903 | 10.164 | 0,8539 | 9.834 | -3,2 |

| Família | Razão usada | Menor | Maior |
| :--- | ---: | ---: | ---: |
| Cyclone V | 0,9693 | 0,9328 | 0,9879 |
| Cyclone IV E | 0,8449 | 0,8154 | 0,8583 |
| MAX 10 | 0,8800 | 0,8371 | 0,9086 |
| Cyclone 10 LP | 0,8356 | 0,8059 | 0,8539 |

O perfil completo da Cyclone V (`p5_full`) dá 8100 ALMs no ajuste, a 5 ALMs do limite da faixa de 8058 a 8095 ALMs que o `core-novo.md` registra para o topo escrito à mão. Na Vidor os perfis do ajuste vão até o `p4_hpm_4x40`, porque os perfis maiores passam dos 15408 LEs do 10CL016.

## 8. Verificação cruzada

A verificação mede 14 perfis em outro dispositivo da mesma família e compara com a tabela, com `riscv-tools calibrate verify`. O topo de cada placa difere do topo da placa de medida (a DE10-Nano e a DE2-115 têm a RAM emulada, a DE0-Nano tem a SDRAM de 16 bits), e por isso a comparação vem em duas colunas. A primeira usa a tabela como está. A segunda desloca o termo do núcleo pela diferença medida no perfil `p1_rv32i`, de modo que a parte do topo que muda sai da conta e sobram os incrementos das extensões e das caches, que são o que a tabela precisa acertar em outro dispositivo.

| Placa | Família | Dispositivo | Deslocamento do núcleo | Maior erro | Maior erro deslocado | Erro médio quadrático deslocado |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| DE10-Nano | Cyclone V | 5CSEBA6 | -628 | 20,39 % | 4,04 % | 3,13 % |
| DE0-Nano | Cyclone IV E | EP4CE22 | 1.449 | 16,69 % | 5,52 % | 2,35 % |

O deslocamento da DE10-Nano (-628 ALMs) é o que o topo da DE0-CV carrega a mais, com o controlador de SDRAM de 16 bits, e o da DE0-Nano (+1449 LEs) é o custo desse controlador na Cyclone IV E, que a DE2-115 não tem. As duas tabelas valem em outro dispositivo da família com erro abaixo de 10 % depois do deslocamento do núcleo, que é o termo que o perfil de cada família refaz.

### DE10-Nano

| Perfil | Medido | Previsto | Erro (%) | Previsto deslocado | Erro deslocado (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 3.494 | 4.122,0 | 17,97 | 3.494,0 | 0,00 |
| `p1_rv32e` | 3.120 | 3.756,0 | 20,39 | 3.128,0 | 0,26 |
| `p2_rv32im` | 3.909 | 4.436,0 | 13,48 | 3.808,0 | -2,58 |
| `p3_zicntr_zifencei` | 4.464 | 4.926,3 | 10,36 | 4.298,3 | -3,71 |
| `p3_zicclsm_zicntr_zifencei` | 4.588 | 5.041,0 | 9,87 | 4.413,0 | -3,81 |
| `p4_hpm_4x40` | 4.790 | 5.253,3 | 9,67 | 4.625,3 | -3,44 |
| `p4_hpm_16x52` | 5.851 | 6.258,1 | 6,96 | 5.630,1 | -3,77 |
| `p5_base` | 7.420 | 7.842,0 | 5,69 | 7.214,0 | -2,78 |
| `p5_full` | 7.643 | 8.185,0 | 7,09 | 7.557,0 | -1,13 |
| `p6_interrupts` | 7.392 | 8.078,6 | 9,29 | 7.450,6 | 0,79 |
| `p7_ic8` | 4.464 | 4.926,2 | 10,35 | 4.298,2 | -3,71 |
| `p7_dc8` | 4.302 | 4.774,6 | 10,98 | 4.146,6 | -3,61 |
| `p7_ic64` | 4.464 | 4.926,5 | 10,36 | 4.298,5 | -3,71 |
| `p7_dc64` | 4.690 | 5.128,6 | 9,35 | 4.500,6 | -4,04 |

### DE0-Nano

| Perfil | Medido | Previsto | Erro (%) | Previsto deslocado | Erro deslocado (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 10.268 | 8.819,0 | -14,11 | 10.268,0 | 0,00 |
| `p1_rv32e` | 8.997 | 7.495,0 | -16,69 | 8.944,0 | -0,59 |
| `p2_rv32im` | 11.249 | 9.761,0 | -13,23 | 11.210,0 | -0,35 |
| `p3_zicntr_zifencei` | 12.623 | 11.275,5 | -10,68 | 12.724,5 | 0,80 |
| `p3_zicclsm_zicntr_zifencei` | 12.873 | 11.399,0 | -11,45 | 12.848,0 | -0,19 |
| `p4_hpm_4x40` | 13.314 | 11.920,5 | -10,47 | 13.369,5 | 0,42 |
| `p4_hpm_16x52` | 15.320 | 14.193,7 | -7,35 | 15.642,7 | 2,11 |
| `p5_base` | 18.422 | 17.895,7 | -2,86 | 19.344,7 | 5,01 |
| `p5_full` | 19.585 | 18.690,2 | -4,57 | 20.139,2 | 2,83 |
| `p6_interrupts` | 19.045 | 18.647,2 | -2,09 | 20.096,2 | 5,52 |
| `p7_ic8` | 12.616 | 11.261,2 | -10,74 | 12.710,2 | 0,75 |
| `p7_dc8` | 12.089 | 10.736,2 | -11,19 | 12.185,2 | 0,80 |
| `p7_ic64` | 12.627 | 11.294,5 | -10,55 | 12.743,5 | 0,92 |
| `p7_dc64` | 13.357 | 11.994,5 | -10,20 | 13.443,5 | 0,65 |

## 9. Portão GMC

O portão pede uma tabela por família com os dados brutos versionados, o erro registrado e o erro máximo de validação menor ou igual a 10 %. Uma família acima de 10 % não habilita o erro de lógica (V12) e fica em aviso (V18).

| Família | Perfis medidos | Erro médio quadrático | Maior erro de validação | Razão ajuste sobre síntese | Erro de lógica habilitado |
| :--- | ---: | ---: | ---: | ---: | :--- |
| Cyclone V | 28 | 0,18 % | 0,27 % | 0,9693 | sim |
| Cyclone IV E | 28 | 0,35 % | 2,62 % | 0,8449 | sim |
| MAX 10 | 28 | 0,14 % | 0,63 % | 0,8800 | sim |
| Cyclone 10 LP | 28 | 0,35 % | 0,95 % | 0,8356 | sim |

## 10. Como refazer

Cada família roda no Tools, sob o `flock` da máquina com o Quartus, e a tabela sai do ajuste dos registros. Os perfis de uma família rodam em sequência, e a Cyclone V roda no notebook ou na PC1, enquanto as outras famílias só rodam na PC1.

```bash
flock /tmp/quartus-<máquina>.lock riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --lock <arquivo-próprio>
riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --stop-after fit --only p1_rv32i,p3_zicntr_zifencei,p5_base,p5_full
riscv-tools --root <Insper-RISC-V> calibrate fit --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --table boards/calibration/max-10.yaml
riscv-tools --root <Insper-RISC-V> calibrate verify --profiles boards/calibration/profiles/verify-de0-nano.yaml --raw boards/calibration/raw/verify-de0-nano --table boards/calibration/cyclone-iv-e.yaml --output boards/calibration/verification/de0-nano.yaml
```

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
