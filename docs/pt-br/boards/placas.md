# Placas suportadas

## 1. Tabela

Cada placa tem o pacote em `boards/<placa>/` e uma ficha de pesquisa em `Plans/Multi-FPGA/placas/<placa>.md` do repositório Capstone, com a fonte e o selo de cada fato. O formato do pacote está em [formato.md](formato.md), e o passo a passo para uma placa nova em [../guide/adicionar-placa.md](../guide/adicionar-placa.md).

| Placa | Dispositivo | Família | IDCODE | Cabo | Memória externa ao FPGA | Nível alvo |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `de0-cv` | 5CEBA4F23C7 | `cyclone-v` | `02B050DD` | USB-Blaster | SDRAM 64 MB, 16 bits | N4 |
| `de2-115` | EP4CE115F29C7 | `cyclone-iv-e` | `020F70DD` | USB-Blaster | SDRAM 128 MB (2 x 16 bits), SRAM 2 MB, FLASH NOR 8 MB | N4 |
| `de0-nano` | EP4CE22F17C6 | `cyclone-iv-e` | `020F30DD` | USB-Blaster | SDRAM 32 MB, EPCS64 | N3 |
| `de10-lite` | 10M50DAF484C7G | `max-10` | `031050DD` | USB-Blaster | SDRAM 64 MB, FLASH interna (UFM) | N3 |
| `de10-nano` | 5CSEBA6U23I7 | `cyclone-v-soc` | `4BA00477` (HPS) e `02D020DD` | USB-Blaster II | nenhuma no fabric (DDR3 é do HPS) | N2 |
| `de0-nano-soc` | 5CSEMA4U23C6 | `cyclone-v-soc` | `4BA00477` (HPS) e `02D010DD` | USB-Blaster II | nenhuma no fabric (DDR3 é do HPS) | N1 |
| `mkr-vidor-4000` | 10CL016YU256C8G | `cyclone-10-lp` | `020F20DD` | SAMD21 com sketch USBBlaster | SDRAM 8 MB, QSPI 2 MB | N1 |

## 2. Diferenças de tratamento

| Placa | O que muda |
| :--- | :--- |
| `de2-115` | O IDCODE é compartilhado com o 10CL120 e o EP3C120; KEY, SW e parte dos HEX seguem o jumper JP7 (fábrica 2,5 V), e a única UART em pinos da lista (RS-232) está em `console.uart` |
| `de0-nano`, `de10-lite` | Sem UART nem reset dedicado; o reset é `KEY[0]` |
| `de10-nano` | A cadeia tem dois dispositivos (HPS e FPGA); o cabo é identificado pelo nome `DE-SoC` e pelos IDs USB `09fb:6010` e `09fb:6810` |
| `de0-nano-soc` | Mesma cadeia e mesmo cabo da `de10-nano`, distinguida pelo IDCODE do FPGA; ver [de10-nano.md](de10-nano.md) |
| `mkr-vidor-4000` | A USB liga só ao SAMD21 (`2341:8056`); o cabo emulado exige o sketch `USBBlaster` no SAMD21, e os pads de JTAG para cabo externo (`J11`) não vêm soldados. Os sete pinos duplicados do `.qsf` oficial foram resolvidos pelo esquemático; ver [mkr-vidor-4000.md](mkr-vidor-4000.md) |

## 3. Console

Todas as placas declaram `console.default: jtag`: o console é a JTAG UART pelo cabo de programação. A UART em pinos existe só na `de2-115`.
