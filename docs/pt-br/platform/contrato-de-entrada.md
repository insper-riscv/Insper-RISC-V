# Contrato de entrada da BOOT_ROM com o firmware

A BOOT_ROM acorda a placa e entrega o controle ao firmware sem saber qual firmware está na FLASH. Este documento define o que a BOOT_ROM garante no instante da entrega e o que fica a cargo do firmware, para que um programa em C, em Rust ou em assembly, com o próprio `_start`, suba em qualquer plataforma deste repositório. A sequência do `crt0` da picolibc, usada pelos programas de teste, está em [boot.md](boot.md).

## 1. Papéis

| Papel | Quem | Onde |
| :--- | :--- | :--- |
| Deixar a placa num estado inicial conhecido e saltar para o firmware | `boot_rom.S` | BOOT_ROM, `0x0`, gravada uma vez no bitstream |
| Inicializar o ambiente do programa (pilha, `gp`, `.data`, `.bss`, TLS, construtores) | `_start` do firmware | FLASH, em `boot.entry` |
| Ser a BIOS, o RTOS ou o programa | Firmware | FLASH |

A pilha e o `gp` ficam fora da BOOT_ROM porque um firmware em Rust ou um RTOS traz o próprio `_start` e define a pilha pelo linker dele. Fixar esses valores na ROM obrigaria o firmware a aceitá-los ou sobrescrevê-los.

## 2. Estado garantido na entrada do firmware

O firmware começa a executar no endereço `boot.entry` do `platform.yaml`, com o seguinte estado.

| Item | Estado na entrada |
| :--- | :--- |
| Contador de programa | `boot.entry` |
| Interrupções | Desligadas, porque a BOOT_ROM não escreve nenhum CSR e vale o valor de reset de `mstatus`, `mie` e `mip` |
| CSRs | Todos com o valor de reset |
| Cache de instruções | Sem linhas do programa anterior, pelo `fence.i` executado antes do salto |
| Palavras compartilhadas no topo da RAM (`stdout`, `tohost` e `fromhost`) | Zeradas |
| Restante da RAM | Indefinido |
| `x0` | `0`, sempre |
| Demais registradores (`x1` a `x31`) | Indefinidos, inclusive `sp`, `gp`, `tp`, `a0` e `a1` |

Nenhum registrador de entrada é definido: o firmware não recebe o identificador do hart nem o ponteiro para a descrição da plataforma, pois o núcleo tem um único hart e a descrição é obtida em tempo de compilação (seção 4).

## 3. O que o firmware faz por conta própria

| Responsabilidade | Observação |
| :--- | :--- |
| Definir `sp` e `gp` | Pelos símbolos do próprio linker script, antes de qualquer chamada |
| Copiar `.data` e `.tdata` da FLASH para a RAM e zerar `.bss` | A FLASH é lida pela porta de dados, ver [memoria.md](memoria.md) |
| Preparar o TLS e rodar os construtores | Quando a linguagem os usa |
| Configurar `mtvec` e habilitar interrupções | Só depois de ter uma pilha válida |
| Respeitar as palavras reservadas do topo da RAM | O linker do firmware limita a RAM ao início de `stdout` |

## 4. Descrição da plataforma

A descrição é uma só e vem do `platform.yaml`, a fonte da verdade da plataforma. O `riscv-tools generate-memory-map` a escreve em `memory_map.h` para C e para assembly, com as constantes abaixo, e o firmware inclui esse cabeçalho em vez de copiar endereços à mão.

| Constante | Significado |
| :--- | :--- |
| `RV32_BOOT_ENTRY` | Endereço em que o firmware começa |
| `RV32_RAM_END` | Fim da RAM |
| `RV32_STDOUT_BASE` | Início da região do `stdout`, que é o limite superior da RAM do firmware |
| `RV32_TOHOST_ADDR` e `RV32_FROMHOST_ADDR` | Palavras do protocolo com o hospedeiro de teste |
| `RV32_UART_BASE`, `RV32_DISPLAY_BASE` | Base de cada periférico presente na plataforma |

Não há tabela de descrição na BOOT_ROM: o mapa de memória é fixo por plataforma e conhecido na compilação do firmware.

## 5. Ponto de entrada compartilhado

`boot.entry` é o único valor que a BOOT_ROM e o linker do firmware repetem. A BOOT_ROM o lê de `RV32_BOOT_ENTRY` e o linker o recebe do `rv32im-fpga.specs`, ambos gerados do mesmo `platform.yaml`, e o `riscv-tools check-memory-map` confere que as cópias escritas à mão coincidem com ele.

## 6. Recomeço pelo ambiente de teste

O `rv32_wait_restart`, fixo em `boot.wait_restart` (`0x100`), é a rotina em que um programa de teste termina: ela para o núcleo até o hospedeiro regravar a FLASH e escrever `fromhost`, e então recomeça em `_reset`. Ela pertence ao ambiente de teste, e um firmware que não é programa de teste não a referencia. O protocolo completo está em [atualizacao-de-programa.md](atualizacao-de-programa.md).

## 7. Plataformas

O mesmo contrato vale nas três plataformas, e só mudam os valores que vêm do `platform.yaml`.

| Plataforma | `boot.entry` | Região do firmware |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `0x1000` | FLASH, 252 KiB |
| [internal-mem](internal-mem.md) | `0x1000` | FLASH, 28 KiB |
| [modular](modular.md) | `0x1000` | Conforme o modelo de memória escolhido |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
