# Pacote de placa: board.yaml e pins.yaml

## 1. O pacote

Cada placa suportada tem uma pasta `boards/<placa>/` na raiz do repositório, com dois arquivos.

| Arquivo | Conteúdo | Quem lê |
| :--- | :--- | :--- |
| `board.yaml` | O que a placa oferece: dispositivo, relógios, papéis de E/S, memórias, cadeia JTAG, capacidades | Validador de recursos, gerador de PLL e de topo, identificação pelo JTAG |
| `pins.yaml` | Pino, padrão de E/S, direção e selo de certeza de cada sinal | Gerador de pinos |

O `board.yaml` cita sinais só pelo nome. Número de pino e padrão de E/S existem apenas no `pins.yaml`, e a organização e os tempos de um chip de memória existem apenas no catálogo de chips. Nenhum dos dois repete o que o outro guarda.

## 2. Campos do board.yaml

| Campo | Significado |
| :--- | :--- |
| `board`, `name` | Identificador (igual ao nome da pasta) e nome comercial |
| `family` | `cyclone-v`, `cyclone-v-soc`, `cyclone-iv-e`, `max-10` ou `cyclone-10-lp` |
| `device`, `speed_grade` | Dispositivo completo e o grau contido nele (`C7`) |
| `target_level` | Nível de suporte alvo, de `N0` (projeto sintetizado) a `N4` (conformidade ACT4 na placa) |
| `jtag.cable` | `usb-blaster`, `usb-blaster-ii`, `samd21-usbblaster` ou `external` |
| `jtag.cable_name` | Nome que o `jtagconfig` dá ao cabo, sem o sufixo de porta, quando não é o padrão |
| `jtag.usb` | IDs USB (`vid:pid`) usados para reconhecer o cabo antes de haver cadeia |
| `jtag.chain` | Dispositivos da cadeia, em ordem. Cada um tem `name`, `idcode` (8 dígitos hexadecimais), `confirmed` e `fpga: true` (exatamente um) ou `hps: true` |
| `jtag.samd21`, `jtag.external_pads` | Só na `samd21-usbblaster`: o sketch que expõe o cabo emulado e os pads de JTAG para cabo externo |
| `resources` | `logic`, `block_ram`, `multipliers`, `plls`, `user_pins` (`null` quando a capacidade é desconhecida) |
| `clocks.inputs`, `clocks.reference`, `clocks.reset` | Relógios de entrada (`name`, `signal`, `mhz`), o que alimenta o PLL e o reset do usuário com polaridade |
| `io.<papel>` | Papéis `leds`, `switches`, `keys` e `display`, cada um com `signals` e `active` (`high` ou `low`) |
| `memories` | `sdram`, `sram`, `nor`, `onchip_flash` e `serial_flash`, cada um com o chip do catálogo e os sinais |
| `console` | `default: jtag` (JTAG UART) e `uart: {rx, tx}` só quando a placa tem UART em pinos |
| `pins` | Caminho do `pins.yaml` |
| `notes` | Armadilhas da placa, em prosa curta |

O campo `confirmed` da cadeia e dos IDs USB usa os selos do `pins.yaml` e mais `measured`, para o que foi lido de um cabo real.

### 2.1. Referência a sinais

Os campos `signals` dos papéis de E/S, dos relógios e da UART usam nomes do `pins.yaml`.

| Forma | Expande para |
| :--- | :--- |
| `CLOCK_50` | O sinal de mesmo nome |
| `LEDR[9:0]` | `LEDR[9]` a `LEDR[0]` |
| `HEX[5:0][6:0]` | `HEX5[6]` a `HEX0[0]`: o primeiro intervalo é o índice no nome, o segundo é o bit |

Em `memories.<tipo>.signals`, o valor é um prefixo (ou uma lista de prefixos) sem o sublinhado final. `DRAM` casa `DRAM_ADDR[0]`, `DRAM_CLK` e todos os que começam por `DRAM_`; na Vidor, `[oSDRAM, bSDRAM]` casa os sinais `oSDRAM_*` e `bSDRAM_*`.

### 2.2. Unidades de recurso

| Família | Lógica | Multiplicadores |
| :--- | :--- | :--- |
| `cyclone-v`, `cyclone-v-soc` | `alm` | `dsp18x18` (dois por bloco DSP) |
| `cyclone-iv-e`, `max-10`, `cyclone-10-lp` | `le` | `dsp9x9` (elementos de 9 bits) |

Nenhuma unidade se converte em outra por fator fixo.

## 3. Campos do pins.yaml

| Campo | Significado |
| :--- | :--- |
| `board`, `device` | Iguais aos do `board.yaml` |
| `signals[].name` | Nome do sinal; barramento com índice entre colchetes (`LEDR[3]`) |
| `signals[].pin` | Pino do dispositivo, sem prefixo (`M9`) |
| `signals[].io_standard` | Padrão de E/S do Quartus |
| `signals[].direction` | `in`, `out` ou `inout` |
| `signals[].source` | Onde o pino foi lido (tabela do manual, linha do `.qsf`, fonte de terceiro) |
| `signals[].confirmed` | `manual` (lido no manual), `repo` (lido no `.qsf` do repositório) ou `inferred` (fonte de terceiro) |
| `signals[].note` | Polaridade, jumper ou outra ressalva |
| `conflicts` | Pinos atribuídos a mais de um sinal: `{pin, signals, note?}` |
| `notes` | Observações da placa |

Um mesmo pino só pode aparecer em dois sinais se estiver listado em `conflicts`. O Tools recusa construir com um pino `inferred` sem `--accept-inferred-pins`.

## 4. Exemplo

```yaml
board: de0-cv
family: cyclone-v
device: 5CEBA4F23C7
jtag:
  cable: usb-blaster
  chain: [{name: "5CE(BA4|FA4)", idcode: "02B050DD", fpga: true, confirmed: measured}]
clocks:
  inputs: [{name: clock_50, signal: CLOCK_50, mhz: 50}]
  reference: clock_50
  reset: {signal: FPGA_RESET_N, active: low}
io:
  leds: {signals: "LEDR[9:0]", active: high}
memories:
  sdram: {chip: IS42S16320D-7, chips: 1, signals: DRAM, clk_phase_ps: 4000}
```

A tabela das placas e o nível alvo de cada uma estão em [placas.md](placas.md).
