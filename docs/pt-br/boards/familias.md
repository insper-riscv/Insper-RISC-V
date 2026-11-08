# Famílias de dispositivos

## 1. Finalidade

O arquivo `boards/families/<família>.yaml` guarda o que vale para todo dispositivo de uma família, para que o `board.yaml` de cada placa cite só a família e o dispositivo. O Tools lê os arquivos com o módulo `board_schema` e os confere com o comando `check-boards`.

## 2. Campos

| Campo | Significado |
| :--- | :--- |
| `family` | Identificador, igual ao nome do arquivo |
| `quartus_family` | Nome da família no Quartus |
| `logic_unit` | `alm` ou `le` |
| `pll` | `ip` (`altera_pll` ou `altpll`), `vco_mhz` (menor e maior frequência do oscilador), `clock_node_pattern` (nome dos nós internos do PLL) e `outputs_max` |
| `block_ram` | Tipo e bits de um bloco de memória |
| `memory_ip` | IP que infere as memórias |
| `virtual_jtag` | Se a família tem o nó de Virtual JTAG |
| `onchip_flash` | IP da FLASH interna, ou `null` |
| `fmax.core_mhz_by_grade` | Frequência de núcleo medida por grau, `null` sem medida |
| `calibration` | Arquivo de calibração do estimador, relativo a `boards/`, ou `null` |
| `slew_rate` | Se o ajuste aceita `SLEW_RATE` nos pinos 3.3-V LVTTL; ausente vale `true`, e a `cyclone-iv-e`, a `max-10` e a `cyclone-10-lp` o recusam (`false`) |
| `qsf` | Linhas que o `.qsf` de todo projeto da família recebe, ou ausente; a `max-10` pede o modo de configuração das memórias com conteúdo inicial |

## 3. Famílias

| Família | Lógica | PLL | Bloco de RAM | FLASH interna |
| :--- | :--- | :--- | :--- | :--- |
| `cyclone-v` | ALM | `altera_pll`, 18 saídas | M10K de 10240 bits | não |
| `cyclone-v-soc` | ALM | `altera_pll`, 18 saídas | M10K de 10240 bits | não |
| `cyclone-iv-e` | LE | `altpll`, 5 saídas | M9K de 9216 bits | não |
| `max-10` | LE | `altpll`, 5 saídas | M9K de 9216 bits | `altera_onchip_flash` |
| `cyclone-10-lp` | LE | `altpll`, 5 saídas | M9K de 9216 bits | não |

O único Fmax medido é o da `cyclone-v` no grau `C7`. Cada família tem a tabela de calibração em `calibration/<família>.yaml`, descrita em [calibracao.md](calibracao.md), e o validador avisa quando ela falta (regra V18).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
