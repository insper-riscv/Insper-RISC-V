# Linha de base de tempo e de ciclos por instrução da plataforma `de0-cv`

🌐 [Português](README.md) · [English](../../../en/platform/timing/README.md)

## 1. Escopo

Este documento registra a medição da plataforma `de0-cv` com o perfil `rv32im_zicclsm_zicntr_zihpm_zifencei` (29 contadores de eventos de 64 bits) antes de qualquer passo estrutural da frente de 100 MHz. Ele traz a Fmax e os caminhos críticos do bitstream (seção 3), os ciclos por instrução dos programas de referência em simulação (seção 4) e a revisão dos cruzamentos de domínio e do `.sdc` (seção 5). A referência para o critério de fechamento a 100 MHz é o pior cenário do Quartus (modelo lento a 85 °C no setup, modelo rápido a 0 °C no hold), registrado como o pior das sementes 1 a 5.

## 2. Condições da medição

| Item | Valor |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, na workstation PC1 |
| Dispositivo | 5CEBA4F23C7 (Cyclone V) |
| Fontes | Insper-RISC-V `4daff3e`, Core `a5f6920`, Memory `743f095`, Peripherals `f773791`, Common-Components `ddbfdcb` |
| Topo e projeto | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, `.sdc` da seção 5 |
| Modo | `HIGH PERFORMANCE EFFORT`, sementes 1 a 5, pelo `de0-cv_synth.tcl` |
| Relógios a 50 MHz | PLL como versionada (núcleo e busca em 50 MHz, fase do núcleo 6625 ps, controlador e `DRAM_CLK` em 142,857 MHz) |
| Relógios a 100 MHz | Mesma PLL com as saídas 2 e 3 em 100 MHz e a fase do núcleo em 3125 ps; só a cópia de trabalho do Quartus muda, o repositório não |
| Contagem do tick do `time` | 50 ciclos nas duas compilações, o que não altera o tempo |

Os resumos por domínio de cada semente estão em `dados/<frequência>-semente-<n>.resumo.txt` (o `.sta.summary` do Quartus), e o relatório completo da semente de pior resultado de cada frequência está em `dados/50mhz-semente-2.relatorio.txt` e `dados/100mhz-semente-2.relatorio.txt` (o `.sta.rpt` do Quartus). O roteiro `dados/pares-de-dominios.tcl` extrai os caminhos por par de relógios de origem e de destino.

## 3. Fmax e caminho crítico

### 3.1. Folgas por domínio

Os domínios são o do núcleo (relógio `clk_idexmem`), o de busca (`clk_if`), o do controlador da SDRAM (142,857 MHz), o `DRAM_CLK` e o JTAG. A tabela dá a folga de setup no modelo lento a 85 °C (ns) em cada semente e o pior valor das cinco.

| Relógio do núcleo | Domínio | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 MHz | Núcleo | -1,103 | -1,604 | -0,224 | -0,388 | -0,783 | -1,604 |
| 50 MHz | Busca | 4,743 | 5,233 | 4,327 | 4,636 | 3,649 | 3,649 |
| 50 MHz | Controlador da SDRAM | -0,745 | -0,255 | -0,205 | -0,173 | -0,713 | -0,745 |
| 50 MHz | `DRAM_CLK` | 0,429 | -0,127 | -0,046 | -0,078 | 0,394 | -0,127 |
| 50 MHz | JTAG | 10,814 | 9,048 | 10,578 | 10,455 | 9,746 | 9,048 |
| 100 MHz | Núcleo | -5,022 | -5,848 | -4,058 | -4,816 | -3,713 | -5,848 |
| 100 MHz | Busca | -0,453 | 0,016 | -1,051 | -1,036 | -0,264 | -1,051 |
| 100 MHz | Controlador da SDRAM | -0,744 | -0,220 | -0,205 | -0,173 | -0,713 | -0,744 |
| 100 MHz | `DRAM_CLK` | 0,428 | -0,162 | -0,046 | -0,078 | 0,394 | -0,162 |
| 100 MHz | JTAG | 10,215 | 10,647 | 10,661 | 10,781 | 10,459 | 10,215 |

A folga de hold no modelo rápido a 0 °C é positiva em todos os domínios e sementes. O pior valor é 0,087 ns (JTAG, 100 MHz, semente 3); no núcleo é 0,121 ns (100 MHz) e 0,132 ns (50 MHz).

A Fmax do domínio do núcleo que o Quartus informa (apenas caminhos entre registradores do mesmo relógio, modelo lento a 85 °C) é a da tabela abaixo.

| Relógio do núcleo | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 50 MHz | 65,73 | 66,92 | 64,30 | 65,98 | 66,15 | 64,30 MHz |
| 100 MHz | 79,35 | 83,14 | 81,73 | 81,40 | 81,32 | 79,35 MHz |

A Fmax sobe com a restrição porque o ajustador trabalha mais quando o relógio pedido é maior. O valor a 50 MHz é o do projeto como entregue (perto de 64 a 67 MHz); o de 100 MHz mostra o que o ajustador consegue do mesmo RTL sob pressão.

### 3.2. Caminhos críticos por par de relógios

A folga que o Quartus atribui a um relógio de destino mistura caminhos entre relógios diferentes, porque a busca e o núcleo têm a mesma frequência com fases distintas. A tabela separa os pares (folga e atraso de dados, em ns, do pior caminho de cada par, modelo lento a 85 °C).

| Relógio do núcleo | Par origem para destino | S1 | S2 | S3 | S4 | S5 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 50 MHz | núcleo para núcleo | 4,787 (15,01) | 5,057 (14,72) | 4,448 (15,28) | 4,844 (15,83) | 4,882 (14,89) |
| 50 MHz | núcleo para busca | 4,743 (8,12) | 5,233 (8,08) | 4,327 (7,96) | 4,636 (7,69) | 3,649 (9,18) |
| 50 MHz | busca para núcleo | -1,103 (5,25) | -1,604 (5,21) | -0,224 (4,85) | -0,388 (5,02) | -0,783 (4,92) |
| 100 MHz | núcleo para núcleo | -2,602 (12,38) | -2,028 (11,85) | -2,236 (12,04) | -2,285 (12,01) | -2,297 (12,09) |
| 100 MHz | núcleo para busca | -0,453 (6,77) | 0,016 (6,79) | -1,051 (6,83) | -1,036 (6,81) | -0,264 (6,60) |
| 100 MHz | busca para núcleo | -5,022 (5,71) | -5,848 (5,94) | -4,058 (5,20) | -4,816 (5,96) | -3,713 (4,35) |

Os três pares correspondem a três laços diferentes.

| Par | Caminho do pior caso | Leitura |
| :--- | :--- | :--- |
| núcleo para núcleo | `EX/MEM r_alu_out` e `EX/MEM r_we_ok` (resultado da ULA e decisão de confirmar a instrução) até o PC, o `IF/ID`, o `mtval`, a escrita da RAM e os registradores `counter64` dos contadores de eventos | Cerca de 12 ns de dados a 100 MHz e 15 ns a 50 MHz. A decisão de exceção e de descarte, tomada em EX com a ULA, chega a todos esses destinos; os contadores são destinos do mesmo sinal, não a origem do atraso |
| busca para núcleo | RAM de tags da cache de instruções (`tag_ram`, no relógio de busca) até o registrador do PC (`u_pc_fetch`, no relógio do núcleo) | 4,4 a 6,0 ns de dados numa janela de 3,125 ns a 100 MHz (6,625 ns a 50 MHz). É o pior caminho do bitstream em todas as sementes |
| núcleo para busca | PC (`u_pc_reg`) até o endereço e o `valid_rd` da cache de instruções | 6,6 a 6,8 ns de dados a 100 MHz numa janela de 6,875 ns |

O laço que passa pela cache de instruções (PC, tag, PC) soma perto de 12 ns de dados (6,8 ns do PC à cache mais 4,4 a 6,0 ns da tag ao PC), então nenhuma fase entre os dois relógios fecha 10 ns. A seção 5.3 mostra a varredura de fase que confirma isso.

### 3.3. Contagem de recursos

| Relógio do núcleo | ALMs (das 18 480) | Registradores | Blocos de RAM |
| :--- | ---: | ---: | ---: |
| 50 MHz | 8 037 a 8 090 (44 %) | 9 142 a 9 241 | 271 de 308 (88 %) |
| 100 MHz | 9 174 a 9 270 (50 %) | 10 769 a 10 852 | 271 de 308 (88 %) |

A diferença de cerca de 1 200 ALMs entre as duas frequências é a duplicação de registradores que o ajustador faz para encurtar os caminhos.

### 3.4. Custo dos contadores de eventos a 100 MHz

A mesma compilação a 100 MHz com `HPM_COUNTERS` em 29, 4 e 0 (largura 64), alterado só no valor padrão do generic da cópia de trabalho, nas sementes 3 e 5.

| Contadores | ALMs (S3 e S5) | Registradores (S3 e S5) | núcleo para núcleo (S3 e S5) | busca para núcleo (S3 e S5) |
| ---: | :--- | :--- | :--- | :--- |
| 29 | 9 270 e 9 174 | 10 769 e 10 784 | -2,236 e -2,297 | -4,058 e -3,713 |
| 4 | 6 263 e 6 259 | 8 143 e 8 180 | -2,218 e -2,193 | -3,669 e -3,975 |
| 0 | 5 872 e 5 836 | 7 534 e 7 537 | -1,953 e -2,091 | -4,232 e -3,802 |

Os 29 contadores custam perto de 3 000 ALMs a mais que 4, e 4 contadores custam perto de 400 ALMs a mais que nenhum. A folga do laço do núcleo varia menos de 0,35 ns entre os três casos, dentro da variação entre sementes, então os contadores não limitam o laço do núcleo; eles aparecem no relatório só como destinos do sinal de confirmação da instrução.

## 4. Ciclos por instrução em simulação

### 4.1. Método

Os programas `cpi-core`, `cpi-data` e `cpi-fetch` (fontes em `dados/programas/`, com o cabeçalho `rv32_cpi.h`) rodam, copiados para `c-sdram/` e `tools/riscv_build/include-sdram/` do repositório Tests, na simulação da `de0-cv` (topo `rv32im_sdram_flash_sim_test`, FLASH de 24 bordas até a primeira palavra e 4 entre as seguintes, caches de 4 KiB com linhas de 16 bytes). Cada kernel roda duas vezes entre leituras de `cycle`, `instret` e de oito contadores de eventos do Zihpm; a primeira passada parte das caches frias e a segunda das caches que a primeira deixou. O custo de uma janela vazia é descontado. As contagens são determinísticas e iguais na placa e na simulação. Os valores brutos estão em `dados/cpi-simulacao.txt`.

Os eventos contados são

| Coluna | Evento | Significado |
| :--- | :--- | :--- |
| e1 | 1 | Ciclos de parada de multiplicação ou divisão |
| e2 | 2 | Ciclos de espera por memória externa |
| e3 | 3 | Desvios ou saltos tomados |
| e5 | 5 | Falhas da cache de instruções |
| e6 | 6 | Falhas da cache de dados |
| e7 | 7 | Ciclos de espera da FLASH |
| e8 | 8 | Ciclos de parada por dependência de load |
| e9 | 9 | Operações de multiplicação ou divisão fundidas |

### 4.2. Resultado

A tabela traz a passada quente, com os eventos dela; as colunas de falhas e de espera da FLASH da passada fria estão em 4.3.

| Kernel | Instruções | Ciclos | CPI | e1 | e2 | e3 | e5 | e6 | e7 | e8 | e9 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `int-loop` (256 voltas de soma, xor e deslocamento) | 1285 | 1805 | 1,40 | 0 | 10 | 255 | 0 | 0 | 8 | 0 | 0 |
| `branches` (256 voltas, metade tomada) | 1157 | 1932 | 1,67 | 0 | 9 | 383 | 0 | 0 | 0 | 0 | 0 |
| `mul` (128 MUL independentes) | 645 | 5388 | 8,35 | 4480 | 9 | 127 | 0 | 0 | 0 | 0 | 0 |
| `mulh-mul-fused` (64 pares MULH, MUL do mesmo operando) | 392 | 2960 | 7,55 | 2432 | 10 | 63 | 0 | 0 | 0 | 0 | 64 |
| `mulh-mul-plain` (64 pares com operandos diferentes) | 458 | 5074 | 11,08 | 4480 | 10 | 63 | 0 | 0 | 0 | 0 | 0 |
| `div-rem-fused` (32 pares DIV, REM do mesmo operando) | 198 | 1550 | 7,83 | 1280 | 10 | 31 | 0 | 0 | 0 | 0 | 32 |
| `div-div-plain` (32 pares DIV, DIV com operandos diferentes) | 231 | 2671 | 11,56 | 2368 | 10 | 31 | 0 | 0 | 0 | 0 | 0 |
| `sdram-load-use` (256 loads de 1 KiB da SDRAM, com uso imediato) | 1029 | 2315 | 2,25 | 0 | 520 | 255 | 0 | 0 | 0 | 256 | 0 |
| `sdram-stream` (2048 loads varrendo 8 KiB da SDRAM) | 8197 | 26705 | 3,26 | 0 | 12366 | 2047 | 0 | 512 | 0 | 2048 | 0 |
| `sdram-store` (256 stores de palavra) | 1283 | 4303 | 3,35 | 0 | 2510 | 255 | 0 | 0 | 0 | 0 | 0 |
| `flash-small` (256 loads de constantes de 1 KiB da FLASH) | 1030 | 2321 | 2,25 | 0 | 525 | 255 | 0 | 0 | 0 | 256 | 0 |
| `flash-stream` (2048 loads varrendo 8 KiB da FLASH) | 8199 | 41997 | 5,12 | 0 | 27656 | 2047 | 0 | 512 | 18432 | 2048 | 0 |
| `fetch-straight` (2048 instruções em linha reta, 8 KiB) | 2048 | 25364 | 12,38 | 0 | -1 | 0 | 519 | 0 | 18682 | 0 | 0 |
| `fetch-loop` (1024 voltas de 4 instruções) | 4097 | 6143 | 1,50 | 0 | 0 | 1023 | 0 | 0 | -2 | 0 | 0 |

Os valores -1 e -2 vêm do desconto da janela vazia e valem zero.

### 4.3. Passada fria

| Kernel | Ciclos frios | CPI frio | e5 | e6 | e7 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `int-loop` | 1894 | 1,47 | 3 | 0 | 88 |
| `branches` | 2137 | 1,85 | 9 | 0 | 324 |
| `mul` | 5558 | 8,62 | 8 | 0 | 288 |
| `mulh-mul-fused` | 3289 | 8,39 | 10 | 0 | 360 |
| `mulh-mul-plain` | 5333 | 11,64 | 11 | 0 | 396 |
| `div-rem-fused` | 1806 | 9,12 | 10 | 0 | 360 |
| `div-div-plain` | 2883 | 12,48 | 10 | 0 | 360 |
| `sdram-load-use` | 3385 | 3,29 | 3 | 64 | 87 |
| `sdram-stream` | 26993 | 3,29 | 8 | 512 | 288 |
| `sdram-store` | 4558 | 3,55 | 7 | 0 | 252 |
| `flash-small` | 5554 | 5,39 | 8 | 64 | 2592 |
| `flash-stream` | 39536 | 4,82 | 8 | 452 | 16560 |
| `fetch-straight` | 25132 | 12,27 | 514 | 0 | 18538 |
| `fetch-loop` | 6347 | 1,55 | 6 | 0 | 214 |

### 4.4. Leitura dos números

| Quantidade | Valor | Como sai |
| :--- | ---: | :--- |
| Penalidade de desvio tomado | 2 ciclos | `int-loop`: (1805 - 1285) / 255 voltas |
| Custo de um MUL | 35 ciclos de parada | `mul`: 4480 / 128 |
| Custo de um par MULH e MUL fundido | 46 ciclos | `mulh-mul-fused`: 2960 / 64; sem fusão são 79 ciclos (`mulh-mul-plain`) |
| Custo de um par DIV e REM fundido | 48 ciclos | `div-rem-fused`: 1550 / 32; sem fusão são 83 ciclos (`div-div-plain`) |
| Load da SDRAM que acerta a cache de dados | 9 ciclos por volta de 4 instruções | `sdram-load-use`: 2315 / 256, com 2 de espera externa, 1 de load-use e 2 de desvio |
| Load da SDRAM que falha a cache de dados | 13 ciclos por load | `sdram-stream`: 26705 / 2048, sendo uma falha a cada quatro loads |
| Load da FLASH que falha a cache de dados | 20,5 ciclos por load | `flash-stream`: 41997 / 2048 |
| Falha de busca na FLASH | cerca de 49 ciclos por linha de quatro instruções | `fetch-straight`: 25364 / 512 linhas, contra 4 ideais |
| Store de palavra na SDRAM | 17 ciclos por volta | `sdram-store`: 4303 / 256, com 10 de espera externa por store (cache write-through) |

A multiplicação e a divisão dominam o CPI dos kernels com elas: o MUL custa 35 ciclos de parada por operação e a fusão reduz o par a cerca de 58 por cento do custo sem fusão (economia de 42 por cento). O critério de aceitação de cada passo estrutural da frente (frequência dividida pelo CPI) usa esta tabela como referência.

## 5. Cruzamentos de domínio e `.sdc`

### 5.1. Cruzamentos do bitstream

O bitstream tem cinco relógios: o do núcleo e o de busca (a mesma frequência, fases distintas), o do controlador da SDRAM, o `DRAM_CLK` e o do JTAG. Os cruzamentos e a restrição de cada um são

| Cruzamento | Mecanismo no RTL | Restrição no `.sdc` | Situação a 100 MHz |
| :--- | :--- | :--- | :--- |
| Núcleo e busca para o controlador, e de volta (ponte da SDRAM) | Toggles de pedido, resposta e inicialização por sincronizador de dois flip-flops; barramentos parados até a resposta | `set_max_delay` de 10 ns e `set_min_delay` de -10 ns nas duas direções | O limite de 10 ns é menor que duas bordas do controlador (14 ns) e do núcleo (20 ns), então vale de 50 a 100 MHz |
| JTAG para o controlador (porta de depuração da SDRAM) | Toggle de comando e flag de inicialização por sincronizador de dois flip-flops | Mesmo par de limites, entre o controlador e o JTAG | Vale |
| Núcleo para o JTAG (UART e display) | Toggle de comando, de resposta e de gravação por sincronizador de dois flip-flops; byte e valor parados até o toggle | Mesmo par de limites, entre o núcleo e o JTAG | Vale |
| Busca para o núcleo e de volta | Mesma frequência com fase fixa; o PC alimenta a cache e a tag volta ao PC | Nenhuma exceção: o Quartus cronometra como caminho síncrono com a diferença de fase | Pior caminho do bitstream (seção 3.2) |
| Controlador para os pinos da SDRAM | Registradores de saída e de entrada do controlador | `set_output_delay`, `set_input_delay` e caminho multiciclo de 2 ciclos no `DRAM_CLK_pin` | Folga de -0,744 a +0,428 ns conforme a semente (100 MHz), no pino `DRAM_DQ` (entrada) e no `o_dram_dq_oe` (saída) |
| Botão de reset | `FPGA_RESET_N` e o travamento da PLL formam `core_reset` | `set_false_path` a partir de `FPGA_RESET_N` | O reset do controlador passa por um sincronizador de dois flip-flops (`rst_sr`); o do núcleo e o da busca usam `core_reset` direto, sem sincronizador de desassert |

O Quartus informa 88 cadeias de sincronização (MTBF acima de 10^9 anos), o que cobre os sincronizadores de dois flip-flops do `Common-Components` e as cadeias do próprio concentrador do JTAG.

### 5.2. Revisão do `.sdc`

O `.sdc` não depende da frequência do núcleo: o único relógio criado é o de 50 MHz da placa, e a PLL derivada traz as demais frequências. A revisão para 100 MHz muda duas coisas.

| Mudança | Motivo |
| :--- | :--- |
| `set_false_path -to` nas saídas `HEX0` a `HEX5` | O registrador do display é escrito pelo núcleo e aciona os pinos direto, sem requisito de tempo; as 42 saídas apareciam sem restrição no relatório |
| Comentário que dá o limite de 10 ns contra a latência dos sincronizadores | Registra que o valor vale de 50 a 100 MHz do núcleo |

Depois da revisão, o relatório de caminhos sem restrição cai de 43 saídas para 1 (o `altera_reserved_tdo` do concentrador do JTAG, do próprio Quartus) e de 173 para 5 caminhos de saída; nenhuma folga muda, porque os caminhos que ganharam a exceção não tinham requisito.

Dois pontos de projeto ficam fora do `.sdc` e valem para a frente de 100 MHz.

| Ponto | Efeito |
| :--- | :--- |
| `tick_cycles` do topo vale 50 | O tick do `time` do Zicntr é de 1 MHz só com o núcleo a 50 MHz; a 100 MHz o valor passa a 100 |
| O reset do núcleo e o da busca não têm sincronizador de desassert | A borda de desassert de `core_reset` vem do botão e do travamento da PLL, sem relação de fase com os relógios do núcleo e da busca; o relatório de metaestabilidade não cobre esse caminho |

### 5.3. Varredura de fase do relógio do núcleo a 100 MHz

A fase do relógio do núcleo em relação ao de busca (passo de 125 ps do VCO de 1000 MHz) reparte os 10 ns entre os caminhos de busca para núcleo e de núcleo para busca. A tabela dá o pior caminho de cada par (folga em ns, modelo lento a 85 °C) para três fases.

| Fase | Semente | núcleo para núcleo | núcleo para busca | busca para núcleo |
| :--- | :--- | ---: | ---: | ---: |
| 3125 ps | 3 | -2,236 | -1,051 | -4,058 |
| 3125 ps | 5 | -2,297 | -0,264 | -3,713 |
| 5000 ps | 3 | -2,002 | -2,862 | -1,939 |
| 5000 ps | 5 | -2,460 | -2,614 | -2,018 |
| 6250 ps | 5 | -2,438 | -3,531 | -1,863 |

Nenhuma fase leva os três pares a folga não negativa. A fase de 5000 ps equilibra os dois cruzamentos em perto de -2 ns, o mesmo valor do laço do próprio núcleo; o fechamento a 100 MHz exige encurtar o laço do núcleo (decisão de exceção em MEM, dado de load registrado) e o laço que passa pela cache de instruções (tag registrada), e não só ajustar a fase.

## 6. Como reproduzir

| Objetivo | Comando |
| :--- | :--- |
| Compilar uma semente | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <semente>`, numa cópia do repositório |
| Mudar a frequência | Editar `output_clock_frequency2`, `output_clock_frequency3` e `phase_shift3` de `src/cyclone-v/de0-cv/pll/sdram_platform_pll.v` na cópia |
| Folga por domínio | `output_files/de0-cv.sta.summary` e `output_files/de0-cv.sta.rpt` |
| Caminhos por registrador | `riscv-tools timing-paths --npaths 300` no projeto compilado |
| Caminhos por par de relógios | `quartus_sta -t docs/pt-br/platform/timing/dados/pares-de-dominios.tcl de0-cv 400 slow` na pasta do projeto compilado |
| Ciclos por instrução | No repositório Tests, depois de copiar `dados/programas/cpi-<nome>.c` para `c-sdram/cpi-<nome>/src.c` e `rv32_cpi.h` para `tools/riscv_build/include-sdram/`, `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit hex` e depois `sim --only cpi-core,cpi-data,cpi-fetch` |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
