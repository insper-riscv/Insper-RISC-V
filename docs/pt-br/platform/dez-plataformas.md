# As dez plataformas: quatro de teste, quatro na FPGA e duas de UART

## 1. O que são

Cada combinação de memória e de periféricos é uma plataforma com o seu `platform.yaml`, o seu `config.yaml` e o seu `runtime/`. As dez rodam o mesmo topo de simulação, o `modular_sim_top` (`src/simulation/modular/`), e diferem pelo mapa, pela combinação de memórias e pelos periféricos ligados. O campo `platform:` de cada `platform.yaml` é o nome da pasta.

| Grupo | Quantas | Onde roda | Periféricos |
| :--- | ---: | :--- | :--- |
| Teste | 4 | Simulação | Nenhum |
| FPGA | 4 | DE0-CV | Chaves, displays de 7 segmentos e botões |
| UART | 2 | DE0-CV | UART via JTAG ou UART via pinos |

## 2. As combinações de memória

As quatro combinações vêm de `rom_external` e `ram_external` da seção `memory` do `platform.yaml`, e as caches existem do lado externo.

| Combinação | ROM | RAM | Caches | Arquitetura da `modular` |
| :--- | :--- | :--- | :--- | :--- |
| `integrated` | interna | interna | nenhuma | A |
| `external-data` | interna | externa | de dados | B |
| `external-instruction` | externa | interna | de instruções | C |
| `external` | externa | externa | de instruções e de dados | D |

## 3. As plataformas

| # | Plataforma | Pasta | Combinação | Perfil | Periféricos |
| ---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `test-integrated` | `src/simulation/` | `integrated` | `rv32im_zicclsm` | nenhum |
| 2 | `test-external-data` | `src/simulation/` | `external-data` | `rv32im_zicclsm` | nenhum |
| 3 | `test-external-instruction` | `src/simulation/` | `external-instruction` | `rv32im_zicclsm_zifencei` | nenhum |
| 4 | `test-external` | `src/simulation/` | `external` | `rv32im_zicclsm_zifencei` | nenhum |
| 5 | `fpga-integrated` | `src/cyclone-v/` | `integrated` | `rv32im_zicclsm_zicntr_zihpm` | chaves, botões, displays |
| 6 | `fpga-external-data` | `src/cyclone-v/` | `external-data` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | chaves, botões, displays |
| 7 | `fpga-external-instruction` | `src/cyclone-v/` | `external-instruction` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | chaves, botões, displays |
| 8 | `fpga-external` | `src/cyclone-v/` | `external` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | chaves, botões, displays |
| 9 | `fpga-uart-jtag` | `src/cyclone-v/` | `external` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | UART via JTAG |
| 10 | `fpga-uart-pins` | `src/cyclone-v/` | `external` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | UART via pinos |

Todas ligam as extensões `Zimop` e `Zicond` pelo campo `extras`. As plataformas com cache de instruções usam o perfil com `Zifencei`.

## 4. Mapas de memória

A BOOT_MEMORY de 4 KiB começa em `0x00000000` nas dez, e a ROM (ou a FLASH) começa logo depois dela.

| Plataformas | ROM | RAM |
| :--- | :--- | :--- |
| 1 a 4 | `0x00001000` a `0x00100000` | `0x00100000`, 1 MiB |
| 5 | `0x00001000`, 28 KiB | `0x00008000`, 160 KiB |
| 7 | `0x00001000`, 252 KiB | `0x00040000`, 160 KiB |
| 6, 8, 9 e 10 | `0x00001000`, 252 KiB | `0x40000000`, 32 MiB |

As palavras que o hospedeiro e o programa compartilham (`stdout`, `tohost` e `fromhost`) ficam no topo da RAM de cada plataforma. A SDRAM da placa tem 64 MiB e o mapa usa 32 MiB dela, o maior tamanho do modelo de chip de RAM da simulação (`ram_chip`).

## 5. Periféricos e janelas

Cada periférico ocupa uma janela de 256 MiB da região a partir de `0x80000000`, cujo índice está nos bits 30:28 do endereço.

| Periférico | Bloco | Pino da placa | Índice | Base | Plataformas |
| :--- | :--- | :--- | ---: | :--- | :--- |
| `SWITCHES` | GPIO de 10 pinos | `SW` | 1 | `0x90000000` | 5 a 8 |
| `KEYS` | GPIO de 4 pinos | `KEY` | 2 | `0xA0000000` | 5 a 8 |
| `UART` pelos pinos | `UART/serial` | dois pinos, TX e RX | 3 | `0xB0000000` | 10 |
| `UART` pelo JTAG | `UART/jtag` | cabo JTAG | 4 | `0xC0000000` | 9 |
| `DISPLAY` | display | `HEX0` a `HEX5` | 5 | `0xD0000000` | 5 a 8 |

Nas plataformas de teste a janela de periféricos não tem dispositivo: uma leitura responde zero e uma escrita não tem efeito. Os GPIO leem os pinos sincronizados na palavra 9 da janela (deslocamento `0x24`), com os pinos como entrada depois do reset.

## 6. Como são montadas

1. O `riscv-tools generate-memory-map` escreve, de cada `platform.yaml`, o pacote `modular_map_pkg.vhd` da pasta da plataforma, o cabeçalho `runtime/memory_map.h`, o arquivo de specs do ligador e o script de ligação da BOOT_MEMORY (`make generate`, e `make generate-check` confere).
2. O pacote de cada plataforma se chama `modular_map_pkg`, o nome que o topo usa, e a lista de fontes da plataforma traz o pacote da própria pasta. O componente `<nome>_sim_top` do `provides` (com o nome da plataforma em snake_case) lista as fontes na ordem certa.
3. A combinação de memórias e os `HAS_*` do perfil chegam ao topo pelo pacote. Os periféricos entram pelos genéricos `has_switches`, `has_keys`, `has_display`, `has_uart_jtag` e `has_uart_pins` do topo, que o `sim.parameters` do `config.yaml` de cada plataforma liga, e os índices das janelas são os genéricos `switches_id`, `keys_id`, `display_id`, `uart_jtag_id` e `uart_pins_id`.
4. As portas dos periféricos no topo são `io_sw` e `io_key` (os GPIO), `o_display_hex` e `o_display_value`, as portas `i_uart_*` e `o_uart_tdo` do Virtual JTAG e os pinos `i_uart_rx` e `o_uart_tx`.

## 7. Como usar

```bash
ulimit -s unlimited
riscv-tools --root . generate-memory-map --platform src/cyclone-v/fpga-external/platform.yaml
riscv-tools --profile rv32im_zicclsm_zicntr_zihpm_zifencei \
  --config src/cyclone-v/fpga-external/config.yaml compile --emit hex ...
```

O `--memory` do `riscv-tools` troca a combinação de memórias para uma execução, e `--profile` troca o perfil.

## 8. Verificação

`make unit-tests` roda o programa mínimo nas dez (`PlatformTestIntegrated` a `PlatformFpgaUartPins` do `tests.json`), que guarda `0x5A` na base da RAM, lê de volta, soma 1 e guarda o resultado na palavra seguinte. O teste lê a base e o lado da RAM dos genéricos do topo, então a mesma verificação vale para todas.

| Entrada de `tests.json` | O que confere |
| :--- | :--- |
| `Platform<Nome>` (dez) | As duas palavras do programa mínimo, na RAM do núcleo ou no chip externo |
| `Platform<Nome>Board` (5 a 8) | O programa lê as chaves e os botões que o teste conduz, escreve o valor do display e o lê de volta; `o_display_value` e o dígito de `HEX0` batem |
| `PlatformFpgaUartPinsUart` | O programa envia `0x55` pelo TX, o teste fecha a linha no RX e o programa recebe o byte com `RX_VALID` |
| `PlatformFpgaUartJtagUart` | O hospedeiro lê o `H` que o programa envia pelo Virtual JTAG, entrega um byte e lê o eco somado de 1 |

`make check-tops` elabora o topo de cada uma, `make check-generics` confere que o topo declara todo `HAS_*` do pacote e `make sources-check` confere as listas de fontes geradas.
