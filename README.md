# RV32IM

🌐 [Português](README.md) · [English](README.en.md)

![Diagrama do pipeline](Core/docs/img/multi-stage-rv32m_pipeline_final-Pipeline.jpg)

SoC RISC-V de 32 bits (RV32I + M) em VHDL, com pipeline em ordem de 5 estágios, suas memórias, periféricos e plataforma de placa, e as ferramentas e testes ao redor. O trabalho é dividido em repositórios da organização [insper-riscv](https://github.com/insper-riscv), um por responsabilidade. Este repositório é o agregador: fixa uma versão de cada um como submódulo git, guarda os relatórios de KPI e a integração contínua conjunta.

## 1. Documentação

- [AUTHORS.md](AUTHORS.md): autores com commits no repositório, com nome e conta do GitHub.
- [CONTRIBUTING.md](CONTRIBUTING.md): regras obrigatórias de contribuição, norma VHDL-2008, norma C23 (ISO/IEC 9899:2024), regras de documentação e verificação antes de abrir Pull Request.
- [CITATION.cff](CITATION.cff): metadados para citação do software.
- [docs/README_kpis.md](docs/README_kpis.md): scripts de KPI (frequência, recursos, CPI e testes) a partir de uma execução do Quartus.

## 2. Repositórios

| Repositório | Responsabilidade | Depende de |
| :--- | :--- | :--- |
| [Infra](https://github.com/insper-riscv/Infra) | A máquina: a imagem de toolchain (GCC com picolibc, Spike, GHDL, uv) em que a integração contínua executa | Nada |
| [Tools](https://github.com/insper-riscv/Tools) | `riscv-tools`: compilar, simular, executar na placa, certificar e verificar | Infra (na execução) |
| [Common-Components](https://github.com/insper-riscv/Common-Components) | Os blocos genéricos de VHDL (somador, flip-flop, registradores, multiplexadores, decodificador one-hot e buffer de três estados) que Core, Memory e Peripherals importam | Nada |
| [Core](https://github.com/insper-riscv/Core) | O processador em VHDL, por extensão da ISA, perfis e testes por entidade | Common-Components |
| [Memory](https://github.com/insper-riscv/Memory) | Modelos de simulação e IPs Quartus da placa | Core (interface de memória) |
| [Peripherals](https://github.com/insper-riscv/Peripherals) | GPIO, TIMER e UART, com testes por entidade | Common-Components |
| [TopLevel](https://github.com/insper-riscv/TopLevel) | As plataformas: projeto Quartus, PLL, topo de simulação, runtime, mapa de memória e testbench | Core, Memory, Peripherals, Tools |
| [Tests](https://github.com/insper-riscv/Tests) | Os programas de teste (`asm/`, `c/`), goldens e os fluxos que os executam | TopLevel, Tools |
| [Certification](https://github.com/insper-riscv/Certification) | A suíte oficial ACT4 (riscv-arch-test) | Core, Memory, TopLevel, Tools |

`Common-Components`, `Core`, `Memory`, `Peripherals`, `TopLevel` e `Tests` são submódulos deste repositório, lado a lado porque o `TopLevel` lê os blocos genéricos em `../Common-Components`; `Infra`, `Tools` e `Certification` são usados por conta própria.

## 3. Clonagem e Execução

```bash
git clone --recurse-submodules https://github.com/insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
make all        # paths, verificação VHDL, testes por entidade, provas formais e a suíte de programas
```

As ferramentas vêm das imagens `ci-vhdl` e `ci-elf` (`ghcr.io/insper-riscv/ci-vhdl` e `ghcr.io/insper-riscv/ci-elf`) do Infra, em que a integração contínua executa; a segunda acrescenta à primeira o GCC RISC-V, a picolibc e o Spike que a suíte de programas usa.

| Alvo | O que executa |
| :--- | :--- |
| `make paths` | Existência de todos os caminhos listados na configuração (`paths.yaml`, `riscv-tools check-paths`) |
| `make check` | Verificação de sintaxe VHDL de cada repositório em ordem de dependência, com a elaboração de cada perfil do `Core` |
| `make unit-tests` | Testes por entidade (cocotb e GHDL) de `Core`, `Memory`, `Peripherals` e `TopLevel`, e a verificação do mapa de memória |
| `make formal` | Provas formais (SymbiYosys e z3) de cada repositório que as tem |
| `make sim` | Suíte de simulação do `Tests` e os testes de host da UART |

Os submódulos ficam lado a lado porque se encontram como irmãos (`../Core`, `../Memory`, `../Peripherals`, `../TopLevel`), o mesmo arranjo de quando cada um é clonado ao lado dos demais pela integração contínua.

## 4. Placa

O projeto Quartus é `TopLevel/platforms/internal-mem/quartus/core_fpga_test.qpf` (Cyclone V 5CEBA4F23, com BOOT_ROM, FLASH e RAM dentro da FPGA). A programação e a execução de testes nela são feitas por `riscv-tools run` a partir do `Tests`, conforme [docs/HARDWARE_PROGRAMMING.md do TopLevel](https://github.com/insper-riscv/TopLevel/blob/main/docs/HARDWARE_PROGRAMMING.md).

## 5. KPIs

`scripts/kpi_report.py` e `scripts/compare_kpis.py` geram os relatórios de KPI (clock, recursos, CPI e testes) a partir de uma execução do Quartus, conforme [docs/README_kpis.md](docs/README_kpis.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](LICENSE).
