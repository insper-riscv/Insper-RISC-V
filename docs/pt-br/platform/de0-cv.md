# Plataforma `de0-cv`: a FLASH como chip atrás das caches

## 1. O que ela é

O núcleo guarda só a BOOT_MEMORY. A FLASH (programa e constantes) e a SDRAM (dados) ficam fora dele, como num SoC real, e o núcleo as alcança por uma cache de instruções e uma cache de dados. Cada falha de cache vira um pedido de linha de quatro palavras, que um roteador de região leva ao modelo de chip de FLASH, através de um árbitro, ou ao controlador da SDRAM.

```
            núcleo (só a BOOT_MEMORY)
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
| BOOT_MEMORY | `0x00000000` | 4 KiB | Busca e leitura, direto, sem cache |
| FLASH | `0x00001000` | 252 KiB de janela, até `0x00040000` | Busca e leitura pelas caches, somente leitura |
| SDRAM | `0x40000000` | 64 MB | Busca, leitura e escrita pelas caches |
| Periféricos | `0x80000000` | janelas de 256 MB | Leitura e escrita, sem cache |

Os 4 KB do topo da SDRAM guardam as palavras que o hospedeiro escreve por trás das caches (`tohost`, `fromhost` e o buffer de `stdout`). A cache de dados as ignora: um load vai à memória como palavra, sem trazer linha, e um store só é repassado.

## 3. Comportamento

1. **Busca.** O PC alimenta só a cache de instruções e a BOOT_MEMORY. A tag da cache leva o bit da região, que separa as linhas da FLASH das da SDRAM; a região da FLASH é a faixa `[4 KiB, 256 KiB)` do endereço do núcleo.
2. **Dados.** Loads e stores à FLASH e à SDRAM passam pela cache de dados, com linhas de 16 bytes e mapeamento direto de 4 KB. Um store à FLASH nunca altera a cache e é concluído pelo roteador sem efeito, como um chip protegido contra escrita.
3. **FLASH.** O chip atende pedidos de linha ou de palavra com dois parâmetros de latência: bordas até a primeira palavra e bordas entre as palavras seguintes. Fora da janela do chip a leitura devolve zero.
4. **Reinício.** A memória de boot executa `fence.i` antes de ler a FLASH. A instrução invalida a cache de instruções e a de dados, então a conferência das bancas e o programa novo que o hospedeiro gravou não encontram linhas do anterior. A FLASH tem duas bancas, e a memória de boot salta para a de maior versão cujo cabeçalho e CRC-32 conferem ([contrato de entrada](contrato-de-entrada.md), seção 6.6); sem banca válida o núcleo espera no laço de reinício.
5. **Hospedeiro.** O hospedeiro grava a imagem da FLASH pelo carregador JTAG (instância 0 do Virtual JTAG), que para o núcleo com o reset enquanto escreve a porta B do armazenamento e o solta no fim, e os dados pela porta de depuração da SDRAM (instância 3). Cada troca de programa reinicia, portanto, o núcleo, o CLINT e o PLIC.
6. **Trap.** O `LEDR1` do topo acende quando o núcleo pulsa `o_trap_take` e fica aceso até o próximo reset, inclusive o do botão `KEY4` (`FPGA_RESET_N`), que o apaga mesmo com o clock parado. O programa continua na memória, então ao soltar o botão ele pode repetir o trap e reacender o LED. `o_trap_take` pulsa quando o núcleo toma uma exceção, com ou sem Zicsr, inclusive a que ele trata em `mtvec`.

## 4. Tamanhos e latências

| Item | Simulação | Placa |
| :--- | :--- | :--- |
| Janela do chip de FLASH | 256 KB (`size_bytes` igual a 262144), dos quais a FLASH ocupa os 252 KiB depois da BOOT_MEMORY | A mesma |
| Armazenamento da FLASH | Vetor de 256 KB | 256 KB em blocos de RAM de duas portas: a porta A é lida pelo chip, a porta B é do carregador JTAG (núcleo parado) e do controlador de FLASH (núcleo em execução) |
| Latência do chip | 24 bordas até a primeira palavra e 4 entre as seguintes (padrão) | A mesma |

O armazenamento tem 256 KB porque o maior teste do ACT4 (`I-jal-00`) ocupa 131 872 bytes e os primeiros 4 KB do vetor correspondem à BOOT_MEMORY, que o programa da FLASH não usa. Um vetor de 1 MB não roda no GHDL.

## 5. Como rodar

| Objetivo | Comando |
| :--- | :--- |
| Simulação dos programas existentes | `riscv-tools --config tools/riscv_build/config.sdram-flash-regression.yaml compile --emit hex`, depois `sim --exclude uart-echo,uart-tx,uart-errors` (no repositório Tests) |
| Simulação dos programas da SDRAM e da FLASH | `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit hex`, depois `sim --exclude cpi-kernels,hex-id` |
| Atualização de programa | `config.sdram-flash-update.yaml` e `-update-slow.yaml` do repositório Tests, que ligam `HAS_FLASH_CONTROLLER` no topo de simulação (ver [atualizacao-de-programa.md](atualizacao-de-programa.md)) |
| Latência do chip | As configurações `config.sdram-flash-lat2.yaml`, `-lat20.yaml` e `-lat60.yaml`, e as `-regression-lat*` |
| Atualização de programa na placa | `tools/board/board_update.py` do repositório Tests (ver [atualizacao-de-programa.md](atualizacao-de-programa.md), seção 8) |
| Compilar a placa | `riscv-tools --config src/cyclone-v/de0-cv/config.yaml program --compile-only --stop-after map` (só a síntese) |
| Zihpm reduzido | `program --compile-only --seed 1 --generic HPM_COUNTERS=4 --generic HPM_WIDTH=40`, sem alterar os padrões do topo |
| Programar a placa | `riscv-tools --config src/cyclone-v/de0-cv/config.yaml program <imagem.mif>`, que escreve o projeto, compila e programa na mesma cadeia |
| Programas na placa | `riscv-tools --config tools/riscv_build/config.sdram-flash.yaml run --skip-reconfigure --skip-recompile` |
| ACT4 na placa | `gen_profiles.py --profile <perfil> --board --out build/target` e `certify-board` com o `config.yaml` gerado, no repositório Certification; o `tools/board/board_run.py act` do repositório Tests reparte os ELFs entre as duas placas |

O `platform.yaml` é a única fonte do mapa. O `riscv-tools generate-memory-map` (`make generate`) escreve dele o pacote `de0_cv_map_pkg.vhd`, que o topo da placa gerado, o topo de simulação e o projeto do Quartus gerado (`build/de0-cv-de0-cv/`) usam para os limites das regiões, o tamanho do chip de FLASH e a página da SDRAM que o hospedeiro compartilha com o programa, além das flags de ligação, do linker script da memória de boot e do `memory_map.h` com os endereços do `tohost`, do `fromhost`, do `stdout` e da UART para o runtime. O pacote traz ainda os `HAS_*` da plataforma (`HAS_E` entre eles), `BOOT_MEMORY_BITS` (12) e `ROM_STORAGE_BYTES` (262144). O `config.yaml` declara `memory_map: platform.yaml` e recebe do mapa as bases, as palavras, o `tohost`, o `fromhost` e a largura de endereço das memórias de simulação. O verificador `check-memory-map` confere só o que sobra escrito à mão: a memória de boot, o VHDL do núcleo e o cabeçalho dos programas.

Os periféricos ocupam os 2 GiB superiores do espaço de endereços (bit 31 em 1), com uma janela de 256 MiB por periférico escolhida pelos bits 30:28: a UART via JTAG no id 4 (`0xC0000000`) e o display de 7 segmentos no id 5 (`0xD0000000`), o CLINT no id 6 (`0xE0000000`, janela de 64 KiB) e o controlador de interrupção externa no id 7 (`0xF0000000`). As linhas MTIP, MSIP e MEIP chegam ao núcleo (ver o [interconector](../interconnect/ext_interconnect.md)), e o `mtime` do CLINT conta a 1 MHz (`mtime_hz` do `platform.yaml`, 50 ciclos de 50 MHz por tick), independente do CSR `time`. A BOOT_MEMORY, a FLASH e a SDRAM ficam nos 2 GiB inferiores.

## 6. ACT4

Os ELFs do ACT4 têm o código e as constantes na FLASH e os dados, a pilha e as palavras do HTIF na SDRAM. O teste `Zifencei-fence.i-00` reescreve o próprio código, e a FLASH ignora stores, então ele usa uma variante do alvo em que o corpo do teste fica na SDRAM e só a entrada, as macros do modelo e as constantes ficam na FLASH.

## 7. Teste do topo de simulação

O catálogo `tests/python/tests.json` traz as entradas `De0CvBootBanks` (a memória de boot de verdade escolhendo a banca, uma simulação por caso, ver [atualizacao-de-programa.md](atualizacao-de-programa.md)) e `De0CvSimTop`, que roda o topo `rv32im_sdram_flash_sim_test` com um programa mínimo em cada região. A BOOT_MEMORY guarda uma marca na SDRAM e salta para a FLASH, a FLASH guarda outra marca, escreve no display e salta para o código que a SDRAM já tem desde o tempo zero (`SDRAM_FILE`), e esse guarda a terceira marca e escreve em `tohost`. O teste lê a SDRAM pela porta de depuração do chip e confere as três marcas, o `tohost` e o valor do display. As imagens saem de `tests/python/gen_de0_cv_images.py`, a partir do `platform.yaml`.

O testbench de simulação de programas (`testbench/test_c_program.py`) só inicia o console da UART no primeiro acesso do núcleo à janela da UART (`UART_START_ON_ACCESS` e `UART_SLOT` do `config.yaml`, o segundo igual a `UART.id`), porque a memória de boot confere as bancas e a inicialização do programa leva muito mais tempo do que a fila de recepção de 64 bytes segura o que o hospedeiro envia. `UART_SCANS_PER_BYTE` ajusta quantas varreduras separam dois bytes enviados.
