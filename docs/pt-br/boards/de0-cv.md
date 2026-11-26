# DE0-CV

## 1. Referência

O pacote da placa está em `boards/de0-cv/`. O formato está em [formato.md](formato.md), a tabela das placas em [placas.md](placas.md) e a plataforma em [../platform/de0-cv.md](../platform/de0-cv.md). Nome e pino de cada sinal do `pins.yaml` foram conferidos contra as tabelas 3-2 a 3-7 e 3-10 a 3-13 do manual, e cada um carrega a tabela e a página.

## 2. Polaridades

| Sinal | Nível ativo | Manual |
| :--- | :--- | :--- |
| `LEDR[9:0]` | Alto acende o LED | Seção 3.2 |
| `SW[9:0]` | Alto com a chave para cima | Seção 3.2 |
| `KEY[3:0]` e `FPGA_RESET_N` | Baixo quando apertado | Seção 3.2 |
| `HEX[5:0][6:0]` | Baixo acende o segmento | Seção 3.3 |

O manual chama o botão de reset de `RESET_N` (tabela 3-2); o catálogo o chama `FPGA_RESET_N`, no mesmo pino `P22`.

## 3. Pinos de expansão

O papel `gpio` é bidirecional e numera `GPIO_0` de 0 a 35 e `GPIO_1` de 36 a 71. Cada cabeçalho 2x20 tem 36 pinos de E/S, mais 5 V, 3,3 V e dois GND nos pinos 11, 12, 29 e 30.

| Papel | Sinais | Pinos | Manual | Nível |
| :--- | :--- | ---: | :--- | :--- |
| `gpio` | `GPIO_0[35:0]`, `GPIO_1[35:0]` | 72 | 3.5, tabela 3-7 | 3,3 V |
| `clock_extra` | `CLOCK2_50`, `CLOCK3_50`, `CLOCK4_50` | 3 | 3.4, tabela 3-6 | 3,3 V |

Ficam só no `pins.yaml`, sem papel: o PS/2 (`PS2_CLK`, `PS2_DAT`, `PS2_CLK2` e `PS2_DAT2`, seção 3.7, tabela 3-11), o VGA (seção 3.6, tabela 3-10), o cartão SD (seção 3.8, tabela 3-12) e os `SPI_FLASH_*`, que só existem no `.qsf` e coincidem com pinos do `GPIO_0`.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
