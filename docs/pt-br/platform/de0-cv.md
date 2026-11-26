# Plataforma `de0-cv`: a SDRAM dividida em FLASH e RAM

## 1. O que ela é

O núcleo guarda só a BOOT_MEMORY. O chip de SDRAM da placa (64 MB, um controlador) é dividido em duas janelas, a FLASH (as instruções e as constantes, somente leitura para o núcleo) e a RAM (os dados). O núcleo as alcança por uma cache de instruções e uma cache de dados. Cada falha de cache vira um pedido de linha de quatro palavras, que um roteador de região leva ao chip pela porta de instruções (FLASH) ou pela porta de dados (RAM) do controlador.

```
   cache de instruções          cache de dados (write-through)
            |                              |
       roteador I                      roteador D
        |       \                      /      |  \
        |        árbitro da FLASH ----+       |   absorvedor de stores à FLASH
        |              |                      |
   execução da RAM     |                      |
        |              |                      |
        +--- árbitro 2:1 ---> ponte I         +--> ponte A
                              |                     |
                              +----> árbitro (A, I, B) ----> controlador ----> pinos DRAM_*
JTAG (porta de depuração, mestre B) --------------------^
```

## 2. Mapa de memória

Os tamanhos e as bases vêm do `platform.yaml`, e o padrão da placa divide o chip em duas metades de 32 MiB. Qualquer outra divisão em que a FLASH e a RAM caibam no chip é válida: basta trocar `size` das duas regiões.

| Região | Base | Tamanho | Acesso |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Busca e leitura, direto, sem cache |
| FLASH | `0x00001000` | até `0x02000000` (32 MiB menos 4 KiB) | Busca e leitura pelas caches, somente leitura para o núcleo |
| RAM | `0x40000000` | 32 MiB | Busca, leitura e escrita pelas caches |
| Periféricos | `0x80000000` | janelas de 256 MB | Leitura e escrita, sem cache |

No chip, a FLASH ocupa o começo com o endereço do SoC, sem subtração, e a RAM começa logo depois do fim da FLASH. Com 32 MiB e 32 MiB, o bit 25 do endereço de byte escolhe a metade do chip (0 na FLASH, 1 na RAM). Os 4 KB do topo da RAM guardam as palavras que o hospedeiro escreve por trás das caches (`tohost`, `fromhost` e o buffer de `stdout`). A cache de dados as ignora: um load vai à memória como palavra, sem trazer linha, e um store só é repassado.

As duas regiões usam `on_bus: true`, isto é, a CPU as alcança pelo barramento (memória externa). Só a BOOT_MEMORY, onchip, é lida direto da porta da CPU.

## 3. Comportamento

1. **Busca.** O PC alimenta só a cache de instruções e a BOOT_MEMORY. A tag da cache leva o bit da região, que separa as linhas da FLASH das da RAM. O código que roda da RAM usa a mesma porta de instruções do chip, atrás de um segundo árbitro com a face da FLASH.
2. **Dados.** Loads e stores à FLASH e à RAM passam pela cache de dados, com linhas de 16 bytes e mapeamento direto, no tamanho de `cache.size_bits` do `platform.yaml` (4 KiB). Um store à FLASH nunca altera a cache.
3. **Proteção da FLASH.** O núcleo só lê a FLASH, por três camadas independentes. Com `AccessFaults`, um store nela é a exceção de causa 7 (falha de acesso de store) com `mtval` igual ao endereço. Sem `AccessFaults`, o roteador conclui o store sem efeito, como um chip protegido contra escrita. Por construção, a porta de instruções do chip nunca escreve, e a porta de dados só alcança a RAM.
4. **Janela de leitura.** O roteador atende a leitura da FLASH até o fim dela (`FLASH_END` do pacote de mapa), e acima disso devolve zero. A janela vem do mapa, e não de um valor fixo.
5. **Reinício.** A memória de boot executa `fence.i` antes de ler a FLASH. A instrução invalida a cache de instruções e a de dados, então a conferência das bancas e o programa novo que o hospedeiro gravou não encontram linhas do anterior. A FLASH tem duas bancas, e a memória de boot salta para a de maior versão cujo cabeçalho e CRC-32 conferem ([contrato de entrada](contrato-de-entrada.md), seção 6.6); sem banca válida o núcleo espera no laço de reinício.
6. **Hospedeiro.** Só o JTAG escreve a FLASH: o hospedeiro usa a porta de depuração da SDRAM (instância 3 do Virtual JTAG), que é um mestre do árbitro do controlador. A plataforma não tem controlador de FLASH, nem a linha 6 do PLIC.
7. **Trap.** O `LEDR1` do topo acende quando o núcleo pulsa `o_trap_take` e fica aceso até o próximo reset, inclusive o do botão `KEY4` (`FPGA_RESET_N`), que reinicia só o núcleo e não o controlador da SDRAM, então o conteúdo da FLASH sobrevive.

## 4. Tamanhos e latências

| Item | Simulação | Placa |
| :--- | :--- | :--- |
| Chip de SDRAM | Modelo de 64 MiB (13 bits de linha, 2 de banco, 10 de coluna) | IS42S16320D, 64 MB |
| FLASH e RAM | Duas janelas do mesmo modelo | Duas janelas do mesmo controlador |
| Latência | A do controlador e do modelo de chip | A do controlador a 100 MHz |

O modelo de chip é uma tabela esparsa, então a imagem de simulação só precisa das palavras que o programa usa. A RAM não precisa de imagem: o programa copia o que precisa da FLASH.

## 5. Como rodar

| Objetivo | Comando |
| :--- | :--- |
| Teste do topo de simulação | `make test TEST=De0CvSimTop` |
| Escolha de banca pela memória de boot | `make test TEST=De0CvBootBanks` |
| Compilar a placa | `riscv-tools --config src/cyclone-v/de0-cv/config.yaml program --compile-only --stop-after map` (só a síntese) |
| Programar a placa | `riscv-tools --config src/cyclone-v/de0-cv/config.yaml program <imagem.mif>` |

O `platform.yaml` é a única fonte do mapa. O `riscv-tools generate-memory-map` (`make generate`) escreve dele o pacote `de0_cv_map_pkg.vhd`, que o topo da placa gerado, o topo de simulação e o projeto do Quartus gerado usam para os limites das regiões e a página da RAM que o hospedeiro compartilha com o programa, além das flags de ligação, do linker script da memória de boot e do `memory_map.h`. O `config.yaml` declara `memory_map: platform.yaml` e recebe do mapa as bases, as palavras e o `tohost`. O verificador `check-memory-map` confere só o que sobra escrito à mão: a memória de boot, o VHDL do núcleo e o cabeçalho dos programas.

Os periféricos ocupam os 2 GiB superiores do espaço de endereços (bit 31 em 1), com uma janela por periférico, de base e tamanho dados pela lista `peripherals` do `platform.yaml` e decodificada pela tabela do pacote de mapa: a UART via JTAG (índice 0, `0xC0000000`), o display de 7 segmentos (índice 1, `0xD0000000`), o CLINT (índice 2, `0xE0000000`, janela de 64 KiB) e o controlador de interrupção externa (índice 3, `0xF0000000`). Um acesso a endereço sem janela termina em falha de acesso. As linhas MTIP, MSIP e MEIP chegam ao núcleo (ver o [interconector](../interconnect/ext_interconnect.md)).

## 6. ACT4

Os ELFs do ACT4 têm o código e as constantes na FLASH e os dados, a pilha e as palavras do HTIF na RAM. O teste `Zifencei-fence.i-00` reescreve o próprio código, e a FLASH ignora stores, então ele usa uma variante do alvo em que o corpo do teste fica na RAM e só a entrada, as macros do modelo e as constantes ficam na FLASH.

## 7. Teste do topo de simulação

O catálogo `tests/python/tests.json` traz as entradas `De0CvBootBanks` (a memória de boot de verdade escolhendo a banca, uma simulação por caso, ver [atualizacao-de-programa.md](atualizacao-de-programa.md)) e `De0CvSimTop`, que roda o topo `rv32im_sdram_flash_sim_test`. A imagem do chip (`SDRAM_FILE`) tem só a FLASH, a partir da palavra 0. A BOOT_MEMORY guarda uma marca na RAM e salta para a FLASH. A FLASH guarda outra marca, escreve no display, instala um tratador de exceção e tenta gravar nela mesma. O teste confere a falha de acesso de causa 7, o `mtval` com o endereço e a palavra intacta no chip. Em seguida a FLASH copia um código para a RAM e salta para ele, e esse guarda a terceira marca e escreve em `tohost`. O teste lê o chip pela porta de depuração do modelo e confere as marcas, o `tohost` e o valor do display. As imagens saem de `tests/python/gen_de0_cv_images.py`, a partir do `platform.yaml`.

O testbench de simulação de programas (`testbench/test_c_program.py`) só inicia o console da UART no primeiro acesso do núcleo à janela da UART (`UART_START_ON_ACCESS` e `UART_INDEX` do `config.yaml`, o segundo igual ao índice da UART na tabela de janelas), porque a memória de boot confere as bancas e a inicialização do programa leva muito mais tempo do que a fila de recepção de 64 bytes segura o que o hospedeiro envia. `UART_SCANS_PER_BYTE` ajusta quantas varreduras separam dois bytes enviados.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
