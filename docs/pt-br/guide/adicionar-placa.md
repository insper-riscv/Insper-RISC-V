# Como adicionar uma placa nova

Este guia leva uma placa Quartus que o repositório não conhece até a execução de programas nela. Cada passo cita as placas já feitas como exemplo: `de0-cv`, `de2-115`, `de0-nano`, `de10-lite`, `de10-nano`, `de0-nano-soc` e `mkr-vidor-4000`. O que cada placa ofereceu e o nível que atingiu estão em [../boards/placas.md](../boards/placas.md). Os comandos rodam na raiz do `Insper-RISC-V`, na imagem `dev_tools` ou numa máquina com o `riscv-tools` instalado; os passos 8 a 10 pedem o Quartus.

## 1. Níveis de suporte

Os níveis são cumulativos, e cada placa declara em `target_level` o que se propõe a atingir.

| Nível | Significado | Prova |
| :--- | :--- | :--- |
| N0 | Projeto gerado e sintetizado | `quartus_map` sem erro |
| N1 | Ajuste e tempo | `quartus_fit` e `quartus_sta` sem erro e com os números registrados na página da placa |
| N2 | Placa viva | Bitstream programado, a BOOT_MEMORY roda e um programa mínimo responde pelo console |
| N3 | Suíte de hardware | Os programas do repositório Tests passam na placa |
| N4 | Conformidade | O ACT4 do perfil que cabe passa na placa |

Uma placa sem cabo à mão fica em N0 ou N1; o pacote entra com a nota de que não foi validado em hardware, como a `de10-nano` e a `mkr-vidor-4000`.

## 2. Ficha de pesquisa

A ficha é um documento por placa em `Plans/Multi-FPGA/placas/<placa>.md` do repositório Capstone, que reúne os fatos antes de qualquer arquivo de dados. Cada fato traz a fonte e um selo de certeza.

| Selo | Significado |
| :--- | :--- |
| `manual` | Lido no manual ou no esquemático da placa |
| `repo` | Lido num arquivo de projeto do repositório (por exemplo um `.qsf`) |
| `inferido` | Deduzido de fonte de terceiros, como uma porta VHDL ou um fórum |
| `measured` | Lido de um cabo real (`jtagconfig`, `lsusb`) |

As seções da ficha, nesta ordem, são as mesmas das placas feitas.

| Seção | Conteúdo | Exemplo |
| :--- | :--- | :--- |
| Identificação | Placa, dispositivo completo, grau, IDCODE medido | `de0-nano`: o IDCODE `020F30DD` é de três dispositivos, e a identificação fecha pelo nome da placa e pelo cabo |
| Recursos do FPGA | Lógica, blocos de RAM, multiplicadores, PLLs, pinos de usuário | `de10-lite`: 49.760 LEs e 182 blocos M9K |
| Relógios e reset | Osciladores, pino e polaridade do reset | `de0-nano`: sem botão de reset, o reset é `KEY[0]` |
| Entrada e saída | LEDs, chaves, botões, displays, UART e suas polaridades | `de2-115`: 18 LEDs vermelhos mais 9 verdes |
| Memórias | Chip, organização e tempos de cada memória externa | `mkr-vidor-4000`: SDRAM AS4C4M16SA com 12 bits de linha |
| Configuração e JTAG | Cabo, IDs USB, cadeia | `de10-nano`: cadeia com o HPS e o FPGA |
| Armadilhas | Jumpers, bancos de tensão, pinos só de entrada | `de2-115`: KEY, SW e parte dos HEX seguem o jumper JP7 |
| Mapa para o projeto | O que o `board.yaml` e a plataforma vão declarar | |

Um fato sem fonte não entra no `board.yaml`. Um valor que o manual não traz (como o nome do chip da SDRAM da `de0-nano`) entra com o selo `inferido`, e a ficha diz como confirmá-lo.

## 3. O `pins.yaml`

O `pins.yaml` lista cada sinal da placa com pino, padrão de E/S, direção, fonte e selo, no formato de [../boards/formato.md](../boards/formato.md). As tabelas de pinos do manual são a fonte; o esquemático resolve as dúvidas.

1. Criar `boards/<placa>/pins.yaml` com `board` e `device`.
2. Uma entrada por sinal, com barramentos indexados (`LEDR[3]`, `DRAM_ADDR[12]`). O nome é o do manual, porque o `board.yaml` cita sinais só por nome.
3. Escrever em `conflicts` cada pino atribuído a mais de um sinal. A `mkr-vidor-4000` tinha sete pinos duplicados no `.qsf` oficial, resolvidos pelo esquemático; a `de2-115` guarda os apelidos de pino reservado.
4. Marcar `inferred` o que veio de terceiros. O Tools recusa construir com um pino assim sem `--accept-inferred-pins`, e a recusa protege o hardware de um pino errado.

## 4. O `board.yaml`

Criar `boards/<placa>/board.yaml` com os campos de [../boards/formato.md](../boards/formato.md). O arquivo cita a família, os chips e os sinais por nome, e nunca repete número de pino, tempo de chip ou parâmetro de família.

| Campo | Como preencher | Exemplo |
| :--- | :--- | :--- |
| `family`, `device`, `speed_grade` | Família do catálogo (passo 5), dispositivo completo e grau | `cyclone-iv-e`, `EP4CE22F17C6`, `C6` |
| `target_level` | O nível do passo 1 que a placa se propõe | `N3` na `de0-nano` |
| `jtag` | Cabo, cadeia com o IDCODE de cada dispositivo, IDs USB (passo 9) | `usb-blaster-ii` na `de10-nano` |
| `resources` | Totais do dispositivo na unidade da família (`alm` ou `le`); `null` onde a capacidade é desconhecida | `logic: {unit: le, total: 22320}` |
| `clocks` | Entradas, a referência do PLL e o reset com polaridade | `reset: {signal: "KEY[0]", active: low}` |
| `io` | Um papel (`leds`, `switches`, `keys`, `display`) por grupo de sinais, com a polaridade | `leds: {signals: "LED[7:0]", active: high}` |
| `memories` | Um bloco por memória externa, com o chip do catálogo e o prefixo dos sinais | `sdram: {chip: IS42S16160B-7, chips: 1, signals: DRAM, clk_phase_ps: 7000}` |
| `console` | `default: jtag`; `uart` só quando a placa tem UART em pinos | `de2-115` |
| `notes` | As armadilhas da ficha | |

Papéis que a placa não tem ficam de fora (a `de0-nano` não tem `display`), e o validador trata a ausência pelas regras V5 e V6 do passo 7. O comando `riscv-tools --root . check-boards` lê o pacote e aponta campo desconhecido, sinal inexistente no `pins.yaml` e pino repetido fora de `conflicts`.

## 5. Família e chips

### 5.1. Família

Se a família do dispositivo já está em `boards/families/`, a placa só a cita: `cyclone-v`, `cyclone-v-soc`, `cyclone-iv-e`, `max-10` e `cyclone-10-lp` cobrem as sete placas. Uma família nova ganha `boards/families/<família>.yaml` com os campos de [../boards/familias.md](../boards/familias.md). Três campos pedem cuidado.

| Campo | Cuidado |
| :--- | :--- |
| `pll.ip` | O Tools escreve `altera_pll` e `altpll`. Medir qual deles o Quartus aceita na família: o `altera_pll` só sintetiza na Cyclone V. Outra primitiva exige um escritor novo no gerador de PLL |
| `pll.vco_mhz` e `clock_node_pattern` | A faixa do oscilador vem do manual da família; o padrão do nome do nó vem do relatório de um projeto gerado e alimenta o `.sdc` |
| `slew_rate` e `qsf` | O que o ajuste do Quartus recusa ou exige na família: a `max-10` recusa `SLEW_RATE` e pede o modo de imagem única na configuração |

### 5.2. Chips

Cada memória externa cita um chip de `Memory/chips/<chip>.yaml`, no formato de [../boards/plataforma-e-placa.md](../boards/plataforma-e-placa.md). O arquivo traz organização, tempos do datasheet e `max_mhz`, com `source: datasheet` ou `source: inferido`. Um chip da mesma série herda de outro com `extends` e escreve só o que muda: o `IS42S16320B-7` da `de2-115` herda tudo do `IS42S16320D-7` da `de0-cv`.

O controlador de SDRAM lê largura, bits de linha, de coluna e de banco do chip, e dois chips lado a lado formam o barramento de 32 bits da `de2-115`. A FLASH NOR de 8 bits tem controlador próprio. Uma memória sem controlador (a SRAM) não gera instância no topo, e a região fica parada.

## 6. A plataforma

A plataforma diz o que o SoC pede, e a placa o que existe. Copiar a plataforma mais próxima e editar o `platform.yaml`: a `de0-nano` para uma placa pequena, a `de0-cv` para uma que comporta o perfil completo.

1. Criar `src/<família>/<placa>/` copiando a pasta da plataforma de partida, e renomear o pacote do mapa de memória.
2. Em `platform.yaml`, ajustar o campo `platform`, `board: auto`, `boards: [<placa>]`, `profile` e `regions`. Os campos novos, com as regras, estão em [../boards/plataforma-e-placa.md](../boards/plataforma-e-placa.md).
3. Escolher o backend de cada região externa. Uma região `emulado` consome blocos de RAM da placa, e uma `dispositivo` consome o chip. Na `de0-nano` a FLASH tem 28 KiB, porque a potência de dois seguinte passaria de 85 % dos blocos.
4. Escolher o relógio do núcleo e o do controlador em `clocks`, e os papéis de E/S em `io` com `need: required` ou `optional`.
5. No `paths.yaml`, declarar o pacote do mapa (`<placa>_map`) e o componente `<placa>_board`, cujo fecho de `requires` é a lista de fontes do projeto; o campo `top` da plataforma aponta para ele. Uma placa com SDRAM de 16 bits usa `requires: [sdram_board, <placa>_map]`.
6. Adaptar o `config.yaml` da plataforma (`extends` da plataforma de partida, `memory_map: platform.yaml`, o bloco `quartus` com `generate`, `project_dir`, `project_name` e `sof_file`) e a pasta `runtime/`.
7. Gerar os arquivos do mapa e conferir.

```bash
riscv-tools --root . generate-memory-map --platform src/<família>/<placa>/platform.yaml
riscv-tools --root . generate-memory-map --platform src/<família>/<placa>/platform.yaml --check
make sources-check
```

A plataforma também entra nas listas do `Makefile` que rodam `generate` e `generate-check`.

## 7. O validador

O validador compara o que a plataforma exige com o que a placa oferece e roda no `check-memory-map`, no `board generate` e antes de compilar.

```bash
riscv-tools --root . check-memory-map --platform src/<família>/<placa>/platform.yaml
```

Cada diferença é um erro (`E`) ou um aviso (`W`) com um código de V1 a V19, listados em [../boards/plataforma-e-placa.md](../boards/plataforma-e-placa.md). Os erros mais comuns numa placa nova são os seguintes.

| Regra | Causa típica | Correção |
| :--- | :--- | :--- |
| V2, V3 | A plataforma pede um dispositivo que a placa não tem | Trocar o backend para `emulado`, como a `de0-nano` faz com a FLASH |
| V5 | Papel `required` ausente | Marcar `optional` ou tirar o papel da plataforma |
| V9 | Banca da FLASH fora do múltiplo do setor | Mover a banca; na `de2-115` a banca B fica em `0x81000` por causa do setor de 64 KiB |
| V11, V12 | O perfil não cabe nos blocos ou na lógica | Reduzir o perfil, as caches ou a memória emulada; a `de0-nano` usa o RV32I com Zicsr |
| V16 | Pino `inferred` em uso | Confirmar o pino na fonte, ou passar `--accept-inferred-pins` ciente do risco |

## 8. Estimador e calibração

O estimador diz se o perfil cabe sem rodar o Quartus, usando a tabela de calibração da família ([../boards/cabimento.md](../boards/cabimento.md)). Uma placa de família já calibrada não pede nada neste passo: o `check-memory-map` e o `board generate` já estimam e escrevem o `capacity.json` no projeto.

Uma família nova precisa da própria tabela, medida na placa de referência dela.

1. Criar `src/calibration/<placa>/platform.yaml`, a plataforma de medida, e o componente `cal_<placa>_board` no `paths.yaml`.
2. Criar `boards/calibration/profiles/<família>.yaml`, a lista dos perfis a medir, e apontar `calibration` da família para `calibration/<família>.yaml`.
3. Medir, ajustar e, quando houver um segundo dispositivo da família, verificar.

```bash
riscv-tools --root . calibrate run --profiles boards/calibration/profiles/<família>.yaml --raw boards/calibration/raw/<família>
riscv-tools --root . calibrate fit --profiles boards/calibration/profiles/<família>.yaml --raw boards/calibration/raw/<família> --table boards/calibration/<família>.yaml
riscv-tools --root . calibrate verify --profiles boards/calibration/profiles/verify-<placa>.yaml --raw boards/calibration/raw/verify-<placa> --table boards/calibration/<família>.yaml --output boards/calibration/verification/<placa>.yaml
```

O `calibrate run` roda o `quartus_map` perfil a perfil, sob o travamento da máquina. Sem a tabela o validador emite V18 e só o ajuste do Quartus decide o cabimento.

## 9. Identificação pelo JTAG

O `riscv-tools` descobre a placa pelo IDCODE da cadeia e pela porta USB do cabo ([../boards/identificacao-jtag.md](../boards/identificacao-jtag.md)). O que o pacote precisa declarar:

1. `jtag.chain` com o `name` que o `jtagconfig` imprime e o `idcode` de 8 dígitos hexadecimais, o do FPGA com `fpga: true`. Ler os dois com a placa ligada.
2. `jtag.cable` com o tipo do cabo. Placas com USB-Blaster na própria placa usam `usb-blaster`; a `de10-nano` e a `de0-nano-soc` usam `usb-blaster-ii` e declaram o HPS como primeiro item da cadeia (`hps: true`); a `mkr-vidor-4000` usa `samd21-usbblaster`.
3. `jtag.usb` com os IDs USB quando o cabo só aparece antes de haver cadeia. O `board scan` reconhece a placa por eles, sem código novo.

Com a placa ligada, registrar o cabo no inventário do host.

```bash
riscv-tools board scan
riscv-tools board scan --save
riscv-tools board doctor
```

IDCODE compartilhado entre dispositivos (o `020F70DD` da `de2-115` serve ao 10CL120 e ao EP3C120) deixa mais de uma placa candidata. Duas placas iguais no mesmo host só se distinguem pelo inventário, e `--board`, `--board-id` e `--cable` desempatam por execução.

## 10. Níveis na prática

### 10.1. N0 e N1

```bash
riscv-tools --root . --board <placa> board generate --platform src/<família>/<placa>/platform.yaml --out build
riscv-tools --config src/<família>/<placa>/config.yaml --board <placa> program --stop-after map
riscv-tools --config src/<família>/<placa>/config.yaml --board <placa> program --stop-after sta
```

O `board generate` escreve o projeto em `build/<plataforma>-<placa>/`, e o `--stop-after` compila até `map` (N0) ou até `sta` (N1) sem programar. O `--accept-inferred-pins` entra na primeira linha enquanto houver pino inferido. Registrar na página da placa (`docs/pt-br/boards/<placa>.md`) o uso de lógica e de memória, os PLLs, os pinos e a menor folga de setup e de hold de cada relógio, como fazem `de0-nano.md` e `de10-lite.md`. Se o ajuste recusar algo da família, o erro entra na família (`slew_rate`, `qsf`) e não na placa.

### 10.2. N2

Com a placa ligada e livre, tomar a trava e programar.

```bash
riscv-tools board lock --board <placa> --wait -- \
  riscv-tools --config src/<família>/<placa>/config.yaml --board <placa> program <imagem.mif>
```

O `program` compila, programa e, no mesmo shell, evita a falha de cadeia descrita em [placa.md](placa.md). O critério é um programa mínimo que escreve no console JTAG e termina. Placa com cabo que não enumera fica em N1.

### 10.3. N3 e N4

O N3 roda os programas do repositório Tests pelas etapas `<placa>-*` do `tools/board/board_run.py` ([Tests](https://github.com/insper-riscv/Tests)), que compilam só os programas cujas extensões o perfil da plataforma liga. O N4 roda o ACT4 do perfil que cabe pelo repositório Certification. Cada etapa nova entra no runner com a placa, a configuração e as exclusões justificadas (por exemplo, programas de UART em pinos numa placa sem UART).

## 11. Testes e conferência

| Onde | Comando | O que prova |
| :--- | :--- | :--- |
| Insper-RISC-V | `make paths` | Caminhos do `paths.yaml`, forma da árvore e catálogo de placas (`check-boards`) |
| Insper-RISC-V | `make generate-check` e `make sources-check` | Os arquivos gerados e as listas de fontes estão em dia |
| Insper-RISC-V | `riscv-tools --root . board generate --platform ... --check` | O projeto no disco é o que o gerador escreveria |
| Tools | `uv run pytest tests/test_board_scan_select.py tests/test_board_special.py` | A seleção de placa com fixtures de `jtagconfig` e de `lsusb` da placa nova, sem hardware |

Para a seleção, copiar uma fixture de `jtagconfig` da placa ligada para `tests/fixtures/jtagconfig` do Tools e o pacote de placa para `tests/fixtures/boards`, e acrescentar o caso aos testes de seleção.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
