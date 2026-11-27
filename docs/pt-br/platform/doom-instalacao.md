# Instalar o DOOM na DE0-CV

🌐 [Português](doom-instalacao.md) · [English](../../en/platform/doom-instalacao.md)

Este guia leva a DE0-CV, com o cartão microSD preparado, a rodar o DOOM a partir de um computador Linux com Docker. Ele cobre o lado da plataforma `doom` com a FLASH como janela da SDRAM: compilar o `.sof`, programar o FPGA e gravar o jogo. A montagem do `doom.bin` e o preparo do cartão estão no guia `docs/pt-br/INSTALAR.md` do repositório [DOOM](https://github.com/insper-riscv/DOOM), e a seção 2 resume o que dele é preciso aqui.

## 1. Como o jogo chega à placa

A plataforma `doom` executa o código da SDRAM. A FLASH é a janela das instruções, de 4 MiB no topo do chip de SDRAM, com base `0x1000` no mapa do núcleo e deslocamento `0x3C01000` dentro do chip. A BOOT_MEMORY salta direto para `0x1000`, então não há carregador.

| Etapa | O que acontece |
| :--- | :--- |
| 1 | O `.sof` configura o FPGA; o núcleo sobe, a SDRAM inicializa e o `0x1000` está vazio |
| 2 | Um programa no computador grava o `doom.bin` na janela FLASH, pela porta de depuração da SDRAM (instância 3 do Virtual JTAG), e relê tudo para conferir |
| 3 | O `.sof` é programado de novo; o núcleo reinicia, a BOOT salta para `0x1000` e o jogo sobe |

A configuração do FPGA e a SDRAM se perdem a cada desligamento da placa, então as três etapas se repetem toda vez que a placa é ligada.

## 2. Arquivos necessários

| Arquivo | Como se obtém |
| :--- | :--- |
| `doom_de0_cv.sof` | Seção 4 |
| `doom.bin` (versão FatFs) | `PLATFORM_DIR=platform_doom SDFS=fatfs MENU=1 VIDEO=1 INTERACTIVE=1 SD=demand ONDEMAND=1 sh scripts/image.sh`, na raiz do repositório DOOM |
| `load_flash.py` | Seção 6, no mesmo repositório como `scripts/load_flash.py` |
| Cartão microSD | FAT32 com `DOOM.WAD`, `DOOM2.WAD`, `PLUTONIA.WAD`, `TNT.WAD` e a pasta `MASTER/`, nomes 8.3 |

O `.sof` e o `doom.bin` formam um par e não se misturam com arquivos de outra versão da plataforma. Um cartão em exFAT aparece sem nenhum jogo no menu, porque o jogo lê só FAT12, FAT16 e FAT32.

## 3. Preparar o computador

| Item | Requisito |
| :--- | :--- |
| Docker | Funcionando, com o contexto `default` |
| Imagem | `ghcr.io/insper-riscv/dev_tools:latest`, que traz o `uv` e o Python 3.14 |
| Quartus Prime Lite 25.1 | Instalado em `/opt/altera_lite`, com `quartus_pgm` e `jtagconfig` no `PATH` |
| USB-Blaster | Regra udev instalada e cabo reconectado depois dela |
| Rede | Acesso a `github.com`, porque a gravação baixa o Tools do commit `f7ea593` |

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

O Python do computador não é usado. Todo comando de Python roda dentro do container.

## 4. Compilar o `.sof`

Na raiz deste repositório, com a plataforma `doom` em `src/cyclone-v/doom/`:

```bash
docker -c default run --rm --network host \
  -v /opt/altera_lite:/opt/altera_lite:ro -v "$PWD":/w -w /w \
  -e HOME=/tmp -u "$(id -u):$(id -g)" ghcr.io/insper-riscv/dev_tools:latest sh -c \
  'export PATH="$PATH:/opt/altera_lite/25.1std/quartus/bin"; \
   riscv-tools --root . --config src/cyclone-v/doom/config.yaml program --compile-only --seed 6'
```

O `.sof` sai em `build/doom-de0-cv/output_files/doom_de0_cv.sof`, depois de 7 a 10 minutos. O `doom_de0_cv.sta.summary`, na mesma pasta, lista a folga de setup de cada relógio, e todas precisam ser positivas. O núcleo e a busca rodam a 100 MHz e a SDRAM a 125 MHz.

## 5. Achar o cabo

1. Conectar a fonte, o cabo USB-Blaster, o monitor VGA, o teclado PS/2 e o cartão microSD, e ligar a placa.
2. Listar os cabos.

```bash
jtagconfig
```

A DE0-CV aparece com o IDCODE `02B050DD` (`5CE(BA4|FA4)`). Guardar o nome do cabo dessa linha, por exemplo `USB-Blaster [3-6]`, porque o número muda entre computadores e depois de reiniciar. A DE2-115 tem IDCODE `020F70DD` e nunca recebe este `.sof`.

## 6. Gravar o jogo

Os três passos usam o mesmo nome de cabo. Só um computador programa a placa por vez.

1. Programar o FPGA.

```bash
quartus_pgm -c "USB-Blaster [3-6]" -m jtag -o "p;build/doom-de0-cv/output_files/doom_de0_cv.sof@1"
```

2. Gravar o `doom.bin`. O programa abaixo, salvo como `load_flash.py` (já existe pronto no repositório DOOM como `scripts/load_flash.py`), escreve a imagem a partir de `0x1000` e relê tudo.

```python
import sys
from pathlib import Path
from riscv_tools import ram_load
from riscv_tools.jtag import JtagLink

link = JtagLink(hardware_name=sys.argv[2], device_name="@1: 5CE(BA4|FA4) (0x02B050DD)", sdram_instance=3)
FLASH_BASE, CHIP_BYTE = 0x1000, 0x3C01000
seg = ram_load.segment_from_file("flash", Path(sys.argv[1]), FLASH_BASE)
ram_load.load_ram(link, [seg], FLASH_BASE, None,
                  ram_load.LoadOptions(verify=True, chip_words=CHIP_BYTE // 4, report=print))
```

Com o `doom.bin` e o `load_flash.py` na pasta atual, a gravação leva cerca de 5 minutos e termina com `flash: conferido`.

```bash
docker -c default run --rm --network host \
  -v /opt/altera_lite:/opt/altera_lite:ro -v "$PWD":/g:ro -w /tmp \
  -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uvc -e RV32_SDRAM_DEBUG_INSTANCE=3 \
  -u "$(id -u):$(id -g)" ghcr.io/insper-riscv/dev_tools:latest sh -c \
  'export PATH="$PATH:/opt/altera_lite/25.1std/quartus/bin"; \
   uv run --no-project --python 3.14 \
     --with "git+https://github.com/insper-riscv/Tools.git@f7ea593" \
     python /g/load_flash.py /g/doom.bin "USB-Blaster [3-6]"'
```

| Parte do comando | Efeito |
| :--- | :--- |
| `--network host` | O container alcança o `jtagd` do computador |
| `-v /opt/altera_lite:...:ro` | Dá ao container o `quartus_stp` que a gravação usa |
| `RV32_SDRAM_DEBUG_INSTANCE=3` | Aponta para a porta de depuração da SDRAM; sem ela a gravação não acha a porta |
| `--python 3.14` | Sem ele o `uv` escolhe o Python 3.15 e a montagem do cocotb falha |
| `@f7ea593` | Versão do Tools cuja porta de depuração combina com este `.sof` |

3. Programar o `.sof` de novo, com o mesmo comando do passo 1. A segunda programação zera o núcleo, e a BOOT salta para `0x1000`, onde o jogo já está gravado.

O menu do DOOM aparece no monitor. Escolher o jogo com as setas ou com `W` e `S`, e confirmar com `Enter`, `E` ou espaço.

## 7. Conferir que a placa está viva

A leitura de uma palavra da SDRAM só responde se o FPGA estiver configurado.

```bash
docker -c default run --rm --network host -v /opt/altera_lite:/opt/altera_lite:ro \
  -e HOME=/tmp -e RV32_SDRAM_DEBUG_INSTANCE=3 -u "$(id -u):$(id -g)" \
  ghcr.io/insper-riscv/dev_tools:latest sh -c \
  'export PATH="$PATH:/opt/altera_lite/25.1std/quartus/bin"; \
   quartus_stp -t /opt/riscv-tools/riscv-tools/lib/python3.14/site-packages/riscv_tools/jtag/tcl/sdram_dbg.tcl \
   "USB-Blaster [3-6]" "@1: 5CE(BA4|FA4) (0x02B050DD)" read 15860736 1'
```

Se o comando falhar, o FPGA perdeu a configuração e os três passos da seção 6 se repetem.

## 8. Se algo não funciona

| Sintoma | Causa provável | O que fazer |
| :--- | :--- | :--- |
| `jtagconfig` não lista a placa | Regra udev ausente ou cabo solto | Seção 3 e reconectar o cabo |
| `load-flash: this bitstream has no hold and CRC` | A gravação foi feita com o `riscv-tools load-flash`, que pede uma palavra `INFO` que a porta de depuração deste `.sof` não tem | Gravar com o `load_flash.py`, como na seção 6 |
| Erro `cocotb ... maximum Python version of 3.14` | O `uv` escolheu o Python 3.15 | Manter `--python 3.14` |
| `the SDRAM is not initialized` | Instância do Virtual JTAG errada | Exportar `RV32_SDRAM_DEBUG_INSTANCE=3` |
| Tela preta depois do passo 3 | Imagem não gravada ou erro na conferência | Repetir o passo 2 e ler a mensagem de conferência |
| Menu sem nenhum jogo | Cartão não é FAT32 ou não foi detectado | Seção 2 |
| Jogo trava logo depois do menu | `.sof` e `doom.bin` de versões diferentes | Refazer a seção 4 e o `doom.bin` do mesmo commit |

## 9. Cuidados

1. Antes de usar a placa, tomar o lock dela, para que nenhum outro processo a programe no meio dos passos. O lock é um arquivo por placa, como `/tmp/de0cv-<máquina>.lock`.

```bash
exec 9>/tmp/de0cv-laptop.lock && flock -w 60 9
```

2. Não rodar `quartus_pgm` nem `quartus_stp` de outra pessoa ao mesmo tempo.
3. Um serviço que reprograma o FPGA sozinho precisa estar parado, ou com o cabo desconectado dele, antes de usar o cabo em outro computador.
