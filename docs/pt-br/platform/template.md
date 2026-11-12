# Plataforma `template`: a plataforma modelo

## 1. O que ela é

A menor plataforma de simulação do repositório (`src/simulation/template/`): o núcleo no perfil `rv32i`, a BOOT_MEMORY, a ROM e a RAM de simulação dentro do chip e, opcionalmente, uma UART sobre JTAG. É o ponto de partida do guia de nova arquitetura, que a copia para `src/<família>/<plataforma>/`, e o CI a mantém compilando e executando um programa mínimo.

## 2. Mapa de memória

O mapa está em `src/simulation/template/platform.yaml`, a fonte de todo valor, e `riscv-tools generate-memory-map` o leva ao pacote VHDL, ao arquivo de specs do linker, ao script da BOOT_MEMORY e ao cabeçalho do runtime.

| Região | Início | Tamanho | Tipo |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | ROM executável |
| ROM | `0x00001000` | 28 KiB | ROM executável |
| RAM | `0x00008000` | 32 KiB | RAM |
| UART sobre JTAG (opcional) | `0xC0000000` | janela de 256 MiB | periférico |

Os 1032 bytes do `stdout`, o `tohost` e o `fromhost` ocupam o topo da RAM, de `0x0000FBE0` a `0x00010000`.

## 3. Arquivos

| Arquivo | Conteúdo |
| :--- | :--- |
| `platform.yaml` | Mapa de memória, perfil do núcleo, palavras reservadas e arquivos gerados |
| `config.yaml` | Configuração do `riscv-tools` para compilar e simular: toolchain, runtime, fontes VHDL e módulo de teste |
| `rtl/template_map_pkg.vhd` | Pacote de constantes gerado do `platform.yaml` (não se edita à mão) |
| `rtl/template_sim_top.vhd` | Topo de simulação, que só liga o gerador de clock, o núcleo, as memórias e a UART |
| `runtime/boot_memory.S` | Carregador fixo da BOOT_MEMORY e rotina `rv32_wait_restart` |
| `runtime/_exit.c` | Fim do programa, que informa o resultado em `tohost` |
| `runtime/stdio.c` | Saída padrão num buffer da RAM |
| `runtime/spike_exit.S` | Substituto de `rv32_wait_restart` para o ELF do Spike |
| `runtime/rv32im-fpga.specs`, `runtime/boot_memory.ld`, `runtime/memory_map.h` | Gerados do `platform.yaml` |

## 4. O topo

`template_sim_top` tem os genéricos de arquivo (`boot_memory_file`, `rom_file`, `ram_file`), os de tamanho (`boot_memory_size_bytes`, `rom_size_bytes`, `ram_size_bytes`, potências de dois cujo padrão vem do pacote do mapa) e `has_uart`. O núcleo lê as extensões do `config_pkg` gerado da plataforma, então o topo não declara genérico de extensão.

| Porta | Uso |
| :--- | :--- |
| `i_clk`, `i_rst` | Clock base e reset ativo em `'1'` |
| `i_uart_tck`, `i_uart_tdi`, `o_uart_tdo`, `i_uart_ir`, `i_uart_cdr`, `i_uart_sdr`, `i_uart_udr`, `i_uart_uir` | Lado do hospedeiro da UART sobre JTAG, ignorado quando `has_uart` é falso |

O testbench observa o barramento da RAM do núcleo (`ram_en`, `ram_wren`, `ram_addr`, `ram_wdata`, `ram_byteena`) e o `tohost`, como nas outras plataformas.

## 5. Verificação

`tests/python/runner.py TemplateSimTop` executa o programa mínimo: guarda `0x5A` na base da RAM, lê de volta, soma 1 e guarda o resultado na palavra seguinte. As imagens `boot_to_rom.hex` e `rom_program.hex` são geradas por `tests/python/gen_template_images.py`. O `make check-tops` elabora o topo com os submódulos fixados, e `make memory-map` confere os arquivos gerados contra o `platform.yaml`.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
