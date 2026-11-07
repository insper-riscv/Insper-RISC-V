# DE10-Lite

Esta página descreve a plataforma `de10-lite`, a Terasic DE10-Lite (MAX 10, 10M50DAF484C7G) com o perfil completo da DE0-CV, e o que se mediu nela. O pacote da placa está em `boards/de10-lite/` e a plataforma em `src/max-10/de10-lite/`.

## 1. Perfil e mapa de memória

O dispositivo tem 49.760 LEs e 182 blocos M9K (1.677.312 bits), o bastante para o perfil `rv32im_zicclsm_zicntr_zihpm_zifencei` com os extras da DE0-CV (Zimop, Zicond, Zihintntl, Zihintpause, interrupções e Sscofpmf).

| Região | Base | Tamanho | Realização |
| :--- | :--- | ---: | :--- |
| `BOOT_MEMORY` | `0x00000000` | 4 KiB | M9K, dentro do núcleo |
| `FLASH` | `0x00001000` | 124 KiB | M9K emulada, atrás das caches, com 24 ciclos na primeira palavra da rajada e 4 nas seguintes |
| `RAM` | `0x40000000` | 64 MiB | SDRAM da placa, atrás das caches |

A FLASH tem 124 KiB porque a loja de blocos ocupa a potência de dois que o endereço pede (128 KiB com a `BOOT_MEMORY` na frente). As bancas do atualizador de programa são a A (`0x1000`, 60 KiB) e a B (`0x10000`, 64 KiB). As caches têm 32 kbit cada. O relógio do núcleo é 50 MHz e o do controlador de SDRAM, 100 MHz. A placa não tem FLASH externa, e a FLASH interna (UFM) fica para um backend à parte.

## 2. Papéis de entrada e saída

| Papel | Uso |
| :--- | :--- |
| `leds` | 10 LEDs, obrigatório |
| `switches` | 10 chaves |
| `keys` | 2 botões, e `KEY[0]` é também o reset |
| `display` | 6 dígitos de 7 segmentos |
| Console | JTAG UART, sem pino |

## 3. SDRAM

O chip é o ISSI IS42S16320D-7 (512 Mbit, 32M x 16), o mesmo da DE0-CV, no catálogo `Memory/chips/IS42S16320D-7.yaml`. O manual da placa não nomeia o chip, então a identificação nesta placa é uma hipótese da família IS42S16320. A fase do `DRAM_CLK` é de 7000 ps.

## 4. Configuração da MAX 10

O Quartus só monta o arquivo de programação de uma MAX 10 com memórias de conteúdo inicial (a `BOOT_MEMORY` e a FLASH emulada) no modo de imagem única com a RAM de configuração. A família `max-10` pede esse modo na chave `qsf` do arquivo `boards/families/max-10.yaml`, e o projeto gerado o carrega. O ajuste também recusa `SLEW_RATE` nos pinos 3.3-V LVTTL, o que a chave `slew_rate: false` da família trata.

## 5. Cabimento

| Recurso | Ajuste do Quartus | Capacidade |
| :--- | ---: | ---: |
| Elementos lógicos | 22.751 | 49.760 (46 %) |
| Bits de memória | 1.155.328 | 1.677.312 (69 %) |
| Blocos de RAM estimados | 126 | 182 |
| PLLs | 1 | 4 |
| Pinos | 104 | 360 |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
