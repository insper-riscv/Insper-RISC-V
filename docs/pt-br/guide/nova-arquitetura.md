# Como criar uma nova arquitetura no Insper-RISC-V

Este guia leva a partir de um clone limpo do `Insper-RISC-V` até uma plataforma nova funcionando em simulação, com o seu programa rodando no projeto de testes e o seu perfil certificado, e, se houver placa, até a FPGA. Uma plataforma é uma pasta `src/<família>/<plataforma>/` com o seu mapa de memória, a sua seleção de memórias e periféricos e o seu perfil do Core. O exemplo corrente se chama `exemplo`, na família `simulation`, com a RAM de 64 KiB e o perfil `rv32im` no lugar do `rv32i` da plataforma modelo. Os capítulos 11 e 12 acrescentam um periférico e um tipo de memória, o capítulo 13 leva o conjunto a um pull request, e o capítulo 14 reúne a referência.

## 1. O que é uma plataforma

### 1.1. Os blocos

| Bloco | Repositório | O que entrega |
| :--- | :--- | :--- |
| Core | `Core` | O processador, escolhido por um perfil (base `rv32i` ou `rv32e` mais as extensões) |
| Memory | `Memory` | BOOT_MEMORY, ROM e FLASH (inclusive a FLASH de duas portas), RAM e SDRAM, caches, chip de FLASH e roteador de regiões |
| Peripherals | `Peripherals` | UART, GPIO, temporizador, CLINT, controlador de interrupção externa, controlador de FLASH e display, cada um com um lado `soc` (independente de família) e, quando precisa, um lado por família |
| Common-Components | `Common-Components` | Multiplexadores, registradores e pacotes de utilidades, presentes como submódulo nos outros três |
| Insper-RISC-V | este repositório | Fixa a versão de cada submódulo e traz as plataformas, que ligam os blocos |

### 1.2. O que a plataforma contém

| Arquivo | Escrito por | Conteúdo |
| :--- | :--- | :--- |
| `platform.yaml` | Pessoa | Fonte do mapa de memória, do perfil do Core, das palavras reservadas e dos periféricos, e a lista dos arquivos a gerar |
| `rtl/<plataforma>_map_pkg.vhd` | `riscv-tools generate-memory-map` | Constantes VHDL do mapa e do perfil |
| `runtime/rv32im-fpga.specs`, `runtime/boot_memory.ld`, `runtime/memory_map.h` | `riscv-tools generate-memory-map` | Parâmetros do linker, script de ligação da BOOT_MEMORY e endereços do runtime |
| `rtl/<plataforma>_sim_top.vhd` | Pessoa | Topo de simulação, que só instancia e conecta os blocos |
| `runtime/boot_memory.S`, `_exit.c`, `stdio.c`, `spike_exit.S` | Pessoa | O que o programa encontra ao iniciar e ao terminar |
| `config.yaml` | Pessoa | Configuração do `riscv-tools` para compilar e simular, que lê o mapa do `platform.yaml` |

Nenhum número do mapa se escreve em dois lugares. O que o `config.yaml` e o `Tests` precisam do mapa chega a eles pelo `platform.yaml`.

### 1.3. Plataformas de referência

| Plataforma | Caminho | Quando copiar |
| :--- | :--- | :--- |
| `template` | `src/simulation/template/` | Ponto de partida de uma plataforma só de simulação, com BOOT_MEMORY, ROM e RAM dentro do chip |
| `external-data` | `src/cyclone-v/external-data/` | Ponto de partida de uma placa DE0-CV, com a FLASH de duas portas dentro da FPGA e a SDRAM atrás da cache de dados |
| `de0-cv` | `src/cyclone-v/de0-cv/` | Placa DE0-CV completa, com a FLASH como chip atrás das caches de instruções e de dados |

A plataforma modelo tem esta forma.

```text
  BOOT_MEMORY 4 KiB  --+
  ROM 28 KiB      --+--  núcleo (perfil do platform.yaml)  --  RAM 32 KiB
  (duas portas)                     |
                                    +-- janela de periféricos (bit 31 = 1) -- UART sobre JTAG (id 4)
```

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

Os comandos `riscv-tools`, `ghdl`, o GCC com picolibc e o Spike vêm da imagem `dev_tools` do Infra. Para rodar um comando dentro dela:

```bash
docker run --rm -v "$PWD":/w -w /w ghcr.io/insper-riscv/dev_tools:latest <comando>
```

Os comandos dos capítulos seguintes que começam por `riscv-tools`, `make` ou `ghdl` rodam assim, ou no shell de um contêiner da mesma imagem. Se o contêiner rodar com outro usuário que o do clone, acrescente `--user "$(id -u):$(id -g)"`, e `-e HOME=/w/.home` quando a ferramenta precisar gravar no diretório pessoal.

### 2.3. Estado inicial

```bash
make all
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `paths OK`, `tree OK`, os topos de todas as plataformas elaboram, os testes passam e `formal: all expectations met` | `ghdl: command not found`, por rodar fora da imagem |

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
| `regions` | Cada região com `name`, `base`, `size` (inteiro com sufixo `K`, `M` ou soma, como `1M-4K`), `kind` (`rom` ou `ram`) e `exec` |
| `reserved` | As três palavras do topo da RAM, `stdout`, `tohost` e `fromhost`, que precisam caber dentro da região de RAM |
| `boot` | `entry`, o endereço do `_start` da ROM, e `wait_restart`, o endereço fixo da rotina de espera |
| `peripherals` | Cada periférico com `name`, `base` e `id` (bits 30:28 do endereço) |
| `generate` | Os arquivos a escrever e os parâmetros do pacote VHDL |
| `config` | O que o `config.yaml` lê do mapa |
| `checks` | Onde moram as cópias escritas à mão que o `check-memory-map` confere |

A tabela completa, com os campos das plataformas de placa, está no capítulo 14.

### 4.2. Editar

Para o exemplo, a RAM passa a 64 KiB e o perfil a `rv32im`. A RAM começa em `0x8000`, então termina em `0x18000`, e as palavras reservadas descem junto.

```yaml
platform: exemplo
profile: rv32im
regions:
  - {name: BOOT_MEMORY, base: 0x00000000, size: 4K,  kind: rom, exec: true}
  - {name: ROM,      base: 0x00001000, size: 28K, kind: rom, exec: true}
  - {name: RAM,      base: 0x00008000, size: 64K, kind: ram}
reserved:
  stdout:   {base: 0x00017BE0, size: 1K+8}
  tohost:   {base: 0x00017FE8, size: 8}
  fromhost: {base: 0x00017FF0, size: 8}
```

As linhas `generate` dizem `src/simulation/template/...`, e a renomeação do passo 3.2 já as levou para `exemplo`.

### 4.3. Gerar e conferir

```bash
riscv-tools --root . generate-memory-map --platform src/simulation/exemplo/platform.yaml
riscv-tools --root . check-memory-map --platform src/simulation/exemplo/platform.yaml
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| Quatro linhas `generated:` (specs, `boot_memory.ld`, `memory_map.h`, pacote VHDL) e `memory map OK` | `reserved stdout ... is not inside a RAM region`, porque os endereços reservados ficaram fora da RAM depois de mudar o tamanho |
| `HAS_M` verdadeiro e `RAM_END_KIB` igual a 96 no pacote gerado | `profile` com nome que não está em `matrix.yaml` |

Quando o mapa mudar, rode o primeiro comando de novo. Com `--check` no fim, o mesmo comando não escreve nada e falha se algum arquivo gerado estiver fora de data.

### 4.4. Registrar no repositório

Todo arquivo versionado novo entra nas listas do repositório, e o `make paths` falha enquanto uma delas estiver incompleta. Os comandos abaixo copiam, para a plataforma nova, o que a plataforma modelo tem em cada lista.

O `paths.yaml` ganha as linhas da plataforma e a sua `platform.yaml` na lista de plataformas.

```bash
awk '/^  - \{name: template /{l=$0; gsub(/template/,"exemplo",l); b=b l "\n"; last=NR} {a[NR]=$0} END{for(i=1;i<=NR;i++){print a[i]; if(i==last) printf "%s", b}}' paths.yaml > paths.novo
mv paths.novo paths.yaml
sed -i 's#src/simulation/template/platform.yaml\]}#src/simulation/template/platform.yaml, src/simulation/exemplo/platform.yaml]}#' paths.yaml
```

O teste de integração do topo é uma cópia do da plataforma modelo, com as suas imagens, e entra no `tests/python/tests.json`.

```bash
cp tests/python/gen_template_images.py tests/python/gen_exemplo_images.py
cp tests/python/unittests/rtl/template_sim_top.py tests/python/unittests/rtl/exemplo_sim_top.py
sed -i 's/template/exemplo/g' tests/python/gen_exemplo_images.py
mkdir -p tests/python/unittests/rtl/data/exemplo
PYTHONPATH=. /opt/riscv-tools/riscv-tools/bin/python tests/python/gen_exemplo_images.py
python3 - <<'EOF'
import json
caminho = "tests/python/tests.json"
dados = json.load(open(caminho))
dados["ExemploSimTop"] = json.loads(json.dumps(dados["TemplateSimTop"]).replace("template", "exemplo"))
json.dump(dados, open(caminho, "w"), indent=4)
open(caminho, "a").write("\n")
EOF
```

O teste lê a base da RAM em `RAM_BASE`, no começo de `exemplo_sim_top.py`, e esse valor muda junto com a região de RAM do `platform.yaml`.

O `Makefile` ganha as linhas abaixo, cada uma ao lado da sua equivalente da plataforma modelo.

| Onde | O que acrescentar |
| :--- | :--- |
| Variáveis do início, depois de `PT :=` | `PX := src/simulation/exemplo` |
| Depois da definição de `TEMPLATE_VHDL` | `EXEMPLO_VHDL := $(subst template,exemplo,$(TEMPLATE_VHDL))` |
| Regra `check-tops`, depois das linhas do `template_sim_top` | Três linhas, uma de análise com `$(EXEMPLO_VHDL)`, uma de elaboração de `exemplo_sim_top` e um `echo` |
| Regras `memory-map`, `generate` e `generate-check` | A mesma linha de cada uma trocando `$(PT)` por `$(PX)` |

A documentação ganha um documento por idioma e a linha na tabela do `README.md` da pasta.

```bash
for l in pt-br en; do sed 's/template/exemplo/g' docs/$l/platform/template.md > docs/$l/platform/exemplo.md; done
```

| Arquivo | O que acrescentar |
| :--- | :--- |
| `paths.yaml` | Os arquivos da plataforma na lista `references` e os campos de caminho do `config.yaml` |
| `Makefile` | A variável `P<x> := src/simulation/exemplo`, as linhas de `memory-map`, `generate` e `generate-check` e a elaboração do topo em `check-tops`, que lê as fontes do `riscv-tools sources` |
| `paths.yaml` (`provides`) | O componente do topo, com as fontes e o que ele requer; o `scripts/generate_sources.py` ganha o arquivo de lista da plataforma |
| `docs/pt-br/platform/` | Um documento `exemplo.md` e a linha na tabela do `README.md` da pasta, com o espelho em `docs/en/` |

```bash
make paths
make memory-map
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `paths OK` e `tree OK`, e as plataformas de `memory-map` com `generated files OK` | `missing docs/pt-br/platform/exemplo.md`, por faltar o documento da plataforma em um dos idiomas |
| | `entity-coverage exemplo_sim_top ... has no entry in tests/python/tests.json`, por faltar a entrada `ExemploSimTop` |

## 5. Escolher o perfil do Core

### 5.1. A regra dos perfis

O nome de um perfil é a base seguida das extensões na ordem de `Core/profiles/matrix.yaml`, ligadas por `_`.

| Parte | Valores |
| :--- | :--- |
| Base | `rv32i` (32 registradores) ou `rv32e` (16) |
| Extensões, nessa ordem | `zicclsm`, `zicsr`, `zicntr`, `zihpm`, `zifencei`, `zmmul`, `m` |

`zicntr` e `zihpm` implicam `zicsr` e por isso o nome nunca cita `zicsr` junto delas; `m` implica `zmmul`, e `m` e `zmmul` não aparecem juntas. Todas as demais combinações são válidas, o que dá 60 perfis por base e 120 no total. Para listá-los:

```bash
riscv-tools profiles --spec Core/profiles/matrix.yaml --format names
```

### 5.2. Extensões fora da matriz

As extensões `Zimop`, `Zicond`, `Zihintntl` e `Zihintpause` não fazem parte do nome do perfil. A plataforma as liga no campo `extras` do `platform.yaml` (`extras: [Zimop, Zicond]`), e o pacote gerado traz `HAS_ZIMOP` e `HAS_ZICOND` verdadeiros.

### 5.3. Como o topo passa o perfil ao `core`

O `generate-memory-map` escreve no pacote uma constante `HAS_*` por extensão (`HAS_E`, `HAS_M`, `HAS_ZICSR` e as outras). O topo as expõe como genéricos `has_*` de mesmo nome, com a constante como valor padrão, e os liga aos genéricos do `core` (passo 6.3). O valor vem do `profile` do `platform.yaml`.

Para rodar a mesma plataforma sobre outro perfil sem editá-la, passe a opção global `--profile`.

```bash
riscv-tools --root . --profile rv32im_zicsr generate-memory-map --platform src/simulation/exemplo/platform.yaml
```

### 5.4. Perfil que não existe

Se nenhum perfil serve, a extensão nova entra em `Core/profiles/matrix.yaml` como pull request no repositório `Core`, com a pasta da extensão em `Core/src/<extensão>/`. O guia de contribuição do `Core` descreve o caminho. Depois disso, o ponteiro do submódulo neste repositório avança e o perfil novo vale em todas as plataformas.

## 6. Escrever o topo

### 6.1. Estrutura do `<plataforma>_sim_top.vhd`

O topo de simulação da plataforma modelo tem seis blocos, que o exemplo mantém.

| Instância | Entidade | Origem |
| :--- | :--- | :--- |
| `u_clock` | `clk_gen_3way` | `src/simulation/internal-mem/rtl/` |
| `u_core` | `core` | `Core/src/core/` |
| `u_boot_memory` | `rom_simulation` | `Memory/src/ROM/SoC/` |
| `u_rom` | `rom_simulation` (duas portas) | `Memory/src/ROM/SoC/` |
| `u_ram` | `ram_simulation` | `Memory/src/RAM/SoC/` |
| `u_uart` (opcional) | `jtag_uart` | `Peripherals/src/UART/jtag/` |

O núcleo tem três saídas de memória: a busca de instrução (BOOT_MEMORY e ROM), a porta de dados da ROM e da RAM, e o barramento externo, por onde passam os periféricos.

### 6.2. Genéricos de tamanho

Os tamanhos das memórias são genéricos em potência de dois, cujo valor padrão vem do pacote gerado (`BOOT_MEMORY_SIZE_BYTES`, `ROM_STORAGE_BYTES`, `RAM_STORAGE_BYTES`). Não se escreve um tamanho no topo.

### 6.3. Perfil e mapa no `core`

O topo declara um genérico `has_*` por extensão (`has_e`, `has_m`, `has_zmmul`, `has_zicsr`, `has_zicntr`, `has_zihpm`, `has_zimop`, `has_zicond`, `has_zihintntl`, `has_zihintpause`, `has_zifencei` e `has_zicclsm`), cada um com a constante `HAS_*` do pacote como valor padrão. No `generic map` do `core`, cada `has_*` do núcleo recebe o genérico de mesmo nome do topo, e os limites das regiões (`rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib`) recebem as constantes de mesmo nome do pacote. Se o perfil do passo 4.2 liga o `M`, `has_m` já chega verdadeiro, e nada mais muda no topo.

O `riscv-tools` passa ao simulador um `-g has_*` por extensão do perfil. Todo topo que ele simula precisa declarar os doze genéricos, e o topo que não declara um deles falha na elaboração com `cannot find in top entity generic`.

### 6.4. Janela de cada periférico

O barramento externo do núcleo entrega ao topo o endereço, o dado de escrita e os enables de leitura e escrita. A UART responde quando os quatro bits mais altos do endereço são os de `UART_BASE`, que vem do pacote, e o dado lido volta ao núcleo no ciclo seguinte ao pedido. Para um periférico novo, repita o padrão: um seletor pelo endereço, os enables filtrados pelo seletor, o dado de leitura registrado. Para vários periféricos numa plataforma de placa, use a interconexão `ext_interconnect` do `src/interconnect/`, que separa a SDRAM da janela de periféricos e entrega o deslocamento de palavra a cada um (`de0-cv_top.vhd` mostra o uso).

### 6.5. Interrupções

O núcleo recebe as interrupções de máquina por três portas de nível, `i_irq_software`, `i_irq_timer` e `i_irq_external`, todas com valor padrão `'0'`. Elas só têm efeito com o genérico `has_interrupts` verdadeiro e `has_zicsr` ligado, e então o `mip` espelha as três portas e o `mie` as mascara. O CLINT (`Peripherals/src/CLINT/soc/`) entrega `o_irq_timer` e `o_irq_software`, e o PLIC (`Peripherals/src/PLIC/soc/`) reúne as linhas dos periféricos em `o_meip`. Cada um é um periférico comum, com janela própria (passo 6.4), e as suas saídas ligam diretamente às portas do núcleo.

### 6.6. Convenções do CONTRIBUTING

| Regra | Aplicação no topo |
| :--- | :--- |
| Portas `i_` e `o_` | `i_clk`, `i_rst`, `o_uart_tdo` |
| Rótulos `u_` | `u_core`, `u_ram` |
| Cabeçalho de 72 colunas | Bloco `-- ====` no início do arquivo, em português |
| Docstring por declaração | Um comentário em português acima de cada generic, port, signal e constant |
| Instanciação direta | `u_x : entity work.nome`, sem `component` |

### 6.7. Conferir

```bash
riscv-tools --root . check-vhdl-style
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `vhdl style OK` | Uma declaração sem o comentário acima dela, ou porta sem prefixo |

### 6.8. Elaborar

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

O `make check-tops` faz o mesmo para todas as plataformas registradas no passo 4.4.

## 7. Runtime

O runtime é o que o programa encontra ao iniciar e ao terminar. Os quatro arquivos escritos à mão vêm do modelo, e o mapa chega a eles pelos três arquivos gerados no capítulo 4.

### 7.1. Os arquivos

| Arquivo | O que faz | O que muda com o mapa |
| :--- | :--- | :--- |
| `runtime/boot_memory.S` | `_reset` zera `stdout`, `tohost` e `fromhost` e salta para `RV32_BOOT_ENTRY`; `rv32_wait_restart` espera o `fromhost` | Nada, lê os endereços de `memory_map.h` |
| `runtime/boot_memory.ld` | Script de ligação da BOOT_MEMORY, com `rv32_wait_restart` em `0x100` | Gerado |
| `runtime/rv32im-fpga.specs` | Parâmetros do linker (`__flash`, `__flash_size`, `__ram`, `__ram_size`) e o crt0 da picolibc | Gerado |
| `runtime/memory_map.h` | Endereços de RAM, `tohost`, `fromhost`, `stdout`, entrada de boot e base de cada periférico | Gerado |
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

Ele reúne, para o `riscv-tools`, o que é da plataforma. Nenhum endereço nem tamanho de memória mora nele, porque a chave `memory_map: platform.yaml` os lê do mapa.

| Seção | Conteúdo |
| :--- | :--- |
| `toolchain` | GCC, `objcopy` e o `rv32im-fpga.specs` da plataforma |
| `memory_map` | O `platform.yaml`, de onde vêm as bases, o `tohost`, o `fromhost` e o perfil |
| `paths` | Fontes do runtime (`_exit.c`, `stdio.c`), `boot_memory.S` e `boot_memory.ld` |
| `sim.toplevel` | `exemplo_sim_top` |
| `sim.vhdl_sources` | Todas as fontes, em ordem de dependência, escritas pelo `make generate-sources` |
| `sim.test_module`, `sim.python_path` | O testbench cocotb, `testbench.test_c_program` da plataforma `internal-mem` |
| `sim.parameters` | `BOOT_MEMORY_FILE` e `ROM_FILE` com as imagens de cada programa |
| `emulator.sources` | `spike_exit.S` |

A lista `sim.vhdl_sources` não se edita à mão. Ela vem do componente do topo no `provides` do `paths.yaml` da plataforma, que declara os componentes que o topo requer, e o `make generate-sources` a escreve na ordem de análise. Se o topo ganhar um periférico, o componente dele entra no `requires` do topo e a lista é regenerada.

As fontes do núcleo, em ordem de dependência, saem de:

```bash
riscv-tools --root . sources Core/core
```

### 8.2. O testbench

O `testbench/test_c_program.py` da `internal-mem` roda o clock, solta o reset, observa as escritas no barramento da RAM (`ram_addr`, `ram_wren`, `ram_en`, `ram_wdata`, `ram_byteena`) e para no `tohost`. O endereço do `tohost` chega a ele pelo ambiente, vindo do `platform.yaml`. Qualquer topo que exponha esses sinais com esses nomes o reutiliza, e o do exemplo os expõe.

### 8.3. O primeiro programa

Os programas ficam no repositório `Tests` (`asm/` e `c/`). O `Tests` traz o `Insper-RISC-V` como submódulo e estende a configuração de cada plataforma por um arquivo gerado.

Primeiro, a plataforma precisa estar em um commit do clone, e o submódulo do `Tests` passa a apontar para ele.

```bash
git add src/simulation/exemplo paths.yaml Makefile tests docs
git commit -m "feat: plataforma exemplo"
cd ..
git clone --recurse-submodules git@github.com:insper-riscv/Tests.git
cd Tests
git -C Insper-RISC-V fetch ../../Insper-RISC-V HEAD
git -C Insper-RISC-V checkout FETCH_HEAD
git -C Insper-RISC-V submodule update --init --recursive
```

Depois, o `platform sync` grava a configuração da plataforma já resolvida contra o `platform.yaml`, com os caminhos precedidos pela pasta do submódulo.

```bash
riscv-tools platform sync --prefix Insper-RISC-V \
    --source Insper-RISC-V/src/simulation/exemplo/config.yaml \
    --output tools/riscv_build/config.platform-exemplo.yaml
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `platform synced: tools/riscv_build/config.platform-exemplo.yaml` | `No such file` em `Insper-RISC-V/src/simulation/exemplo`, porque o submódulo ainda aponta para um commit sem a plataforma |

Os programas incluem um cabeçalho com o mapa, escolhido pelo `include_dir` da configuração. Cada plataforma tem a sua pasta de cabeçalhos, copiada da `include/` com os três endereços trocados pelos do `platform.yaml`.

```bash
mkdir tools/riscv_build/include-exemplo
sed -e 's/0x00030000/0x00018000/' -e 's/0x0002FBE0/0x00017BE0/' -e 's/0x0002FFE8/0x00017FE8/' \
    tools/riscv_build/include/rv32_platform.h > tools/riscv_build/include-exemplo/rv32_platform.h
echo "tools/riscv_build/include-exemplo/rv32_test.h" >> .gitignore
```

| Endereço | Valor no exemplo | Origem no `platform.yaml` |
| :--- | :--- | :--- |
| `RV32_RAM_END` | `0x00018000` | Fim da região `RAM` |
| `RV32_STDOUT_BASE` | `0x00017BE0` | `reserved.stdout.base` |
| `RV32_TOHOST` | `0x00017FE8` | `reserved.tohost.base` |

Para o `check-memory-map` conferir essa cópia, troque `checks: []` no fim do `platform.yaml` do exemplo pelas três linhas abaixo.

```yaml
checks:
  - {name: Tests header RV32_RAM_BASE, file: ../Tests/tools/riscv_build/include-exemplo/rv32_platform.h, optional: true, pattern: '#define RV32_RAM_BASE\s+(0x[0-9A-Fa-f]+)', expect: RAM.base}
  - {name: Tests header RV32_RAM_END, file: ../Tests/tools/riscv_build/include-exemplo/rv32_platform.h, optional: true, pattern: '#define RV32_RAM_END\s+(0x[0-9A-Fa-f]+)', expect: RAM.end}
  - {name: Tests header RV32_STDOUT_BASE, file: ../Tests/tools/riscv_build/include-exemplo/rv32_platform.h, optional: true, pattern: '#define RV32_STDOUT_BASE\s+(0x[0-9A-Fa-f]+)', expect: stdout.base}
```

Crie `tools/riscv_build/config.exemplo.yaml` com o conteúdo abaixo.

```yaml
extends: config.platform-exemplo.yaml
paths:
  include_dir: tools/riscv_build/include-exemplo
  build_dir: build-exemplo
  c_dir: c
  asm_dir: asm
```

Por fim, gere o cabeçalho dos programas em C, compile e simule um programa de `asm/` e dois de `c/`.

```bash
riscv-tools --config tools/riscv_build/config.exemplo.yaml generate-header
riscv-tools --config tools/riscv_build/config.exemplo.yaml compile --emit hex --only arithmetic-add,multiply,stdout-printf
riscv-tools --config tools/riscv_build/config.exemplo.yaml sim
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `arithmetic-add: PASS`, `multiply: PASS` e `stdout-printf: PASS`, com o rótulo `(rv32im)` nos dois últimos | `timed out after ... cycles without a result`, quando o `rv32_platform.h` ficou com os endereços de outra plataforma e o programa escreve o `tohost` onde o testbench não olha |
| `compile` gera `manifest.json` com os programas | `cannot find in top entity generic 'has_e'`, quando o topo não declara os genéricos `has_*` do passo 6.3 |
| | `rv32_test.h: No such file or directory`, por pular o `generate-header` |
| | `region ... overflowed` na ligação, quando o programa não cabe na ROM de 28 KiB |

Dentro do `Insper-RISC-V`, o `make test TEST=ExemploSimTop` roda o teste de integração do topo registrado no passo 4.4, sem o projeto de testes.

## 9. Certificação

### 9.1. O que se certifica

A suíte ACT4 certifica um perfil do núcleo, e não um mapa de memória. O repositório `Certification` roda cada um dos 120 perfis de `Core/profiles/matrix.yaml` na plataforma modular de simulação (`src/simulation/modular`), com ROM e RAM de 1 MB. Um perfil sem `Zifencei` roda com as memórias dentro do chip, e um perfil com `Zifencei` roda com a ROM e a RAM atrás das caches de 4 kbit. O alvo de cada perfil (UDB, configuração do Sail, `test_config.yaml`) e o `config.profile-<perfil>.yaml` ou `config.flash-<perfil>.yaml` já estão no repositório, gerados por `tools/riscv_build/gen_profiles.py` e `gen_flash_profiles.py` a partir da matriz de perfis do submódulo.

Para a plataforma nova, a certificação vale para o perfil que ela escolhe no passo 4.2. O mapa de memória dela é provado pelo programa do passo 8.3.

### 9.2. Rodar o perfil escolhido

As ferramentas vêm da imagem `ci-act4` do Infra. A execução usa cerca de 15 GiB de memória por perfil e precisa de um diretório pessoal gravável.

```bash
git clone --recurse-submodules git@github.com:insper-riscv/Certification.git
cd Certification
docker run --rm --memory=22g --ulimit stack=-1 -e HOME=/w/.home --user "$(id -u):$(id -g)" \
    -v "$PWD":/w -w /w ghcr.io/insper-riscv/ci-act4:latest \
    riscv-tools --config tools/riscv_build/config.profile-rv32im.yaml certify
```

Para um perfil com `Zifencei`, use `config.flash-<perfil>.yaml` no lugar do `config.profile-<perfil>.yaml`. Para restringir às extensões do perfil, acrescente `--extensions I,M` ao `certify`.

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| Uma linha `PASS` por teste do perfil (51 no `rv32im`) e `=== Summary ===` sem nenhuma linha `FAIL`; o log fica em `logs/certification/latest.log` | `Permission denied @ dir_s_mkdir - /.local`, porque o contêiner roda com outro usuário e o diretório pessoal não é gravável. Passe `-e HOME=<pasta gravável>` |
| | `profile ... not found`, porque o perfil da plataforma não está em `matrix.yaml` |
| | Falha de `Zifencei-fence.i`, quando o teste que reescreve o próprio código roda a partir da ROM, que ignora stores. O alvo `flash-ram-*` usa a variante com o corpo do teste na RAM |

### 9.3. Perfil sem alvo

Um perfil novo da matriz do Core ganha o alvo rodando os geradores no repositório `Certification`.

```bash
uv run python tools/riscv_build/gen_profiles.py
uv run python tools/riscv_build/gen_flash_profiles.py
```

## 10. Placa

Este capítulo vale só se a plataforma tem uma FPGA. A `external-data` é a menor plataforma de placa e serve de ponto de partida; a `de0-cv` é a referência completa.

### 10.1. Copiar e renomear

```bash
cp -r src/cyclone-v/external-data src/cyclone-v/minhaplaca
cd src/cyclone-v/minhaplaca
for f in $(find . -name '*external*data*' -type f); do
    mv "$f" "$(echo $f | sed 's/external-data/minhaplaca/;s/external_data/minhaplaca/')"
done
grep -rl "external[-_]data" . | xargs sed -i 's/external-data/minhaplaca/g;s/external_data/minhaplaca/g'
cd ../../..
```

Depois da cópia, registre a plataforma como no passo 4.4, usando as linhas `external-data` do `paths.yaml`, do `Makefile` e do `tests/python/tests.json` como modelo no lugar das da plataforma modelo.

### 10.2. Arquivos do projeto do Quartus

| Arquivo | Conteúdo |
| :--- | :--- |
| `<plataforma>.qpf` | O projeto, com a revisão |
| `<plataforma>.qsf` | Dispositivo, pinos e a lista de fontes VHDL e IP, escrita pelo `make generate-sources` e conferida contra o disco pelo `check-paths` |
| `<plataforma>.sdc` | Os clocks e as restrições de entrada, saída e cruzamento de domínio |
| `<plataforma>_assignment_defaults.qdf` | Atribuições padrão do projeto |
| `../de0-cv/pll/` | A IP do PLL que gera os clocks do núcleo e da SDRAM, compartilhada entre as plataformas da DE0-CV |
| `<plataforma>_synth.tcl` | Compila com a semente escolhida; com o argumento `map` só sintetiza |
| `<plataforma>_program.sh` | Programa o `.sof` pelo primeiro cabo do `jtagconfig` |
| `<plataforma>_top.vhd` | O topo da placa, que liga o PLL, o núcleo, as memórias da placa e os periféricos |
| `<plataforma>_map_pkg.vhd` | Pacote do mapa, gerado do `platform.yaml` |
| `boot_memory_init.mif`, `init.mif` | Imagens iniciais da BOOT_MEMORY e da FLASH |

### 10.3. Editar o `.qsf` e o `.sdc`

O `.qsf` tem a lista de fontes escrita pelo `make generate-sources`, com caminhos relativos à pasta da plataforma (`../../../Core/src/...`). As fontes do núcleo, em ordem de dependência, saem de:

```bash
riscv-tools --root . sources Core/core
```

O `.sdc` declara o clock de entrada (`create_clock`), os clocks do PLL (`derive_pll_clocks`) e a incerteza (`derive_clock_uncertainty`). Cada clock externo gerado, como o da SDRAM, ganha o seu `create_generated_clock` e os atrasos de entrada e saída do datasheet do chip. Cada cruzamento entre os domínios do núcleo, da SDRAM e do JTAG tem a sua restrição `set_max_delay` e `set_min_delay`, e os botões, LEDs e displays lentos têm `set_false_path`.

Com a lista pronta, confira os caminhos.

```bash
make paths
```

### 10.4. Compilar e programar

```bash
quartus_sh -t src/cyclone-v/minhaplaca/minhaplaca_synth.tcl map
quartus_sh -t src/cyclone-v/minhaplaca/minhaplaca_synth.tcl && src/cyclone-v/minhaplaca/minhaplaca_program.sh
```

O primeiro comando só sintetiza e confere que os caminhos e as entidades resolvem. O segundo compila e programa a placa, e os dois comandos precisam sair no mesmo shell (`&&`). O guia [placa.md](placa.md) explica a regra e o que fazer quando a placa não responde.

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `Analysis & Synthesis was successful. 0 errors` | `design library "work" does not contain primary unit ...`, por faltar um arquivo no `.qsf` (um `sdram_jtag_shell.vhd` de `../de0-cv/`, por exemplo) |
| `output_files/minhaplaca.sof` depois da compilação completa | `Can't scan JTAG chain` no programador, por compilar e programar em shells diferentes |

### 10.5. Programas e certificação na placa

Com o bitstream programado, o `Tests` escreve cada programa na BOOT_MEMORY e na FLASH por JTAG e confere o resultado, sem recompilar a FPGA. A configuração da placa no `Tests` é gerada como no passo 8.3, a partir do `config.yaml` da plataforma de placa.

```bash
riscv-tools platform sync --prefix Insper-RISC-V \
    --source Insper-RISC-V/src/cyclone-v/minhaplaca/config.yaml \
    --output tools/riscv_build/config.platform-minhaplaca.yaml
riscv-tools --config tools/riscv_build/config.minhaplaca.yaml run --skip-reconfigure --skip-recompile --only arithmetic-add
```

O `config.minhaplaca.yaml` estende o arquivo gerado, como no passo 8.3, com o `include_dir` da plataforma. O `certify-board` roda o ACT4 do perfil escolhido na placa, com a configuração `config.flash-board-<perfil>.yaml` do repositório `Certification`.

### 10.6. Relatório de tempo

Depois da compilação, o relatório do Timing Analyzer fica em `output_files/<plataforma>.sta.rpt`. Os números de interesse são o Fmax de cada clock e o pior slack de setup e de hold. Um slack negativo de setup indica um caminho mais longo que o período do clock. Para listar os caminhos críticos, use o `riscv-tools timing-paths` na pasta do projeto compilado.

## 11. Adicionar um periférico novo

O exemplo é um registrador de LEDs, `led_register`, com um registrador de 32 bits cujos bits baixos acendem os LEDs. Um periférico tem um lado `soc`, independente de família, e, quando precisa de uma casca de FPGA, um lado `<família>`. Os passos abaixo valem no repositório `Peripherals`, em `Insper-RISC-V/Peripherals` ou num clone próprio.

### 11.1. Pasta e entidade

O periférico mora em `Peripherals/src/<PERIFÉRICO>/soc/`. A pasta leva o nome do que o periférico é, em minúsculas com hífen, ou em maiúsculas quando o nome é uma sigla que o `identifier_folders` do `paths.yaml` do repositório lista.

```bash
mkdir -p Peripherals/src/LED/soc
```

O `Peripherals/src/LED/soc/led_register.vhd` segue o barramento comum dos periféricos (`i_clk`, `i_rst`, `i_data_in`, `i_address`, `i_write`, `i_read`, `o_data_out`) e o guia de estilo do repositório.

```vhdl
-- ============================================================================
-- Registrador de LEDs
-- ============================================================================
-- Periférico mapeado em memória com um único registrador de 32 bits, cujos
-- bits menos significativos acendem os LEDs da placa. A escrita no endereço 0
-- carrega o registrador no próximo clock; a leitura devolve o valor guardado
-- e não tem efeito colateral. Endereços diferentes de 0 leem zero e ignoram
-- a escrita.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity led_register is
    generic(
        -- Número de LEDs ligados aos bits menos significativos do registrador
        led_count : positive := 10
    );
    port(
        -- Clock do módulo
        i_clk      : in  std_logic;
        -- Reset síncrono, ativo em '1'
        i_rst      : in  std_logic;
        -- Dado de escrita vindo do processador
        i_data_in  : in  std_logic_vector(31 downto 0);
        -- Endereço de palavra dentro do periférico
        i_address  : in  std_logic_vector(3 downto 0);
        -- Pulso de escrita do processador ('1' = escreve)
        i_write    : in  std_logic;
        -- Pulso de leitura do processador (sem efeito colateral)
        i_read     : in  std_logic;
        -- Dado de leitura para o processador
        o_data_out : out std_logic_vector(31 downto 0);
        -- Saída para os LEDs, ativa em '1'
        o_leds     : out std_logic_vector(led_count - 1 downto 0)
    );
end entity led_register;

architecture rtl of led_register is

    -- Valor guardado dos LEDs
    signal leds_reg : std_logic_vector(led_count - 1 downto 0);
    -- Endereço de palavra do registrador
    constant ADDR_LEDS : std_logic_vector(3 downto 0) := "0000";

begin

    p_write : process(i_clk)
    begin
        if rising_edge(i_clk) then
            if i_rst = '1' then
                leds_reg <= (others => '0');
            elsif i_write = '1' and i_address = ADDR_LEDS then
                leds_reg <= i_data_in(led_count - 1 downto 0);
            end if;
        end if;
    end process p_write;

    o_data_out <= std_logic_vector(resize(unsigned(leds_reg), 32))
                  when i_address = ADDR_LEDS else (others => '0');
    o_leds     <= leds_reg;

end architecture rtl;
```

### 11.2. Teste de entidade

Todo periférico tem um teste cocotb em `Peripherals/tests/python/unittests/<PERIFÉRICO>/`, com um `__init__.py`, e um protocolo que descreve os sinais do periférico em `tests/python/utils/dut.py`.

```bash
mkdir -p Peripherals/tests/python/unittests/LED
echo '"""Package LED of the peripheral tests."""' > Peripherals/tests/python/unittests/LED/__init__.py
```

Acrescente ao fim de `tests/python/utils/dut.py`:

```python
class LedDut(BusDut, Protocol):
    """Signals of the LED register."""

    o_leds: LogicArrayObject
```

O teste `unittests/LED/led_register.py` usa os auxiliares de barramento de `tests/python/utils/bus.py`.

```python
"""LED_REGISTER: a escrita carrega os LEDs e a leitura devolve o valor."""

import cocotb

from tests.python.utils import bus
from tests.python.utils.check import check
from tests.python.utils.dut import LedDut

LEDS_ADDR = 0
OTHER_ADDR = 1
PATTERN = 0x2A5


@cocotb.test()
async def test_write_then_read(dut: LedDut) -> None:
    """Depois do reset os LEDs estão apagados, e a escrita os acende."""
    await bus.reset(dut)
    check(int(dut.o_leds.value) == 0, "LEDs apagados depois do reset")
    await bus.write(dut, LEDS_ADDR, PATTERN)
    check(int(dut.o_leds.value) == PATTERN, "LEDs acesos com o padrão")
    check(await bus.read(dut, LEDS_ADDR) == PATTERN, "leitura devolve o valor")
    check(await bus.read(dut, OTHER_ADDR) == 0, "outro endereço lê zero")
```

### 11.3. Manifesto

O teste entra no catálogo `tests/python/tests.json`, com a entidade de topo, as fontes e o módulo de teste.

```json
"LedRegister": {
    "toplevel": "led_register",
    "sources": ["src/LED/soc/led_register.vhd"],
    "test_module": "tests.python.unittests.LED.led_register",
    "build_args": ["--std=08"],
    "test_args": ["--std=08"]
}
```

O `paths.yaml` do repositório ganha a pasta do periférico em `entry points`, o par de documentos do passo 11.4 e, quando a pasta é maiúscula, o nome dela em `tree.identifier_folders`.

### 11.4. Documento

Cada periférico tem um documento por idioma, `docs/pt-br/<PERIFÉRICO>/led_register.md` e `docs/en/<PERIFÉRICO>/led_register.md`, com o seletor de idioma, as seções numeradas e o rodapé de licença. O `README.md` e o `README.en.md` do repositório ganham a linha do periférico nas tabelas de estrutura.

### 11.5. Conferir

```bash
make check
make paths
make test TEST=LedRegister
riscv-tools --root . check-vhdl-style
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `VHDL syntax check passed`, `tree OK`, `TESTS=1 PASS=1` e `vhdl style OK` | `TREE folder-names src/LED: use lowercase letters...`, por faltar `LED` em `tree.identifier_folders` do `paths.yaml` |
| | `entity-coverage ... has no entry in tests/python/tests.json`, por faltar o manifesto do passo 11.3 |

### 11.6. Janela no `platform.yaml` e no topo

Um repositório de plataforma usa o periférico depois que o ponteiro do submódulo `Peripherals` avança até o commit que o traz. A janela entra no `platform.yaml` da plataforma.

```yaml
peripherals:
  - {name: UART, base: 0xC0000000, id: 4}
  - {name: LED,  base: 0xD0000000, id: 5}
```

Depois de `generate-memory-map`, o pacote ganha `LED_BASE` e `LED_ID`, e o `memory_map.h`, `RV32_LED_BASE`. No topo, o seletor da janela, os enables filtrados e o dado de leitura seguem o padrão do passo 6.4, e a fonte `led_register.vhd` entra na lista `sim.vhdl_sources` do `config.yaml`, no `Makefile` da plataforma e no `.qsf`, se houver placa.

## 12. Adicionar um tipo de memória novo

O caminho é o do capítulo 11, no repositório `Memory`. O exemplo é uma RAM de rascunho, `scratchpad_ram`, de uma porta com escrita e leitura síncronas.

### 12.1. Pasta e entidade

Uma memória mora em `Memory/src/<tipo>/`, com `SoC/` para o que é independente de família e a pasta da família (`Cyclone-V/`, `FPGA/`) para o que usa megafunções. As pastas `SoC`, `RAM`, `ROM`, `FPGA` e `Cyclone-V` mantêm as maiúsculas porque são identificadores, e o nome de um tipo novo usa minúsculas.

```bash
mkdir -p Memory/src/scratchpad/SoC
```

O `Memory/src/scratchpad/SoC/scratchpad_ram.vhd` segue o mesmo guia de estilo.

```vhdl
-- ============================================================================
-- RAM de rascunho
-- ============================================================================
-- Memória de uma porta com escrita e leitura síncronas, de palavra inteira.
-- A leitura devolve, no ciclo seguinte ao pedido, o conteúdo do endereço
-- pedido; uma escrita e uma leitura no mesmo ciclo devolvem o valor antigo.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity scratchpad_ram is
    generic(
        -- Largura do endereço de palavra em bits
        addr_width : positive := 4
    );
    port(
        -- Clock da memória
        i_clk      : in  std_logic;
        -- Endereço de palavra
        i_addr     : in  std_logic_vector(addr_width - 1 downto 0);
        -- Dado de escrita
        i_data_in  : in  std_logic_vector(31 downto 0);
        -- Habilita de escrita ('1' = escreve)
        i_we       : in  std_logic;
        -- Dado lido, válido no ciclo seguinte ao pedido
        o_data_out : out std_logic_vector(31 downto 0)
    );
end entity scratchpad_ram;

architecture rtl of scratchpad_ram is

    -- Vetor de palavras da memória
    type word_array_t is array (0 to 2 ** addr_width - 1) of std_logic_vector(31 downto 0);
    -- Conteúdo da memória, zerado no início da simulação
    signal words : word_array_t := (others => (others => '0'));

begin

    p_access : process(i_clk)
    begin
        if rising_edge(i_clk) then
            o_data_out <= words(to_integer(unsigned(i_addr)));
            if i_we = '1' then
                words(to_integer(unsigned(i_addr))) <= i_data_in;
            end if;
        end if;
    end process p_access;

end architecture rtl;
```

### 12.2. Teste de entidade

Os testes do `Memory` ficam em `tests/python/unittests/<tipo>/` e usam `Dut` e os auxiliares de `tests/python/unittests/checks.py`.

```bash
mkdir -p Memory/tests/python/unittests/scratchpad
echo '"""Package scratchpad of the memory tests."""' > Memory/tests/python/unittests/scratchpad/__init__.py
```

```python
"""SCRATCHPAD_RAM: a leitura devolve o que a escrita guardou."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from tests.python.unittests.checks import check_equal
from tests.python.unittests.dut import Dut

WORD = 0xCAFE_F00D
ADDR = 5


@cocotb.test()
async def test_write_then_read(dut: Dut) -> None:
    """Escreve uma palavra, lê no ciclo seguinte e confere o valor."""
    cocotb.start_soon(Clock(dut.i_clk, 10, unit="ns").start())
    dut.i_we.value = 0
    dut.i_addr.value = ADDR
    dut.i_data_in.value = WORD
    await Timer(1, unit="ns")
    dut.i_we.value = 1
    await RisingEdge(dut.i_clk)
    dut.i_we.value = 0
    await RisingEdge(dut.i_clk)
    await Timer(1, unit="ns")
    check_equal(int(dut.o_data_out.value), WORD, "palavra lida")
```

### 12.3. Manifesto, documento e conferência

O manifesto é uma entrada de `tests/python/tests.json` como a do passo 11.3, com `toplevel` `scratchpad_ram`, a fonte `src/scratchpad/SoC/scratchpad_ram.vhd` e o módulo `tests.python.unittests.scratchpad.scratchpad_ram`. O `paths.yaml` do `Memory` ganha a pasta `src/scratchpad/SoC` em `entry points` e os dois documentos, `docs/pt-br/scratchpad/scratchpad_ram.md` e `docs/en/scratchpad/scratchpad_ram.md`, numa linha `design documents`. Uma entidade sem teste de entidade próprio precisa de justificativa em `tree.exceptions`, e a que tem teste não precisa.

```bash
make check
make paths
make test TEST=ScratchpadRam
riscv-tools --root . check-vhdl-style
```

| Saída esperada | Erro comum e causa |
| :--- | :--- |
| `VHDL syntax check passed`, `tree OK`, `TESTS=1 PASS=1` e `vhdl style OK` | `entity-coverage`, por entidade sem entrada no `tests.json` nem justificativa em `tree.exceptions` |

### 12.4. Uso numa plataforma

O topo instancia a memória nova no lugar de uma das existentes, desde que a interface seja a do bloco que ela substitui (regra 3 da seção 5 do CONTRIBUTING). Quando a região deixa de ser interna, o campo `memory` do `platform.yaml` muda (`rom: {external: true}`, `icache: {enabled: true, size_bits: 32768}`), e o pacote gerado traz `ROM_EXTERNAL`, `RAM_EXTERNAL` e os tamanhos das caches.

## 13. CI e pull request

### 13.1. Conferir antes de abrir

Todo pull request deste repositório passa, localmente, por:

```bash
git submodule update --init --recursive
make all
make generate-check
```

| Comando | O que roda |
| :--- | :--- |
| `make paths` | Os caminhos do `paths.yaml` e a forma da árvore (`check-tree --kind top`) |
| `make check` | A elaboração dos topos de todas as plataformas e a unicidade dos nomes de entidade entre os repositórios |
| `make unit-tests` | A conferência do mapa de memória e os testes cocotb das plataformas |
| `make formal` | A prova formal da interconexão |
| `make generate-check` | Os arquivos gerados de cada `platform.yaml` estão em dia |

### 13.2. O que o CI roda

O CI roda a cada push, em nove jobs, dentro da imagem `ci-vhdl` do Infra.

| Job | O que confere |
| :--- | :--- |
| `reuse` | Reaproveita o resultado de um pull request aprovado da mesma árvore; na dúvida, roda tudo |
| `vhdl-syntax` | `make paths`, `check-vhdl-style` e `make check` |
| `unit-tests` | `make unit-tests` |
| `formal - yices`, `formal - bitwuzla`, `formal - boolector`, `formal - abc-bmc3` | A prova formal, uma vez por engine |
| `formal` | Agrega os engines; é o check que o ruleset da branch exige |
| `python-static-analysis` | `ruff`, `pycodestyle`, `pydocstyle`, `pylint`, `pyright`, `pyrefly`, `deptry`, `complexipy`, `codeclone`, `semgrep` e `uv audit` sobre os arquivos Python |

Uma plataforma nova entra nesses jobs pelas listas do passo 4.4: o `make paths` confere os arquivos dela, o `make check` elabora o topo e o `make unit-tests` roda o teste dela e confere o mapa.

### 13.3. Abrir o pull request

1. Se a mudança alterou um submódulo (um periférico, uma memória, uma extensão do Core), abra e conclua primeiro o pull request no repositório dele, seguindo o `CONTRIBUTING.md` dele. Depois avance o ponteiro do submódulo neste repositório.
2. Aumente a versão em `pyproject.toml` e a mesma versão no bloco `insper-riscv` do `uv.lock`.
3. Atualize `README.md`, `README.en.md` e a documentação afetada, nos dois idiomas.
4. Abra o pull request contra a `main`. O commit de uma plataforma nova leva a pasta `src/<família>/<plataforma>/`, o `paths.yaml`, o `Makefile`, o `tests/python/tests.json`, os testes, os documentos e os arquivos gerados.
5. No projeto de testes, a configuração gerada pelo `platform sync` (`config.platform-<plataforma>.yaml`), o `config.<plataforma>.yaml` e a pasta de cabeçalhos entram em um pull request do repositório `Tests`, depois que o ponteiro do `Insper-RISC-V` avançar.

Num pull request de alguém de fora do projeto, o CI só começa depois que um membro que pode fazer o merge aprova a execução na página do pull request.

## 14. Referência

### 14.1. O porquê das decisões

| Decisão | Motivo |
| :--- | :--- |
| `platform.yaml` como fonte única | Cada endereço e cada tamanho existe num só lugar, e o `check-memory-map` e o `generate-memory-map --check` falham quando uma cópia diverge, em vez de o erro aparecer na placa |
| Pasta `soc/` e pasta por família | O lado `soc` roda em simulação e em qualquer FPGA; o lado da família guarda só o que depende de uma megafunção |
| `src/common/` como submódulo em Core, Memory e Peripherals | Os blocos comuns têm uma só origem (`Common-Components`), e cada repositório compila sozinho |
| O topo só conecta | Um bloco reutilizável mora no repositório dono dele, e a plataforma o instancia por submódulo |
| Genéricos `has_*` no topo | O `riscv-tools` roda a mesma plataforma sobre qualquer perfil passando `-g has_*`, sem editar o VHDL |
| Cada módulo confere só o que é dele | Cada repositório tem os próprios testes e provas, e este repositório roda só a integração |
| Certificação por perfil | O resultado do ACT4 depende da implementação do núcleo, e não do mapa de memória que a plataforma escolhe |

### 14.2. Campos do `platform.yaml`

| Campo | Obrigatório | Conteúdo |
| :--- | :--- | :--- |
| `platform` | Sim | Nome da plataforma |
| `profile`, `profiles` | Sim | Perfil do Core e caminho da matriz de perfis, relativo ao `platform.yaml` |
| `regions` | Sim | `name`, `base`, `size`, `kind` (`rom` ou `ram`) e `exec` de cada região; toda região termina em `0x80000000` ou antes |
| `reserved` | Sim | `stdout`, `tohost` e `fromhost`, dentro da região de RAM |
| `boot` | Sim | `entry` numa região executável e `wait_restart` na primeira região |
| `peripherals` | Sim | `name`, `base` e `id`, com a base igual a `0x80000000 \| id << 28` |
| `flash` | Não | Região da FLASH e as bancas (`name`, `base`, `size`) que a placa grava e executa |
| `memory` | Não | `rom` e `ram` com `external`, `icache` e `dcache` com `enabled` e `size_bits` |
| `extras` | Não | Extensões fora da matriz que a plataforma liga (`Zimop`, `Zicond`, `Zihintntl`, `Zihintpause`) |
| `generate` | Sim | `specs`, `bank_specs`, `boot_ld`, `runtime`, `banks_h` e `vhdl`, cada um com o `path` a escrever |
| `config` | Sim | `rom`, `ram` e `addr_widths`, o que o `config.yaml` lê do mapa |
| `checks` | Não | Cópias escritas à mão a conferir, cada uma com `name`, `file`, `pattern` ou `yaml`, e `expect` |

### 14.3. Erros conhecidos

| Mensagem | Causa |
| :--- | :--- |
| `reserved stdout ... is not inside a RAM region` | As palavras reservadas ficaram fora da RAM depois de mudar o tamanho ou a base |
| `generated files are out of date` | O `platform.yaml` mudou sem rodar `generate-memory-map` |
| `cannot find in top entity generic 'has_e'` | O topo simulado não declara os doze genéricos `has_*` |
| `timed out after ... cycles without a result` | O cabeçalho `rv32_platform.h` do projeto de testes tem o `tohost` de outra plataforma, ou a BOOT_MEMORY não salta para o início da ROM |
| `rv32_test.h: No such file or directory` | O `generate-header` não rodou para a configuração da plataforma |
| `unit "..." not found` | Falta uma fonte na lista do `ghdl`, ou a lista está fora de ordem |
| `missing docs/...` no `make paths` | Falta o documento da plataforma, do periférico ou da memória em um dos idiomas |
| `entity-coverage ... has no entry in tests/python/tests.json` | A entidade ou o topo não tem teste registrado |
| `TREE folder-names ...: use lowercase letters, digits and hyphens` | Pasta com nome em maiúsculas que não está em `tree.identifier_folders` |
| `Permission denied @ dir_s_mkdir - /.local` no `certify` | O contêiner roda sem diretório pessoal gravável; passe `-e HOME=<pasta>` |
| `Can't scan JTAG chain` | A compilação e a programação do Quartus rodaram em shells diferentes |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
