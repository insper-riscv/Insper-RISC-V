# Interconector externo

## 1. O que é

Todo acesso de dados do core em `0x40000000` ou acima sai por uma porta externa com handshake de `ready`. O interconector atrás dessa porta decide para onde ele vai, para a SDRAM ou para um periférico. Ele decodifica o mapa de endereços da plataforma, e por isso mora neste repositório (`src/interconnect/`) e não no Memory nem no Peripherals, que ele liga sem que um dependa do outro.

| Bloco | Papel |
| :--- | :--- |
| Interconector (`ext_interconnect.vhd`) | Decodifica o endereço e dá ao core o ready e o dado do escravo que respondeu |
| Ponte da SDRAM | O escravo de memória (ver [sdram_debug.md](https://github.com/insper-riscv/Memory/blob/main/docs/pt-br/ram/sdram_debug.md) no Memory para o caminho do hospedeiro até o mesmo chip) |
| UART sobre JTAG | O único periférico hoje, com filas de transmissão e de recepção de 64 bytes e uma instância do Virtual JTAG para o hospedeiro (ver [jtag_uart.md](https://github.com/insper-riscv/Peripherals/blob/main/docs/pt-br/UART/jtag_uart.md) no Peripherals) |

## 2. Mapa de endereços

| Faixa | Escravo |
| :--- | :--- |
| Bit 31 = 0 (a partir de `0x40000000`) | A ponte da SDRAM |
| Bit 31 = 1 | Uma janela de periféricos: os bits 30:28 são o id e os bits 9:2 o deslocamento de palavra dentro da janela |

| Id | Janela | Periférico |
| ---: | :--- | :--- |
| 4 | `0xC0000000` | UART sobre JTAG |
| 0 a 3, 5 a 7 | | Nenhum: uma leitura dá 0, uma escrita não tem efeito e o acesso termina |

## 3. O handshake

O core segura o acesso na porta até o `ready`, que fica alto como nível até `mem_advance`.

1. Um acesso à memória passa direto: os strobes de leitura e escrita vão à ponte e o seu `ready` e o seu dado voltam, qualquer que seja o número de ciclos que ela leve.
2. Um acesso a periférico leva um ciclo: o interconector envia um pulso de leitura ou de escrita ao escravo e depois mantém o `ready` alto até `mem_advance`. Um pipeline que continua parado por outro motivo não repete o pulso, então uma leitura que retira um byte de uma fila retira um só.
3. O dado de um load é copiado quando o load avança, e a escolha do escravo é registrada ao mesmo tempo. O acesso seguinte, já na porta enquanto o load está no último estágio, não o perturba.

## 4. A variante AXI4

O `ext_axi_interconnect.vhd` faz a mesma decodificação sobre AXI4: a cache de dados e a ponte mestre do Memory na frente, depois o `axi_router.vhd` e, atrás dele, a ponte escrava da SDRAM do Memory e o `axi_slave_periph_bank.vhd`. O roteador envia `0x40000000` a `0x43FFFFFF` à SDRAM e `0x80000000` em diante aos periféricos, e responde DECERR em qualquer outro lugar. O banco de periféricos atende oito janelas de 256 palavras, escolhidas pelos bits 30:28. A cadeia inteira está descrita em [dcache_axi.md](https://github.com/insper-riscv/Memory/blob/main/docs/pt-br/barramento/dcache_axi.md) no Memory.

## 5. Verificação

Os testes rodam aqui, com o barramento do Memory e a UART sobre JTAG do Peripherals juntos (`make test TEST=<nome>`):

| Teste | O que cobre |
| :--- | :--- |
| `ExtBus` | O interconector com a UART sobre JTAG no slot de periférico 4: bytes em ordem, pipeline parado que retira uma vez, filas cheias, janela sem mapa que lê 0, dado do load que se mantém enquanto o próximo acesso roda |
| `ExtAxiBus` | Os mesmos testes sobre a cadeia AXI4, com uma memória de palavra atrás do escravo da SDRAM |
| `ExtAxiCache` | A cache de dados sobre AXI4: flush, invalidação e o mestre compartilhado com o core |
| `AxiRouter` | O roteador sozinho: os dois escravos, rajadas, W antes de AW e DECERR |

O defeito achado no roteador pela leitura das regras de handshake está em [ROUTER_W_BEFORE_AW.md](../bugs/ROUTER_W_BEFORE_AW.md).

A prova formal (`formal/ext_interconnect_props.sv`, SymbiYosys sobre a netlist que o GHDL sintetiza, com o método do Core) cobre o interconector sozinho, com o núcleo, a memória e os oito periféricos livres e presos ao contrato por suposições.

| Propriedade | Prova |
| :--- | :--- |
| Um só escravo selecionado por acesso: no máximo um bit de seleção, o do campo de identificação do endereço | Indução |
| Memória e periférico se excluem: o endereço de periférico não chega à memória, e o de memória não chega a periférico | Indução |
| O endereço, o dado e a máscara passam sem mudar | Indução |
| O pulso ao periférico dura um ciclo, só com o interconector livre, e o acesso termina no ciclo seguinte com a resposta mantida até o avanço (nenhum acesso trava) | Indução |
| O dado lido de um periférico é o do escravo selecionado no pulso, e o da memória vem direto dela | Indução |

Oito defeitos propositais do VHDL (identificação do escravo deslocada, pulso sem o estado livre, memória que vê o endereço de periférico, pronto sempre alto, dado do escravo errado, seleção do dado que não volta à memória, escrita que lê e endereço de palavra deslocado) fazem a prova falhar. O `make formal` roda só esta prova, e o `formal/aggregate.sh` decide o resultado dos engines.

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
