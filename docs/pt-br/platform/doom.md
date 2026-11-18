# Plataforma `doom`: o código executa da SDRAM

## 1. O que ela é

A plataforma `doom` é a `de0-cv` com a FLASH reduzida ao mínimo e a SDRAM executável. O binário do DOOM (porta `doomgeneric`, entre 363 e 412 KiB com o código, as constantes e os dados iniciais) não cabe na FLASH emulada em blocos M10K, porque o chip inteiro tem 308 blocos (cerca de 385 KiB). O código do jogo roda, portanto, da SDRAM, e a FLASH guarda só um carregador de poucas instruções.

O projeto nasce do `riscv-tools new-project doom --board de0-cv --profile rv32im_zicclsm_zicntr_zihpm_zifencei --rom 8K --ram 64M --icache 32768 --dcache 32768`. A `de0-cv`, a BOOT_MEMORY dela e os testes dela não mudam.

## 2. Mapa de memória

| Região | Base | Tamanho | Acesso |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Busca e leitura, direto, sem cache |
| FLASH, banca A | `0x00001000` | 4 KiB | Busca e leitura pelas caches, somente leitura |
| FLASH, banca B | `0x00002000` | 4 KiB | Busca e leitura pelas caches, somente leitura |
| SDRAM (`RAM`, `exec: true`) | `0x40000000` | 64 MB | Busca, leitura e escrita pelas caches |
| Memória interna da cache de dados | `0x43FE8000` | 32 KiB | Leitura e escrita em dois ciclos, dentro da SDRAM, sem passar pela SDRAM |
| Periféricos | `0x80000000` | janelas de 256 MB | Leitura e escrita, sem cache |

Os 4 KiB do topo da SDRAM (`0x43FFF000` a `0x43FFFFFF`), que a cache de dados ignora, guardam as palavras compartilhadas com o hospedeiro.

| Palavra | Endereço | Uso |
| :--- | :--- | :--- |
| `stdout` | `0x43FFFBE0` | Cabeçalho e buffer da saída do programa (1 KiB mais 8 bytes) |
| `tohost` | `0x43FFFFE8` | Fim do programa (protocolo HTIF) |
| `fromhost` | `0x43FFFFF0` | Reinício pelo hospedeiro |
| `launch` | `0x43FFFFF8` | Campainha do carregador da FLASH |

A BOOT_MEMORY zera `stdout`, `tohost` e `fromhost` a cada reset. A `launch` só é zerada pelo carregador, depois de consumi-la.

## 3. Como o código chega a executar da SDRAM

A BOOT_MEMORY só salta para uma banca cujo cabeçalho e CRC-32 conferem, e não sabe que existe uma SDRAM executável. A banca A guarda, por isso, o programa `runtime/doom_loader.S`, de 44 bytes, ligado em `0x1100`, que faz o seguinte.

1. Lê a palavra `launch` em laço. A palavra está na última página da SDRAM, que a cache de dados ignora, então cada leitura vai à memória.
2. Quando a palavra vale `0x4D4F4F44` (os bytes `DOOM`), escreve zero nela, para que o reset seguinte espere uma nova imagem em vez de rodar a antiga.
3. Executa `fence.i`, que descarta as linhas das duas caches deixadas por uma execução anterior.
4. Salta para `0x40000000`, a base da SDRAM, onde está o `_start` do DOOM.

O programa entra com `sp`, `gp` e `tp` indefinidos, como qualquer banca, e o `_start` da imagem os ajusta.

O gerador do mapa (`riscv-tools generate-memory-map` e `check-memory-map`) aceita a região `RAM` com `exec: true` sem mudança, e confere as duas condições dela: a RAM externa com a busca pela porta do núcleo, e a extensão Zifencei no perfil, porque a cache de instruções fica sobre a SDRAM. A flag `exec` não altera o VHDL gerado, que já executa código da SDRAM nos testes da `de0-cv`. O `boot.entry` continua na FLASH, em `0x1000`.

## 4. Como carregar o binário na SDRAM

O binário é ligado em `0x40000000` com o código, as constantes e os dados iniciais em sequência. A WAD (`doom1.wad`) vai para outro endereço da SDRAM, acima do fim do binário, que a porta do jogo define. A carga usa a porta de depuração da SDRAM (instância 3 do Virtual JTAG), com o núcleo rodando no carregador.

| Passo | Operação |
| :--- | :--- |
| 1 | Gravar a FLASH com o carregador (seção 4.1) |
| 2 | Zerar a campainha `launch`, para o carregador não saltar sobre uma imagem pela metade |
| 3 | Escrever a imagem do binário a partir da palavra 0 da SDRAM, e a WAD no endereço dela |
| 4 | Escrever a magia `0x4D4F4F44` em `launch` |

### 4.1. Gravar o carregador na banca A

```bash
riscv32-unknown-elf-gcc -march=rv32i_zifencei -mabi=ilp32 -nostdlib -nostartfiles \
  -Isrc/cyclone-v/doom/runtime -T carregador.ld src/cyclone-v/doom/runtime/doom_loader.S -o doom_loader.elf
riscv32-unknown-elf-objcopy -O binary doom_loader.elf doom_loader.bin
riscv-tools --root . flash-image pack doom_loader.bin --output doom_loader.img --version 1 \
  --platform src/cyclone-v/doom/platform.yaml --bank A
```

O script de ligação `carregador.ld`, escrito pelo usuário, coloca a seção `.text` em `0x1100` (`ENTRY(_start)` e `SECTIONS { . = 0x1100; .text : { *(.text.loader) *(.text*) } }`). A imagem `doom_loader.img` entra na FLASH pelo `flash-image send` ou pelo carregador JTAG da FLASH, como a de qualquer outra banca (ver [atualização de programa](atualizacao-de-programa.md)).

### 4.2. Escrever a SDRAM e tocar a campainha

O subcomando `load-ram` faz os passos 2 a 4 em uma só chamada: zera `launch`, escreve o binário e a WAD pela porta de depuração, lê cada um de volta para conferir e só então escreve a magia em `launch`. Uma diferença na leitura aborta a carga sem tocar a campainha.

```bash
riscv-tools --root . --config src/cyclone-v/doom/config.yaml load-ram doom.bin \
  --wad doom1.wad --wad-address 0x40100000
```

O endereço do binário é a base da SDRAM, e o da WAD é o que a porta do jogo define. O `launch` vem do `reserved` do `platform.yaml` (`memory.launch_addr`). Um reset do núcleo sem nova carga deixa o carregador esperando, porque a campainha foi consumida. A descrição completa do subcomando está na documentação do módulo `ram_load` do repositório Tools.

## 5. Orçamento de blocos M10K

A compilação do Quartus Prime Lite 25.1 do projeto gerado (`build/doom-de0-cv`, semente padrão, DE0-CV) ajusta e fecha o tempo no modelo lento a 85 C.

| Recurso | Usado | Disponível |
| :--- | ---: | ---: |
| Blocos de RAM (M10K) | 31 | 308 (10 %) |
| Bits de memória em bloco | 239.872 | 3.153.920 (8 %) |
| Lógica (ALMs) | 9.503 | 18.480 (51 %) |
| Pior folga de setup, modelo lento a 85 C | 0,515 ns | |

O armazenamento da FLASH tem $2^{14}$ bytes (a menor potência de dois que cobre o fim da FLASH, 12 KiB). Os blocos M10K restantes ficam livres para o framebuffer do controlador de vídeo.

## 6. Relógio do jogo

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

## 7. Teste do topo de simulação

O catálogo `tests/python/tests.json` traz as entradas `DoomSimTop` e `DoomSimWait`, que rodam o topo `doom_sim_test` com a BOOT_MEMORY de verdade (`boot_memory.S`) e o `doom_loader.S` de verdade, empacotado como banca A por `flash_image.pack`.

| Entrada | SDRAM no tempo zero | Resultado conferido |
| :--- | :--- | :--- |
| `DoomSimTop` | Programa de teste na base e a magia na campainha | O programa roda, guarda a marca `0xD00D`, escreve `tohost`, e a campainha volta a zero |
| `DoomSimWait` | Programa de teste na base, sem a magia | Depois de 400 mil ciclos nada do programa rodou |

O simulador carrega a SDRAM linearmente a partir da base, e a última página fica 64 MiB acima dela, então o teste põe a campainha em `0x40000800` (`-DDOOM_LAUNCH_ADDR`). A única diferença para a placa é esse endereço, e a verificação `check-memory-map` confere o valor padrão do `doom_loader.S` contra o `platform.yaml`. As imagens saem de `tests/python/gen_doom_images.py`, e `--check` confere que estão em dia.

As entradas `DoomSimVideo` e `DoomSimKeyboard` rodam o mesmo topo com os programas das seções 8.4 e 8.5.

## 8. Vídeo e teclado

### 8.1. Periféricos e endereços

O `platform.yaml` lista dois periféricos externos, que o topo gerado da placa instancia ao lado do SoC e o topo de simulação `doom_sim_test` instancia nas mesmas janelas.

| Periférico | `kind` | Base | Janela | Interrupção | Pinos da DE0-CV |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `VIDEO` | `video` | `0x80100000` | 256 KiB | nenhuma | `VGA_R[3:0]`, `VGA_G[3:0]`, `VGA_B[3:0]`, `VGA_HS`, `VGA_VS` |
| `KBD` | `ps2` (`device: keyboard`) | `0x80007000` | 16 bytes | linha 5 do PLIC (`IRQ_KBD`) | `PS2_CLK` (D3), `PS2_DAT` (G2) |

O segundo canal do cabo Y (`PS2_CLK2` em E2 e `PS2_DAT2` em G1) pertence a um mouse, que entra como mais uma entrada de `peripherals` (`MOUSE: {kind: ps2, device: mouse, base: 0x80007100}`). O mapa gerado (`memory_map.h` e `doom_map_pkg.vhd`) traz `RV32_VIDEO_BASE`, `RV32_KBD_BASE` e `RV32_IRQ_KBD`.

### 8.2. Vídeo indexado

O `io.video` do `platform.yaml` pede um framebuffer indexado de 320x200 (8 bits por pixel e uma paleta de 256 entradas de 12 bits, a largura do conversor da DE0-CV). O modo é o padrão da placa, 640x480 a 60 Hz com clock de pixel de 25 MHz, e a imagem sai ampliada duas vezes e centralizada, com faixas pretas de 40 linhas em cima e embaixo.

| Região da janela do vídeo | Deslocamento | Conteúdo |
| :--- | :--- | :--- |
| Registradores | `0x00000` a `0x00010` | Controle, estado, contador de quadros, geometria e formato |
| Paleta | `0x00400` | 256 palavras, a cor nos 12 bits baixos (vermelho nos bits 11:8) |
| Framebuffer | `0x20000` | 16000 palavras, quatro pixels por palavra, o de menor coluna nos bits baixos |

O framebuffer e a paleta só aceitam escrita, e o núcleo os atualiza com `sw`, `sh` ou `sb`. A exibição liga com o bit 0 do registrador de controle. O pacote `Peripherals` documenta o periférico em `docs/pt-br/video/video.md`.

O clock de pixel é uma saída a mais do PLL do topo gerado, e o `.sdc` gerado declara falsos os caminhos entre o domínio do núcleo e o do pixel, porque o vídeo os atravessa só por sincronizadores de dois flip-flops e por memórias com um clock em cada porta.

### 8.3. Recursos

O vídeo sozinho, com estes generics, compilado no Quartus Prime Lite 25.1 para a DE0-CV, ocupa 137 ALMs, 65 blocos M10K (21 %) e 527.360 bits de memória (17 %). O Tools estima 51 blocos para o mesmo framebuffer e a paleta, porque conta bits e não a organização em blocos de 32 bits de largura.

### 8.4. Teste do vídeo na simulação

O programa `sdram_video.hex` lê a geometria e o formato, escreve a paleta e um quadro de 16x8 pixels de uma diagonal de quatro cores, liga a exibição e escreve `tohost`. O testbench (`doom_video.py`) usa um modo pequeno de 40x20 com a estrutura do 640x480, captura um quadro inteiro da saída `VGA_*` a partir da borda do sincronismo vertical e compara cada pixel e os dois sincronismos com o modelo de `tests/python/utils/doom_frame.py`. Confere também o que o núcleo leu dos registradores.

### 8.5. Teste do teclado na simulação

O programa `sdram_kbd.hex` liga a linha 5 do PLIC e a interrupção de recepção do teclado, avisa que está pronto, espera cada byte na fila, lê o claim do PLIC com o primeiro e guarda os 20 bytes. O testbench (`doom_keyboard.py`) é o teclado: pelas linhas open drain do conector injeta o make e o break das quatro setas em scancodes do conjunto 2 (`E0 75`, `E0 F0 75`, `E0 6B`, `E0 74` e `E0 72` com os `E0 F0`), e confere os bytes que o núcleo guardou e o claim.

### 8.6. Testes C para a primeira execução na placa

Os programas `tests/c/doom_video/src.c` e `tests/c/doom_keyboard/src.c` são ligados na banca A e compilados com os demais testes C da plataforma (seção 6).

| Programa | O que faz | Código de retorno |
| :--- | :--- | :--- |
| `doom_video` | Lê a geometria e o formato, escreve a paleta e as barras (oito barras de cor e uma rampa de 16 cinzas), liga a exibição e espera três quadros | 1 geometria, 2 formato, 3 o contador de quadros não avançou |
| `doom_keyboard` | Liga a interrupção do teclado e espera uma seta apertada e solta, imprimindo os bytes em hexadecimal | 1 transmissor, 2 erro de estado, 3 tempo esgotado (30 s), 4 sem linha no PLIC, 5 bytes que não são de seta |

No Spike os dois devolvem zero sem tocar nos dispositivos. Na placa, o `doom_video` deixa as barras no monitor depois de terminar, e o `doom_keyboard` precisa de uma pessoa que aperte e solte uma seta.

## 9. Caches, fila de escrita e memória interna

O `platform.yaml` dimensiona as três peças que cortam o tempo de memória do jogo, e nenhuma é fixada no código.

| Peça | Chave | Valor | Efeito |
| :--- | :--- | :--- | :--- |
| Cache de instruções | `memory.instructions[].cache.size_bits` | 262144 (32 KiB) | O laço de renderização e o código quente cabem na cache |
| Cache de dados | `memory.data[].cache.size_bits` | 32768 (4 KiB) | Sem mudança |
| Fila de escrita | `memory.data[].cache.write_buffer` | 4 palavras | Um store completa sem esperar a SDRAM; a leitura só sai com a fila vazia, então a ordem do programa vale |
| Memória interna | `memory.data[].cache.scratch_kib` e `scratch_base` | 32 KiB em `0x43FE8000` | A cache de dados atende a janela em dois ciclos, sem SDRAM |

A memória interna fica dentro da SDRAM e guarda só o que o programa escreve depois do reset, porque o hospedeiro carrega a SDRAM por trás da cache. O DOOM põe nela a pilha e o bss do laço de desenho (`SCRATCH=1` no build do repositório DOOM), e a RAM do linker acaba onde ela começa (`0x43FE8000`).

## 9. O que a plataforma não tem

| Item | Estado |
| :--- | :--- |
| Mouse | Fora do `platform.yaml`, por depender do cabo Y |
| Banca B | Livre; um carregador novo entra nela com versão maior |
| Linker script e `crt0` do DOOM | Pertencem à porta do jogo, que liga o binário em `0x40000000` |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
