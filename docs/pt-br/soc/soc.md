# SoC (`soc`)

🌐 [Português](../../pt-br/soc/soc.md) · [English](../../en/soc/soc.md)

## 1. O que é

A entidade `soc` (`src/soc/soc.vhd`) é o sistema em chip independente de placa. Ela contém o núcleo, as caches, as pontes e os roteadores de memória, a interconexão, o CLINT, o PLIC e os periféricos de E/S, e liga tudo por contratos de interface. Não tem pino de placa, nome de família nem modelo de chip. Quem a instancia fornece os dois relógios, o reset e os backends das regiões de memória.

O topo de simulação `modular_sim_top` a instancia e acrescenta o gerador de relógio de três fases e os modelos de chip. Um topo de placa instancia o mesmo `soc` e acrescenta o PLL, o anel de pinos e os controladores dos chips reais. Toda a lógica do SoC existe uma só vez, e a escolha entre simulação e placa fica fora dele.

## 2. Relógios e reset

| Porta | Papel |
| :--- | :--- |
| `i_clk_core` | Núcleo, memórias de dados, interconexão, caches de dados e periféricos |
| `i_clk_fetch` | Memórias de instrução (BOOT_MEMORY e ROM interna), em fase com o relógio do núcleo |
| `i_rst` | Reset, ativo em `'1'` |

O SoC não gera relógio. O topo escolhe a fase de cada um e a latência do reset.

## 3. Faces de memória

Cada região que o núcleo alcança tem uma face de portas. A face de uma região que o núcleo não alcança pela porta externa fica parada, com as saídas em zero e as entradas ignoradas.

| Região | Portas do SoC | Backend que o topo liga |
| :--- | :--- | :--- |
| BOOT_MEMORY | `o_if_addr`, `o_if_rden`, `i_boot_data` | Bloco de memória do FPGA com imagem inicial |
| ROM interna | `o_if_addr`, `o_if_rden`, `i_rom_data`, `o_rom_addr2`, `o_rom_rden2`, `i_rom_data2` | Bloco de memória de duas portas |
| ROM externa | `o_flash_*`, `i_flash_*` | Chip de FLASH, emulado ou de dispositivo |
| RAM interna | `o_ram_*`, `i_ram_rdata` | Bloco de memória do FPGA |
| RAM externa | `o_ramd_*` e `o_rami_*`, com `i_ramd_*` e `i_rami_*` | Chip de RAM, emulado ou de dispositivo |

As condições abaixo dizem quando o núcleo alcança cada memória pela porta.

$$\text{rom\_via\_porta} = \text{rom\_external} \lor \text{has\_icache} \qquad \text{ram\_via\_porta} = \text{ram\_external} \lor \text{has\_dcache}$$

A face do chip de FLASH leva o endereço de byte, a leitura, o pedido de linha, o avanço e a linha de 96 bits, e devolve a resposta pronta, a palavra, a linha e o sinal de ocupado que alimenta o Zihpm. A face do chip de RAM tem uma porta de dados e uma de instruções, com os mesmos sinais do contrato de memória. Os caminhos de dados entre o núcleo e essas faces estão em [modular](../platform/modular.md).

## 4. Papéis de E/S

Os papéis de E/S têm a largura por generic, e um papel de largura zero é omitido junto com o seu periférico. A polaridade do pino é um generic por papel, que o topo resolve. O programa vê sempre o valor ativo em `'1'`.

| Papel | Presença | Largura | Polaridade | Porta |
| :--- | :--- | :--- | :--- | :--- |
| Chaves | `has_switches` | `switches_width` | `switches_active_low` | `io_switches` |
| Botões | `has_keys` | `keys_width` | `keys_active_low` | `io_keys` |
| Display | `has_display` | `display_digits` | `display_active_low` | `o_display_hex`, `o_display_value` |

As chaves e os botões são blocos GPIO, e o display é o registrador `seg_display`. Os dois periféricos aceitam largura zero e têm o generic de polaridade, descritos nos documentos do repositório Peripherals. O console em pinos recebe a polaridade das suas duas linhas de `uart_tx_invert` e `uart_rx_invert`. O console sobre JTAG e o console em pinos têm as portas `i_uart_*`, `o_uart_tdo`, `i_uart_rx` e `o_uart_tx`, e o temporizador, o CLINT e o PLIC não têm porta de placa.

## 5. Mapa e generics

O mapa de memória chega por generics, sem valor padrão: `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib` e `periph_base_kib`. Os valores vêm do `platform.yaml`, pelo pacote que o topo lê. O núcleo lê o mesmo mapa do `config_pkg` que o `platform.yaml` gera para a plataforma (`generate.config_pkg`), e o SoC confere em asserções que esses generics concordam com ele. As extensões do núcleo (`has_*`), as caches (`has_icache`, `has_dcache` e os tamanhos), as interrupções (`has_interrupts`, `plic_*`, `clint_*`) e os índices das janelas dos periféricos são generics com valor neutro.

### 5.1. Generics do mapa e das extensões

| Grupo | Generics | Valor padrão |
| :--- | :--- | :--- |
| Mapa | `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib` | sem padrão |
| Regiões externas | `rom_external`, `ram_external` | `false` |
| Caches | `has_icache`, `has_dcache` | `false` |
| Tamanho das caches | `icache_size_bits`, `dcache_size_bits` | 4096 bits |
| Janela das caches | `cache_window_bits`, de 26 a 29 (26 é 64 MiB, 27 é 128 MiB, a janela de endereços que a tag cobre) | 26 |
| Base e extensões do núcleo | `has_e`, `has_zicsr`, `has_zicntr`, `has_zihpm`, `has_zimop`, `has_zicond`, `has_zihintntl`, `has_zihintpause`, `has_m`, `has_zmmul`, `has_zifencei`, `has_zicclsm`, `has_access_faults` | `false` |
| Contadores do Zihpm | `hpm_counters`, de 0 a 29, e `hpm_width`, de 0 a 64 bits | 29 e 64 |
| Interrupções | `has_interrupts`, `has_sscofpmf`, `periph_slots`, `clint_tick_cycles`, `clint_id`, `plic_id`, `plic_n_sources`, `plic_priority_bits`, `plic_addr_width` | desligadas, janelas 6 (CLINT) e 7 (PLIC), 6 fontes, 3 bits, 20 bits |
| Janelas dos periféricos | `timer_id`, `switches_id`, `keys_id`, `uart_pins_id`, `uart_jtag_id`, `display_id`, `flash_ctrl_id` | 0, 1, 2, 3, 4, 5 e 3 |
| Presença dos periféricos | `has_timer`, `has_switches`, `has_keys`, `has_display`, `has_uart_jtag`, `has_uart_pins` | `false` |
| Largura dos papéis | `switches_width`, `keys_width`, `display_digits` | 10, 4 e 6 |
| Polaridade dos pinos | `switches_active_low`, `keys_active_low`, `display_active_low`, `uart_tx_invert`, `uart_rx_invert` | `false`, exceto o display (`true`) |

### 5.2. Cortes de caminho crítico e atualização de programa

Cinco generics ligam o que as placas de relógio alto precisam, todos desligados por padrão para que as plataformas de simulação fiquem como estavam.

| Generic | Efeito |
| :--- | :--- |
| `registered_irqs` | As três linhas de interrupção entram no núcleo por um registrador, um ciclo de latência a mais, e saem do caminho que decide a tomada da interrupção |
| `fast_icache_select` | A cache de instruções escolhe a região pelo endereço registrado e não confere o endereço a cada consulta; exige o relógio de busca defasado do relógio do núcleo |
| `has_dcache_bypass` e `bypass_page` | A página de 4 KiB indicada (a do topo da RAM) nunca fica na cache de dados, porque ali estão as palavras que o hospedeiro compartilha com o programa |
| `has_flash_ctrl` e `flash_ctrl_id` | O controlador de FLASH da atualização de programa fica na janela indicada, com a interrupção na linha 6 e os comandos do chip em `o_flash_cmd_*` e `i_flash_cmd_*` |
| `i_inval_valid`, `i_inval_first` e `i_inval_last` (portas) | A região regravada da FLASH, que derruba as linhas das duas caches |
| `i_display_*`, `o_display_tdo` e `o_display_fail` (portas) | O Virtual JTAG pelo qual o hospedeiro lê e grava o registrador do display e a bandeira de falha; o topo da placa liga o nó de índice 2 |

### 5.3. Validação dos generics

A elaboração do SoC para com `severity failure` quando uma combinação de generics não tem sentido, e a mensagem traz o nome do generic e a causa.

| Regra | Generics |
| :--- | :--- |
| A BOOT_MEMORY é potência de dois e múltipla de 1 KiB | `boot_memory_size_bytes` |
| O mapa é ordenado, sem sobreposição: BOOT_MEMORY, ROM, RAM, janela externa e janela de periféricos | `rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib` |
| A ROM alcançada pela porta cabe na janela das caches, e a RAM cabe nela com a cache de dados | `cache_window_bits`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib` |
| Cada cache existente tem tamanho em potência de dois de pelo menos 256 bits | `icache_size_bits`, `dcache_size_bits` |
| As opções de uma cache só valem com ela | `has_dcache_bypass` exige `has_dcache`, `fast_icache_select` exige `has_icache` |
| Os contadores são CSRs | `has_zicntr` e `has_zihpm` exigem `has_zicsr` |
| A polaridade dos pinos da UART só vale no papel de pinos | `uart_tx_invert` e `uart_rx_invert` exigem `has_uart_pins` |
| Dois periféricos presentes não dividem o índice de janela | `clint_id`, `plic_id`, `timer_id`, `switches_id`, `keys_id`, `display_id`, `uart_jtag_id`, `uart_pins_id`, `flash_ctrl_id` |

`has_interrupts`, `has_sscofpmf` e `has_access_faults` não geram erro sem `has_zicsr`, porque o SoC os desliga antes de entregá-los ao núcleo.

## 6. Linhas do PLIC

Cada periférico liga a sua interrupção a uma linha fixa do PLIC, a mesma em toda plataforma.

| Linha | Fonte |
| ---: | :--- |
| 1 | Console em pinos |
| 2 | Console sobre JTAG |
| 3 | Chaves |
| 4 | Botões |
| 5 | Temporizador |
| 6 | Controlador de FLASH |

O `make check-irq-sources` confere esses números contra a lista `interrupts.sources` de cada `platform.yaml`.

## 7. Verificação

A entrada `SocRoles` do `tests.json` instancia só o `soc`, sem modelo de chip. O teste faz o papel da BOOT_MEMORY e do relógio de três fases, roda um programa que lê quatro chaves ativas em nível baixo e guarda a palavra lida na RAM, e confere que o programa a vê com a polaridade invertida e que as faces dos chips ficam paradas com as memórias internas. As plataformas do `modular_sim_top` provam o SoC com todas as combinações de memória e cache, e o `make check-tops` o elabora nas dez plataformas.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
