# Interrupções da plataforma

🌐 [Português](../../pt-br/platform/interrupcoes.md) · [English](../../en/platform/interrupcoes.md)

## 1. Visão geral

O núcleo recebe três linhas de interrupção de máquina, em nível, no domínio de clock do núcleo e sem sincronizador. Com a extensão Sscofpmf (`extras: [Sscofpmf]`, ligada na `de0-cv`) o núcleo ainda gera, por dentro, a interrupção 13 de estouro de contador (`LCOFIP` no bit 13 do `mip`), que não tem linha externa.

| Linha | Origem | Bit do `mip` |
| :--- | :--- | :--- |
| `MSIP` | `o_irq_software` do CLINT | 3 |
| `MTIP` | `o_irq_timer` do CLINT | 7 |
| `MEIP` | `o_meip` do PLIC | 11 |

Cada periférico que tem eventos de interesse do software expõe uma saída `o_irq` de nível. As saídas são as fontes do PLIC, e o PLIC (`riscv-plic-1.0.0`, um hart, o contexto de modo máquina) entrega ao núcleo um único `MEIP`. O handler lê o registrador de claim, atende e escreve o identificador de volta no mesmo registrador (complete). O PLIC está documentado em `Peripherals/docs/pt-br/PLIC/plic.md`.

## 2. Fontes

O identificador de cada fonte é o mesmo em toda plataforma que a tem. Ele vem da lista `interrupts.sources` do `platform.yaml`, de onde o `generate-memory-map` escreve `IRQ_<NOME>` no pacote VHDL e `RV32_IRQ_<NOME>` no cabeçalho do runtime. O topo modular repete os números nas constantes `LINE_<NOME>`, e `make check-irq-sources` confere os dois lados.

| Id | Nome | Periférico | Plataformas |
| ---: | :--- | :--- | :--- |
| 1 | `UART` | UART serial pelos pinos | `modular` |
| 2 | `UART_JTAG` | UART sobre JTAG | `modular`, `de0-cv` |
| 3 | `SWITCHES` | GPIO das chaves SW | `modular` |
| 4 | `KEYS` | GPIO dos botões KEY | `modular` |
| 5 | `TIMER` | Temporizador de uso geral | `modular` |
| 6 | `FLASH` | Controlador de FLASH | `de0-cv` (topo de simulação) |

## 3. Eventos de cada periférico

A tabela lista todo evento que o software pode querer receber por interrupção, o registrador de status, o de habilitação e como a causa é limpa. Os registradores novos não mudam o mapa dos que já existiam: um bit antes reservado ou um registrador antes sem uso.

| Periférico | Evento | Status | Habilitação | Limpeza |
| :--- | :--- | :--- | :--- | :--- |
| UART serial | Byte recebido | `STATUS.RX_VALID` | `CONTROL.RX_IRQ_ENABLE` (bit 0) | Ler `RX_DATA` até esvaziar |
| UART serial | Transmissor vazio | `STATUS.TX_EMPTY` | `CONTROL.TX_EMPTY_IRQ_ENABLE` (bit 1) | Escrever em `TX_DATA` ou desabilitar |
| UART serial | Erro: overrun de recepção ou descarte de transmissão | `STATUS.RX_OVERRUN`, `STATUS.TX_DROPPED` | `CONTROL.ERROR_IRQ_ENABLE` (bit 2) | Escrever 1 no bit em `STATUS` |
| UART sobre JTAG | Byte recebido | `STATUS` bits 15:8 não nulos | `CONTROL` bit 0 | Ler `RXDATA` até esvaziar |
| UART sobre JTAG | Fila de transmissão vazia (o hospedeiro levou tudo) | `STATUS` bits 7:0 iguais à profundidade | `CONTROL` bit 1 | Escrever em `TXDATA` ou desabilitar |
| UART sobre JTAG | Byte descartado | `STATUS` bit 16 | `CONTROL` bit 2 | Ler `STATUS` |
| GPIO | Borda de subida, de descida ou mudança, por pino | `IRQ_STAT` | `IRQ_MASK` e `RISE_MASK`, `FALL_MASK` | Ler `IRQ_STAT` |
| GPIO | Nível alto ou baixo, por pino | `IRQ_STAT` | `IRQ_MASK`, `LEVEL_MASK` e `RISE_MASK` (alto), `FALL_MASK` (baixo) | Remover o nível ou mascarar o pino, e ler `IRQ_STAT` |
| TIMER | Estouro do contador | `OVF_STATUS` | Bit 3 de `CONFIG` | Ler `OVF_STATUS` |
| Controlador de FLASH | Comando concluído (apagar ou gravar) | `IRQ_STATUS.DONE` | `IRQ_ENABLE` bit 0 | Escrever 1 no bit |
| Controlador de FLASH | Comando recusado | `IRQ_STATUS.REFUSED` | `IRQ_ENABLE` bit 1 | Escrever 1 no bit |
| CLINT | `mtime >= mtimecmp` e `msip` | `mip.MTIP` e `mip.MSIP` | `mie.MTIE`, `mie.MSIE` | Reescrever `mtimecmp`, zerar `msip` |
| Display, SDRAM, caches, pontes, ROM e RAM | Nenhum: não geram evento que o software queira receber | | | |

## 4. Mapa do PLIC

A janela do PLIC é de 4 MiB, na base dada pelo `platform.yaml` (`0xF0000000` nas plataformas atuais), e o tamanho dá a largura do endereço (`PLIC_ADDR_WIDTH`). O `ext_interconnect` entrega ao periférico a quantidade de bits do genérico `periph_addr_width`, que as plataformas com PLIC fixam em `PLIC_ADDR_WIDTH`.

| Registrador | Endereço | Constante do runtime |
| :--- | :--- | :--- |
| Prioridade da fonte $n$ | base $+ 4n$ | `RV32_PLIC_PRIORITY` $+ 4n$ |
| Pendentes | base $+ \texttt{0x1000}$ | `RV32_PLIC_PENDING` |
| Habilitação do contexto 0 | base $+ \texttt{0x2000}$ | `RV32_PLIC_ENABLE` |
| Limiar | base $+ \texttt{0x200000}$ | `RV32_PLIC_THRESHOLD` |
| Claim e complete | base $+ \texttt{0x200004}$ | `RV32_PLIC_CLAIM` |

## 5. Verificação

Cada periférico tem teste de entidade e prova formal do que a interrupção acrescenta (documentos de cada periférico no repositório Peripherals). Os programas de `asm-plic/` do repositório Tests exercitam, na plataforma `modular` simulada, cada fonte de ponta a ponta: habilitam a causa no periférico e no PLIC, provocam o evento, entram no handler, fazem claim, tratam, completam e conferem; um programa à parte confere prioridade, desempate, limiar e prioridade zero com duas fontes.
