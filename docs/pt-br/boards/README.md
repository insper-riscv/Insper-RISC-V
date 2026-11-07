# Placas

As placas são dados: um pacote por placa, uma família por dispositivo e um catálogo de chips, e o Tools gera tudo o que depende delas. Para acrescentar uma placa, siga [../guide/adicionar-placa.md](../guide/adicionar-placa.md).

## 1. Referência

| Documento | Conteúdo |
| :--- | :--- |
| [arquitetura.md](arquitetura.md) | Camadas, regiões e backends, contratos K1 a K9, matriz região, backend e placa, orçamento de RAM |
| [formato.md](formato.md) | Campos do `board.yaml` e do `pins.yaml` |
| [familias.md](familias.md) | Campos e valores das famílias de dispositivos |
| [plataforma-e-placa.md](plataforma-e-placa.md) | Campos do `platform.yaml` que ligam a placa, catálogo de chips e regras V1 a V19 |
| [geracao.md](geracao.md) | O que o Tools gera, o topo gerado, o PLL e o `.sdc`, compilar e programar |
| [identificacao-jtag.md](identificacao-jtag.md) | Como o Tools acha, escolhe e trava a placa |
| [cabimento.md](cabimento.md) | Estimador, política de cabimento e confirmação pelo ajuste |
| [calibracao.md](calibracao.md) | Tabelas de calibração medidas de cada família |
| [equivalencia-de0-cv.md](equivalencia-de0-cv.md) | Equivalência da DE0-CV gerada com a escrita à mão |

## 2. Placas

[placas.md](placas.md) tem a tabela das placas. Cada placa tem uma página própria.

| Página | Placa |
| :--- | :--- |
| [de2-115.md](de2-115.md) | Terasic DE2-115 |
| [de0-nano.md](de0-nano.md) | Terasic DE0-Nano |
| [de10-lite.md](de10-lite.md) | Terasic DE10-Lite |
| [de10-nano.md](de10-nano.md) | Terasic DE10-Nano e DE0-Nano-SoC |
| [mkr-vidor-4000.md](mkr-vidor-4000.md) | Arduino MKR Vidor 4000 |

A DE0-CV tem a página [../platform/de0-cv.md](../platform/de0-cv.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
