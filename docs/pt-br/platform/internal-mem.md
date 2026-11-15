# Plataforma `internal-mem`: a plataforma de simulação

## 1. O que ela é

Uma Cyclone V 5CEBA4F23 com BOOT_MEMORY, FLASH e RAM dentro da FPGA. É a base dos testes de entidade do pipeline e da simulação com arrays VHDL puros, e também tem um topo de hardware (`core_fpga_test`) para conferir o projeto do Quartus.

## 2. Estrutura

| Caminho | Conteúdo |
| :--- | :--- |
| `platform.yaml` | Mapa de memória (o bloco `memory`, palavras reservadas, pontos de entrada de boot e janelas dos periféricos) e a lista de cada cópia manuscrita dele, verificada por `riscv-tools check-memory-map` |
| `quartus/` | Projeto do Quartus da placa, com `core_fpga_test.vhd` (topo de hardware), `.qpf`, `.qsf`, `.sdc` e as imagens `.mif` iniciais |
| `pll/` | IP da PLL (50 MHz em três fases) e `pll_sim.vhd`, o substituto comportamental que a simula |
| `rtl/` | Topo de simulação `rv32i3stage_core_sim_test` (arrays VHDL puros no lugar dos IPs de memória), `clk_gen_3way` e `Blinky` |
| `runtime/` | O que a plataforma acrescenta à picolibc da toolchain, com `rv32im-fpga.specs`, `boot_memory.S`, `boot_memory.ld`, `memory_map.h`, `_exit.c`, `stdio.c` e `spike_exit.S` |
| `testbench/` | `test_c_program.py`, o testbench cocotb que observa o barramento de escrita da RAM para decidir PASS ou FAIL de um programa |
| `config.yaml`, `config.fpga-sim.yaml` | Configuração do `riscv-tools` para a plataforma, do topo de simulação e do topo de hardware sobre os modelos `altera_mf` da Intel |

## 3. Uso por um projeto

Um projeto que executa testes nesta plataforma estende a configuração dela e acrescenta só os próprios caminhos.

```yaml
extends: <caminho>/src/simulation/internal-mem/config.yaml
paths: {include_dir: ..., build_dir: build, c_dir: c, asm_dir: asm}
```

Os caminhos dentro do `config.yaml` são relativos à raiz do repositório. O campo `sim.python_path` coloca `testbench/` no caminho de busca do módulo de teste da simulação.

## 4. UART serial

A janela de periférico 4, em `0xC0000000`, contém a UART serial física. Ela opera em 115200 baud, 8N1, e possui filas independentes de transmissão e recepção com 16 bytes cada. O topo de hardware liga RX ao pino M16 e TX ao pino C16 da DE0-CV. O topo de simulação expõe as mesmas linhas para o testbench.

O mapa tem `TX_DATA` em `0xC0000000`, `RX_DATA` em `0xC0000004`, `STATUS` em `0xC0000008` e `CONTROL` em `0xC000000C`. O contrato completo dos registradores e das filas está na [documentação da UART serial](https://github.com/insper-riscv/Peripherals/blob/main/docs/pt-br/UART/serial_uart.md).

Esta UART é diferente da UART sobre JTAG da plataforma `de0-cv`. Os dois periféricos usam a mesma janela em plataformas distintas, mas possuem interfaces com o hospedeiro e mapas de estado próprios.

## 5. Verificação

| Alvo | O que confere |
| :--- | :--- |
| `make memory-map` | Concordância de cada cópia do mapa de memória com o `platform.yaml` |
| `make check-tops` | O topo de simulação elabora no GHDL |
| `make test` | Testes por entidade em cocotb do RTL da plataforma |
