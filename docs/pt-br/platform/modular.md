# Plataforma `modular`: memórias e caches em qualquer combinação

## 1. O que ela é

Um único topo de simulação, `modular_sim_top` (`src/simulation/modular/`), monta o núcleo com quatro escolhas independentes: a ROM e a RAM dentro ou fora do chip, e a cache de instruções e a de dados presentes ou não. Uma memória que o núcleo alcança pela porta (externa, ou interna atrás de uma cache) fica num modelo de chip simulado, de tamanho configurável. Serve a qualquer variação do núcleo (os genéricos `has_*` escolhem as extensões), roda os programas dos repositórios de teste (seção 7) e é a base da simulação do ACT4 dos 60 perfis.

Todas as combinações têm a BOOT_ROM, a memória de inicialização que deixa a CPU num estado conhecido, e a ROM sempre começa logo depois dela.

## 2. As escolhas e as arquiteturas

| Escolha | Genérico | Valores |
| :--- | :--- | :--- |
| ROM | `rom_external` | interna (falso) ou externa (verdadeiro) |
| RAM | `ram_external` | interna (falso) ou externa (verdadeiro) |
| Cache de instruções | `has_icache` | sem ou com |
| Cache de dados | `has_dcache` | sem ou com |

O núcleo só conhece o protocolo da porta, então uma cache só existe do lado dele. As duas condições abaixo dizem quando o núcleo alcança cada memória pela porta.

$$\text{rom\_via\_porta} = \text{rom\_external} \lor \text{has\_icache} \qquad \text{ram\_via\_porta} = \text{ram\_external} \lor \text{has\_dcache}$$

Os genéricos `rom_external` e `ram_external` do núcleo recebem esses dois valores. A posição física (interna ou externa) não muda a simulação além disso, porque o chip simulado faz o papel da memória em qualquer das duas. As 16 combinações resultam em 9 estruturas distintas, uma por par de lados.

| Lado da ROM | Busca de instrução | Dado da ROM |
| :--- | :--- | :--- |
| Do núcleo (não via porta) | FLASH interna de duas portas | Segunda porta da FLASH interna |
| Via porta, sem cache | Ponte de busca, que guarda só a linha corrente | Roteador dos dados, árbitro e chip de FLASH |
| Via porta, com cache | Cache de instruções | Roteador dos dados, árbitro e chip de FLASH |

| Lado da RAM | Acesso a dados |
| :--- | :--- |
| Do núcleo (não via porta) | RAM interna do núcleo |
| Via porta, sem cache | Interconexão, palavra a palavra, direto ao chip de RAM |
| Via porta, com cache | Interconexão, cache de dados e chip de RAM |

As quatro arquiteturas que os repositórios de teste e o ACT4 usam são as seguintes.

| Arquitetura | `--memory` | ROM | RAM | Caches |
| :--- | :--- | :--- | :--- | :--- |
| A | `rom=int,ram=int,icache=off,dcache=off` | interna | interna | nenhuma |
| B | `rom=int,ram=ext,icache=off,dcache=on` | interna | externa | de dados |
| C | `rom=ext,ram=int,icache=on,dcache=off` | externa | interna | de instruções |
| D | `rom=ext,ram=ext,icache=on,dcache=on` | externa | externa | as duas |

Os genéricos `has_icache` e `has_dcache` valem, quando não informados, `rom_external` ou `HAS_ICACHE` do pacote e `ram_external` ou `HAS_DCACHE` do pacote. Os quatro modelos originais (`integrated`, `external-data`, `external-instruction` e `external`) continuam sendo as arquiteturas A, B, C e D, escolhidas só por `rom_external` e `ram_external`.

## 3. Caminhos de dados

### 3.1. Dados via porta

Quando a ROM ou a RAM é via porta, o núcleo tem o barramento externo de dados. A interconexão separa a janela de periféricos e entrega o pedido à cache de dados ou, sem ela, direto ao lado da memória, com os endereços do mapa e uma palavra por vez.

| ROM via porta | RAM via porta | Destino dos pedidos de dados |
| :--- | :--- | :--- |
| não | sim | Chip de RAM |
| sim | não | Roteador dos dados: a ROM vai ao chip de FLASH e o que cai fora dela responde zero |
| sim | sim | Roteador dos dados: a ROM vai ao chip de FLASH e o resto ao chip de RAM |

Com a ROM via porta, o roteador dos dados e o árbitro da FLASH ficam entre o núcleo e o chip, e a busca de instruções é a outra entrada do árbitro. Com as duas via porta, um segundo roteador leva a busca à FLASH ou ao chip de RAM.

### 3.2. Dado lido sem cache de dados

O estágio de escrita (WB) lê o dado de um load depois que o pedido termina, e o endereço do núcleo já mudou nessa hora. A cache de dados guarda o dado, mas sem ela o roteador dos dados escolheria a região pelo endereço novo e entregaria o dado errado. O roteador dos dados usa então `hold_rdata`, que faz o dado lido seguir a região do último pedido concluído (documentado no `mem_region_router` do Memory).

### 3.3. Memória interna com cache e memória externa sem cache

| Combinação | Como a simulação a monta |
| :--- | :--- |
| Memória interna com cache | A cache fica sobre o modelo de chip, com a latência dos genéricos do chip; a cache só soma latência numa falha |
| ROM externa sem cache de instruções | A ponte de busca lê o chip de FLASH, que atende pedido de palavra e de linha |
| RAM externa sem cache de dados | A interconexão fala com o chip de RAM em pedidos de palavra |

Os dois chips simulados atendem pedidos de palavra sem cache. A FLASH e a SDRAM da placa DE0-CV ficam atrás das caches no topo da placa, que não muda com a escolha.

## 4. Mapa de memória

O mapa vem de genéricos e vale para o núcleo e para o topo. O valor padrão de cada um está em `src/simulation/modular/platform.yaml`, que é a fonte do mapa, e o `riscv-tools generate-memory-map` o leva ao pacote `modular_map_pkg.vhd` que o topo usa, ao cabeçalho `memory_map.h` do runtime, ao arquivo de specs do ligador e ao script de ligação da BOOT_ROM (`make generate`, e `make generate-check` confere no CI). Os valores são os da simulação do ACT4. O pacote traz também os `HAS_*` da plataforma (`HAS_E` entre eles), que são o padrão dos genéricos `has_*`, além de `BOOT_ROM_BITS` (12) e `ROM_STORAGE_BYTES` (1048576). A escolha padrão é a seção `memory` do `platform.yaml` (as duas memórias do núcleo, sem cache), de onde saem `ROM_EXTERNAL`, `RAM_EXTERNAL`, `HAS_ICACHE` e `HAS_DCACHE`; `--memory` do `riscv-tools` a troca para uma execução, e cada teste a sobrescreve pelos parâmetros do `tests.json`. As conferências do `riscv-tools check-memory-map` (`checks` do `platform.yaml`) cobrem a cópia manuscrita da base da RAM nos testes e o cabeçalho de plataforma do repositório de teste. `HAS_ZIMOP` e `HAS_ZICOND` vêm do pacote, ligados pelo campo `extras` do `platform.yaml`.

| Região | Início | Fim | Genéricos |
| :--- | :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | `0x00001000` | `boot_rom_size_bytes` |
| ROM | logo depois da BOOT_ROM, `0x00001000` | `0x00100000` | `rom_end_kib` |
| RAM | `0x00100000` | `0x00200000` | `ram_base_kib`, `ram_end_kib` |
| Janela externa e periféricos | `0x80000000` | | `ext_base_kib`, `periph_base_kib` |

Os limites estão em KiB. As palavras que o hospedeiro e o programa compartilham (a saída padrão, `tohost` e `fromhost`) ficam no topo da RAM, na última página de 4 KiB, que as caches contornam. A BOOT_ROM zera essas palavras e salta para o início da ROM.

## 5. Tamanhos

Todo tamanho é uma potência de dois, verificada em tempo de elaboração pelo `log2_exact` do `utils_pkg`, e um valor fora da regra falha a elaboração.

| Genérico | Unidade | Padrão |
| :--- | :--- | :--- |
| `boot_rom_size_bytes` | bytes | 4096, múltiplo de 1 KiB |
| `rom_size_bytes` | bytes | 1048576 (1 MB) |
| `ram_size_bytes` | bytes | 1048576 (1 MB) |
| `icache_size_bits` | bits | 4096 (4 kbit) |
| `dcache_size_bits` | bits | 4096 (4 kbit) |

Os genéricos `flash_first_latency`, `flash_next_latency` e `ext_ram_latency` dão a latência dos chips em bordas de clock.

## 6. Como usar

As imagens entram pelos genéricos `boot_rom_file`, `rom_file` e `ram_file`, uma palavra de 32 bits por linha em hexadecimal.

| Porta | Uso |
| :--- | :--- |
| `i_clk`, `i_rst` | Clock base e reset |
| `i_dbg_word_addr`, `o_dbg_word_data` | Lê uma palavra do chip de RAM pelo índice, sem passar pelas caches. É como o testbench vê o `tohost` quando ele está no chip |
| `o_ram_en`, `o_ram_wren`, `o_ram_addr`, `o_ram_wdata`, `o_ram_byteena` | O barramento da RAM interna do núcleo, que o testbench observa quando a RAM é do núcleo |

O GHDL aloca os arrays das memórias na pilha, então a simulação de memórias de 1 MB pede o limite de pilha elevado (`ulimit -s unlimited` ou `--max-stack-alloc=0`).

## 7. Programas dos repositórios de teste

O `src/simulation/modular/config.yaml` leva a plataforma ao `riscv-tools`: o runtime (`boot_rom.S`, `_exit.c`, `stdio.c`, `spike_exit.S`), o script de ligação e o arquivo de specs gerados do mapa, o testbench cocotb e a lista de fontes VHDL. Nada do mapa é escrito nele. O perfil e as memórias de uma execução vêm da linha de comando, sem alterar arquivo versionado.

```bash
ulimit -s unlimited
riscv-tools --profile rv32im_zicclsm_zicntr_zihpm_zifencei \
  --memory rom=ext,ram=int,icache=on,dcache=off \
  platform sync --prefix Insper-RISC-V \
  --source Insper-RISC-V/src/simulation/modular/config.yaml \
  --output tools/riscv_build/config.generated.yaml
```

O comando escreve, no repositório de teste, o `config.generated.yaml` com os genéricos `ROM_EXTERNAL`, `RAM_EXTERNAL`, `HAS_ICACHE`, `HAS_DCACHE` e os `HAS_*` do perfil. Um arquivo que o estenda e aponte `paths.include_dir` para o diretório de cabeçalhos da plataforma modular (`tools/riscv_build/include-modular` do repositório de teste, com o mapa da seção 4) compila e simula os programas de `c/` e `asm/` com `compile --emit hex` e `sim`.

| Item | Comportamento na plataforma modular |
| :--- | :--- |
| BOOT_ROM | Zera o cabeçalho da saída padrão, `tohost` e `fromhost` e salta para a ROM; não executa `fence.i`, porque a simulação parte de caches vazias |
| Saída padrão | Buffer linear de 1 KiB no topo da RAM |
| UART e display | Sem periférico ligado: os programas `uart-echo`, `uart-tx` e `uart-errors` não se aplicam |
| Testbench | Vigia o barramento da RAM do núcleo e o barramento externo ao mesmo tempo, detecta a escrita de `tohost` e, nos testes com `golden.json`, confere a RAM reconstruída das escritas |
| Tempo limite | 2000000 ciclos do núcleo |

## 8. Verificação

`tests/python/runner.py` roda um programa mínimo nas estruturas da seção 2. O programa guarda `0x5A` na base da RAM, lê de volta, soma 1 e guarda o resultado na palavra seguinte, e o teste confere as duas palavras na RAM do núcleo ou no chip externo. Todas as entradas usam as mesmas duas imagens, `boot_to_rom.hex` e `rom_program.hex`, geradas por `tests/python/gen_modular_images.py`.

| Entrada de `tests.json` | ROM | RAM |
| :--- | :--- | :--- |
| `ModularIntegrated` (A) | do núcleo | do núcleo |
| `ModularExternalData` (B) | do núcleo | via porta, cache de dados |
| `ModularExternalInstruction` (C) | via porta, cache de instruções | do núcleo |
| `ModularExternal` (D) | via porta, cache de instruções | via porta, cache de dados |
| `ModularRomBridge` | via porta, ponte de busca | do núcleo |
| `ModularRamDirect` | do núcleo | via porta, direto |
| `ModularBridgeDirect` | via porta, ponte de busca | via porta, direto |
| `ModularBridgeDcache` | via porta, ponte de busca | via porta, cache de dados |
| `ModularIcacheDirect` | via porta, cache de instruções | via porta, direto |
| `ModularInternalCaches` | interna com cache de instruções | interna com cache de dados |
| `ModularInterrupts` | do núcleo, com `has_zicsr` e CLINT na janela de periféricos | do núcleo |

As entradas que estendem `ModularIntegrated` (`extends` no `tests.json`) herdam a lista de fontes e trocam só os parâmetros. `make check-tops` elabora o topo e `make check-generics` confere que o topo declara todo `HAS_*` do pacote gerado.

O `ModularInterrupts` roda o modelo `integrated` com `has_zicsr` ligado e a imagem `rom_irq_program.hex`: o programa escreve o maior valor no `mtimecmp`, lê o `mip` (MTIP baixo), arma o `mtimecmp` poucos ticks à frente do `mtime` e espera o bit MTIP do `mip`. O `mtimecmp` do CLINT é limpo de forma síncrona e o gerador de clock para os clocks durante o reset, então o programa o escreve antes de ler o `mip`.
