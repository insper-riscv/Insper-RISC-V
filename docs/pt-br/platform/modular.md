# Plataforma `modular`: os modelos base de simulação

## 1. O que ela é

Um único topo de simulação, `modular_sim_top` (`src/simulation/modular/`), monta o núcleo com a memória de instruções e a de dados dentro ou fora do chip. O que fica fora do chip passa por uma cache e por um modelo de chip simulado, de tamanho configurável. Serve a qualquer variação do núcleo (os genéricos `has_*` escolhem as extensões) e é a base da simulação do ACT4 dos 60 perfis.

## 2. Os modelos

| Modelo | Instruções | Dados | `instr_external` | `data_external` |
| :--- | :--- | :--- | :--- | :--- |
| `integrated` | internas | internos | falso | falso |
| `external-data` | internas | externos, atrás da cache de dados | falso | verdadeiro |
| `external-instruction` | externas, atrás da cache de instruções | internos | verdadeiro | falso |
| `external` | externas, atrás da cache de instruções | externos, atrás da cache de dados | verdadeiro | verdadeiro |
| `external-flash` | externas, FLASH atrás da cache de instruções | externos, atrás da cache de dados | verdadeiro | verdadeiro |

O último modelo é o `external` com o genérico `ext_flash` verdadeiro, o desenho da plataforma [de0-cv](de0-cv.md) com o chip de RAM simulado no lugar do controlador e do chip da SDRAM.

## 3. Mapas de memória

| Região | Mapa A (`ext_flash` falso) | Mapa B (`ext_flash` verdadeiro) |
| :--- | :--- | :--- |
| BOOT_ROM | `0x00000000`, interna | `0x00000000`, interna |
| FLASH | `0x00000800`, interna | `0x20000000`, chip externo |
| RAM interna | `0x00008000` | não existe |
| Chip de RAM externo | `0x40000000` | `0x40000000` |

No mapa A as instruções externas são buscadas no chip de RAM externo, e o mapa B exige os dois lados externos. A BOOT_ROM de cada modelo salta para onde o código está.

## 4. Tamanhos

Todo tamanho é uma potência de dois, verificada em tempo de elaboração pelo `log2_exact` do `utils_pkg`, e um valor fora da regra falha a elaboração.

| Genérico | Unidade | Padrão |
| :--- | :--- | :--- |
| `boot_rom_size_bytes` | bytes | 2048 |
| `flash_size_bytes` | bytes | 1048576 (1 MB) |
| `ram_size_bytes` | bytes | 1048576 (1 MB) |
| `ext_ram_size_bytes` | bytes | 1048576 (1 MB) |
| `icache_size_bits` | bits | 4096 (4 kbit) |
| `dcache_size_bits` | bits | 4096 (4 kbit) |

Os genéricos `flash_first_latency`, `flash_next_latency` e `ext_ram_latency` dão a latência dos chips em bordas de clock.

## 5. Como usar

As imagens entram pelos genéricos `boot_rom_file`, `rom_file`, `ram_file` e `ext_ram_file`, uma palavra de 32 bits por linha em hexadecimal.

| Porta | Uso |
| :--- | :--- |
| `i_clk`, `i_rst` | Clock base e reset |
| `i_dbg_word_addr`, `o_dbg_word_data` | Lê uma palavra do chip de RAM externo pelo índice, sem passar pelas caches. É como o testbench vê o `tohost` quando ele está no chip |
| `o_ram_en`, `o_ram_wren`, `o_ram_addr`, `o_ram_wdata`, `o_ram_byteena` | O barramento da RAM interna do núcleo, que o testbench observa quando a RAM é interna |

O GHDL aloca os arrays das memórias na pilha, então a simulação de memórias de 1 MB pede o limite de pilha elevado (`ulimit -s unlimited` ou `--max-stack-alloc=0`).

## 6. Verificação

`tests/python/runner.py` roda um programa mínimo em cada configuração (`ModularIntegrated`, `ModularExternalData`, `ModularExternalInstruction`, `ModularExternal` e `ModularExternalFlash`). O programa guarda `0x5A`, lê de volta, soma 1 e guarda o resultado na palavra seguinte, e o teste confere as duas palavras na RAM interna ou no chip externo, conforme o modelo. As imagens são geradas por `tests/python/gen_modular_images.py`.
