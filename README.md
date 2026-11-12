# Insper-RISC-V

🌐 [Português](README.md) · [English](README.en.md)

![Diagrama do pipeline](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

SoC RISC-V de 32 bits em VHDL. O núcleo é um pipeline em ordem de cinco estágios que implementa RV32IM com as extensões Zicsr, Zicntr, Zihpm, Zifencei e Zicclsm, em 60 perfis sobre a base RV32I e 60 sobre a RV32E gerados a partir de uma matriz, mais as extensões Zimop, Zicond, Zihintntl e Zihintpause ligadas por genéricos. Este repositório é o topo do projeto. Ele liga o núcleo (`Core`), as memórias (`Memory`), os periféricos (`Peripherals`) e os blocos comuns (`Common-Components`) em cinco plataformas (três de simulação e duas da placa DE0-CV, Cyclone V), e guarda o projeto do Quartus, o runtime, o mapa de memória, os testbenches das plataformas e a integração contínua conjunta. O trabalho é dividido em repositórios da organização [insper-riscv](https://github.com/insper-riscv), um por responsabilidade.

## 1. Documentação

- [AUTHORS.md](AUTHORS.md): autores com commits no repositório, com nome e conta do GitHub.
- [CONTRIBUTING.md](CONTRIBUTING.md): regras obrigatórias de contribuição, normas VHDL-2008, C23 e Python, regras de documentação e verificação antes de abrir Pull Request.
- [CITATION.cff](CITATION.cff): metadados para citação do software.
- [docs/pt-br/guide/](docs/pt-br/guide/README.md): guias (placa, adicionar uma placa nova, simulação, KPIs e nova arquitetura).
- [docs/pt-br/platform/](docs/pt-br/platform/README.md): as cinco plataformas e as dez (quatro de teste, quatro na FPGA e duas de UART), com o mapa de memória, o boot, o runtime e a atualização de programa de cada uma.
- [docs/pt-br/boards/](docs/pt-br/boards/README.md): a arquitetura multi-FPGA, o formato do pacote de placa (`boards/<placa>/board.yaml` e `pins.yaml`), a geração do projeto, a identificação pelo JTAG, o cabimento do perfil e a tabela das sete placas.
- [docs/pt-br/bugs/](docs/pt-br/bugs): defeitos já diagnosticados.
- [docs/pt-br/conformance/](docs/pt-br/conformance/riscv-nao-privilegiado.md): o relatório de conformidade com os capítulos 1, 2 e 4 a 11 do volume não privilegiado do RISC-V, com a evidência de cada requisito, e [riscv-privilegiado.md](docs/pt-br/conformance/riscv-privilegiado.md), o do volume privilegiado para o hart só com o modo máquina.
- [docs/pt-br/interconnect/ext_interconnect.md](docs/pt-br/interconnect/ext_interconnect.md): o interconector externo, que decodifica o mapa da plataforma entre a SDRAM e os periféricos, a sua variante AXI4 e os testes de integração.
- [docs/pt-br/guide/kpis.md](docs/pt-br/guide/kpis.md): scripts de KPI (frequência, recursos, CPI e testes) a partir de uma execução do Quartus.

## 2. Repositórios

| Repositório | Responsabilidade | Depende de |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | A imagem de toolchain (GCC com picolibc, Spike, GHDL, uv) em que a integração contínua executa | Nada |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`, para compilar, simular, executar na placa, certificar e verificar | Infra (na execução) |
| [Common-Components](https://github.com/insper-riscv/Common-Components) | Os blocos genéricos de VHDL (somador, flip-flop, registradores, multiplexadores, decodificador one-hot e buffer de três estados) | Nada |
| [Core](https://github.com/insper-riscv/Core) | O processador em VHDL, por extensão da ISA, perfis e testes por entidade | Common-Components |
| [Memory](https://github.com/insper-riscv/Memory) | Memórias, caches, controladores e modelos de simulação | Core (interface de memória) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO, TIMER, CLINT, controlador de interrupção externa, UART, controlador de FLASH e display, com testes por entidade | Common-Components |
| [Tests](https://github.com/insper-riscv/Tests) | Os programas de teste (`asm/`, `c/`), goldens e os fluxos que os executam | Este repositório, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | A suíte oficial ACT4 (riscv-arch-test) | Este repositório, Tools |

`Common-Components`, `Core`, `Memory` e `Peripherals` são os submódulos deste repositório.

## 3. Plataformas

| Caminho | Plataforma |
| :--- | :--- |
| `src/simulation/internal-mem/` | Plataforma só de simulação, com BOOT_MEMORY, FLASH e RAM dentro da FPGA e o topo de simulação `rv32i3stage_core_sim_test`. É a base dos testes de entidade do pipeline |
| `src/simulation/modular/` | Topo de simulação configurável, com a ROM e a RAM dentro ou fora do chip e as caches de instruções e de dados presentes ou não, nas 16 combinações, FLASH e RAM de 1 MB e caches de 4 kbit por padrão. Roda os programas do repositório Tests e é a base da simulação do ACT4 |
| `src/simulation/template/` | Plataforma modelo mínima (RAM e ROM internas, UART sobre JTAG opcional, perfil `rv32i`), o ponto de partida do guia de nova arquitetura |
| `src/cyclone-v/external-data/` | Plataforma da placa DE0-CV com a BOOT_MEMORY e a FLASH de duas portas dentro da FPGA (uma só cópia, regravada por JTAG) e a SDRAM atrás da cache de dados, mais JTAG UART e display. O topo do Quartus é `external-data_top.vhd` e o de simulação é `rv32im_external_data_sim_test` |
| `src/cyclone-v/de0-cv/` | Plataforma da placa DE0-CV, com a BOOT_MEMORY no núcleo e a FLASH e a SDRAM atrás das caches, mais JTAG UART e display. O topo do Quartus é gerado por `riscv-tools board generate` (`build/de0-cv-de0-cv/`) e o de simulação é `rv32im_sdram_flash_sim_test` |

Todas as plataformas têm o `platform.yaml` e o `runtime/`. A `internal-mem` separa o projeto do Quartus em `quartus/` e os módulos próprios em `rtl/`, a `template` tem só o `rtl/`, a `modular` tem só o topo de simulação e o pacote do mapa, e as da placa (`de0-cv` e `external-data`) guardam o projeto do Quartus, o topo e os scripts de síntese e programação na própria pasta.

| Pasta ou arquivo | Conteúdo |
| :--- | :--- |
| `platform.yaml` | Mapa de memória e a lista de cada cópia manuscrita dele, verificada por `riscv-tools check-memory-map` |
| `config.yaml` | Configuração do `riscv-tools` para toolchain, memória, Quartus e simulação |
| `quartus/`, ou a própria pasta nas plataformas da placa | Projeto do Quartus (`.qpf`, `.qsf`, `.sdc`, topo de hardware, imagens `.mif` e os scripts `<plataforma>_synth.tcl` e `<plataforma>_program.sh`) |
| `pll/` | IP da PLL |
| `rtl/` | Topo de simulação e os módulos próprios da plataforma |
| `runtime/` | `rv32im-fpga.specs`, `boot_memory.S`, `boot_memory.ld`, `_exit.c`, `stdio.c` e `spike_exit.S` |
| `testbench/` | `test_c_program.py`, o testbench cocotb que decide PASS ou FAIL de um programa (`internal-mem` e `de0-cv`) |

Os testes por entidade do RTL das plataformas ficam em `tests/python/`, com o catálogo `tests.json` que os conduz.

## 4. Clonagem e Execução

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
make all        # paths, verificação de integração, testes e provas formais deste repositório
```

As ferramentas vêm da imagem `ci-vhdl` (`ghcr.io/insper-riscv/ci-vhdl`) do Infra, em que a integração contínua executa.

| Alvo | O que executa |
| :--- | :--- |
| `make paths` | Existência dos caminhos listados na configuração deste repositório (`paths.yaml`, `riscv-tools check-paths`) e a forma da árvore |
| `make check` | A construção do topo de simulação de cada plataforma com os submódulos fixados e a conferência de que nenhuma entidade ou pacote é definido em dois repositórios |
| `make memory-map` | Concordância de cada cópia do mapa de memória com o `platform.yaml` da plataforma |
| `make unit-tests` | Testes cocotb das plataformas deste repositório, mais o `memory-map` |
| `make formal` | Provas formais (SymbiYosys) do interconector deste repositório, com o engine de `FORMAL_ENGINE` (`bitwuzla` por padrão; o CI roda `yices`, `bitwuzla`, `boolector` e `abc-bmc3`) |

Cada repositório roda só as próprias verificações, testes e provas; as dos submódulos rodam no CI de cada um.

## 5. Placa

O projeto do Quartus da DE0-CV (Cyclone V 5CEBA4F23) é escrito por `riscv-tools board generate` em `build/de0-cv-de0-cv/de0_cv_de0_cv.qpf`. A programação e a execução de testes nela são feitas por `riscv-tools run` a partir do `Tests`, conforme [placa.md](docs/pt-br/guide/placa.md); outras placas seguem o mesmo comando, e uma placa nova segue [adicionar-placa.md](docs/pt-br/guide/adicionar-placa.md).

## 6. KPIs

`scripts/kpi_report.py` e `scripts/compare_kpis.py` geram os relatórios de KPI (clock, recursos, CPI e testes) a partir de uma execução do Quartus, conforme [docs/pt-br/guide/kpis.md](docs/pt-br/guide/kpis.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).

O workflow `embench` compara a base de cada PR com o merge proposto usando os 19 programas do Embench IoT nos perfis explícitos do Core. O resumo reúne simulação e FPGA, incluindo instruções, IPC, MIPS, clock configurado, estimativa de Fmax e notas por programa, perfil e tipo de operação. O modo `ci` usa uma repetição local por algoritmo e identifica a nota como estimativa; `workload=full` preserva os loops originais. A execução física exige a [configuração do runner](benchmarks/embench/FPGA-SETUP.md). Método, limites e reprodução estão em [benchmarks/embench/AUTOMATION.md](benchmarks/embench/AUTOMATION.md).
