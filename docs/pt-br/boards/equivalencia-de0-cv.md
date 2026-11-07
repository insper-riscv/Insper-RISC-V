# Equivalência da DE0-CV gerada

Este relatório compara o projeto do Quartus que `riscv-tools board generate` escreve para a DE0-CV com o projeto que a plataforma tinha escrito à mão (topo, `.qsf`, `.sdc` e PLL). A comparação segue a tabela de equivalência do plano de geração.

## 1. Como comparar

```bash
uv run riscv-tools --root . board generate --platform src/cyclone-v/de0-cv/platform.yaml --out build \
    --hand-qsf <.qsf escrito à mão> --hand-sdc <.sdc escrito à mão> --hand-pll <PLL escrito à mão>
```

O relatório normaliza os dois lados e lista, por seção, o que só existe à mão, o que só existe no gerado e o que mudou. Cada seção é equivalente quando nada só existe à mão e nada mudou.

## 2. Resultado por item

| Item | Comparação | Resultado |
| :--- | :--- | :--- |
| Pinos e padrões de E/S | Conjunto de (sinal, pino, padrão) do `.qsf` | Equivalente, 107 pinos |
| Atribuições por instância | Atribuições que não são padrão de E/S | Equivalente |
| Projeto | Família, dispositivo, versão do VHDL, modo de otimização | Equivalente |
| Relógios e restrições | Comandos do `.sdc` normalizados | Equivalente; o gerado acrescenta dois caminhos falsos, das chaves e dos botões |
| PLL | Frequência, fase e razão de cada saída | Equivalente: 100 MHz (fase 0 e 4000 ps), 76,923077 MHz (fases 0 e 7500 ps) |
| Fontes | Arquivos VHDL | Diferem só pelo que a geração substitui (ver seção 4) |
| Síntese | ALMs, registradores e bits de memória | Seção 3 |
| Tempo | Folgas por domínio, sementes 1 a 5 | Seção 3 |

## 3. Síntese e tempo

As duas tabelas vêm do mesmo Quartus, com o modo `HIGH PERFORMANCE EFFORT`, e as folgas são o pior caso entre os modelos de 85 C e de 0 C.

Projeto gerado:

| Semente | ALMs | Registradores | Bits de memória | Setup núcleo (ns) | Setup busca (ns) | Hold núcleo (ns) | Hold SDRAM (ns) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10.382 | 11.193 | 2.205.952 | 0,749 | 0,960 | 0,121 | 0,159 |
| 2 | 10.348 | 11.271 | 2.205.952 | 0,210 | 1,244 | 0,130 | 0,162 |
| 3 | 10.345 | 11.200 | 2.205.952 | 1,079 | 0,724 | 0,122 | 0,163 |
| 4 | 10.349 | 11.171 | 2.205.952 | 1,271 | 0,416 | 0,133 | 0,157 |
| 5 | 10.324 | 11.192 | 2.205.952 | 0,782 | 0,915 | 0,119 | 0,164 |

Projeto escrito à mão (sementes 1 a 3):

| Semente | ALMs | Registradores | Bits de memória | Setup núcleo (ns) | Setup busca (ns) | Hold núcleo (ns) | Hold SDRAM (ns) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10.382 | 10.768 | 2.205.952 | 0,352 | 0,570 | 0,121 | 0,165 |
| 2 | 10.395 | 10.757 | 2.205.952 | 0,166 | 0,734 | 0,124 | 0,153 |
| 3 | 10.376 | 10.762 | 2.205.952 | 0,694 | 0,465 | 0,119 | 0,166 |

O gerado fecha o setup e o hold em todos os domínios nas cinco sementes. Os bits de memória são os mesmos. As ALMs ficam dentro da dispersão entre sementes (10.324 a 10.382 no gerado e 10.376 a 10.395 no escrito à mão), e o gerado usa cerca de 4 % mais registradores; a diferença vem dos blocos GPIO das chaves e dos botões e do console, que o topo escrito à mão não tinha.

## 4. O que a geração substitui

| Escrito à mão | Gerado |
| :--- | :--- |
| Topo da placa | Topo fino que liga o SoC, os backends de FLASH e de SDRAM, o PLL e o anel de pinos |
| PLL em Verilog | PLL com os mesmos parâmetros, escrito a partir de `clocks` |
| `.qsf`, `.qpf` e `.sdc` | Os mesmos arquivos, com as fontes tiradas do fecho de `requires` do componente `top` |
| Arquivos `.qip` das memórias | Entidade de bloco de memória parametrizada |
| Invólucros do Virtual JTAG da UART e do display | Entidade de Virtual JTAG parametrizada, com os nós de índice 0 (carregador), 1 (UART), 2 (display) e 3 (SDRAM) |
| LEDs de extensões e de exceção | Só o primeiro LED, que acende com a bandeira de falha do display |

## 5. Placa

Os programas do repositório de testes rodaram na placa DE0-CV com o bitstream do projeto gerado (semente 5), pelo executor de placa do repositório de testes.

| Etapa | Programas | Passaram | Falharam |
| :--- | ---: | ---: | :--- |
| SDRAM | 20 | 20 | nenhum |
| Interrupções | 13 | 13 | nenhum |
| Regressão | 128 | 127 | `hpm-cpi` |

O `hpm-cpi` confere que a soma dos ciclos atribuídos pelos contadores de eventos fica a 1 % do `mcycle`, e falha do mesmo modo com o bitstream escrito à mão compilado da mesma árvore (a primeira palavra do resultado vem 0 onde o valor esperado é 1). Com o bitstream escrito à mão, a etapa SDRAM passa em 19 de 20 programas, e o `clint-mtip` é o que falha.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
