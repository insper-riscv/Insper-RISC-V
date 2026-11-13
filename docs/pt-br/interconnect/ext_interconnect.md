# Interconector externo

## 1. O que é

O núcleo conhece só a BOOT_MEMORY, a FLASH e a RAM. Todo acesso de dados fora delas, e todo acesso a uma região que a plataforma liga ao barramento, sai por uma porta externa com handshake de `ready` e de `error`. O interconector atrás dessa porta decide para onde o acesso vai: a memória do barramento, um periférico ou nenhum escravo. Ele decodifica a tabela de janelas da plataforma, e por isso mora neste repositório (`src/interconnect/`) e não no Memory nem no Peripherals, que ele liga sem que um dependa do outro.

| Bloco | Papel |
| :--- | :--- |
| Interconector (`ext_interconnect.vhd`) | Decodifica o endereço e dá ao core o ready, o error e o dado do escravo que respondeu |
| Pacote do interconector (`interconnect_pkg.vhd`) | O tipo `addr_array_t` das tabelas, a tabela padrão de oito janelas e as funções de decodificação que o interconector, o roteador AXI4 e o banco de periféricos compartilham |
| Ponte da SDRAM | O escravo de memória (ver [sdram_debug.md](https://github.com/insper-riscv/Memory/blob/main/docs/pt-br/ram/sdram_debug.md) no Memory para o caminho do hospedeiro até o mesmo chip) |
| UART sobre JTAG | Um periférico, com filas de transmissão e de recepção de 64 bytes e uma instância do Virtual JTAG para o hospedeiro (ver [jtag_uart.md](https://github.com/insper-riscv/Peripherals/blob/main/docs/pt-br/UART/jtag_uart.md) no Peripherals) |

## 2. Mapa de endereços

### 2.1. A tabela de janelas

A plataforma gera, no pacote de mapa (`<plataforma>_map_pkg`), a tabela dos periféricos a partir da lista `peripherals` do `platform.yaml`, em que cada entrada tem `base` e `size`.

| Constante | Significado |
| :--- | :--- |
| `PERIPH_COUNT` | Número de janelas; zero é uma plataforma sem periféricos |
| `PERIPH_BASES` | Base de cada janela, alinhada ao tamanho dela |
| `PERIPH_MASKS` | Máscara de cada janela: um nos bits que a janela fixa, zero nos de dentro dela |
| `STRICT_PERIPH` | O padding de uma janela termina em erro |
| `<NOME>_BASE`, `<NOME>_INDEX` | Base e índice na tabela de cada periférico, na ordem da lista do `platform.yaml` |

O periférico $i$ é acertado por um endereço $a$ quando

$$a \wedge \texttt{PERIPH\_MASKS}(i) = \texttt{PERIPH\_BASES}(i)$$

A janela é a menor potência de dois que contém os registradores, com no mínimo 16 bytes, e os bits `periph_addr_width + 1` a 2 do endereço são o deslocamento de palavra dentro dela (14 bits e 64 KiB no padrão, 20 bits e 4 MiB para o PLIC). O que passa dos registradores dentro da janela é o padding (o SoC passa ao interconector a janela inteira como tamanho, então ele é vazio): com `STRICT_PERIPH` o acesso ao padding terminaria em erro, e sem ele a leitura dá 0 e a escrita não tem efeito.

### 2.2. A decisão por acesso

| O endereço | Escravo | Resposta |
| :--- | :--- | :--- |
| Cai na FLASH (com `flash_on_bus`) ou na RAM (com `ram_on_bus`) | A memória do barramento | O `ready` e o dado da memória |
| Acerta uma janela, dentro dos registradores | O periférico da janela | Um pulso e o `ready` do interconector |
| Acerta uma janela, no padding, com `strict_periph` | Nenhum | `ready` e `error`, leitura 0 |
| Não acerta janela nem memória | Nenhum | `ready` e `error`, leitura 0 |

O `error` sobe junto com o `ready` e fica até `mem_advance`. O núcleo o recebe em `i_ext_error` e gera a falha de acesso de load ou de store (causas 5 e 7), com o endereço em `mtval`.

### 2.3. Os generics

| Generic | Significado |
| :--- | :--- |
| `periph_count` | Número de janelas (natural) |
| `periph_bases`, `periph_masks`, `periph_sizes` | As tabelas de janelas; o SoC deriva `periph_sizes` das máscaras (janela inteira, sem padding) |
| `strict_periph` | O padding termina em erro |
| `periph_addr_width` | Largura do deslocamento de palavra entregue ao periférico |
| `flash_on_bus`, `flash_base`, `flash_last` | A FLASH está no barramento, e o primeiro e o último endereço dela |
| `ram_on_bus`, `ram_base`, `ram_last` | O mesmo para a RAM |

O valor padrão dos generics é a tabela de oito janelas de `0x80000000 | i << 28`, máscara `0xF0000000` e 64 KiB de registradores, e só a RAM em `0x40000000` a `0x43FFFFFF` no barramento: é o que os testes de entidade usam. As portas `p_we` e `p_re` são one-hot pelo índice da tabela, e `p_rdata` guarda uma palavra de `XLEN` bits por índice.

Na `de0-cv` a tabela tem cinco janelas.

| Índice | Base | Periférico |
| ---: | :--- | :--- |
| 0 | `0xB0000000` | Controlador de FLASH |
| 1 | `0xC0000000` | UART sobre JTAG |
| 2 | `0xD0000000` | Display de 7 segmentos |
| 3 | `0xE0000000` | CLINT (`msip`, `mtimecmp` e `mtime`; janela de 64 KiB) |
| 4 | `0xF0000000` | PLIC (janela de 4 MiB; ver [Interrupções da plataforma](../platform/interrupcoes.md)) |

### 2.4. Interrupções de máquina

O CLINT e o PLIC entram como escravos pelo mesmo caminho dos outros periféricos, no domínio de clock do núcleo, sem sincronizador. As três saídas chegam às portas do núcleo.

| Saída | Porta do núcleo | Bit do `mip` |
| :--- | :--- | :--- |
| `o_irq_software` do CLINT (`msip`) | `i_irq_software` | MSIP, bit 3 |
| `o_irq_timer` do CLINT (`mtime >= mtimecmp`) | `i_irq_timer` | MTIP, bit 7 |
| `o_meip` do PLIC | `i_irq_external` | MEIP, bit 11 |

O `mtime` do CLINT é um contador próprio, que soma 1 a cada $\texttt{CLINT\_TICK\_CYCLES} = clock\_hz / mtime\_hz$ ciclos do núcleo e o CSR `time` da Zicntr, que o núcleo atende, é o sombreamento somente leitura dele: a saída `o_mtime` do CLINT chega à porta `i_mtime` do núcleo. A base do CLINT, o `mtime_hz` e o `clock_hz` saem da seção `interrupts` do `platform.yaml`, e nenhum endereço do CLINT é escrito à mão no topo nem no runtime. O núcleo só habilita as interrupções com `has_interrupts` e Zicsr, e as linhas do `EXT_IRQ` ficam em zero enquanto nenhum periférico do topo gera uma.

## 3. O handshake

O core segura o acesso na porta até o `ready`, que fica alto como nível até `mem_advance`.

1. Um acesso à memória passa direto: os strobes de leitura e escrita vão à ponte e o seu `ready` e o seu dado voltam, qualquer que seja o número de ciclos que ela leve.
2. Um acesso a periférico leva um ciclo: o interconector envia um pulso de leitura ou de escrita ao escravo e depois mantém o `ready` alto até `mem_advance`. Um acesso sem escravo leva o mesmo ciclo, sem pulso, e mantém `ready` e `error` altos até `mem_advance`. Um pipeline que continua parado por outro motivo não repete o pulso, então uma leitura que retira um byte de uma fila retira um só.
3. O dado de um load é copiado quando o load avança, e a escolha do escravo é registrada ao mesmo tempo. O acesso seguinte, já na porta enquanto o load está no último estágio, não o perturba.

## 4. A variante AXI4

O `ext_axi_interconnect.vhd` faz a mesma decodificação sobre AXI4: a cache de dados e a ponte mestre do Memory na frente, depois o `axi_router.vhd` e, atrás dele, a ponte escrava da SDRAM do Memory e o `axi_slave_periph_bank.vhd`. As respostas nativas do AXI4 fazem o papel do `error`.

| Bloco | Generics | Comportamento |
| :--- | :--- | :--- |
| `axi_router` | `mem_base`, `mem_last`, `periph_count`, `periph_bases`, `periph_masks` | Envia `mem_base` a `mem_last` à SDRAM e as janelas da tabela aos periféricos; qualquer outro endereço recebe DECERR |
| `axi_slave_periph_bank` | A tabela completa, `strict_periph` e `periph_addr_width` | Sem janela acertada responde DECERR; o padding com `strict_periph` e um beat que não é único, de 4 bytes e alinhado respondem SLVERR; nenhum periférico é tocado nesses casos |
| `ext_axi_interconnect` | Os dois acima e `cache_ctrl_index` | `o_error` sobe junto com o `o_ready` quando o mestre recebe SLVERR ou DECERR; o índice `cache_ctrl_index` da tabela é o controle da própria cache (escrita faz o flush, leitura dá o estado ocupado) e não aparece nos strobes externos |

A cadeia inteira está descrita em [dcache_axi.md](https://github.com/insper-riscv/Memory/blob/main/docs/pt-br/barramento/dcache_axi.md) no Memory.

## 5. Verificação

Os testes rodam aqui, com o barramento do Memory e a UART sobre JTAG do Peripherals juntos (`make test TEST=<nome>`):

| Teste | O que cobre |
| :--- | :--- |
| `ExtBus` | O interconector com a UART sobre JTAG no índice 4 da tabela padrão: bytes em ordem, pipeline parado que retira uma vez, filas cheias, janela sem periférico que lê 0, dado do load que se mantém enquanto o próximo acesso roda, e o `error` de um buraco do mapa e do padding de uma janela |
| `ExtAxiBus` | Os mesmos testes sobre a cadeia AXI4, com uma memória de palavra atrás do escravo da SDRAM |
| `ExtAxiCache` | A cache de dados sobre AXI4: flush, invalidação e o mestre compartilhado com o core |
| `AxiRouter` | O roteador sozinho: os dois escravos, rajadas, W antes de AW e DECERR |
| `AxiSlavePeriphBank` | O banco de periféricos sozinho: um pulso por beat, SLVERR para beat malformado e para o padding, DECERR sem janela |
| `ExtInterconnect` | O interconector sozinho, com a tabela padrão: um pulso por acesso, o `error` de um buraco do mapa e do padding, e o `error` mantido até o avanço |

O defeito achado no roteador pela leitura das regras de handshake está em [ROUTER_W_BEFORE_AW.md](../bugs/ROUTER_W_BEFORE_AW.md).

A prova formal (`formal/ext_interconnect_props.sv`, SymbiYosys sobre a netlist que o GHDL sintetiza, com o método do Core) cobre o interconector sozinho, com a tabela padrão de janelas (oito janelas, `strict_periph` ligado e só a RAM no barramento), o núcleo, a memória e os oito periféricos livres e presos ao contrato por suposições.

| Propriedade | Prova |
| :--- | :--- |
| Um só escravo selecionado por acesso: no máximo um bit de seleção, o da janela que o endereço acerta | Indução |
| Memória e periférico se excluem: só o endereço da memória chega a ela, e o dela não chega a periférico | Indução |
| O endereço, o dado e a máscara passam sem mudar | Indução |
| O pulso ao periférico dura um ciclo, só com o interconector livre, e o acesso termina no ciclo seguinte com a resposta mantida até o avanço (nenhum acesso trava) | Indução |
| O dado lido de um periférico é o do escravo selecionado no pulso, e o da memória vem direto dela | Indução |
| O `error` sobe junto com o `ready` de um acesso sem escravo (fora da memória e de toda janela, ou no padding de uma janela), só nele, dura até o avanço, e a leitura dá 0 | Indução |

Doze defeitos propositais do VHDL (janela decodificada sempre da primeira, pulso sem o estado livre, memória que vê o endereço de periférico, pronto sempre alto, dado do escravo errado, seleção do dado que não volta à memória, escrita que lê, endereço de palavra deslocado, buraco do mapa sem erro, padding tratado como periférico, buraco tratado como memória e erro que não cai no avanço) fazem a prova falhar. O `make formal` roda só esta prova, e o `formal/aggregate.sh` decide o resultado dos engines.

## 6. Avisos são erros

Um aviso do GHDL, do Yosys ou do SymbiYosys indica código fora da norma ou no limite dela, e por isso faz a execução da prova falhar. A correção é no código, na prova ou na netlist, e nenhuma opção `-Wno-*` nem lista de avisos ignorados é permitida.

| Etapa | Onde o aviso é detectado | Efeito |
| :--- | :--- | :--- |
| `ghdl -a` e `ghdl --synth` | Saída de erro do GHDL, lida por `ghdl_run` | O comando falha e imprime cada aviso com o arquivo e a linha do VHDL |
| `sby` de cada prova e de cada mutante | Log completo da prova, lido por `prove` | O veredito vira `error`, mesmo quando o código de saída foi 0 ou 2, e a mensagem aponta `<log>:<linha>` |

Um aviso é uma linha com a palavra `warning` ou `warnings`, em qualquer caixa, como palavra inteira. Nomes que apenas contêm a palavra (`no_warnings.sv`) e o resumo do Yosys com contagem zero (`Warnings: 0 unique messages, 0 total`) não contam. A única exceção são três mensagens do ABC, aceitas só no log do motor `abc-bmc3` (o relógio do módulo de propriedades sem driver, a contagem de bits sem driver e as saídas lidas como restrições), pois a leitura da netlist pelo ABC as produz. Yices, Bitwuzla e Boolector não têm exceção, e qualquer outra mensagem do ABC continua sendo erro.

Duas regras mantêm as netlists sem aviso.

1. Um sinal exposto como `dbg_<sinal>` que o GHDL removeu da netlist (porque um mutante tirou o único leitor) é ligado a zero, nunca deixado sem driver, pois um fio sem driver é livre e podia fazer uma propriedade falhar sem que o defeito fosse a causa.
2. O `ext_interconnect.vhd` é analisado sem nenhum arquivo de submódulo, então nenhum atributo do Quartus chega à netlist. Se uma prova futura precisar de um arquivo com `altera_attribute`, a netlist formal deve ser gerada de uma cópia sem esse atributo.

Os testes da guarda estão em `formal/aggregate_test.sh`, que injeta um aviso no GHDL e no `sby` de uma execução real e exige que ela falhe.
