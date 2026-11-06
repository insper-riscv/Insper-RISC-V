# Como criar uma nova arquitetura no Insper-RISC-V

Este guia leva a partir de um clone limpo do `Insper-RISC-V` até uma plataforma nova funcionando em simulação (e, se houver placa, na FPGA). Uma plataforma é uma pasta `src/<família>/<plataforma>/` com o seu mapa de memória, a sua seleção de memórias e periféricos e o seu perfil do Core. O exemplo corrente se chama `exemplo`, na família `simulation`, com a RAM maior e o perfil `rv32im` em vez do da plataforma modelo.

## 1. O que é uma plataforma

### 1.1. Os blocos

| Bloco | Repositório | O que entrega |
| :--- | :--- | :--- |
| Core | `Core` | O processador, escolhido por um perfil (base `rv32i` ou `rv32e` mais as extensões) |
| Memory | `Memory` | BOOT_ROM, ROM, RAM, caches, chip de FLASH e roteador de regiões |
| Peripherals | `Peripherals` | UART, GPIO, temporizador e display, cada um com um lado `soc` (independente de família) e um lado por família |
| Common-Components | `Common-Components` | Multiplexadores, registradores e pacotes de utilidades, presentes como submódulo nos outros três |
| Insper-RISC-V | este repositório | Fixa a versão de cada submódulo e traz as plataformas, que ligam os blocos |

### 1.2. O que a plataforma contém

| Arquivo | Escrito por | Conteúdo |
| :--- | :--- | :--- |
| `platform.yaml` | Pessoa | Fonte do mapa de memória, perfil do Core, palavras reservadas, periféricos e arquivos a gerar |
| `rtl/<plataforma>_map_pkg.vhd` | `riscv-tools generate-memory-map` | Constantes VHDL do mapa e do perfil |
| `runtime/rv32im-fpga.specs`, `runtime/boot_rom.ld`, `runtime/memory_map.h` | `riscv-tools generate-memory-map` | Parâmetros do linker, script da BOOT_ROM e endereços do runtime |
| `rtl/<plataforma>_sim_top.vhd` | Pessoa | Topo, que só instancia e conecta os blocos |
| `runtime/boot_rom.S`, `_exit.c`, `stdio.c`, `spike_exit.S` | Pessoa | O que o programa encontra ao iniciar e ao terminar |
| `config.yaml` | Pessoa | Configuração do `riscv-tools` para compilar e simular |

### 1.3. Exemplo de referência

A plataforma `de0-cv` (`src/cyclone-v/de0-cv/`) mostra o caso completo.

```text
 BOOT_ROM 4 KiB          Core (rv32im_...)             periféricos (bit 31 = 1)
 ROM (FLASH) externa  <-- caches de instruções e dados  --> UART sobre JTAG (id 4)
 RAM (SDRAM) externa  <-- roteador de regiões / interconexão --> display (id 5)
```

A plataforma modelo `src/simulation/template/` é a versão mínima, só com memórias internas, e é o ponto de partida do capítulo 3.

## 2. Preparar o ambiente

### 2.1. Clonar

```bash
git clone --recurse-submodules git@github.com:insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| Quatro submódulos baixados (`Common-Components`, `Core`, `Memory`, `Peripherals`) | Pastas de submódulo vazias, por clone sem `--recurse-submodules`. Rode `git submodule update --init --recursive` |

### 2.2. Ferramentas

Os comandos `riscv-tools`, `ghdl`, o GCC com picolibc e o Spike vêm da imagem do Infra. Para rodar um comando dentro dela:

```bash
docker run --rm -v "$PWD":/w -w /w ghcr.io/insper-riscv/dev_tools:latest <comando>
```

Os comandos dos capítulos seguintes que começam por `riscv-tools`, `make` ou `ghdl` rodam assim, ou no shell de um contêiner da mesma imagem. Se o contêiner rodar com outro usuário que o do clone, acrescente `--user "$(id -u):$(id -g)"`.

### 2.3. Estado inicial

```bash
make all
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `paths OK`, `tree OK`, as plataformas elaboram e os testes passam | `ghdl: command not found`, por rodar fora da imagem |

### 2.4. Quartus (só para placa)

Para uma plataforma de FPGA da família Cyclone V, instale o Quartus Prime Lite no host e deixe `quartus_sh`, `quartus_pgm` e `jtagconfig` no `PATH`. O capítulo 10 os usa.

## 3. Criar a pasta da plataforma

### 3.1. Copiar o modelo

```bash
cp -r src/simulation/template src/simulation/exemplo
```

### 3.2. Renomear

Os arquivos que levam o nome da plataforma passam de `template_*` para `exemplo_*`, e a palavra `template` dentro dos arquivos passa para `exemplo`.

```bash
cd src/simulation/exemplo
mv rtl/template_map_pkg.vhd rtl/exemplo_map_pkg.vhd
mv rtl/template_sim_top.vhd rtl/exemplo_sim_top.vhd
grep -rl template . | xargs sed -i 's/template/exemplo/g'
cd ../../..
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `grep -r template src/simulation/exemplo` não acha nada | `check-vhdl-style` acusar nome de entidade diferente do arquivo, por esquecer de renomear um dos dois arquivos de `rtl/` |

## 4. Descrever a plataforma no `platform.yaml`

O `platform.yaml` é a única fonte do mapa. Nada do mapa se escreve à mão em outro arquivo.

### 4.1. Campos

| Campo | O que define |
| :--- | :--- |
| `platform` | Nome da plataforma |
| `profile` | Perfil do Core, no formato `rv32i` ou `rv32e` seguido das extensões (`rv32im`, `rv32im_zicsr`) |
| `profiles` | Caminho de `Core/profiles/matrix.yaml`, a especificação dos perfis |
| `regions` | Cada região com `name`, `base`, `size` (potência de dois ou soma, como `1M-4K`), `kind` (`rom` ou `ram`) e `exec` |
| `reserved` | As três palavras do topo da RAM, `stdout`, `tohost` e `fromhost`, que precisam caber dentro da região de RAM |
| `boot` | `entry`, o endereço do `_start` da ROM, e `wait_restart`, o endereço fixo da rotina de espera |
| `peripherals` | Cada periférico com `name`, `base` e `id` (bits 30:28 do endereço) |
| `generate` | Os arquivos a escrever e os parâmetros do pacote VHDL |
| `config` | O que o `config.yaml` lê do mapa |

### 4.2. Editar

Para o exemplo, a RAM passa a 64 KiB e o perfil a `rv32im`. A RAM começa em `0x8000`, então termina em `0x18000`, e as palavras reservadas descem junto.

```yaml
platform: exemplo
profile: rv32im
regions:
  - {name: BOOT_ROM, base: 0x00000000, size: 4K,  kind: rom, exec: true}
  - {name: ROM,      base: 0x00001000, size: 28K, kind: rom, exec: true}
  - {name: RAM,      base: 0x00008000, size: 64K, kind: ram}
reserved:
  stdout:   {base: 0x00017BE0, size: 1K+8}
  tohost:   {base: 0x00017FE8, size: 8}
  fromhost: {base: 0x00017FF0, size: 8}
```

As linhas `generate` dizem `src/simulation/template/...`; a renomeação do passo 3.2 já as levou para `exemplo`.

### 4.3. Gerar e conferir

```bash
riscv-tools --root . generate-memory-map --platform src/simulation/exemplo/platform.yaml
riscv-tools --root . check-memory-map --platform src/simulation/exemplo/platform.yaml
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| Quatro linhas `generated:` (specs, `boot_rom.ld`, `memory_map.h`, pacote VHDL) e `memory map OK` | `reserved stdout ... is not inside a RAM region`, porque os endereços reservados ficaram fora da RAM depois de mudar o tamanho |
| `HAS_M` verdadeiro e `RAM_END_KIB` igual a 96 no pacote gerado | `profile` com nome que não está em `matrix.yaml` |

Quando o mapa mudar, rode o primeiro comando de novo. O `--check` do mesmo comando falha se algum arquivo gerado estiver fora de data.

### 4.4. Registrar no repositório

O CONTRIBUTING exige atualizar, ao acrescentar arquivos, o `paths.yaml`, o `Makefile` e a documentação. Para a plataforma nova:

| Arquivo | O que acrescentar |
| :--- | :--- |
| `paths.yaml` | Os arquivos da plataforma na lista `references` e os campos de caminho do `config.yaml` |
| `Makefile` | A variável `P<x> := src/simulation/exemplo`, as linhas de `memory-map`, `generate` e `generate-check` e a elaboração do topo em `check-tops`, que lê as fontes do `riscv-tools sources` |
| `paths.yaml` (`provides`) | O componente do topo, com as fontes e o que ele requer; o `scripts/generate_sources.py` ganha o arquivo de lista da plataforma |
| `docs/pt-br/platform/` | Um documento `exemplo.md` e a linha na tabela do `README.md` da pasta, com o espelho em `docs/en/` |

## 5. Escolher o perfil do Core

### 5.1. A regra dos perfis

O nome de um perfil é a base seguida das extensões na ordem de `Core/profiles/matrix.yaml`, ligadas por `_`.

| Parte | Valores |
| :--- | :--- |
| Base | `rv32i` (32 registradores) ou `rv32e` (16) |
| Extensões, nessa ordem | `zicclsm`, `zicsr`, `zicntr`, `zihpm`, `zifencei`, `zmmul`, `m` |

`zicntr` e `zihpm` implicam `zicsr` e por isso o nome nunca cita `zicsr` junto delas; `m` implica `zmmul`, e `m` e `zmmul` não aparecem juntas. Todas as demais combinações são válidas, o que dá 60 perfis. Para listá-los:

```bash
riscv-tools profiles --spec Core/profiles/matrix.yaml --format names
```

### 5.2. Como o topo passa o perfil ao `core`

O `generate-memory-map` escreve no pacote uma constante `HAS_*` por extensão (`HAS_E`, `HAS_M`, `HAS_ZICSR` e as outras). O topo as liga aos genéricos de mesmo nome do `core`, e o valor vem do `profile` do `platform.yaml` (passo 6.3).

### 5.3. Perfil que não existe

Se nenhum perfil serve, a extensão nova entra em `Core/profiles/matrix.yaml` como pull request no repositório `Core`, com a pasta da extensão em `Core/src/<extensão>/`. O guia de contribuição do `Core` descreve o caminho. Depois disso, o ponteiro do submódulo neste repositório avança e o perfil novo vale em todas as plataformas.

## 6. Escrever o topo

### 6.1. Estrutura do `<plataforma>_sim_top.vhd`

O topo de simulação da plataforma modelo tem seis blocos, que o exemplo mantém.

| Instância | Entidade | Origem |
| :--- | :--- | :--- |
| `u_clock` | `clk_gen_3way` | `src/simulation/internal-mem/rtl/` |
| `u_core` | `core` | `Core/src/core/` |
| `u_boot_rom` | `rom_simulation` | `Memory/src/ROM/SoC/` |
| `u_rom` | `rom_simulation` (duas portas) | `Memory/src/ROM/SoC/` |
| `u_ram` | `ram_simulation` | `Memory/src/RAM/SoC/` |
| `u_uart` (opcional) | `jtag_uart` | `Peripherals/src/UART/jtag/` |

O núcleo tem três saídas de memória: a busca de instrução (BOOT_ROM e ROM), a porta de dados da ROM e da RAM, e o barramento externo, por onde passam os periféricos.

### 6.2. Genéricos de tamanho

Os tamanhos das memórias são genéricos em potência de dois, cujo valor padrão vem do pacote gerado (`BOOT_ROM_SIZE_BYTES`, `ROM_STORAGE_BYTES`, `RAM_STORAGE_BYTES`). Não se escreve um tamanho no topo.

### 6.3. Perfil e mapa no `core`

No `generic map` do `core`, cada `has_*` recebe a constante `HAS_*` do pacote, e os limites das regiões (`rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib`) recebem as constantes de mesmo nome. Se o perfil do passo 4.2 liga o `M`, `HAS_M` já chega verdadeiro, e nada mais muda no topo.

### 6.4. Janela de cada periférico

O barramento externo do núcleo entrega ao topo o endereço, o dado de escrita e os enables de leitura e escrita. A UART responde quando os quatro bits mais altos do endereço são os de `UART_BASE`, que vem do pacote, e o dado lido volta ao núcleo no ciclo seguinte ao pedido. Para um periférico novo, repita o padrão: um seletor pelo endereço, os enables filtrados pelo seletor, o dado de leitura registrado. Para vários periféricos numa plataforma de placa, use a interconexão `ext_interconnect` do `src/interconnect/`, que separa a SDRAM da janela de periféricos e entrega o deslocamento de palavra a cada um (`de0-cv_top.vhd` mostra o uso).

### 6.5. Convenções do CONTRIBUTING

| Regra | Aplicação no topo |
| :--- | :--- |
| Portas `i_` e `o_` | `i_clk`, `i_rst`, `o_uart_tdo` |
| Rótulos `u_` | `u_core`, `u_ram` |
| Cabeçalho de 72 colunas | Bloco `-- ====` no início do arquivo, em português |
| Docstring por declaração | Um comentário em português acima de cada generic, port, signal e constant |
| Instanciação direta | `u_x : entity work.nome`, sem `component` |

### 6.6. Conferir

```bash
riscv-tools --root . check-vhdl-style
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `vhdl style OK` | Uma declaração sem o comentário acima dela, ou porta sem prefixo |

### 6.7. Elaborar

```bash
mkdir -p build/exemplo
ghdl -a --std=08 --workdir=build/exemplo $(riscv-tools vhdl-sort \
    $(find Common-Components/src Core/src -name '*.vhd' -not -path 'Core/src/common/*') \
    Memory/src/RAM/SoC/ram_simulation.vhd Memory/src/ROM/SoC/rom_simulation.vhd \
    Peripherals/src/UART/jtag/jtag_uart.vhd \
    src/simulation/internal-mem/rtl/clk_gen_3way.vhd \
    src/simulation/exemplo/rtl/*.vhd)
ghdl -e --std=08 --workdir=build/exemplo exemplo_sim_top
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| Nenhuma mensagem de erro | `unit "..." not found`, por faltar um arquivo na lista ou por ela fora de ordem (o `vhdl-sort` ordena) |

## 7. Runtime

O runtime é o que o programa encontra ao iniciar e ao terminar. Os quatro arquivos escritos à mão vêm do modelo, e o mapa chega a eles pelos três arquivos gerados no capítulo 4.

### 7.1. Os arquivos

| Arquivo | O que faz | O que muda com o mapa |
| :--- | :--- | :--- |
| `runtime/boot_rom.S` | `_reset` zera `stdout`, `tohost` e `fromhost` e salta para `RV32_BOOT_ENTRY`; `rv32_wait_restart` espera o `fromhost` | Nada, lê os endereços de `memory_map.h` |
| `runtime/boot_rom.ld` | Script de ligação da BOOT_ROM, com `rv32_wait_restart` em `0x100` | Gerado |
| `runtime/rv32im-fpga.specs` | Parâmetros do linker (`__flash`, `__flash_size`, `__ram`, `__ram_size`) e o crt0 da picolibc | Gerado |
| `runtime/memory_map.h` | Endereços de RAM, `tohost`, `fromhost`, `stdout`, entrada de boot e UART | Gerado |
| `runtime/_exit.c` | Escreve o resultado em `tohost` e entra em `rv32_wait_restart` | Nada |
| `runtime/stdio.c` | Leva `printf` e `putchar` ao buffer de `stdout` na RAM | Nada |
| `runtime/spike_exit.S` | O mesmo fim de programa para o ELF do Spike | Nada |

### 7.2. Como o `tohost` termina um programa

| Valor escrito em `tohost` | Significado |
| :--- | :--- |
| `1` | Programa aprovado (`main` retornou 0) |
| `(código << 1) \| 1` | Programa falhou com o código dado |
| `0` | Ainda não terminou |

O testbench observa as escritas no barramento da RAM, e a primeira escrita diferente de zero no endereço de `tohost` encerra a simulação com o resultado.

### 7.3. Conferir

```bash
make memory-map
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `memory map OK` e `generated files OK` | `generated files are out of date`, por editar o `platform.yaml` sem rodar o `generate-memory-map` de novo |

## 8. Topo de simulação e primeiro programa

### 8.1. O `config.yaml`

Ele reúne, para o `riscv-tools`, o que é da plataforma.

| Seção | Conteúdo |
| :--- | :--- |
| `toolchain` | GCC, `objcopy` e o `rv32im-fpga.specs` da plataforma |
| `memory_map` | `platform.yaml`, de onde vêm as bases, o `tohost` e o `fromhost` |
| `paths` | Fontes do runtime (`_exit.c`, `stdio.c`), `boot_rom.S` e `boot_rom.ld` |
| `sim.toplevel` | `exemplo_sim_top` |
| `sim.vhdl_sources` | Todas as fontes, em ordem de dependência, escritas pelo `make generate-sources` |
| `sim.test_module`, `sim.python_path` | O testbench cocotb, `testbench.test_c_program` da plataforma `internal-mem` |
| `sim.parameters` | `BOOT_ROM_FILE` e `ROM_FILE` com as imagens de cada programa |
| `emulator.sources` | `spike_exit.S` |

A lista `sim.vhdl_sources` não se edita à mão. Ela vem do componente do topo no `provides` do `paths.yaml` da plataforma, que declara os componentes que o topo requer, e o `make generate-sources` a escreve na ordem de análise. Se o topo ganhar um periférico, o componente dele entra no `requires` do topo e a lista é regenerada.

### 8.2. O testbench

O `testbench/test_c_program.py` da `internal-mem` roda o clock, solta o reset, observa as escritas no barramento da RAM (`ram_addr`, `ram_wren`, `ram_en`, `ram_wdata`, `ram_byteena`) e para no `tohost`. Qualquer topo que exponha esses sinais com esses nomes o reutiliza, e o do exemplo os expõe.

### 8.3. O primeiro programa

Os programas ficam no repositório `Tests` (`asm/` e `c/`). Ele estende o `config.yaml` de cada plataforma por um arquivo gerado.

```bash
cd Tests
riscv-tools platform sync --prefix Insper-RISC-V \
    --source Insper-RISC-V/src/simulation/exemplo/config.yaml \
    --output tools/riscv_build/config.platform-exemplo.yaml
```

Crie `tools/riscv_build/config.exemplo.yaml` com o conteúdo abaixo e rode um programa de `Tests/asm/`.

```yaml
extends: config.platform-exemplo.yaml
paths:
  include_dir: tools/riscv_build/include
  build_dir: build-exemplo
  c_dir: c
  asm_dir: asm
```

```bash
riscv-tools --config tools/riscv_build/config.exemplo.yaml compile --emit hex --only arithmetic-add
riscv-tools --config tools/riscv_build/config.exemplo.yaml sim --only arithmetic-add
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `PASS` do programa, com o `tohost` lido do barramento | `timeout` sem `tohost`, quando a BOOT_ROM não salta para a ROM (`boot.entry` diferente do início da ROM) ou o programa foi ligado para outro mapa |
| `compile` gera `manifest.json` com o programa | Erro de ligação com `region ... overflowed`, quando o programa não cabe na ROM de 28 KiB |

## 9. Certificação

### 9.1. O que se gera

O ACT4 exige um alvo por perfil: o YAML do UDB, a configuração do Sail, o `test_config.yaml`, as macros do modelo e o script de ligação. O repositório `Certification` os gera com `tools/riscv_build/gen_profiles.py` para cada perfil de `Core/profiles/matrix.yaml`, a partir do mapa da plataforma. O `riscv-tools profiles` lista os perfis que valem para a plataforma.

### 9.2. Rodar o perfil escolhido

```bash
cd Certification
riscv-tools --config tools/riscv_build/config.profile-rv32im.yaml certify
```

Para restringir às extensões do perfil, acrescente `--extensions I,M`. O comando constrói a suíte para o alvo, compila os testes com o GCC, simula no GHDL e compara o resultado com o Sail.

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| Todos os testes do perfil aprovados | Falha em teste que escreve código na ROM (`Zifencei-fence.i`), porque a ROM ignora stores. O alvo usa a variante com o corpo do teste na RAM |
| Alvo e configuração do perfil existentes depois do `gen_profiles.py` | `profile ... not found`, porque o perfil da plataforma não está em `matrix.yaml` |

## 10. Placa

Este capítulo vale só se a plataforma tem uma FPGA. A `de0-cv` é a referência.

### 10.1. Arquivos do projeto do Quartus

| Arquivo | Conteúdo |
| :--- | :--- |
| `<plataforma>.qpf` | O projeto, com a revisão |
| `<plataforma>.qsf` | Dispositivo, pinos e a lista de fontes VHDL e IP, escrita pelo `make generate-sources` e conferida contra o disco pelo `check-paths` |
| `<plataforma>.sdc` | Os clocks e as restrições de entrada e saída, escritos a partir dos clocks da plataforma |
| `pll/` | A IP do PLL que gera os clocks do núcleo |
| `<plataforma>_synth.tcl` | Compila com a semente escolhida; com o argumento `map` só sintetiza |
| `<plataforma>_program.sh` | Programa o `.sof` pelo primeiro cabo do `jtagconfig` |
| `<plataforma>_top.vhd` | O topo da placa, que liga o PLL, o núcleo, as memórias da placa e os periféricos |

### 10.2. Restrições de tempo

O `.sdc` declara o clock de entrada (`create_clock`), os clocks do PLL (`derive_pll_clocks`) e a incerteza (`derive_clock_uncertainty`). Cada clock externo gerado (por exemplo o da SDRAM) ganha o seu `create_generated_clock` e os atrasos de entrada e saída do datasheet do chip.

### 10.3. Compilar e programar

```bash
quartus_sh -t src/<família>/<plataforma>/<plataforma>_synth.tcl && src/<família>/<plataforma>/<plataforma>_program.sh
```

Os dois comandos precisam sair no mesmo shell (`&&`). O guia [placa.md](placa.md) explica a regra e o que fazer quando a placa não responde.

### 10.4. Programas e certificação na placa

```bash
riscv-tools --config tools/riscv_build/config.<plataforma>.yaml run --skip-reconfigure --skip-recompile --only arithmetic-add
```

O `certify-board` roda o ACT4 do perfil escolhido na placa, com a configuração `config.flash-board-<perfil>.yaml` do repositório `Certification`.

### 10.5. Relatório de tempo

Depois da compilação, o relatório do Timing Analyzer fica em `output_files/<plataforma>.sta.rpt`. Os números de interesse são o Fmax de cada clock e o pior slack de setup e de hold. Um slack negativo de setup indica um caminho mais longo que o período do clock. Para listar os caminhos críticos, use `riscv-tools timing-paths`.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
