# Plataforma `de0-cv`: a FLASH como chip atrás das caches

## 1. O que ela é

O núcleo guarda só a BOOT_ROM. A FLASH (programa e constantes) e a SDRAM (dados) ficam fora dele, como num SoC real, e o núcleo as alcança por uma cache de instruções e uma cache de dados. Cada falha de cache vira um pedido de linha de quatro palavras, que um roteador de região leva ao modelo de chip de FLASH, através de um árbitro, ou ao controlador da SDRAM.

```
            núcleo (só a BOOT_ROM)
              |                |
        cache de             cache de dados
        instruções           (write-through)
              |                |
        roteador I          roteador D
         |        \          /      |  \
         |         árbitro de FLASH   |  absorvedor de stores à FLASH
         |              |             |
         |         chip de FLASH      |
         |      (armazenamento)       |
         +------------+---------------+
                      |
              SDRAM (ponte, árbitro, controlador)
```

## 2. Mapa de memória

| Região | Base | Tamanho | Acesso |
| :--- | :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | 4 KiB | Busca e leitura, direto, sem cache |
| FLASH | `0x00001000` | 252 KiB de janela, até `0x00040000` | Busca e leitura pelas caches, somente leitura |
| SDRAM | `0x40000000` | 64 MB | Busca, leitura e escrita pelas caches |
| Periféricos | `0x80000000` | janelas de 256 MB | Leitura e escrita, sem cache |

Os 4 KB do topo da SDRAM guardam as palavras que o hospedeiro escreve por trás das caches (`tohost`, `fromhost` e o buffer de `stdout`). A cache de dados as ignora: um load vai à memória como palavra, sem trazer linha, e um store só é repassado.

## 3. Comportamento

1. **Busca.** O PC alimenta só a cache de instruções e a BOOT_ROM. A tag da cache leva o bit da região, que separa as linhas da FLASH das da SDRAM; a região da FLASH é a faixa `[4 KiB, 256 KiB)` do endereço do núcleo.
2. **Dados.** Loads e stores à FLASH e à SDRAM passam pela cache de dados, com linhas de 16 bytes e mapeamento direto de 4 KB. Um store à FLASH nunca altera a cache e é concluído pelo roteador sem efeito, como um chip protegido contra escrita.
3. **FLASH.** O chip atende pedidos de linha ou de palavra com dois parâmetros de latência: bordas até a primeira palavra e bordas entre as palavras seguintes. Fora da janela do chip a leitura devolve zero.
4. **Reinício.** O boot ROM executa `fence.i` antes de saltar para a FLASH. A instrução invalida a cache de instruções e a de dados, então o programa novo que o hospedeiro gravou não encontra linhas do anterior.
5. **Hospedeiro.** O hospedeiro grava a imagem da FLASH pela memória interna do Quartus (instância 0) e os dados pela porta de depuração da SDRAM, com o núcleo parado no laço de reinício do boot ROM. Ele reinicia o núcleo escrevendo um valor diferente de zero em `fromhost`.

## 4. Tamanhos e latências

| Item | Simulação | Placa |
| :--- | :--- | :--- |
| Janela do chip de FLASH | 256 KB (`size_bytes` igual a 262144), dos quais a FLASH ocupa os 252 KiB depois da BOOT_ROM | A mesma |
| Armazenamento da FLASH | Vetor de 256 KB | 256 KB em blocos de RAM, regravável por JTAG |
| Latência do chip | 24 bordas até a primeira palavra e 4 entre as seguintes (padrão) | A mesma |

O armazenamento tem 256 KB porque o maior teste do ACT4 (`I-jal-00`) ocupa 131 872 bytes e os primeiros 4 KB do vetor correspondem à BOOT_ROM, que o programa da FLASH não usa. Um vetor de 1 MB não roda no GHDL.

## 5. Como rodar

| Objetivo | Comando |
| :--- | :--- |
| Simulação dos programas existentes | `riscv-tools --config tools/riscv_build/config.sdram-flash-regression.yaml compile --emit hex`, depois `sim --exclude uart-echo,uart-tx,uart-errors` (no repositório Tests) |
| Simulação dos programas da SDRAM e da FLASH | `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit hex`, depois `sim --exclude cpi-kernels,hex-id` |
| Latência do chip | As configurações `config.sdram-flash-lat2.yaml`, `-lat20.yaml` e `-lat60.yaml`, e as `-regression-lat*` |
| Compilar a placa | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl` (só a síntese, com o argumento `map`) |
| Programar a placa | `src/cyclone-v/de0-cv/de0-cv_program.sh`, no mesmo shell da compilação (`&&`) |
| Programas na placa | `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml run --skip-reconfigure --skip-recompile` |
| ACT4 na placa | `certify-board --skip-build` com a configuração `config.flash-board-<perfil>.yaml` do repositório Certification |

O `platform.yaml` é a única fonte do mapa. O `riscv-tools generate-memory-map` (`make generate`) escreve dele o pacote `de0_cv_map_pkg.vhd`, que o topo da placa, o topo de simulação e o projeto do Quartus (`de0-cv.qsf`) usam para os limites das regiões, o tamanho do chip de FLASH e a página da SDRAM que o hospedeiro compartilha com o programa, além das flags de ligação, do linker script da boot ROM e do `memory_map.h` com os endereços do `tohost`, do `fromhost`, do `stdout` e da UART para o runtime. O pacote traz ainda `NUM_REGS` e os `HAS_*` do perfil da plataforma, `BOOT_ROM_BITS` (12) e `ROM_STORAGE_BYTES` (262144). O `config.yaml` declara `memory_map: platform.yaml` e recebe do mapa as bases, as palavras, o `tohost`, o `fromhost` e a largura de endereço das memórias de simulação. O verificador `check-memory-map` confere só o que sobra escrito à mão: o boot ROM, o VHDL do núcleo e o cabeçalho dos programas.

Os periféricos ocupam os 2 GiB superiores do espaço de endereços (bit 31 em 1), com uma janela de 256 MiB por periférico escolhida pelos bits 30:28: a UART via JTAG no id 4 (`0xC0000000`) e o display de 7 segmentos no id 5 (`0xD0000000`). A BOOT_ROM, a FLASH e a SDRAM ficam nos 2 GiB inferiores.

## 6. ACT4

Os ELFs do ACT4 têm o código e as constantes na FLASH e os dados, a pilha e as palavras do HTIF na SDRAM. O teste `Zifencei-fence.i-00` reescreve o próprio código, e a FLASH ignora stores, então ele usa uma variante do alvo em que o corpo do teste fica na SDRAM e só a entrada, as macros do modelo e as constantes ficam na FLASH.
