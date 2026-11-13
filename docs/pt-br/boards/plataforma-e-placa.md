# Campos de placa do platform.yaml, chips e regras de validação

## 1. Os campos do platform.yaml que ligam a placa

O `platform.yaml` descreve o mapa de memória, o perfil do Core, as janelas dos periféricos e as interrupções, e traz os campos abaixo para ligar a plataforma a uma placa. O leitor deles é o mesmo dos arquivos de placa, de modo que um campo desconhecido ou de tipo errado é um erro apontado pelo caminho pontilhado do campo.

| Campo | Tipo | Significado |
| :--- | :--- | :--- |
| `board` | texto | `auto` (padrão) pede a identificação pelo JTAG ([identificacao-jtag.md](identificacao-jtag.md)); um nome fixa a placa |
| `boards` | lista de texto | Placas em que a plataforma é construída, e a lista que `auto` considera |
| `top` | texto ou lista | Componente(s) do `paths.yaml` cujo fecho de `requires` é a lista de fontes do projeto gerado e reúne os recursos que a placa precisa oferecer |
| `memory.<rom ou ram>.backend` | `emulado` ou `dispositivo` | Realização da região externa; obrigatório com `external: true` |
| `memory.<rom ou ram>.device` | `nor`, `flash-interna`, `serial`, `sdram`, `sram` | Só com `dispositivo`, e do tipo da região (`nor`, `flash-interna` e `serial` para a ROM; `sdram` e `sram` para a RAM) |
| `memory.<rom ou ram>.latency` | `{first, next}` | Ciclos de `clocks.core` da primeira palavra de uma rajada e das seguintes; só com `emulado` |
| `memory.rom.sector_bytes` | potência de 2 | Setor da FLASH `emulado`; com `dispositivo` o setor vem do chip |
| `memory.icache`, `memory.dcache` | `{enabled, size_bits}` | Caches |
| `clocks.core` | `{mhz, phase_ps}` | Relógio do núcleo; é também a fonte de `interrupts.clock_hz` |
| `clocks.fetch` | `{mhz, phase_ps}` | Relógio das memórias de instrução, com fase relativa ao `core`; sem ele vale o do núcleo |
| `clocks.mem` | `{mhz}` | Teto do relógio do controlador de dispositivo; o efetivo é o menor entre ele e o limite do chip |
| `console` | `jtag` ou `pinos` | `jtag` é o padrão; `pinos` exige UART em pinos na placa |
| `io.<papel>` | `{count, need}` | Papéis `leds`, `switches`, `keys` e `display`; `need` é `required` ou `optional` |

Cada relógio é escrito uma vez. O PLL, o `.sdc` e `interrupts.clock_hz` derivam de `clocks`, e a fase do relógio que sai pelo pino da SDRAM é da placa (`memories.sdram.clk_phase_ps`).

### 1.1. Exemplo

Trechos do `platform.yaml` da `de2-115`, com a FLASH NOR e a SDRAM da placa.

```yaml
platform: de2-115
board: auto
boards: [de2-115]
top: Insper-RISC-V/de2_115_board
core:
  type: 32
  base: I
  extensions:
    - M
    - Zicclsm
    - Zicntr
    - Zihpm
    - Zifencei
regions:
  - {name: BOOT_MEMORY, base: 0x00000000, size: 4K,    kind: rom, exec: true}
  - {name: FLASH,       base: 0x00001000, size: 1024K, kind: rom, exec: true}
  - {name: RAM,         base: 0x40000000, size: 64M,   kind: ram}
flash:
  region: FLASH
  banks:
    - {name: A, base: 0x00001000, size: 512K}
    - {name: B, base: 0x00081000, size: 512K}
memory:
  rom:    {external: true, backend: dispositivo, device: nor}
  ram:    {external: true, backend: dispositivo, device: sdram}
  icache: {enabled: true, size_bits: 32768}
  dcache: {enabled: true, size_bits: 32768}
clocks:
  core:  {mhz: 50, phase_ps: 8250}
  fetch: {mhz: 50, phase_ps: 0}
  mem:   {mhz: 100}
console: jtag
io:
  leds:    {count: 18, need: required}
  display: {count: 8,  need: optional}
```

A FLASH começa em `0x00001000`, o deslocamento 0 do chip. Com o setor de 64 KiB, cada banca começa em múltiplo de 64 KiB a partir do início do chip, e por isso a banca B está em `0x00081000`, deslocamento `0x80000`.

## 2. Derivação de requires e provides

Dois conjuntos são calculados e nunca escritos. O `requires` da plataforma reúne o que ela pede (`regions`, `memory`, `clocks`, `io`, `console`) e a união das chaves `needs` dos componentes do fecho do topo. O `provides` da placa vem do `board.yaml`, do chip do catálogo e do `pins.yaml`. A inclusão do primeiro no segundo é a verificação.

| Recurso exigido | Origem em `requires` | Origem em `provides` |
| :--- | :--- | :--- |
| Tipo de dispositivo (`sdram`, `sram`, `nor`, `onchip_flash`, `serial_flash`, `vjtag`, `block_ram`) | União dos `needs` do fecho do topo | Chave presente em `memories` e `jtag.chain` |
| Capacidade e largura | `regions` e `memory.<região>` | Chip do catálogo e `chips` ou `bus_width` |
| Blocos de RAM | Memórias `emulado`, caches e banco de registradores | `resources.block_ram` |
| Lógica e multiplicadores | Estimativa de [cabimento.md](cabimento.md) | `resources.logic` e `resources.multipliers` |
| PLLs | Relógios distintos de `clocks` | `resources.plls` |
| Papéis de E/S e console | `io` e `console` | `io` e `console.uart` |
| Frequência | `clocks.*` | Faixa do PLL da família e `max_mhz` do chip |

A chave `needs` mora ao lado de `sources` e `requires` no `paths.yaml` do repositório dono do componente, com os tipos `block_ram`, `sdram`, `sram`, `nor`, `onchip_flash`, `serial_flash` e `vjtag`.

## 3. Catálogo de chips

Cada chip de memória é um arquivo `Memory/chips/<chip>.yaml`, e o nome do arquivo é o do chip.

| Campo | Significado |
| :--- | :--- |
| `chip` | Nome |
| `extends` | Opcional; nome de outro chip cujos campos este herda e sobrescreve |
| `kind` | `sdram`, `sram`, `nor` ou `serial_flash` |
| `organization` | `{words, width, banks, row_bits, col_bits}` para a SDRAM; `{words, width}` para os demais |
| `cas_latency` | Latência de coluna da SDRAM |
| `timing` | Tempos com os nomes do datasheet; picossegundos na SDRAM (`trcd_ps`), nanossegundos na SRAM e na NOR (`access_ns`) |
| `io_timing` | Setup, hold e acesso dos pinos, usados no `.sdc` |
| `sector_bytes`, `boot_sector_bytes` | Setor da FLASH |
| `max_mhz` | Teto de relógio do chip |
| `source` | `datasheet` ou `inferido` |

```yaml
chip: IS42S16320B-7
extends: IS42S16320D-7
source: inferido
```

O chip da `de2-115` pertence à mesma série do da `de0-cv` e não repete nenhum valor. Os tempos do chip viram um pacote VHDL gerado, lido pelo controlador e pelo modelo de simulação, e os atrasos de E/S do `.sdc`.

## 4. Regras de validação

As regras rodam no `check-memory-map`, no `board generate` e antes de compilar. Cada uma é um erro (E) ou um aviso (W), e as mensagens são em inglês.

| Regra | Nível | O que confere |
| :--- | :--- | :--- |
| V1 | E | A placa, a família e os chips existem e os arquivos seguem o esquema |
| V2 | E | Todo tipo de `needs` está na placa, e a soma das regiões de um dispositivo cabe nele |
| V3 | E | O dispositivo de um backend `dispositivo` existe na placa |
| V4 | E | O console `pinos` exige `console.uart` |
| V5 | E | Papel `required` ausente ou com menos unidades |
| V6 | W | Papel `optional` ausente ou com menos unidades; o periférico é omitido |
| V7 | E | Relógio acima da faixa do PLL da família ou do teto do chip |
| V8 | W | Relógio do núcleo acima do Fmax medido da família e do grau |
| V9 | E | Banca da FLASH fora do múltiplo do setor, contado a partir do início da região |
| V10 | E | Região maior que a capacidade do dispositivo |
| V11 | E ou W | Blocos de RAM acima da capacidade (E) ou de 85 % dela (W) |
| V12 | E | Lógica estimada acima da capacidade, em família com erro máximo de validação até 10 % |
| V13 | W | Lógica estimada entre 85 % e 100 % da capacidade |
| V14 | E ou W | O relatório do ajuste estoura um recurso (E) ou passa de 85 % dele (W) |
| V15 | E | Mais saídas de PLL que a placa oferece |
| V16 | E | Pino `inferred` em uso sem `--accept-inferred-pins` |
| V17 | E | A cadeia JTAG lida do cabo não é a da placa |
| V18 | W | Família sem calibração, capacidade `null` ou coeficiente `null` de um termo do perfil |
| V19 | E | Largura do barramento que o backend não sabe fatiar (8 e 16 na NOR, 16 e 32 na SRAM e na SDRAM) |

Exemplos de mensagem.

```text
E platform 'de0-cv' requires sdram (64M) but board 'de0-nano' provides sdram of 32M
E memory.rom.device nor is not provided by board 'de0-cv' (provides: none); use backend emulado
E flash bank B base 0x7F000 is not a multiple of the NOR sector 0x10000 of chip S29GL064N90
E pin M16 for SPI_FLASH_CS is inferred, not confirmed; pass --accept-inferred-pins
```

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
