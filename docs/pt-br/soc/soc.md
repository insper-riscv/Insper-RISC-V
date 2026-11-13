# SoC (`soc`)

🌐 [Português](../../pt-br/soc/soc.md) · [English](../../en/soc/soc.md)

## 1. O que é

A entidade `soc` (`src/soc/soc.vhd`) é o sistema em chip independente de placa. Ela contém o núcleo, as caches, as pontes e os roteadores de memória, a interconexão, o CLINT, o PLIC e os periféricos de E/S, e liga tudo por contratos de interface. Não tem pino de placa, nome de família nem modelo de chip. Quem a instancia fornece os dois relógios, o reset e os backends das regiões de memória.

O topo de simulação `modular_sim_top` a instancia e acrescenta o gerador de relógio de três fases e os modelos de chip. Um topo de placa instancia o mesmo `soc` e acrescenta o PLL, o anel de pinos e os controladores dos chips reais. Toda a lógica do SoC existe uma só vez, e a escolha entre simulação e placa fica fora dele.

## 2. Relógios e reset

| Porta | Papel |
| :--- | :--- |
| `i_clk_core` | Núcleo, memórias de dados, interconexão, caches de dados e periféricos |
| `i_clk_fetch` | Memórias de instrução (BOOT_MEMORY e FLASH direta), em fase com o relógio do núcleo |
| `i_rst` | Reset, ativo em `'1'` |

O SoC não gera relógio. O topo escolhe a fase de cada um e a latência do reset.

## 3. Faces de memória

Cada região que o núcleo alcança tem uma face de portas. A face de uma região que não está no barramento fica parada, com as saídas em zero e as entradas ignoradas.

| Região | Portas do SoC | Backend que o topo liga |
| :--- | :--- | :--- |
| BOOT_MEMORY | `o_if_addr`, `o_if_rden`, `i_boot_data` | Bloco de memória do FPGA com imagem inicial |
| FLASH direta | `o_if_addr`, `o_if_rden`, `i_rom_data`, `o_rom_addr2`, `o_rom_rden2`, `i_rom_data2` | Bloco de memória de duas portas |
| FLASH no barramento | `o_flash_*`, `i_flash_*` | Chip de FLASH, emulado ou de dispositivo |
| RAM direta | `o_ram_*`, `i_ram_rdata` | Bloco de memória do FPGA |
| RAM no barramento | `o_ramd_*` e `o_rami_*`, com `i_ramd_*` e `i_rami_*` | Chip de RAM, emulado ou de dispositivo |

Uma cache só existe do lado do barramento: a cache de instruções exige `rom_external` e a cache de dados exige `ram_external`, a regra estrita do `check_isa` do `config_pkg`. As combinações válidas de FLASH, RAM e caches são as 9 que o `check_isa` do `config_pkg` aceita, e o núcleo alcança cada memória pelo barramento exatamente quando a plataforma a liga a ele.

$$\text{rom\_via\_porta} = \text{flash\_on\_bus} \qquad \text{ram\_via\_porta} = \text{ram\_on\_bus}$$

Todo endereço fora da BOOT_MEMORY, da FLASH e da RAM sai pela porta externa e chega ao interconector, que o envia a um periférico da tabela de janelas ou o termina em erro (ver [interconector](../interconnect/ext_interconnect.md)). Sem interconector, todo acesso externo termina em erro.

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

O mapa de memória chega por generics, sem valor padrão: `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib` e `ram_end_kib`. Os valores vêm do `platform.yaml`, pelo pacote que o topo lê. O núcleo lê o mesmo mapa do `config_pkg` que o `platform.yaml` gera para a plataforma (`generate.config_pkg`), e o SoC confere em asserções que esses generics concordam com ele. A base, as extensões do núcleo, as interrupções e a cache de dados (`IS_E`, `HAS_*`) não são generics: o núcleo e o SoC as leem do `config_pkg`. As caches de instruções (`has_icache` e os tamanhos), os parâmetros do PLIC e do CLINT (`plic_*`, `clint_*`) e os índices dos periféricos na tabela de janelas são generics. A tabela (`periph_count`, `periph_bases`, `periph_masks` e `strict_periph`) vem do pacote de mapa da plataforma e o SoC liga cada periférico pelo índice dele.

### 5.1. Generics do mapa e das caches

| Grupo | Generics | Valor padrão |
| :--- | :--- | :--- |
| Mapa | `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib` | sem padrão |
| Regiões no barramento | `rom_external`, `ram_external` | `false` |
| Tabela de janelas | `periph_count`, `periph_bases`, `periph_masks`, `strict_periph` | a tabela padrão de oito janelas de 256 MiB, 64 KiB de registradores e `true` |
| Cache de instruções | `has_icache` | `false` |
| Tamanho das caches | `icache_size_bits`, `dcache_size_bits` | 4096 bits |
| Janela das caches | `cache_window_bits`, de 26 a 29 (26 é 64 MiB, 27 é 128 MiB, a janela de endereços que a tag cobre) | 26 |
| Contadores do Zihpm | `hpm_counters`, de 0 a 29, e `hpm_width`, de 0 a 64 bits | 29 e 64 |
| Interrupções | `clint_tick_cycles`, `clint_index`, `plic_index`, `plic_n_sources`, `plic_priority_bits`, `plic_addr_width` | 1 ciclo, CLINT no índice 6 e PLIC no 7, 6 fontes, 3 bits, 20 bits |
| Índices dos periféricos | `timer_index`, `switches_index`, `keys_index`, `uart_pins_index`, `uart_jtag_index`, `display_index`, `flash_ctrl_index` | 0, 1, 2, 3, 4, 5 e 3 |
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
| `has_flash_ctrl` e `flash_ctrl_index` | O controlador de FLASH da atualização de programa fica na janela do índice indicado, com a interrupção na linha 6 e os comandos do chip em `o_flash_cmd_*` e `i_flash_cmd_*` |
| `i_inval_valid`, `i_inval_first` e `i_inval_last` (portas) | A região regravada da FLASH, que derruba as linhas das duas caches |
| `i_display_*`, `o_display_tdo` e `o_display_fail` (portas) | O Virtual JTAG pelo qual o hospedeiro lê e grava o registrador do display e a bandeira de falha; o topo da placa liga o nó de índice 2 |

### 5.3. Validação dos generics

A elaboração do SoC para com `severity failure` quando uma combinação de generics não tem sentido, e a mensagem traz o nome do generic e a causa.

| Regra | Generics |
| :--- | :--- |
| A BOOT_MEMORY é potência de dois e múltipla de 1 KiB | `boot_memory_size_bytes` |
| O mapa é ordenado, sem sobreposição: BOOT_MEMORY, FLASH e RAM | `rom_end_kib`, `ram_base_kib`, `ram_end_kib` |
| As regiões e as caches concordam com o `config_pkg`, e uma cache exige a memória dela no barramento | `rom_external`, `ram_external`, `has_icache` |
| A tabela de janelas é alinhada, de máscara contígua e sem sobreposição | `periph_bases`, `periph_masks`, `periph_count` |
| A FLASH e a RAM no barramento cabem nas janelas das caches | `cache_window_bits`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib` |
| Cada cache existente tem tamanho em potência de dois de pelo menos 256 bits | `icache_size_bits`, `dcache_size_bits` |
| As opções de uma cache só valem com ela | `has_dcache_bypass` exige `HAS_DCACHE` do `config_pkg`, `fast_icache_select` exige `has_icache` |
| A polaridade dos pinos da UART só vale no papel de pinos | `uart_tx_invert` e `uart_rx_invert` exigem `has_uart_pins` |
| Um periférico presente tem índice dentro da tabela, e dois não dividem o mesmo índice | `clint_index`, `plic_index`, `timer_index`, `switches_index`, `keys_index`, `display_index`, `uart_jtag_index`, `uart_pins_index`, `flash_ctrl_index` |

A coerência entre as extensões (os contadores exigem Zicsr, as interrupções e o Sscofpmf exigem Zicsr) é conferida pelo `config_pkg`, que o `riscv-tools generate-config-pkg` gera do `platform.yaml`.

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
