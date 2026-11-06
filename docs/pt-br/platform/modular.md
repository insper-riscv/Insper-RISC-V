# Plataforma `modular`: os modelos base de simulação

## 1. O que ela é

Um único topo de simulação, `modular_sim_top` (`src/simulation/modular/`), monta o núcleo com a ROM e a RAM cada uma dentro ou fora do chip. O que fica fora do chip passa por uma cache e por um modelo de chip simulado, de tamanho configurável. Serve a qualquer variação do núcleo (os genéricos `has_*` escolhem as extensões) e é a base da simulação do ACT4 dos 60 perfis.

Todos os modelos têm a BOOT_ROM, a memória de inicialização que deixa a CPU num estado conhecido, e a ROM sempre começa logo depois dela.

## 2. Os modelos

| Modelo | ROM | RAM | Caches | `rom_external` | `ram_external` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `integrated` | interna | interna | nenhuma | falso | falso |
| `external-data` | interna | externa | cache de dados | falso | verdadeiro |
| `external-instruction` | externa | interna | cache de instruções | verdadeiro | falso |
| `external` | externa | externa | cache de instruções e cache de dados | verdadeiro | verdadeiro |

Com uma só memória externa, a cache fala direto com o chip (`ram_chip` para a RAM, `flash_chip` para a ROM). Com as duas externas, um roteador por cache separa a ROM da RAM e a ROM tem um árbitro entre as duas caches. No modelo `external-instruction` não há cache de dados, então a ROM externa só é lida como instrução, e o `.rodata` do programa fica na RAM.

## 3. Mapa de memória

O mapa vem de genéricos e vale para o núcleo e para o topo. O valor padrão de cada um está em `src/simulation/modular/platform.yaml`, que é a fonte do mapa, e o `riscv-tools generate-memory-map` o leva ao pacote `modular_map_pkg.vhd` que o topo usa (`make generate`, e `make generate-check` confere no CI). Os valores são os da simulação do ACT4. O pacote traz também os `HAS_*` da plataforma (`HAS_E` entre eles), que são o padrão dos genéricos `has_*`, além de `BOOT_ROM_BITS` (12) e `ROM_STORAGE_BYTES` (1048576). O modelo padrão (`integrated`) é a seção `memory` do `platform.yaml`, de onde saem `ROM_EXTERNAL` e `RAM_EXTERNAL`, os padrões dos genéricos `rom_external` e `ram_external`; cada teste os sobrescreve pelos parâmetros do `tests.json`. As conferências do `riscv-tools check-memory-map` (`checks` do `platform.yaml`) cobrem a cópia manuscrita da base da RAM nos testes. `HAS_ZIMOP` e `HAS_ZICOND` também vêm do pacote, ligados pelo campo `extras` do `platform.yaml` quando a plataforma os usa (a modular não os usa).

| Região | Início | Fim | Genéricos |
| :--- | :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | `0x00001000` | `boot_rom_size_bytes` |
| ROM | logo depois da BOOT_ROM, `0x00001000` | `0x00100000` | `rom_end_kib` |
| RAM | `0x00100000` | `0x00200000` | `ram_base_kib`, `ram_end_kib` |
| Janela externa e periféricos | `0x40000000` | | `ext_base_kib`, `periph_base_kib` |

Nos quatro modelos a janela de periféricos tem o CLINT (id 6, `0xE0000000`) e o controlador de interrupção externa (id 7, `0xF0000000`), cujas saídas são as linhas MTIP, MSIP e MEIP do núcleo, que as habilita com `has_zicsr` (o perfil padrão não o tem). O `mtime` do CLINT conta um tick por ciclo do núcleo (`interrupts` do `platform.yaml`) e é independente do CSR `time`.

Os limites estão em KiB. A BOOT_ROM de cada modelo salta para o início da ROM. O `config.yml` da plataforma que usa o topo é quem escolhe esses valores.

## 4. Tamanhos

Todo tamanho é uma potência de dois, verificada em tempo de elaboração pelo `log2_exact` do `utils_pkg`, e um valor fora da regra falha a elaboração.

| Genérico | Unidade | Padrão |
| :--- | :--- | :--- |
| `boot_rom_size_bytes` | bytes | 4096, múltiplo de 1 KiB |
| `rom_size_bytes` | bytes | 1048576 (1 MB) |
| `ram_size_bytes` | bytes | 1048576 (1 MB) |
| `icache_size_bits` | bits | 4096 (4 kbit) |
| `dcache_size_bits` | bits | 4096 (4 kbit) |

Os genéricos `flash_first_latency`, `flash_next_latency` e `ext_ram_latency` dão a latência dos chips em bordas de clock.

## 5. Como usar

As imagens entram pelos genéricos `boot_rom_file`, `rom_file` e `ram_file`, uma palavra de 32 bits por linha em hexadecimal.

| Porta | Uso |
| :--- | :--- |
| `i_clk`, `i_rst` | Clock base e reset |
| `i_dbg_word_addr`, `o_dbg_word_data` | Lê uma palavra do chip de RAM externo pelo índice, sem passar pelas caches. É como o testbench vê o `tohost` quando ele está no chip |
| `o_ram_en`, `o_ram_wren`, `o_ram_addr`, `o_ram_wdata`, `o_ram_byteena` | O barramento da RAM interna do núcleo, que o testbench observa quando a RAM é interna |

O GHDL aloca os arrays das memórias na pilha, então a simulação de memórias de 1 MB pede o limite de pilha elevado (`ulimit -s unlimited` ou `--max-stack-alloc=0`).

## 6. Verificação

`tests/python/runner.py` roda um programa mínimo em cada modelo (`ModularIntegrated`, `ModularExternalData`, `ModularExternalInstruction` e `ModularExternal`). O programa guarda `0x5A` na base da RAM, lê de volta, soma 1 e guarda o resultado na palavra seguinte, e o teste confere as duas palavras na RAM interna ou no chip externo, conforme o modelo. Os quatro modelos usam as mesmas duas imagens, `boot_to_rom.hex` e `rom_program.hex`, geradas por `tests/python/gen_modular_images.py`.

O `ModularInterrupts` roda o modelo `integrated` com `has_zicsr` ligado e a imagem `rom_irq_program.hex`: o programa escreve o maior valor no `mtimecmp`, lê o `mip` (MTIP baixo), arma o `mtimecmp` poucos ticks à frente do `mtime` e espera o bit MTIP do `mip`. O `mtimecmp` do CLINT é limpo de forma síncrona e o gerador de clock para os clocks durante o reset, então o programa o escreve antes de ler o `mip`.
