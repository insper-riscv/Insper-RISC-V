# Resultados da DE2-115

Este relatório registra o que as duas plataformas da DE2-115 fizeram na placa, com o Quartus 25.1 Lite e a placa da PC1 do laboratório. A descrição das plataformas está em [de2-115.md](de2-115.md).

## 1. Síntese

| Plataforma | Elementos lógicos | Bits de memória | Folga de setup |
| :--- | ---: | ---: | :--- |
| `de2-115-n2` | 18.961 de 114.480 | 3.254.528 de 3.981.312 | positiva em todos os domínios, mínima de 0,084 ns |
| `de2-115` | 20.111 de 114.480 | 108.800 de 3.981.312 | positiva em todos os domínios, mínima de 0,172 ns |

O núcleo roda a 50 MHz com a fase de 8250 ps contra o relógio de busca. Com a fase em zero, o núcleo salta instruções, porque as memórias de instrução leem no relógio de busca um ciclo à frente do núcleo.

## 2. Nível N2 (`de2-115-n2`)

| Programa | Resultado |
| :--- | :--- |
| `hello`, `display`, `code-sweep`, `conformance-fencei` | passam |
| `clint-mtip` | falha com o código 2: a escrita no `msip` não acende o bit MSIP do `mip` |
| programas da janela de 16 MB da SDRAM | fora do nível, a RAM emulada tem 128 KiB |

## 3. SDRAM de 32 bits e fase do `DRAM_CLK`

O teste usa a porta de depuração: preenche as duas metades de $2^{24}$ palavras com valores diferentes, confere palavras nas pontas e no meio de cada metade, e escreve e lê de volta 32 endereços (24 sorteados e os dois extremos de cada banco). O bit 24 do endereço viaja no bit 3 do código da operação.

| Fase do `DRAM_CLK` (ps, a 100 MHz) | Resultado |
| ---: | :--- |
| 0 | passa |
| 2000 | falha |
| 4000 | passa |
| 6000 | passa |
| 8000 | passa |

O valor do `board.yaml` é 6000 ps, no meio da janela que passa. Os endereços `tohost` e `fromhost` mudam sozinhos porque o núcleo os escreve, e o teste não os conta.

## 4. FLASH NOR e nível N4 (`de2-115`)

Cada programa é gravado na banca A da NOR por um programa que o hospedeiro deixa na SDRAM, e o BOOT_MEMORY o inicia pela entrada de RAM (magia `RAMB` e entrada nos 8 últimos bytes da RAM). O chip tem oito setores de boot de 8 KiB nos primeiros 64 KiB, e o controlador apaga com essa granularidade.

| Programa | Resultado |
| :--- | :--- |
| `cache-sweep`, `code-sweep`, `conformance-fencei`, `cpi-kernels`, `display`, `hello` | passam |
| `misaligned-cache-lines`, `misaligned-crossing`, `sdram-bytes`, `sdram-copy`, `sdram-exec-copy` | passam |
| `sdram-loop`, `sdram-memtest`, `sdram-muldiv`, `sdram-refresh`, `selfmod-repeat` | passam |
| `clint-mtip` | falha com o código 2, como no N2 |
| `flash-const` | falha com o código 6: a leitura da palavra da FLASH depois de um store a ela não devolve o valor de antes |

São 16 dos 18 programas compilados para a placa. `monitor` e `hex-id` pedem uma pessoa e não entram.

## 5. Limitações

| Item | Limitação |
| :--- | :--- |
| RAM do mapa | 64 MiB dos 128 MB, porque a tag das caches guarda os bits de endereço até o 25 |
| FLASH do mapa | 1024 KiB do chip, a janela do roteador de regiões |
| Invalidação das caches | o pulso de invalidação do controlador cobre um setor de 8 KiB, mesmo quando o chip apaga um setor de 64 KiB |
| Atualização de programa | as bancas A e B pelo firmware (`c-sdram-update`) não rodaram nesta placa, porque o `uart_input.txt` dos testes é a imagem da banca B da DE0-CV |
| ACT4 | os ELFs do perfil completo não rodaram nesta placa |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
