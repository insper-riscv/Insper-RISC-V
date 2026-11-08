# DE0-Nano

Esta página descreve a plataforma `de0-nano`, a Terasic DE0-Nano (Cyclone IV E, EP4CE22F17C6) com o perfil reduzido, e o que se mediu nela. O pacote da placa está em `boards/de0-nano/` e a plataforma em `src/cyclone-iv-e/de0-nano/`.

## 1. Perfil e mapa de memória

O dispositivo tem 22.320 LEs e 608 kbit de M9K. O perfil completo da DE0-CV não cabe, então a plataforma liga só o RV32I com as extensões Zicsr e Zifencei, sem contadores, multiplicador nem interrupções. O Zifencei entra porque a boot memory executa `fence.i` a cada reinício, e sem ele o núcleo trata a instrução como ilegal e volta ao reinício para sempre.

| Região | Base | Tamanho | Realização |
| :--- | :--- | ---: | :--- |
| `BOOT_MEMORY` | `0x00000000` | 4 KiB | M9K, dentro do núcleo |
| `FLASH` | `0x00001000` | 28 KiB | M9K emulada, atrás das caches, com 24 ciclos na primeira palavra da rajada e 4 nas seguintes |
| `RAM` | `0x40000000` | 32 MiB | SDRAM da placa, atrás das caches |

A FLASH tem 28 KiB porque a loja de blocos ocupa a potência de dois que o endereço pede (32 KiB com a `BOOT_MEMORY` na frente), e a próxima, de 64 KiB, passaria de 85 % dos blocos. As duas bancas do atualizador de programa são a A (`0x1000`, 12 KiB) e a B (`0x4000`, 16 KiB). As caches de instruções e de dados têm 8 kbit cada. O relógio do núcleo é 50 MHz e o do controlador de SDRAM, 100 MHz.

## 2. O que a placa oferece e o que a plataforma deixa de fora

| Papel | Uso |
| :--- | :--- |
| `leds` | 8 LEDs, obrigatório |
| `switches` e `keys` | Fora da plataforma |
| `display` | A placa não tem |
| Console | JTAG UART, sem pino |
| Reset | `KEY[0]` |

A polaridade do `KEY[0]` (ativo em nível baixo) é inferida da convenção dos botões da Terasic. Conferir no esquemático da placa se o botão tem pull-up e fecha para o terra, antes de contar com o reset.

Os quatro `DIP` e o `KEY[1]` ficam em pinos que o Quartus aceita só como entrada, e a célula de GPIO do SoC é bidirecional (erro 169009 no ajuste). Por isso a plataforma não pede os papéis `switches` e `keys`.

## 3. SDRAM

O chip é o ISSI IS42S16160B-7 (256 Mbit, 16M x 16, 143 MHz, CL3), no catálogo `Memory/chips/IS42S16160B-7.yaml`. Os tempos são os da coluna `-7` do datasheet da ISSI (tRCD e tRP de 20 ns, tRAS de 45 ns, tRC de 67,5 ns, tDPL de 14 ns). O manual da placa não nomeia o chip, e o nome vem de uma porta VHDL de terceiros, de modo que a identificação continua inferida. A organização (13 bits de linha, 9 de coluna, 4 bancos) dá os 32 MiB, e o controlador é o mesmo da DE0-CV com esses valores nos generics.

A fase do `DRAM_CLK` é de 7000 ps (a defasagem de -3 ns da demonstração da Terasic para 100 MHz), e o teste de memória da placa passou com ela.

## 4. Cabimento

O estimador roda no `board generate` e no `check-memory-map` e escreve `capacity.json` no projeto.

| Recurso | Estimado | Ajuste do Quartus | Capacidade |
| :--- | ---: | ---: | ---: |
| Elementos lógicos | 7.465 | 8.992 | 22.320 |
| Blocos de RAM | 35 | 316.096 bits | 66 blocos, 608.256 bits |
| PLLs | 1 | 1 | 4 |
| Pinos | | 49 | 154 |

A estimativa fica 17 % abaixo do ajuste, porque a razão ajuste sobre síntese da tabela da Cyclone IV E está invertida para a unidade de LE. O perfil completo da DE0-CV nesta placa é recusado com o erro V11: precisa de 240 blocos de RAM, e a placa tem 66.

## 5. Tempo

O núcleo anda 8250 ps atrás do relógio de busca, como na DE2-115 e na DE0-CV, porque as memórias de instrução leem no relógio de busca um ciclo à frente do núcleo, e sem a fase o núcleo salta instruções. Com a semente 5 e o núcleo a 50 MHz, a menor folga de setup é de 1,09 ns (85 C, relógio de busca) e a menor de hold, de 0,17 ns, ambas positivas.

## 6. Na placa

O bitstream sai do `program` com a boot memory embutida, e o `board_run.py --stages de0-nano-regression de0-nano-sdram` roda os programas do Tests que o perfil comporta (os de cabeçalho `RV32_EXT` com só Zicsr e Zifencei).

| Etapa | Programas | Resultado |
| :--- | ---: | :--- |
| `de0-nano-regression` | 71 | 71 passam |
| `de0-nano-sdram` | 7 | 7 passam |

Ficam fora a `code-sweep` (17 KiB, mais que o banco A de 12 KiB), a `flash-const` (pede a falha de acesso, que é um extra que a plataforma não liga), a `monitor` e a `hex-id` (pedem uma pessoa), e as três de UART em pinos (a placa não tem UART). O teste de barramento de endereços da `sdram-memtest` para antes do fim da RAM de 32 MiB, e a janela de teste da SDRAM tem 8 MiB, a partir de 8 MiB acima da base.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
