# Boards

Boards are data: one package per board, one family per device and a chip catalog, and the Tools generates everything that depends on them. To add a board, follow [../guide/adicionar-placa.md](../guide/adicionar-placa.md).

## 1. Reference

| Document | Content |
| :--- | :--- |
| [arquitetura.md](arquitetura.md) | Layers, regions and backends, contracts K1 to K9, region, backend and board matrix, RAM budget |
| [formato.md](formato.md) | Fields of the `board.yaml` and the `pins.yaml` |
| [familias.md](familias.md) | Fields and values of the device families |
| [plataforma-e-placa.md](plataforma-e-placa.md) | `platform.yaml` fields that link the board, chip catalog and rules V1 to V19 |
| [geracao.md](geracao.md) | What the Tools generates, the generated top, the PLL and the `.sdc`, compile and program |
| [identificacao-jtag.md](identificacao-jtag.md) | How the Tools finds, chooses and locks the board |
| [cabimento.md](cabimento.md) | Estimator, fit policy and confirmation by the fit |
| [calibracao.md](calibracao.md) | Measured calibration tables of each family |
| [equivalencia-de0-cv.md](equivalencia-de0-cv.md) | Equivalence of the generated DE0-CV with the hand-written one |

## 2. Boards

[placas.md](placas.md) has the table of the boards. Each board has its own page.

| Page | Board |
| :--- | :--- |
| [de2-115.md](de2-115.md) | Terasic DE2-115 |
| [de0-nano.md](de0-nano.md) | Terasic DE0-Nano |
| [de10-lite.md](de10-lite.md) | Terasic DE10-Lite |
| [de10-nano.md](de10-nano.md) | Terasic DE10-Nano and DE0-Nano-SoC |
| [mkr-vidor-4000.md](mkr-vidor-4000.md) | Arduino MKR Vidor 4000 |

The DE0-CV has the page [../platform/de0-cv.md](../platform/de0-cv.md).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
