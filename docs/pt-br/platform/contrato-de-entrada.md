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
| Contador de programa | `boot.entry`; na `de0-cv`, o início do programa da banca escolhida (seção 6.6) |
| Interrupções | Desligadas, porque a BOOT_ROM não escreve nenhum CSR e vale o valor de reset de `mstatus`, `mie` e `mip` |
| CSRs | Todos com o valor de reset |
| Cache de instruções | Sem linhas do programa anterior, pelo `fence.i` executado antes do salto |
| Palavras compartilhadas no topo da RAM (`stdout`, `tohost` e `fromhost`) | Zeradas |
| Restante da RAM | Indefinido |
| `x0` | `0`, sempre |
| `a0` | `0`, o identificador do hart |
| `a1` | `0` |
| Demais registradores (`x1` a `x31`) | Indefinidos, inclusive `sp`, `gp` e `tp` |

Os registradores de entrada seguem a convenção de RISC-V. `a0` leva o identificador do hart, sempre `0` porque o núcleo tem um único hart, e `a1` leva `0` no lugar do ponteiro para a descrição da plataforma, que o firmware obtém em tempo de compilação (seção 4). Um firmware que não precisa deles os ignora, e `sp`, `gp` e `tp` continuam por conta dele.

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

`boot.entry` é o único valor que a BOOT_ROM e o linker do firmware repetem. A BOOT_ROM o lê de `RV32_BOOT_ENTRY` e o linker o recebe do `rv32im-fpga.specs`, ambos gerados do mesmo `platform.yaml`, e o `riscv-tools check-memory-map` confere que as cópias escritas à mão coincidem com ele. Na `de0-cv` a BOOT_ROM lê, no lugar dele, a base, o tamanho e o início do programa de cada banca em `flash_banks.h`, e o linker de cada banca recebe o `rv32im-fpga-bank-a.specs` ou o `rv32im-fpga-bank-b.specs`, todos gerados das mesmas `flash.banks`.

## 6. Como o núcleo chega à FLASH

Há duas políticas de salto, conforme a plataforma tenha ou não bancas na FLASH. Nas plataformas sem bancas o `_reset` da BOOT_ROM salta para `boot.entry` sempre, e a garantia de que a FLASH está completa nesse instante vem do hardware que a escreve e da ordem em que o hospedeiro o usa. Na `de0-cv`, que declara `flash.banks`, a BOOT_ROM confere as duas bancas e só salta para uma imagem válida (seção 6.6). Quanto à escrita da FLASH, existem dois mecanismos.

| Mecanismo | Plataformas | Quem mantém o núcleo fora da FLASH durante a escrita |
| :--- | :--- | :--- |
| Carregador da FLASH | FLASH interna de duas portas, reescrita pela JTAG ([internal-mem](internal-mem.md)) | O hardware: a saída de parada do carregador segura o núcleo em reset |
| Escrita com o núcleo estacionado | Chip de FLASH atrás das caches, escrito pela memória interna do Quartus ([de0-cv](de0-cv.md)) | O protocolo: o núcleo espera no `rv32_wait_restart`, na BOOT_ROM, e só sai quando o hospedeiro escreve `fromhost` |

### 6.1. Partida a frio

1. A FPGA é programada com o `.sof`, que já traz a BOOT_ROM e a imagem inicial da FLASH.
2. Com o PLL travado, o reset do núcleo é solto. O reset do núcleo é a combinação do PLL destravado, do botão da placa e, onde há carregador, da saída de parada dele.
3. O carregador sai do reset com a parada desligada, então o núcleo não fica retido.
4. O núcleo busca o endereço `0x0`, executa o `_reset`, zera `fromhost`, `tohost` e o cabeçalho do `stdout`, executa `fence.i` onde há caches e salta para `boot.entry`.
5. O que o núcleo encontra em `boot.entry` é a imagem inicial do `.sof`. Na `internal-mem` é um programa de teste. Na `de0-cv` a FLASH inicial não tem cabeçalho de imagem válido, então a BOOT_ROM não salta para banca nenhuma e estaciona o núcleo no `rv32_wait_restart` até o hospedeiro gravar uma imagem.

Nas plataformas sem bancas nenhuma etapa da partida a frio confere a FLASH antes do salto. Na `de0-cv` a etapa 4 inclui a escolha da banca.

### 6.2. Troca de teste com o carregador da FLASH

1. O hospedeiro zera `tohost` pela porta de acesso à RAM, para não confundir o resultado do teste anterior com o do novo.
2. Envia o comando de parada. A saída de parada sobe, o núcleo entra em reset onde quer que estivesse, e a porta B da FLASH passa a ser do carregador.
3. Posiciona o cursor e envia a imagem em uma varredura do `STREAM`. A escrita só chega à memória com o núcleo parado.
4. Lê a contagem e a soma de verificação do carregador e compara com as da imagem. Se diferirem, a troca é abortada e o núcleo continua parado.
5. Envia o comando de liberação. O reset do núcleo cai, e o núcleo parte do endereço `0x0`.
6. O `_reset` zera as palavras compartilhadas e salta para `boot.entry`, que agora é a imagem completa e conferida.

O hospedeiro não escreve `fromhost` nesse caminho. O reinício vem da liberação do reset, e não do laço do `rv32_wait_restart`.

### 6.3. Troca de teste com o núcleo estacionado

1. O hospedeiro zera `tohost` pela porta de depuração da SDRAM.
2. Escreve a imagem da FLASH pela memória interna do Quartus. O núcleo está no laço do `rv32_wait_restart`, que fica na BOOT_ROM, sem cache, e por isso não executa nada da FLASH que está sendo reescrita.
3. Escreve um valor diferente de zero em `fromhost`.
4. O laço lê `fromhost`, sai e salta para o `_reset`, que zera as palavras compartilhadas, executa `fence.i` para descartar as linhas do programa anterior e salta para `boot.entry`, ou, na `de0-cv`, para a banca que a seção 6.6 escolhe.

### 6.4. Fim de teste

1. O programa escreve o resultado em `tohost` (`1` para sucesso, `(código << 1) | 1` para falha).
2. Salta para o `rv32_wait_restart`, que fica na BOOT_ROM e por isso nunca é reescrito.
3. O hospedeiro lê `tohost` em intervalos e, ao ver o bit 0 em `1`, registra o veredito.
4. O núcleo permanece no laço até a próxima troca. Com o carregador, a parada seguinte o tira do laço pelo reset. Com o núcleo estacionado, é o `fromhost` que o tira.

### 6.5. Garantias de hardware

| Garantia | Carregador da FLASH | Chip de FLASH com caches |
| :--- | :--- | :--- |
| Escrita na FLASH com o núcleo executando | Impossível: a habilitação de escrita da porta B é o pulso do carregador combinado com o estado de parada, e um pedido de escrita ou de leitura fora da parada é recusado e sinalizado no status | Não é impedida pelo hardware; vale o protocolo do núcleo estacionado |
| Núcleo executando a FLASH enquanto ela é escrita | Não: o núcleo está em reset | Não, desde que esteja no `rv32_wait_restart`; o hospedeiro precisa esperar o fim do teste anterior |
| Imagem conferida antes da execução | Contagem e soma de verificação lidas do carregador antes da liberação, a cargo do hospedeiro | A BOOT_ROM confere o CRC-32 de cada banca antes do salto (seção 6.6) |
| Linhas de cache do programa anterior | A plataforma não tem cache de instruções, e o reset do núcleo reinicia as caches que houver | O `fence.i` do `_reset` as descarta |
| Estado do restante da plataforma na troca | A RAM e os periféricos mantêm o conteúdo, e só as palavras compartilhadas são zeradas pelo `_reset` | O mesmo |
| Efeito do botão de reset | Reinicia o núcleo pelo `_reset` com a FLASH que estiver gravada. O carregador não é reiniciado pelo botão, então uma parada em curso continua | Reinicia o núcleo pelo `_reset` com a FLASH que estiver gravada |

### 6.6. Escolha da banca na `de0-cv`

A BOOT_ROM lê o cabeçalho de 256 bytes no início de cada banca, no formato do módulo `flash_image` do Tools.

| Deslocamento | Campo | Conteúdo |
| ---: | :--- | :--- |
| 0 | Magia | `0x52564946` |
| 4 | Tamanho | Bytes da carga, múltiplo de 4 e dentro da banca |
| 8 | CRC da carga | CRC-32 (IEEE 802.3) da carga |
| 12 | Versão | A imagem mais nova tem a versão maior |
| 16 | CRC do cabeçalho | CRC-32 dos primeiros 16 bytes do cabeçalho |

Uma banca vale quando a magia confere, o CRC do cabeçalho confere, o tamanho é um múltiplo de 4 diferente de zero que cabe na banca e o CRC-32 da carga lida da FLASH confere. A escolha segue três regras.

1. Salta para a banca válida de maior versão, e a banca A vence um empate.
2. Uma banca que não vale é ignorada, então uma atualização que falhou deixa o sistema na outra banca.
3. Sem banca válida, a BOOT_ROM estaciona o núcleo no `rv32_wait_restart`, onde o hospedeiro pode gravar uma imagem e escrever `fromhost` para recomeçar.

O salto entrega ao firmware o estado da seção 2, com `a0` e `a1` em `0`, e o endereço é o início do programa da banca, `base + 0x100`. A atualização grava o cabeçalho por último, de modo que uma banca interrompida no meio da gravação nunca vale, e o CRC-32 da carga também recusa uma banca corrompida depois de gravada.

A conferência é um CRC-32 bit a bit, sem tabela e sem pilha, sobre uma palavra de 32 bits por vez, com os 32 passos de bit desenrolados em sequência (a BOOT_ROM só busca instrução, então não há tabela a ler). A BOOT_ROM executa cerca de 166 instruções por palavra da carga, com um único desvio tomado por palavra, o que dá cerca de 0,11 s para uma banca de 128 KiB cheia a 50 MHz, e o código inteiro, junto do `_reset` e do `rv32_wait_restart`, são 940 bytes de instruções que terminam no endereço `0x480` dos 4 KiB. Ela usa só os registradores do RV32E, e `sp`, `gp` e `tp` servem de rascunho porque o `_start` do programa os inicializa.

## 7. Recomeço pelo ambiente de teste

O `rv32_wait_restart`, fixo em `boot.wait_restart` (`0x100`), é a rotina em que um programa de teste termina: ela para o núcleo até o hospedeiro regravar a FLASH e escrever `fromhost`, e então recomeça em `_reset`. Ela pertence ao ambiente de teste, e um firmware que não é programa de teste não a referencia. O protocolo completo está em [atualizacao-de-programa.md](atualizacao-de-programa.md).

## 8. Plataformas

O mesmo contrato de estado e de registradores vale em todas as plataformas, e só mudam os valores que vêm do `platform.yaml`. A escolha da banca da seção 6.6 existe onde o `platform.yaml` declara `flash.banks`.

| Plataforma | `boot.entry` | Região do firmware |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `0x1000` | FLASH, 252 KiB |
| [internal-mem](internal-mem.md) | `0x1000` | FLASH, 28 KiB |
| [modular](modular.md) | `0x1000` | Conforme o modelo de memória escolhido |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
