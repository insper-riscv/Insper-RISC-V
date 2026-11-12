# Pacote de placa: board.yaml e pins.yaml

## 1. O pacote

Cada placa suportada tem uma pasta `boards/<placa>/` na raiz do repositório, com dois arquivos.

| Arquivo | Conteúdo | Quem lê |
| :--- | :--- | :--- |
| `board.yaml` | O que a placa oferece: dispositivo, relógios, papéis de E/S, memórias, cadeia JTAG, capacidades | Validador de recursos, gerador de PLL e de topo, identificação pelo JTAG |
| `pins.yaml` | Pino, padrão de E/S, direção e selo de certeza de cada sinal | Gerador de pinos |

O `board.yaml` cita sinais só pelo nome. Número de pino e padrão de E/S existem apenas no `pins.yaml`, e a organização e os tempos de um chip de memória existem apenas no catálogo de chips. Nenhum dos dois repete o que o outro guarda. A temporização de cada modo de vídeo mora num catálogo único, `boards/video-modes.yaml`, comum a todas as placas (seção 4.3).

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
| `io.<papel>` | Papéis `leds`, `switches`, `keys` e `display`, cada um com `signals` e `active` (`high` ou `low`), e o papel `video`, descrito na seção 4 |
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
| `cyclone-v`, `cyclone-v-soc` | `alm` | `dsp_block` (o bloco DSP, como o Quartus o conta) |
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

## 4. Papel video

O papel `io.video` declara a saída de vídeo da placa. As placas sem saída de vídeo não o têm.

### 4.1. Campos

| Campo | Significado |
| :--- | :--- |
| `kind` | `vga` (DAC analógico, com ou sem chip) ou `hdmi` (transmissor digital com RGB paralelo) |
| `channel_bits` | Bits por canal de cor entregues à placa, `4` ou `8` |
| `signals` | Prefixo dos sinais de vídeo no `pins.yaml`, sem o sublinhado final |
| `default_mode` | Modo usado quando a plataforma não pede outro; precisa constar em `modes` |
| `modes` | Modos que o manual da placa especifica ou que o chip de saída suporta; cada nome existe em `boards/video-modes.yaml` |

### 4.2. Sinais por tipo de saída

O prefixo de `signals` casa todos os sinais do `pins.yaml` que começam por ele.

| `kind` | Prefixo | Sinais esperados |
| :--- | :--- | :--- |
| `vga` com DAC de resistores | `VGA` | `VGA_R[n]`, `VGA_G[n]`, `VGA_B[n]`, `VGA_HS`, `VGA_VS` |
| `vga` com DAC integrado (ADV7123) | `VGA` | Os acima mais `VGA_CLK`, `VGA_BLANK_N` e `VGA_SYNC_N` |
| `hdmi` (ADV7513) | `HDMI_TX` | `HDMI_TX_D[n]` (24 bits), `HDMI_TX_DE`, `HDMI_TX_HS`, `HDMI_TX_VS`, `HDMI_TX_CLK` e `HDMI_TX_INT` |

O barramento de cada cor tem `channel_bits` fios nos tipos `vga`. No `hdmi`, o transmissor recebe 24 bits e `channel_bits` diz quantos bits de cada canal o conteúdo usa. O transmissor HDMI é configurado por um barramento I2C que fica fora do prefixo (`I2C_SCL` e `I2C_SDA` na DE10-Nano) e consta no `pins.yaml` como qualquer outro sinal.

### 4.3. Catálogo de modos

O arquivo `boards/video-modes.yaml` guarda a temporização de cada modo, e o nome do modo tem a forma `<largura>x<altura>@<atualização em Hz>`.

| Campo | Significado |
| :--- | :--- |
| `width`, `height`, `refresh_hz` | Área visível em pixels e taxa de atualização |
| `aspect` | Proporção reduzida da área visível (`4:3`, `16:9` ou `5:4`) |
| `pixel_clock_mhz` | Clock de pixel em MHz |
| `horizontal`, `vertical` | Por eixo, `sync`, `back_porch`, `visible`, `front_porch`, `total` e `polarity` |
| `source` | Tabela do manual ou norma de onde vieram os valores |

Em cada eixo, o total é a soma dos quatro intervalos, e `polarity` vale `neg` (pulso em nível baixo) ou `pos` (pulso em nível alto). O eixo horizontal conta pixels, e o vertical conta linhas.

$$
\text{total} = \text{sync} + \text{back\_porch} + \text{visible} + \text{front\_porch}
$$

$$
\text{refresh\_hz} \approx \frac{\text{pixel\_clock\_mhz} \cdot 10^{6}}{\text{total}_{h} \cdot \text{total}_{v}}
$$

```yaml
modes:
  640x480@60:
    width: 640
    height: 480
    refresh_hz: 60
    aspect: "4:3"
    pixel_clock_mhz: 25.0
    horizontal: {total: 800, sync: 96, back_porch: 48, visible: 640, front_porch: 16, polarity: neg}
    vertical:   {total: 525, sync: 2, back_porch: 33, visible: 480, front_porch: 10, polarity: neg}
```

### 4.4. Modo padrão e sobrescrita pela plataforma

O `platform.yaml` pode pedir outro modo em `io.video`, e os três campos são opcionais.

| Campo | Significado |
| :--- | :--- |
| `width`, `height` | Resolução pedida; o modo é procurado no catálogo |
| `aspect` | Proporção pedida, `4:3` ou `16:9` |

| Pedido da plataforma | Modo escolhido |
| :--- | :--- |
| Sem `io.video` | O `default_mode` da placa |
| Só `aspect` | O maior modo de `modes` com essa proporção |
| `width` e `height` | O modo do catálogo com essa resolução |

```yaml
io:
  video:
    width: 1280
    height: 720
    aspect: 16:9
```

O modo escolhido precisa constar em `modes` da placa, e a proporção pedida precisa bater com `width` e `height`. Um modo fora de `modes` só é aceito quando a plataforma o marca de forma explícita como fora do manual. O clock de pixel precisa ser gerável pelo PLL da placa, o framebuffer precisa caber na memória livre, e `channel_bits` da placa limita os bits por canal pedidos.

### 4.5. Exemplos

```yaml
# DE2-115: DAC ADV7123 de 8 bits, cinco modos
io:
  video: {kind: vga, channel_bits: 8, signals: VGA, default_mode: 640x480@60,
          modes: [640x480@60, 640x480@85, 800x600@60, 1024x768@60, 1280x1024@60]}
```

```yaml
# DE10-Nano: transmissor HDMI ADV7513, configurado por I2C
io:
  video: {kind: hdmi, channel_bits: 8, signals: HDMI_TX, default_mode: 640x480@60,
          modes: [640x480@60, 1024x768@60, 1280x1024@60, 1920x1080@60]}
```

## 5. Exemplo

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
