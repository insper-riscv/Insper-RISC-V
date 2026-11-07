# Geração do projeto de uma placa

## 1. Princípio

Cada conceito tem um gerador, e o gerador lê o dado da fonte única. Nenhum arquivo gerado é editado à mão, e nenhum conceito é gerado por dois caminhos.

| Conceito | Fonte única | Saída |
| :--- | :--- | :--- |
| Mapa de memória | `platform.yaml` | Pacote VHDL, scripts de ligação, `.specs` e cabeçalhos (`generate-memory-map`) |
| Tempos de chip | `Memory/chips/<chip>.yaml` | Pacote VHDL `chip_<chip>_pkg` e atrasos de E/S do `.sdc` |
| Pinos | `board.yaml` e `pins.yaml` | Atribuições de pino e de padrão de E/S do `.qsf` |
| Relógios e PLL | `clocks` do `platform.yaml`, `clocks` do `board.yaml` e a família | Módulo de PLL (`altera_pll` ou `altpll`) |
| Restrições de tempo | Relógios, chips e domínios do SoC | `.sdc` |
| Projeto Quartus | Família, dispositivo e fecho de fontes do `top` | `.qpf` e `.qsf` |
| Topo da placa | Todos os acima | Entidade fina |
| Estimativa de cabimento | Calibração da família e `platform.yaml` | `capacity.json` |

## 2. O comando

```bash
riscv-tools --root . --board <placa> board generate --platform src/<família>/<plataforma>/platform.yaml --out build
```

A pasta de saída é de construção e não é versionada. O projeto fica em `build/<plataforma>-<placa>/`.

| Arquivo gerado | Conteúdo |
| :--- | :--- |
| `<plataforma>_<placa>_top.vhd` | Topo fino (seção 3) |
| `<plataforma>_<placa>_pll.v` | PLL da família com os relógios pedidos |
| `<plataforma>_<placa>.qpf` e `.qsf` | Família, dispositivo, fontes, pinos, padrões de E/S, modo de otimização e semente |
| `<plataforma>_<placa>.sdc` | Relógios, relógios gerados, atrasos de E/S e exceções de domínio |
| `chip_<chip>_pkg.vhd` | Tempos de cada chip de memória da placa |
| `capacity.json` | Estimativa por recurso e o resultado da política de cabimento |

O mapa de memória é escrito nos caminhos que o campo `generate` da plataforma declara, pelo mesmo código do `generate-memory-map`.

| Opção | Efeito |
| :--- | :--- |
| `--board` (global) | Placa; sem ela vale o campo `board` ou a única entrada de `boards` |
| `--target` | Componente cujo fecho de fontes entra no `.qsf`; sem ele vale o `top` da plataforma |
| `--seed` | Semente do posicionamento, padrão 5 |
| `--accept-inferred-pins` | Aceita construir com pino `inferred` |
| `--check` | Não escreve; sai com status 1 se o projeto ou o mapa no disco diferem do que seria gerado |

Os avisos (papel opcional ausente, fase do relógio do pino de memória não medida, backend sem entidade) saem em `stderr`. Uma entrada inválida sai com status 2, e um perfil que passa de 100 % de um recurso recusa a geração.

## 3. O topo gerado

O topo só liga. Nenhuma lógica nasce nele além do reset.

1. Portas da placa, geradas dos papéis de `io` e de `memories` do `board.yaml` (`LEDR` de 18 bits e `DRAM_DQ` de 32 bits na `de2-115`).
2. O PLL e o reset: o reset do usuário com a polaridade da placa, e o reset do SoC liberado dois ciclos de `core` depois do travamento do PLL.
3. A instância do `soc`, com os relógios por papel e os vetores de E/S de polaridade normalizada.
4. Uma instância de backend por região externa (seção 4).
5. O anel de pinos dos backends de dispositivo, com um buffer de três estados por bit em um `generate`.
6. Os generics do Zihpm, as polaridades dos papéis, os cortes de caminho crítico e o controlador de FLASH da atualização de programa, com os mesmos valores para toda placa que liga o recurso.

## 4. Backends que o topo instancia

| Backend | Instância gerada | Generics preenchidos |
| :--- | :--- | :--- |
| `emulado` da FLASH | Chip de FLASH, armazenamento de duas portas, carregador e casca de Virtual JTAG | Tamanho, latência de `memory.rom.latency`, família |
| `emulado` da RAM | Porta de RAM sobre o bloco de memória | Tamanho, latência |
| `dispositivo/sdram` | Pontes de dados e de instruções, árbitro, mestre de depuração, casca de Virtual JTAG e controlador | Largura (16 ou 32 bits), bits de linha, coluna e banco, tempos do chip, período de `mem` |
| `dispositivo/nor` | Controlador de FLASH NOR de 8 bits com leitura em página e comandos | Ciclos de acesso aleatório e de página, tamanho do setor |

Uma região com `dispositivo/sram`, `flash-interna` ou `serial` não gera instância: o topo avisa e deixa a região parada.

## 5. PLL e restrições por família

| Família | Primitiva de PLL |
| :--- | :--- |
| Cyclone V, Cyclone V SoC | `altera_pll` |
| Cyclone IV E, MAX 10, Cyclone 10 LP | `altpll` |

O gerador de PLL escolhe o menor VCO dentro da faixa `vco_mhz` da família para o qual cada saída tem divisor inteiro de 1 a 511 e a fase é múltiplo de um oitavo do período do VCO. Sem solução, ou com mais saídas que `outputs_max`, o erro nomeia os pedidos (V7 e V15). Mudar a frequência do núcleo é gerar o PLL de novo com outro `clocks.core.mhz`.

O `.sdc` traz, nesta ordem, o relógio de referência, `derive_pll_clocks`, o relógio gerado do pino da memória e os atrasos de E/S de cada chip, o caminho de leitura da memória, os cruzamentos entre `mem`, `core`, `fetch` e a JTAG, e os caminhos falsos de reset, chaves, botões, LEDs e displays. Cada cruzamento é limitado pelo menor período entre os relógios do SoC,

$$ b = \min_{r} T_r $$

e o nome dos nós do PLL vem do campo `clock_node_pattern` da família.

## 6. Compilar e programar

O comando `program` usa o mesmo gerador antes de compilar (chave `quartus.generate` do `config.yaml`) e acrescenta as opções de compilação.

| Opção | Efeito |
| :--- | :--- |
| `--seed N` | Semente do posicionamento, com o modo `HIGH PERFORMANCE EFFORT` fixo |
| `--generic NOME=VALOR` | Troca um generic do topo só nessa compilação |
| `--stop-after map\|fit\|sta` | Para depois da etapa e não programa |
| `--compile-only` | Compila e não programa |
| `--project-dir`, `--project-name` | Projeto escrito por `board generate` |

A compilação passa por um único script de Tcl para todas as placas, e a calibração do estimador usa o mesmo script.

## 7. Unicidade e equivalência

Três verificações automáticas protegem o princípio da seção 1.

| Verificação | O que garante |
| :--- | :--- |
| Teste de unicidade do Tools | Cada tipo de texto gerado tem um só módulo escritor |
| `check-boards` | O pino aparece só no `pins.yaml`, e o chip e a família só são citados pelo nome |
| `board generate --check` | O projeto no disco é o que o gerador escreveria |

A equivalência do projeto gerado da DE0-CV com o que foi escrito à mão está em [equivalencia-de0-cv.md](equivalencia-de0-cv.md).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
