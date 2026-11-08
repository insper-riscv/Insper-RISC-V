# Arduino MKR Vidor 4000

## 1. Referência

O pacote da placa está em `boards/mkr-vidor-4000/`. As fontes de hardware são o esquemático `ABX00022-schematics.pdf`, o datasheet e o `.qsf` oficial do VidorBitstream, todos citados nesta página. O formato do pacote está em [formato.md](formato.md).

| Item | Valor |
| :--- | :--- |
| FPGA | Cyclone 10 LP `10CL016YU256C8G` |
| IDCODE | `020F20DD`, o mesmo do EP3C16, lido do banco de dispositivos do Quartus |
| Memória externa | SDRAM AS4C4M16SA-7BCN de 8 MB e FLASH QSPI W25Q16DV de 2 MB |
| Relógio e reset | `iCLK` (48 MHz, pino E2) e `iRESETn` (pino E1) |

A SDRAM tem 12 bits de endereço (`A0` a `A11`), 4 bancos (`BS0` e `BS1`) e 16 bits de dado, e a FLASH guarda o bitstream da placa, dos quais 1 MB é do usuário.

## 2. Pinos do `.qsf` oficial resolvidos pelo esquemático

O `.qsf` oficial atribuía a dois sinais cada um de sete pinos. A rede que o esquemático liga a cada pino decide, e o sinal que não tem rede nesse pino sai de `pins.yaml` (`conflicts` fica vazio).

| Pino | Rede do esquemático | Sinal mantido | Sinal removido |
| :--- | :--- | :--- | :--- |
| L4 | `PANEL_SDA` | `bHDMI_SDA` | `panel_en` |
| R4 | `WM_PIO35` | `bWM_PIO35` | `bWM_PIO17` (vai a um resistor) |
| T4 | `WM_PIO31` | `bWM_PIO31` | `bWM_PIO16` (vai a um resistor) |
| R5 | `WM_PIO20` | `bWM_PIO20` | `iWM_RTS` |
| R6 | `WM_PIO21` | `bWM_PIO21` | `iWM_CTS` |
| R7 | `CFG_HOLD` | `oFLASH_HOLD` | `bWM_PIO25` |
| T7 | `CFG_WP` | `oFLASH_WP` | `bWM_PIO24` |

Quatro pinos mantêm o nome do `.qsf` com rede de outro nome no esquemático: `bWM_PIO2`, `bWM_PIO3`, `bWM_PIO4` e `bWM_PIO34` estão em R10, P11, R11 e M6, que o esquemático liga a `PEX_PIN1`, `PEX_PIN3`, `PEX_PIN5` e `PEX_PIN7`. O pino é o mesmo e fica `inferred`.

## 3. Cadeia JTAG e cabo

A USB da placa liga só ao SAMD21 (`2341:8056`, porta serial CDC). O JTAG do FPGA fica atrás dele, e há duas vias.

| Via | Cabo | `jtagconfig` |
| :--- | :--- | :--- |
| Emulada | O sketch `USBBlaster` no SAMD21 faz a USB parecer um USB-Blaster | `USB-Blaster [bus-porta]` com `020F20DD` |
| Externa | Um USB-Blaster de 10 pinos no conector `J11` | O mesmo |

### 3.1. Conector J11

`J11` é um Samtec FTSH-105-01-F-D-K de 2x5 pinos com passo de 1,27 mm, e os pads não vêm soldados.

| Pino | Sinal | Pino | Sinal |
| :---: | :--- | :---: | :--- |
| 1 | `+3V3` | 2 | `TMS` |
| 3 | `GND` | 4 | `TCK` |
| 5 | `GND` | 6 | `TDO` |
| 7 | sem ligação | 8 | `TDI` |
| 9 | `GND` | 10 | sem ligação |

As quatro redes `JTAG.CPORT_*` ligam o conector, o SAMD21 (`TMS` em PA14, `TDI` em PA12, `TCK` em PA13 e `TDO` em PA15) e os pinos de JTAG do FPGA (`TMS` em J5, `TCK` em H3, `TDO` em J4 e `TDI` em H4). Com um cabo externo, o SAMD21 fica em modo bootloader (duplo toque no reset) para não disputar as linhas.

## 4. Detecção da placa

O Tools reconhece a placa pela USB do SAMD21 antes de existir cadeia JTAG, porque o `2341:8056` está em `jtag.usb` do pacote.

| Comando | O que mostra |
| :--- | :--- |
| `riscv-tools board scan` | Um bloco `usb 2341:8056 board: mkr-vidor-4000` com o estado "sem cadeia" |
| `riscv-tools board doctor` | O aviso `MKR Vidor 4000` com as instruções do item 5 |

Com o sketch em execução o SAMD21 reaparece como USB-Blaster, o ID `2341:8056` some, e a placa passa a ser identificada pelo IDCODE da cadeia como as demais.

## 5. Instruções do sketch USBBlaster

As ferramentas não gravam o sketch no SAMD21, porque uma gravação errada pode inutilizar a via USB. O usuário carrega o sketch pela IDE do Arduino.

1. Instalar o núcleo `Arduino SAMD Boards` na versão 1.6.25 ou posterior.
2. Escolher a placa `Arduino MKR Vidor 4000` e a porta serial do SAMD21.
3. Abrir o exemplo `USBBlaster` da biblioteca do mesmo nome e carregá-lo.
4. Conferir com `jtagconfig`, que deve listar um `USB-Blaster` com o IDCODE `020F20DD`.
5. Para voltar a usar o SAMD21 como Arduino, carregar outro sketch pela IDE.

O nome exato do exemplo na IDE deve ser conferido na primeira carga. O `.sof` carregado por JTAG é volátil e some ao religar a placa.

## 6. Níveis de suporte

| Nível | Critério | O que vale para a placa |
| :--- | :--- | :--- |
| N0 | `board generate` e `quartus_map` sem erro | O dispositivo é aceito pelo Quartus nas medições do M.0 |
| N1 | Ajuste e análise de tempo | Alvo do pacote |
| N2 | Placa viva | Exige o cabo emulado ou externo funcionando |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
