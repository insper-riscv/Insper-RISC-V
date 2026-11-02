# Insper-RISC-V

🌐 [Português](README.md) · [English](README.en.md)

![Diagrama do pipeline](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

SoC RISC-V de 32 bits em VHDL. O núcleo é um pipeline em ordem de cinco estágios que implementa RV32IM com as extensões Zicsr, Zicntr, Zihpm, Zifencei e Zicclsm, em 60 perfis gerados a partir de uma matriz. Este repositório é o topo do projeto. Ele liga o núcleo (`Core`), as memórias (`Memory`), os periféricos (`Peripherals`) e os blocos comuns (`Common-Components`) em duas plataformas, a de simulação `internal-mem` e a da placa DE0-CV (Cyclone V), e guarda o projeto do Quartus, o runtime, o mapa de memória, os testbenches das plataformas e a integração contínua conjunta. O trabalho é dividido em repositórios da organização [insper-riscv](https://github.com/insper-riscv), um por responsabilidade.

## 1. Documentação

- [AUTHORS.md](AUTHORS.md): autores com commits no repositório, com nome e conta do GitHub.
- [CONTRIBUTING.md](CONTRIBUTING.md): regras obrigatórias de contribuição, normas VHDL-2008, C23 e Python, regras de documentação e verificação antes de abrir Pull Request.
- [CITATION.cff](CITATION.cff): metadados para citação do software.
- [docs/pt-br/](docs/pt-br): guias (placa, simulação e KPIs), plataformas (memória, boot e runtime) e defeitos já diagnosticados.
- [docs/pt-br/guide/kpis.md](docs/pt-br/guide/kpis.md): scripts de KPI (frequência, recursos, CPI e testes) a partir de uma execução do Quartus.

## 2. Repositórios

| Repositório | Responsabilidade | Depende de |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | A imagem de toolchain (GCC com picolibc, Spike, GHDL, uv) em que a integração contínua executa | Nada |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`, para compilar, simular, executar na placa, certificar e verificar | Infra (na execução) |
| [Common-Components](https://github.com/insper-riscv/Common-Components) | Os blocos genéricos de VHDL (somador, flip-flop, registradores, multiplexadores, decodificador one-hot e buffer de três estados) | Nada |
| [Core](https://github.com/insper-riscv/Core) | O processador em VHDL, por extensão da ISA, perfis e testes por entidade | Common-Components |
| [Memory](https://github.com/insper-riscv/Memory) | Memórias, caches, controladores e modelos de simulação | Core (interface de memória) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO, TIMER e UART, com testes por entidade | Common-Components |
| [Tests](https://github.com/insper-riscv/Tests) | Os programas de teste (`asm/`, `c/`), goldens e os fluxos que os executam | Este repositório, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | A suíte oficial ACT4 (riscv-arch-test) | Este repositório, Tools |

`Common-Components`, `Core`, `Memory` e `Peripherals` são os submódulos deste repositório.

## 3. Plataformas

| Caminho | Plataforma |
| :--- | :--- |
| `src/simulation/internal-mem/` | Plataforma só de simulação, com BOOT_ROM, FLASH e RAM dentro da FPGA e o topo de simulação `rv32i3stage_core_sim_test`. É a base dos testes de entidade do pipeline |
| `src/simulation/modular/` | Topo de simulação configurável, com a memória de instruções e a de dados dentro ou fora do chip (`integrated`, `external-data`, `external-instruction` e `external`), FLASH e RAM de 1 MB e caches de 4 kbit por padrão. É a base da simulação do ACT4 |
| `src/cyclone-v/de0-cv/` | Plataforma da placa DE0-CV, com a BOOT_ROM no núcleo e a FLASH e a SDRAM atrás das caches, mais JTAG UART e display. O topo do Quartus é `de0-cv_top.vhd` e o de simulação é `rv32im_sdram_flash_sim_test` |

Cada plataforma tem a mesma estrutura.

| Pasta ou arquivo | Conteúdo |
| :--- | :--- |
| `platform.yaml` | Mapa de memória e a lista de cada cópia manuscrita dele, verificada por `riscv-tools check-memory-map` |
| `config.yaml` | Configuração do `riscv-tools` para toolchain, memória, Quartus e simulação |
| `quartus/` | Projeto do Quartus (`.qpf`, `.qsf`, `.sdc`, topo de hardware e imagens `.mif`) |
| `pll/` | IP da PLL |
| `rtl/` | Topo de simulação e os módulos próprios da plataforma |
| `runtime/` | `rv32im-fpga.specs`, `boot_rom.S`, `boot_rom.ld`, `_exit.c`, `stdio.c` e `spike_exit.S` |
| `testbench/` | `test_c_program.py`, o testbench cocotb que decide PASS ou FAIL de um programa |

Os testes por entidade do RTL das plataformas ficam em `tests/python/`, com o catálogo `tests.json` que os conduz.

## 4. Clonagem e Execução

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
make all        # paths, verificação VHDL, testes por entidade e provas formais
```

As ferramentas vêm da imagem `ci-vhdl` (`ghcr.io/insper-riscv/ci-vhdl`) do Infra, em que a integração contínua executa.

| Alvo | O que executa |
| :--- | :--- |
| `make paths` | Existência de todos os caminhos listados na configuração (`paths.yaml`, `riscv-tools check-paths`) |
| `make check` | Verificação de sintaxe VHDL de cada repositório, a elaboração de cada perfil do `Core`, a construção do topo de simulação de cada plataforma e a conferência de que nenhuma entidade ou pacote é definido em dois repositórios |
| `make memory-map` | Concordância de cada cópia do mapa de memória com o `platform.yaml` da plataforma |
| `make unit-tests` | Testes por entidade (cocotb e GHDL) de cada repositório e das plataformas, mais o `memory-map` |
| `make formal` | Provas formais (SymbiYosys) de cada repositório que as tem, com o engine de `FORMAL_ENGINE` (`bitwuzla` por padrão; o CI roda `yices`, `bitwuzla`, `boolector` e `abc-bmc3`) |

## 5. Placa

O projeto do Quartus da DE0-CV (Cyclone V 5CEBA4F23) é `src/cyclone-v/de0-cv/de0-cv.qpf`. A programação e a execução de testes nela são feitas por `riscv-tools run` a partir do `Tests`, conforme [placa.md](docs/pt-br/guide/placa.md).

## 6. KPIs

`scripts/kpi_report.py` e `scripts/compare_kpis.py` geram os relatórios de KPI (clock, recursos, CPI e testes) a partir de uma execução do Quartus, conforme [docs/pt-br/guide/kpis.md](docs/pt-br/guide/kpis.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).
