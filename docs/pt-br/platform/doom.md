# Plataforma `doom`: a DE0-CV com o código na SDRAM e o vídeo em 4:3

## 1. O que ela é

A plataforma `doom` é a `de0-cv` ajustada para rodar o DOOM (porta `doomgeneric`, cerca de 540 KiB com o código, as constantes e os dados iniciais). O núcleo guarda só a BOOT_MEMORY. O chip de SDRAM da placa (64 MB, um controlador) é dividido em duas janelas, a FLASH (as instruções e as constantes, 4 MiB no topo do chip, somente leitura para o núcleo) e a RAM (os dados, 60 MiB desde o começo do chip), ambas atrás da cache de instruções e da cache de dados. Não há FLASH emulada em blocos M10K, controlador de FLASH nem carregador: o hospedeiro grava a imagem na janela da FLASH pela porta de depuração da SDRAM (`riscv-tools load-flash`) e solta o núcleo, e a BOOT_MEMORY salta para `0x1000`.

A organização das duas janelas é a da plataforma [de0-cv](de0-cv.md). Esta página descreve o que a `doom` muda: o mapa, os relógios, o vídeo, o cartão SD e os testes.

## 2. Mapa de memória

| Região | Base | Tamanho | Acesso |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Busca e leitura, direto, sem cache |
| FLASH (`type: sdram`) | `0x00001000` | `0x3FF000` (4 MiB menos 4 KiB) | Busca e leitura pelas caches, somente leitura para o núcleo |
| RAM (`type: sdram`) | `0x40000000` | 60 MiB | Leitura e escrita pelas caches |
| Memória interna da cache de dados | `0x43BE8000` | 32 KiB | Leitura e escrita em dois ciclos, dentro da RAM, sem passar pela SDRAM |
| Periféricos | `0x80000000` | janelas de 256 MB | Leitura e escrita, sem cache |

Dentro do chip de 64 MiB, a RAM começa no byte 0 (`offset: 0`), o que mantém os endereços de chip que a WAD e o bloco de medição sempre tiveram, e a FLASH começa no byte `0x3C01000` (`offset`), isto é, 60 MiB mais a base `0x1000`. Os 4 KiB do topo da RAM (`0x43BFF000` a `0x43BFFFFF`), que a cache de dados ignora, guardam as palavras compartilhadas com o hospedeiro.

| Palavra | Endereço | Uso |
| :--- | :--- | :--- |
| `stdout` | `0x43BFFBE0` | Cabeçalho e buffer da saída do programa (1 KiB mais 8 bytes) |
| `tohost` | `0x43BFFFE8` | Fim do programa (protocolo HTIF) |
| `fromhost` | `0x43BFFFF0` | Reinício pelo hospedeiro |

A BOOT_MEMORY zera `stdout`, `tohost` e `fromhost` a cada reset.

## 3. Como o código executa

A BOOT_MEMORY é a comum (`base/src/boot/boot_core.S`) e, como a plataforma não tem bancos de FLASH, salta direto para `boot.entry`, `0x1000`, onde está o `_start` do DOOM. O binário é ligado com duas regiões: a ROM em `0x1000` (`.init`, `.text`, `.rodata` e os valores iniciais de `.data`) e a RAM em `0x40000000` (`.data`, `.bss`, a pilha e o heap), e o `crt0` da picolibc copia os valores iniciais de uma para a outra.

| Passo | Operação |
| :--- | :--- |
| 1 | Gerar a imagem plana, a partir de `0x1000` (`doom.bin`) |
| 2 | `riscv-tools --root . load-flash --platform src/cyclone-v/doom/platform.yaml --image doom.bin --address 0x1000` |
| 3 | O comando prende o núcleo, grava a janela da FLASH, confere o CRC-32 calculado na placa e solta o núcleo |

O descritor do comando está em `flash_load` e `sdram_windows` do repositório Tools. Uma reconfiguração do FPGA apaga a SDRAM, e a imagem é gravada de novo depois dela; o botão de reset da placa reinicia só o núcleo e preserva a FLASH. As WADs do jogo não ficam na SDRAM de partida: a porta lê o cartão microSD (seção 7.7).

## 4. Relógios e fechamento do tempo

O `platform.yaml` declara os relógios do PLL gerado.

| Relógio | Frequência | Fase | Saída do PLL |
| :--- | ---: | ---: | :--- |
| `core` | 100 MHz | 0 | uma só, compartilhada com `fetch` |
| `fetch` | 100 MHz | 0 | a do `core` |
| `mem` | 125 MHz | 0 | própria, sem fusão com o `core` |

Com `fetch` igual a `core` em frequência e fase, o gerador liga o generic `early_fetch_addr` do SoC. As memórias de instrução (a BOOT_MEMORY e a cache de instruções) passam a ler, na borda do clock do núcleo, o endereço que o PC terá no ciclo seguinte, e o laço do PC até a cache é feito de ciclos inteiros, sem depender da fase de um clock adiantado. O alvo de um desvio tomado, de um salto ou de uma exceção chega um ciclo depois, e o `fast_icache_select` é pré-requisito. O `mem` fica numa saída própria do PLL porque o Quartus funde saídas de mesma frequência e fase, e o `.sdc` gerado trataria o cruzamento entre `mem` e `core` como assíncrono, escondendo o caminho real da cache de instruções até o núcleo.

Medido na DE0-CV com o `.sof` final (Quartus Prime Lite 25.1, semente 6):

| Item | Valor |
| :--- | ---: |
| Folga de setup do domínio do núcleo (100 MHz) | +0,090 ns |
| Folga de setup do domínio da memória (125 MHz) | +0,806 ns |
| Folga de hold | positiva em todos os cantos |

O multiplicador usa blocos DSP em três ciclos (Core, `dsp_multiplier_rv32`), o que tira do caminho crítico o multiplicador de Booth em lógica.

## 5. Relógio do jogo

A porta `doomgeneric` pede o tempo em milissegundos por `DG_GetTicksMs`, que o runtime da plataforma (`runtime/doom_clock.c`) fornece a partir do CSR `time` do Zicntr.

| Item | Valor |
| :--- | :--- |
| Origem do `time` | `mtime` do CLINT, espelhado pelo núcleo |
| Ciclos do núcleo por tick | 100 (`CLINT_TICK_CYCLES`) |
| Clock do núcleo | 100 MHz |
| Ticks por segundo reais | $100 \cdot 10^{6} / 100 = 1\,000\,000$ |
| Ticks por segundo nominais (`mtime_hz`) | 1.000.000 |

O relógio converte com o valor nominal, que coincide com a taxa real do contador.

A conversão evita a instrução `div` (CPI de cerca de 11) e a divisão de 64 bits. A cada leitura, o relógio soma ao total o avanço dos 32 bits baixos do `time`, calculado por subtração sem sinal (certa mesmo quando o contador passa de $2^{32}$ para 0), e divide por 1000 por uma multiplicação:

$$\left\lfloor \frac{x}{1000} \right\rfloor = \left\lfloor \frac{x \cdot \mathtt{0x10624DD3}}{2^{38}} \right\rfloor \quad \forall\, x < 2^{32}$$

O compilador a faz com um `mulhu`, e o objeto gerado não tem `div`, `rem` nem chamada. O resto de menos de 1000 ticks passa de uma leitura para a seguinte, então nenhum tick se perde. O relógio devolve os milissegundos desde a primeira chamada, que devolve zero. Ele perde tempo só se duas chamadas ficarem mais de $2^{32}$ ticks (71,6 minutos) afastadas, o que um jogo que consulta o tempo a cada tic não faz. Se o `mtime_hz` da plataforma mudar, o inverso deixa de valer e a compilação falha por uma asserção estática.

O teste `tests/c/doom_clock/src.c` confere a conversão contra a conta em 64 bits em 4000 avanços de tamanho variado (inclusive a passagem do contador por 0 e o avanço máximo de 32 bits) e a ausência de retrocesso do `time` real.

```bash
riscv-tools --root . --config tests/c/config.yaml compile --emit mif
riscv-tools --root . --config tests/c/config.yaml spike-run
riscv-tools --root . --config tests/c/config.yaml compile --emit hex
riscv-tools --root . --config tests/c/config.yaml sim
```

O Spike do `spike-run` roda sem CLINT, e nele o `time` fica em zero; o avanço do `time` real é conferido na simulação da plataforma (`sim`), onde o `time` espelha o `mtime` do CLINT.


## 6. Teste do topo de simulação

O catálogo `tests/python/tests.json` traz as entradas `DoomSimTop` e `DoomSimTopStaggered`, que rodam o topo `doom_sim_test` com a BOOT_MEMORY de verdade (`boot_memory.S`), a mesma que a placa usa. O topo tem as janelas da FLASH e da RAM no mesmo modelo de chip de SDRAM, nos deslocamentos dados pelos generics `flash_chip_offset_bytes` e `ram_chip_offset_bytes` (os do `platform.yaml` por padrão). A entrada `DoomSimTop` liga `early_fetch`, que é o que o topo gerado da placa faz, e `DoomSimTopStaggered` roda o clock de busca adiantado.

| Entrada | Imagem do chip no tempo zero | Resultado conferido |
| :--- | :--- | :--- |
| `DoomSimTop` | Programa de teste na base da FLASH | A BOOT_MEMORY salta para ele, ele guarda a marca `0xD00D` na RAM e escreve `tohost` |
| `DoomSimTopStaggered` | A mesma, com o clock de busca adiantado | O mesmo resultado |

Para a imagem ser pequena, o teste põe a FLASH no byte `0x1000` do chip e a RAM no byte `0x10000`, e usa só o começo das duas janelas; o clock da SDRAM do teste tem o período do `clocks.mem` (8 ns), que o topo usa nos tempos de refresh do chip. As imagens saem de `tests/python/gen_doom_images.py`, e `--check` confere que estão em dia. As entradas `DoomSimVideo` e `DoomSimKeyboard` rodam o mesmo topo com os programas das seções 7.4 e 7.5.

## 7. Vídeo e teclado

### 7.1. Periféricos e endereços

O `platform.yaml` lista três periféricos externos, que o topo gerado da placa instancia ao lado do SoC e o topo de simulação `doom_sim_test` instancia nas mesmas janelas.

| Periférico | `kind` | Base | Janela | Interrupção | Pinos da DE0-CV |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `VIDEO` | `video` | `0x80100000` | 256 KiB | nenhuma | `VGA_R[3:0]`, `VGA_G[3:0]`, `VGA_B[3:0]`, `VGA_HS`, `VGA_VS` |
| `KBD` | `ps2` (`device: keyboard`) | `0x80007000` | 16 bytes | linha 5 do PLIC (`IRQ_KBD`) | `PS2_CLK` (D3), `PS2_DAT` (G2) |
| `SD` | `sd_native` | `0x80008000` | 4 KiB | linha 7 do PLIC (`IRQ_SD`), não usada | `SD_CLK`, `SD_CMD`, `SD_DATA[3:0]` |

O segundo canal do cabo Y (`PS2_CLK2` em E2 e `PS2_DAT2` em G1) pertence a um mouse, que entra como mais uma entrada de `peripherals` (`MOUSE: {kind: ps2, device: mouse, base: 0x80007100}`). O mapa gerado (`memory_map.h` e `doom_map_pkg.vhd`) traz `RV32_VIDEO_BASE`, `RV32_KBD_BASE`, `RV32_SD_BASE`, `RV32_IRQ_KBD` e `RV32_IRQ_SD`.

### 7.2. Vídeo indexado em 4:3

O `io.video` do `platform.yaml` pede um framebuffer indexado de 320x200 (8 bits por pixel e uma paleta de 256 entradas de 12 bits, a largura do conversor da DE0-CV), ampliado duas vezes na horizontal (`scale: 2`) e por 12/5 na vertical (`scale_y: 12/5`). O modo é o padrão da placa, 640x480 a 60 Hz com clock de pixel de 25 MHz, e a imagem de 640x480 preenche a tela inteira em 4:3, sem as faixas pretas de 40 linhas que a ampliação 2x2 deixava.

A linha de origem da linha exibida $n$ é

$$\mathrm{src}(n)=\left\lfloor \frac{n \cdot 5}{12} \right\rfloor$$

calculada sem divisão por um acumulador de erro. Cada grupo de 5 linhas de origem ocupa 12 linhas da tela, repetidas 3, 2, 3, 2 e 2 vezes (média 2,4), de modo que cada pixel de origem ocupa 2 colunas por 2,4 linhas, a razão 1,2 do pixel não quadrado do DOOM. O jogo continua a desenhar 320x200 nos mesmos endereços. Com `v_scale_num` diferente de zero, o registrador 4 do vídeo traz o numerador nos bits 28:25 e o denominador nos bits 31:29.

| Região da janela do vídeo | Deslocamento | Conteúdo |
| :--- | :--- | :--- |
| Registradores | `0x00000` a `0x00010` | Controle, estado, contador de quadros, geometria e formato |
| Paleta | `0x00400` | 256 palavras, a cor nos 12 bits baixos (vermelho nos bits 11:8) |
| Framebuffer | `0x20000` | 16000 palavras, quatro pixels por palavra, o de menor coluna nos bits baixos |

O framebuffer e a paleta só aceitam escrita, e o núcleo os atualiza com `sw`, `sh` ou `sb`. A exibição liga com o bit 0 do registrador de controle. O pacote `Peripherals` documenta o periférico em `docs/pt-br/video/video.md`.

O clock de pixel é uma saída a mais do PLL do topo gerado, e o `.sdc` gerado declara falsos os caminhos entre o domínio do núcleo e o do pixel, porque o vídeo os atravessa só por sincronizadores de dois flip-flops e por memórias com um clock em cada porta.

#### 7.2.1. Bordas do vídeo

O catálogo `boards/video-modes.yaml` tem uma só temporização de 640x480 a 60 Hz (pórtico frontal 16, sincronismo 96 e pórtico traseiro 48 na horizontal), a do manual da DE0-CV, e o `io.video` do `platform.yaml` não tem campo para trocar os pórticos. Um monitor que corta os primeiros 16 pixels de cada linha à esquerda (o caso do monitor da validação na placa) pede `h_front_porch => 0` e `h_back_porch => 64`, com o mesmo total de 800 pixels, no `generic map` do `video` do topo gerado (`doom_de0_cv_top.vhd`). Esse ajuste é feito à mão no topo gerado, antes da compilação do Quartus, porque o gerador do Tools não tem campo para os pórticos.

### 7.3. Recursos

O vídeo sozinho, com estes generics, compilado no Quartus Prime Lite 25.1 para a DE0-CV, ocupa 137 ALMs, 65 blocos M10K (21 %) e 527.360 bits de memória (17 %). O Tools estima 51 blocos para o mesmo framebuffer e a paleta, porque conta bits e não a organização em blocos de 32 bits de largura.

### 7.4. Teste do vídeo na simulação

O programa de `sdram_video.hex`, na FLASH, lê a geometria e o formato, escreve a paleta e um quadro de 16x8 pixels de uma diagonal de quatro cores, liga a exibição e escreve `tohost`. O testbench (`doom_video.py`) usa um modo pequeno de 40x20 com a estrutura do 640x480, captura um quadro inteiro da saída `VGA_*` a partir da borda do sincronismo vertical e compara cada pixel e os dois sincronismos com o modelo de `tests/python/utils/doom_frame.py`. Confere também o que o núcleo leu dos registradores.

### 7.5. Teste do teclado na simulação

O programa de `sdram_kbd.hex`, na FLASH, liga a linha 5 do PLIC e a interrupção de recepção do teclado, avisa que está pronto, espera cada byte na fila, lê o claim do PLIC com o primeiro e guarda os 20 bytes. O testbench (`doom_keyboard.py`) é o teclado: pelas linhas open drain do conector injeta o make e o break das quatro setas em scancodes do conjunto 2 (`E0 75`, `E0 F0 75`, `E0 6B`, `E0 74` e `E0 72` com os `E0 F0`), e confere os bytes que o núcleo guardou e o claim.

### 7.6. Testes C para a primeira execução na placa

Os programas `tests/c/doom_video/src.c` e `tests/c/doom_keyboard/src.c` são ligados na base da FLASH e compilados com os demais testes C da plataforma (seção 5).

| Programa | O que faz | Código de retorno |
| :--- | :--- | :--- |
| `doom_video` | Lê a geometria e o formato, escreve a paleta e as barras (oito barras de cor e uma rampa de 16 cinzas), liga a exibição e espera três quadros | 1 geometria, 2 formato, 3 o contador de quadros não avançou |
| `doom_keyboard` | Liga a interrupção do teclado e espera uma seta apertada e solta, imprimindo os bytes em hexadecimal | 1 transmissor, 2 erro de estado, 3 tempo esgotado (30 s), 4 sem linha no PLIC, 5 bytes que não são de seta |

No Spike os dois devolvem zero sem tocar nos dispositivos. Na placa, o `doom_video` deixa as barras no monitor depois de terminar, e o `doom_keyboard` precisa de uma pessoa que aperte e solte uma seta.

### 7.7. Cartão microSD

O periférico `SD` (`kind: sd_native`, `0x80008000`) liga o soquete microSD da placa no modo nativo de 4 bits (`SD_CLK`, `SD_CMD`, `SD_DATA[3:0]`). O clock do controlador é o `clocks.core`, então `SD_CLK` vale $100\,\mathrm{MHz} / (2 (\mathtt{DIVIDER} + 1))$: 399 kHz depois do reset e 25 MHz com `DIVIDER = 1`. A porta do jogo lê as WADs do cartão por consulta, e os bits de interrupção de `CONTROL` ficam desligados, de modo que a linha 7 do PLIC, atribuída pelo mapa, fica inerte. A saída do controlador para os pinos é registrada (`sd_native` do Peripherals).

## 8. Caches, fila de escrita e memória interna

O `platform.yaml` dimensiona as peças que cortam o tempo de memória do jogo, e nenhuma é fixada no código.

| Peça | Chave | Valor | Efeito |
| :--- | :--- | :--- | :--- |
| Cache de instruções | `memory.instructions[].cache.size_bits` | 262144 (32 KiB) | O laço de renderização e o código quente cabem na cache |
| Cache de dados | `memory.data[].cache.size_bits` | 262144 (32 KiB) | Mais dados do jogo e da WAD ficam na cache |
| Fila de escrita | `memory.data[].cache.write_buffer` | 4 palavras | Um store completa sem esperar a SDRAM; a leitura só sai com a fila vazia, então a ordem do programa vale |
| Memória interna | `memory.data[].cache.scratch_kib` e `scratch_base` | 32 KiB em `0x43BE8000` | A cache de dados atende a janela em dois ciclos, sem SDRAM |

A memória interna fica dentro da RAM e guarda só o que o programa escreve depois do reset. O DOOM põe nela a pilha e o bss do laço de desenho (`SCRATCH=1` no build do repositório DOOM), e a RAM do linker acaba onde ela começa (`0x43BE8000`).

## 9. O que a plataforma não tem

| Item | Estado |
| :--- | :--- |
| Mouse | Fora do `platform.yaml`, por depender do cabo Y |
| FLASH emulada, controlador de FLASH e bancos | Não existem; a atualização de programa em campo é a da [`de0-cv-emulated`](de0-cv-emulated.md) |
| Ajuste dos pórticos do vídeo no `platform.yaml` | Não existe (seção 7.2.1) |
| Linker script e `crt0` do DOOM | Pertencem à porta do jogo, que liga o binário em `0x1000` (ROM) e `0x40000000` (RAM) |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
