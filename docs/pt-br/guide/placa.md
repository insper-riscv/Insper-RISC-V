# Compilar e programar a DE0-CV

## 1. A regra: compilar e programar no mesmo shell

`quartus_sh --flow compile` e `quartus_pgm` rodam encadeados no mesmo shell (`cmd1 && cmd2`). Lançá-los como duas chamadas `subprocess.run()` do Python em sequência faz o `quartus_pgm` falhar com `Can't scan JTAG chain. Error code 87`, e depois disso o `jtagconfig` deixa de enxergar a placa até um ciclo de energia dela.

| Como compilar e programar foram lançados | Resultado |
| :--- | :--- |
| Duas chamadas `subprocess.run()` do Python em sequência | 4 falhas em 4 |
| Dois comandos de shell separados, um para cada ferramenta | 2 sucessos em 2 |
| Um único `bash -c "cmd1 && cmd2"` | 2 sucessos em 2, mesmo com 1 s entre eles |

O tempo de espera entre os dois não é a variável. A causa mecanística não foi confirmada, e a pesquisa na comunidade Intel aponta que as ferramentas de linha de comando do Quartus às vezes não inicializam o ambiente JTAG como a interface gráfica faz. O `riscv-tools` (`quartus_program/core.py` do [Tools](https://github.com/insper-riscv/Tools/blob/main/src/riscv_tools/quartus_program/core.py)) já monta a cadeia numa única string de shell.

## 2. Compilar e programar a de0-cv

O projeto do Quartus não é um arquivo versionado: o `program` o escreve a partir do `platform.yaml` e do pacote da placa (`boards/de0-cv`) e o compila numa pasta de construção. Um único comando escreve, compila e programa.

```bash
uv run riscv-tools --config src/cyclone-v/de0-cv/config.yaml program <imagem.mif>
```

| Opção | O que faz |
| :--- | :--- |
| `--seed N` | Semente do posicionamento (padrão 5), com o modo `HIGH PERFORMANCE EFFORT` fixo |
| `--stop-after map\|fit\|sta` | Para depois da etapa e não programa; `map` basta para conferir caminhos e entidades |
| `--compile-only` | Compila sem programar a placa e sem exigir a imagem |
| `--generic NOME=VALOR` | Troca um generic do topo só nessa compilação (`HPM_COUNTERS=4 HPM_WIDTH=40` compila o Zihpm reduzido), sem gravar nada no projeto |
| `--board NOME` | Escolhe a placa pela identificação, no lugar do campo `board` da plataforma |

O comando `riscv-tools board generate --platform src/cyclone-v/de0-cv/platform.yaml --out build` escreve só o projeto (`build/de0-cv-de0-cv/`) e os arquivos do mapa de memória, e com `--check` os confere sem escrever. A frequência do núcleo muda em `clocks.core.mhz` do `platform.yaml`, e o PLL, o `.sdc` e o pacote do mapa seguem dela.

O cabo da bancada aparece como `USB-Blaster [3-6]`, com o dispositivo `5CE(BA4|FA4)`.

## 3. Rodar programas na placa

Com o bitstream já programado, o `riscv-tools` do projeto de testes ([Tests](https://github.com/insper-riscv/Tests)) escreve cada programa na BOOT_MEMORY, na FLASH e na SDRAM por JTAG e confere o resultado, sem recompilar a FPGA.

```bash
cd Tests
riscv-tools --config tools/riscv_build/config.sdram-flash.yaml compile --emit mif --only conformance-fencei
riscv-tools --config tools/riscv_build/config.sdram-flash.yaml run --skip-reconfigure --skip-recompile --only conformance-fencei
```

Sem `--skip-reconfigure`, o `run` compila e programa antes, pela cadeia da seção 1. A troca de um programa por outro está descrita em [atualizacao-de-programa.md](../platform/atualizacao-de-programa.md).

## 4. Se a placa não responde

| Sintoma | O que verificar |
| :--- | :--- |
| `jtagconfig` não lista o cabo | Cabo USB, alimentação da placa e, se a cadeia aparecer quebrada, um ciclo de energia dela |
| `jtagconfig` lista a placa, mas leituras e escritas pelo JTAG travam | O PLL perdeu o lock e o núcleo ficou em reset. Só um ciclo de energia recupera |
| O `quartus_pgm` falha logo depois de uma compilação | A regra da seção 1 foi quebrada |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
