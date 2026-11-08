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
| `boards/calibration/profiles/sdram-cost-max-10.yaml` | Perfis do custo do controlador de SDRAM de 16 bits, na plataforma `src/calibration/de10-lite-emulated` |
| `boards/calibration/verification/<placa>.yaml` | Comparação da tabela da família com esses perfis |
| `boards/calibration/cyclone-v-manual.yaml` e `raw/cyclone-v-manual/` | Medidas do topo da DE0-CV escrito à mão, com o ponto conhecido de 8058 a 8095 ALMs |

## 2. Plataforma de calibração

Cada família é medida na sua placa de referência com a mesma plataforma de calibração, que troca a cada medida o perfil, os extras, as caches e os generics do Zihpm. A plataforma tem a BOOT_MEMORY de 4 KiB, a FLASH emulada (28 KiB, ou 12 KiB na Vidor) com carregador e JTAG, o console pela JTAG UART, o display e o controlador de FLASH. Esses blocos existem em todos os perfis e ficam dentro do termo do núcleo, de modo que os termos de cada periférico valem zero (`absorbed` na tabela). Alguns coeficientes de extensões pequenas saem negativos (por exemplo `extensions.Zimop` na Cyclone IV E e `extras.Sscofpmf` na Cyclone 10 LP), porque a síntese reorganiza a lógica quando a extensão liga e o perfil com ela sai menor que a base. O coeficiente guarda a diferença medida, e o estimador a soma com o sinal que ela tem. A RAM é o que muda de uma placa para outra, e na Vidor as memórias ficam dentro dos 504 kbit do 10CL016, porque acima disso a síntese converte a RAM em lógica e o custo das caches de 64 e 128 kbit deixa de ser o da cache.

| Família | Placa de medida | Dispositivo | Unidade | RAM da plataforma |
| :--- | :--- | :--- | :--- | :--- |
| Cyclone V | DE0-CV | 5CEBA4 | ALM | SDRAM de 16 bits, com o controlador dentro do termo do núcleo |
| Cyclone IV E | DE2-115 | EP4CE115 | LE | emulada em blocos de 64 KiB, para o topo ser o mesmo da DE0-Nano e da Vidor |
| MAX 10 | DE10-Lite | 10M50DA | LE | SDRAM de 16 bits, com o controlador dentro do termo do núcleo |
| Cyclone 10 LP | MKR Vidor 4000 | 10CL016 | LE | emulada em blocos de 8 KiB, porque o controlador de SDRAM do Memory tem endereço de linha de 13 bits e a SDRAM da placa tem 12 |

Os termos `backends.sdram_32`, `backends.nor` e `backends.sram` não têm medida e ficam `null`, o que faz o estimador emitir V18 quando um perfil os pede. O termo `backends.sdram_16` vale zero nas famílias cuja plataforma tem a SDRAM e vale 1185,3 LEs na Cyclone IV E, a média da diferença medida na 10M50DA entre a plataforma com a SDRAM e a emulada (`raw/sdram-cost-max-10`, de 598 a 1660 LEs conforme o perfil), porque o `sdram_dbg_master` do Memory não aceita o chip da DE0-Nano. Cada cache tem o termo $c_0 = -32\,c_1$, porque o tamanho de 32 kbit já está no núcleo.

Cada plataforma de calibração fica em `src/calibration/<placa>/` com o pacote do mapa de memória gerado, e o campo `top` dela cita o componente `cal_<placa>_board` do `paths.yaml`, cujo fecho de `requires` é a lista de fontes do projeto que o `board generate` escreve.

O Quartus é o 25.1std.0 Build 1129 Lite Edition, a semente é 5 e o núcleo é o commit `451f5fcceb4bd2aef6cf4f9046a59d30961d40a0` do Core. A cache de dados de 128 kbit (`p7_dc128`) é medida e fica fora do ajuste e dos erros (`outside`), porque a síntese a converte em registradores e o custo deixa de ser linear: as tabelas valem até 64 kbit de cache de dados.

## 3. Cyclone V (DE0-CV, 5CEBA4)

| Coeficiente | ALMs |
| :--- | ---: |
| `cache.dcache.c0` | -351,46 |
| `cache.dcache.c1` | 10,98 |
| `cache.icache.c0` | -4,10 |
| `cache.icache.c1` | 0,13 |
| `core.rv32e` | 3.965,00 |
| `core.rv32i` | 4.343,00 |
| `extensions.M` | 148,00 |
| `extensions.Zicclsm` | 84,41 |
| `extensions.Zicntr` | 304,60 |
| `extensions.Zicond` | 5,00 |
| `extensions.Zicsr` | 166,00 |
| `extensions.Zifencei` | 137,00 |
| `extensions.Zimop` | 87,00 |
| `extensions.Zmmul` | 166,00 |
| `extras.Interrupts` | 104,00 |
| `extras.Sscofpmf` | 236,00 |
| `extras.Zihintntl` | 1,00 |
| `extras.Zihintpause` | -1,00 |
| `zihpm.a0` | -11,76 |
| `zihpm.a1` | -10,58 |
| `zihpm.a2` | 1,70 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,18 % |
| Maior erro no ajuste | 0,73 % |
| Maior erro nos perfis de validação | 0,97 % |
| Razão ajuste sobre síntese | 0,9642 |

Resíduos dos perfis de validação (os outros perfis estão em `boards/calibration/cyclone-v.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 6.597 | 6.579,9 | -0,26 |
| `p5_full` | 8.532 | 8.612,2 | 0,94 |
| `p7_ic64` | 5.273 | 5.268,7 | -0,08 |
| `p7_dc64` | 5.671 | 5.616,1 | -0,97 |

## 4. Cyclone IV E (DE2-115, EP4CE115)

| Coeficiente | LEs |
| :--- | ---: |
| `backends.sdram_16` | 1.185,30 |
| `cache.dcache.c0` | -860,00 |
| `cache.dcache.c1` | 26,88 |
| `cache.icache.c0` | -5,34 |
| `cache.icache.c1` | 0,17 |
| `core.rv32e` | 8.401,00 |
| `core.rv32i` | 9.726,00 |
| `extensions.M` | 386,00 |
| `extensions.Zicclsm` | 306,00 |
| `extensions.Zicntr` | 711,00 |
| `extensions.Zicond` | -80,25 |
| `extensions.Zicsr` | 610,00 |
| `extensions.Zifencei` | 199,00 |
| `extensions.Zimop` | -66,25 |
| `extensions.Zmmul` | 434,00 |
| `extras.Interrupts` | 352,75 |
| `extras.Sscofpmf` | 601,00 |
| `extras.Zihintntl` | -60,26 |
| `extras.Zihintpause` | -94,25 |
| `zihpm.a0` | -29,18 |
| `zihpm.a1` | -57,06 |
| `zihpm.a2` | 4,50 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,38 % |
| Maior erro no ajuste | 1,10 % |
| Maior erro nos perfis de validação | 3,39 % |
| Razão ajuste sobre síntese | 0,8418 |

Resíduos dos perfis de validação (os outros perfis estão em `boards/calibration/cyclone-iv-e.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 15.192 | 15.170,6 | -0,14 |
| `p5_full` | 20.015 | 19.685,5 | -1,65 |
| `p7_ic64` | 12.094 | 12.071,3 | -0,19 |
| `p7_dc64` | 13.379 | 12.926,0 | -3,39 |

## 5. MAX 10 (DE10-Lite, 10M50DA)

| Coeficiente | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -884,22 |
| `cache.dcache.c1` | 27,63 |
| `cache.icache.c0` | -14,02 |
| `cache.icache.c1` | 0,44 |
| `core.rv32e` | 9.929,00 |
| `core.rv32i` | 11.194,00 |
| `extensions.M` | 383,00 |
| `extensions.Zicclsm` | 415,83 |
| `extensions.Zicntr` | 674,17 |
| `extensions.Zicond` | 34,76 |
| `extensions.Zicsr` | 573,00 |
| `extensions.Zifencei` | -87,00 |
| `extensions.Zimop` | -11,24 |
| `extensions.Zmmul` | 639,00 |
| `extras.Interrupts` | 498,76 |
| `extras.Sscofpmf` | 414,00 |
| `extras.Zihintntl` | -14,24 |
| `extras.Zihintpause` | -32,24 |
| `zihpm.a0` | 62,33 |
| `zihpm.a1` | -30,06 |
| `zihpm.a2` | 3,37 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,31 % |
| Maior erro no ajuste | 0,96 % |
| Maior erro nos perfis de validação | 2,80 % |
| Razão ajuste sobre síntese | 0,8797 |

Resíduos dos perfis de validação (os outros perfis estão em `boards/calibration/max-10.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 16.213 | 16.175,5 | -0,23 |
| `p5_full` | 20.262 | 20.123,4 | -0,68 |
| `p7_ic64` | 13.422 | 13.390,2 | -0,24 |
| `p7_dc64` | 14.671 | 14.260,4 | -2,80 |

## 6. Cyclone 10 LP (MKR Vidor 4000, 10CL016)

| Coeficiente | LEs |
| :--- | ---: |
| `cache.dcache.c0` | -820,26 |
| `cache.dcache.c1` | 25,63 |
| `cache.icache.c0` | -5,54 |
| `cache.icache.c1` | 0,17 |
| `core.rv32e` | 8.032,00 |
| `core.rv32i` | 9.296,00 |
| `extensions.M` | 375,00 |
| `extensions.Zicclsm` | 256,81 |
| `extensions.Zicntr` | 736,19 |
| `extensions.Zicond` | -25,52 |
| `extensions.Zicsr` | 478,00 |
| `extensions.Zifencei` | 185,00 |
| `extensions.Zimop` | -58,52 |
| `extensions.Zmmul` | 635,00 |
| `extras.Interrupts` | -833,52 |
| `extras.Sscofpmf` | 535,00 |
| `extras.Zihintntl` | -66,52 |
| `extras.Zihintpause` | -13,52 |
| `zihpm.a0` | 67,76 |
| `zihpm.a1` | -49,81 |
| `zihpm.a2` | 4,25 |

| Medida | Valor |
| :--- | ---: |
| Erro médio quadrático no ajuste | 0,20 % |
| Maior erro no ajuste | 0,81 % |
| Maior erro nos perfis de validação | 3,76 % |
| Razão ajuste sobre síntese | 0,8390 |

Resíduos dos perfis de validação (os outros perfis estão em `boards/calibration/cyclone-10-lp.yaml`):

| Perfil | Medido | Previsto | Erro (%) |
| :--- | ---: | ---: | ---: |
| `p4_hpm_16x52` | 14.857 | 14.771,3 | -0,58 |
| `p5_full` | 18.220 | 18.016,2 | -1,12 |
| `p7_ic64` | 11.714 | 11.710,7 | -0,03 |
| `p7_dc64` | 13.015 | 12.525,4 | -3,76 |

## 7. Razão ajuste sobre síntese

O estimador soma os termos da tabela, que são estimativas do `quartus_map`, e multiplica a soma pela razão `map_to_fit_ratio` para chegar à lógica que o ajuste (`quartus_fit`) usa. A razão de cada família é a média de `fit_result.logic` sobre `result.logic` de alguns perfis rodados até o ajuste (`calibrate run --stop-after fit`), e o ajuste empacota a lógica melhor nos perfis maiores, de modo que a razão cresce com o perfil. As duas últimas colunas mostram o erro da soma da tabela vezes a razão contra a lógica do ajuste, que fica abaixo de 10 % em todos os perfis rodados.

| Família | Perfil | Síntese | Ajuste | Ajuste sobre síntese | Tabela vezes razão | Erro (%) |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| Cyclone V | `p1_rv32i` | 4.343 | 4.087 | 0,9411 | 4.188 | 2,5 |
| Cyclone V | `p3_zicntr_zifencei` | 5.269 | 5.072 | 0,9626 | 5.076 | 0,1 |
| Cyclone V | `p5_base` | 8.177 | 7.944 | 0,9715 | 7.887 | -0,7 |
| Cyclone V | `p5_full` | 8.532 | 8.373 | 0,9814 | 8.304 | -0,8 |
| Cyclone IV E | `p1_rv32i` | 9.726 | 7.958 | 0,8182 | 8.187 | 2,9 |
| Cyclone IV E | `p3_zicntr_zifencei` | 12.076 | 10.255 | 0,8492 | 10.157 | -1,0 |
| Cyclone IV E | `p5_base` | 19.006 | 16.059 | 0,8449 | 16.022 | -0,2 |
| Cyclone IV E | `p5_full` | 20.015 | 17.111 | 0,8549 | 16.571 | -3,2 |
| MAX 10 | `p1_rv32i` | 11.194 | 9.400 | 0,8397 | 9.847 | 4,8 |
| MAX 10 | `p3_zicntr_zifencei` | 13.352 | 11.587 | 0,8678 | 11.767 | 1,6 |
| MAX 10 | `p5_base` | 19.201 | 17.377 | 0,9050 | 16.920 | -2,6 |
| MAX 10 | `p5_full` | 20.262 | 18.365 | 0,9064 | 17.703 | -3,6 |
| Cyclone 10 LP | `p1_rv32i` | 9.296 | 7.599 | 0,8174 | 7.799 | 2,6 |
| Cyclone 10 LP | `p2_rv32im` | 10.306 | 8.638 | 0,8382 | 8.647 | 0,1 |
| Cyclone 10 LP | `p3_zicntr_zifencei` | 11.709 | 9.855 | 0,8417 | 9.821 | -0,3 |
| Cyclone 10 LP | `p4_hpm_4x40` | 12.562 | 10.786 | 0,8586 | 10.497 | -2,7 |

| Família | Razão usada | Menor | Maior |
| :--- | ---: | ---: | ---: |
| Cyclone V | 0,9642 | 0,9411 | 0,9814 |
| Cyclone IV E | 0,8418 | 0,8182 | 0,8549 |
| MAX 10 | 0,8797 | 0,8397 | 0,9064 |
| Cyclone 10 LP | 0,8390 | 0,8174 | 0,8586 |

Na Vidor os perfis do ajuste vão até o `p4_hpm_4x40`, porque os perfis maiores passam dos 15408 LEs do 10CL016.

## 8. Verificação cruzada

A verificação mede 14 perfis (12 na DE0-Nano, sem as caches de 64 kbit, que não cabem nos blocos dela) em outro dispositivo da mesma família e compara com a tabela, com `riscv-tools calibrate verify`. O topo de cada placa difere do topo da placa de medida (a DE10-Nano tem a RAM emulada e a DE0-Nano tem memórias menores), e por isso a comparação vem em duas colunas. A primeira usa a tabela como está. A segunda desloca o termo do núcleo pela diferença medida no perfil `p1_rv32i`, de modo que a parte do topo que muda sai da conta e sobram os incrementos das extensões e das caches, que são o que a tabela precisa acertar em outro dispositivo.

| Placa | Família | Dispositivo | Deslocamento do núcleo | Maior erro | Maior erro deslocado | Erro médio quadrático deslocado |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| DE10-Nano | Cyclone V | 5CSEBA6 | -633 | 18,64 % | 4,63 % | 3,20 % |
| DE0-Nano | Cyclone IV E | EP4CE22 | -436 | 4,50 % | 2,02 % | 1,11 % |

O deslocamento da DE10-Nano (-633 ALMs) é o que o topo da DE0-CV carrega a mais, com o controlador de SDRAM de 16 bits, e o da DE0-Nano (-436 LEs) vem das memórias menores da plataforma dela (FLASH de 12 KiB e RAM de 8 KiB, que cabem nos 66 blocos da EP4CE22). As duas tabelas valem em outro dispositivo da família com erro abaixo de 10 % depois do deslocamento do núcleo.

### DE10-Nano

| Perfil | Medido | Previsto | Erro (%) | Previsto deslocado | Erro deslocado (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 3.710 | 4.343,0 | 17,06 | 3.710,0 | 0,00 |
| `p1_rv32e` | 3.342 | 3.965,0 | 18,64 | 3.332,0 | -0,30 |
| `p2_rv32im` | 4.137 | 4.657,0 | 12,57 | 4.024,0 | -2,73 |
| `p3_zicntr_zifencei` | 4.806 | 5.264,6 | 9,54 | 4.631,6 | -3,63 |
| `p3_zicclsm_zicntr_zifencei` | 4.921 | 5.349,0 | 8,70 | 4.716,0 | -4,17 |
| `p4_hpm_4x40` | 5.144 | 5.566,5 | 8,21 | 4.933,5 | -4,09 |
| `p4_hpm_16x52` | 6.162 | 6.579,9 | 6,78 | 5.946,9 | -3,49 |
| `p5_base` | 7.735 | 8.180,2 | 5,75 | 7.547,2 | -2,43 |
| `p5_full` | 8.045 | 8.612,2 | 7,05 | 7.979,2 | -0,82 |
| `p6_interrupts` | 7.786 | 8.284,2 | 6,40 | 7.651,2 | -1,73 |
| `p7_ic8` | 4.798 | 5.261,5 | 9,66 | 4.628,5 | -3,53 |
| `p7_dc8` | 4.506 | 5.001,0 | 10,98 | 4.368,0 | -3,06 |
| `p7_ic64` | 4.812 | 5.268,7 | 9,49 | 4.635,7 | -3,66 |
| `p7_dc64` | 5.225 | 5.616,1 | 7,48 | 4.983,1 | -4,63 |

### DE0-Nano

| Perfil | Medido | Previsto | Erro (%) | Previsto deslocado | Erro deslocado (%) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `p1_rv32i` | 9.290 | 9.726,0 | 4,69 | 9.290,0 | 0,00 |
| `p1_rv32e` | 8.039 | 8.401,0 | 4,50 | 7.965,0 | -0,92 |
| `p2_rv32im` | 10.318 | 10.546,0 | 2,21 | 10.110,0 | -2,02 |
| `p3_zicntr_zifencei` | 11.723 | 12.066,0 | 2,93 | 11.630,0 | -0,79 |
| `p3_zicclsm_zicntr_zifencei` | 11.992 | 12.372,0 | 3,17 | 11.936,0 | -0,47 |
| `p4_hpm_4x40` | 12.544 | 12.834,0 | 2,31 | 12.398,0 | -1,16 |
| `p4_hpm_16x52` | 14.852 | 15.170,6 | 2,15 | 14.734,6 | -0,79 |
| `p5_base` | 18.613 | 19.032,8 | 2,25 | 18.596,8 | -0,09 |
| `p5_full` | 19.615 | 19.685,5 | 0,36 | 19.249,5 | -1,86 |
| `p6_interrupts` | 18.792 | 19.385,5 | 3,16 | 18.949,5 | 0,84 |
| `p7_ic8` | 11.712 | 12.062,0 | 2,99 | 11.626,0 | -0,73 |
| `p7_dc8` | 11.096 | 11.421,0 | 2,93 | 10.985,0 | -1,00 |

## 9. Como refazer

Cada família roda no Tools, sob o `flock` da máquina com o Quartus, e a tabela sai do ajuste dos registros. Os perfis de uma família rodam em sequência, e a Cyclone V roda no notebook ou na PC1, enquanto as outras famílias só rodam na PC1.

```bash
flock /tmp/quartus-<máquina>.lock riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --lock <arquivo-próprio>
riscv-tools --root <Insper-RISC-V> calibrate run --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --stop-after fit --only p1_rv32i,p3_zicntr_zifencei,p5_base,p5_full
riscv-tools --root <Insper-RISC-V> calibrate fit --profiles boards/calibration/profiles/max-10.yaml --raw boards/calibration/raw/max-10 --table boards/calibration/max-10.yaml
riscv-tools --root <Insper-RISC-V> calibrate verify --profiles boards/calibration/profiles/verify-de0-nano.yaml --raw boards/calibration/raw/verify-de0-nano --table boards/calibration/cyclone-iv-e.yaml --output boards/calibration/verification/de0-nano.yaml
```

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
