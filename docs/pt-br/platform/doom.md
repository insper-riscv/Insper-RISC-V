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

O `riscv-tools` ainda não tem um subcomando que carregue uma imagem na SDRAM. O módulo `sdram_debug` tem a função, que o `certify-board` já usa, e o script abaixo roda no Python da imagem `dev_tools`, com o Quartus visível e o cabo JTAG da placa.

```python
from pathlib import Path
import struct

from riscv_tools import sdram_debug
from riscv_tools.jtag import JtagLink

LAUNCH_WORD = (0x43FFFFF8 - 0x40000000) // 4
MAGIC = 0x4D4F4F44

link = JtagLink(hardware_name="<cabo>", device_name="<chip>", sdram_instance=3)
data = Path("doom.bin").read_bytes()
words = [
    w
    for (w,) in struct.iter_unpack(
        "<I", data.ljust(-(-len(data) // 4) * 4, b"\0")
    )
]

sdram_debug.write_word(link, LAUNCH_WORD, 0, 0xF)
sdram_debug.load_words(link, 0, words)
sdram_debug.write_word(link, LAUNCH_WORD, MAGIC, 0xF)
```

Um reset do núcleo sem nova carga deixa o carregador esperando, porque a campainha foi consumida.

## 5. Orçamento de blocos M10K

A compilação do Quartus Prime Lite 25.1 do projeto gerado (`build/doom-de0-cv`, semente padrão, DE0-CV) ajusta e fecha o tempo no modelo lento a 85 C.

| Recurso | Usado | Disponível |
| :--- | ---: | ---: |
| Blocos de RAM (M10K) | 31 | 308 (10 %) |
| Bits de memória em bloco | 239.872 | 3.153.920 (8 %) |
| Lógica (ALMs) | 9.503 | 18.480 (51 %) |
| Pior folga de setup, modelo lento a 85 C | 0,515 ns | |

O armazenamento da FLASH tem $2^{14}$ bytes (a menor potência de dois que cobre o fim da FLASH, 12 KiB). Os blocos M10K restantes ficam livres para o framebuffer do controlador de vídeo.

## 6. Teste do topo de simulação

O catálogo `tests/python/tests.json` traz as entradas `DoomSimTop` e `DoomSimWait`, que rodam o topo `doom_sim_test` com a BOOT_MEMORY de verdade (`boot_memory.S`) e o `doom_loader.S` de verdade, empacotado como banca A por `flash_image.pack`.

| Entrada | SDRAM no tempo zero | Resultado conferido |
| :--- | :--- | :--- |
| `DoomSimTop` | Programa de teste na base e a magia na campainha | O programa roda, guarda a marca `0xD00D`, escreve `tohost`, e a campainha volta a zero |
| `DoomSimWait` | Programa de teste na base, sem a magia | Depois de 400 mil ciclos nada do programa rodou |

O simulador carrega a SDRAM linearmente a partir da base, e a última página fica 64 MiB acima dela, então o teste põe a campainha em `0x40000800` (`-DDOOM_LAUNCH_ADDR`). A única diferença para a placa é esse endereço, e a verificação `check-memory-map` confere o valor padrão do `doom_loader.S` contra o `platform.yaml`. As imagens saem de `tests/python/gen_doom_images.py`, e `--check` confere que estão em dia.

## 7. O que a plataforma não tem

| Item | Estado |
| :--- | :--- |
| PS/2 e VGA | Não estão ligados no topo; o `platform.yaml` traz só os periféricos da `de0-cv` |
| Carga da SDRAM pela linha de comando | Só pela função `sdram_debug.load_words` (seção 4.2) |
| Banca B | Livre; um carregador novo entra nela com versão maior |
| Linker script e `crt0` do DOOM | Pertencem à porta do jogo, que liga o binário em `0x40000000` |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
