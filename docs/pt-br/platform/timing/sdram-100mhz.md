# Controlador da SDRAM e `DRAM_CLK` a 100 MHz

🌐 [Português](sdram-100mhz.md) · [English](../../../en/platform/timing/sdram-100mhz.md)

## 1. Escopo

Este documento mede o passo F.P6 da frente de 100 MHz: o controlador da SDRAM e o pino `DRAM_CLK` da `de0-cv` deixam o relógio de 142,857 MHz e passam a 100 MHz, a frequência final do núcleo, e registra o que isso custa na taxa da SDRAM. As referências são o [marco M1](MARCOS.md) (controlador em 142,857 MHz) e a [linha de base](README.md).

## 2. Condições da medição

| Item | Valor |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, no notebook, um compilador por vez |
| Dispositivo | 5CEBA4F23C7 (Cyclone V) |
| Fontes | Insper-RISC-V da `onda2` com o passo F.P6, Core `7e05744`, Memory `1c4de11`, Peripherals `69abd8b`, Common-Components `56c293e` |
| Modo | `HIGH PERFORMANCE EFFORT`, sementes 1 a 5, pelo `de0-cv_synth.tcl` |
| Relógios | Controlador e `DRAM_CLK` a 100 MHz; núcleo e busca a 50 MHz, com a fase do núcleo em 8250 ps (a do [marco M1](MARCOS.md)) |
| Folga de setup | Modelo lento a 85 °C, folga do domínio de relógio de destino |
| Folga de hold | Modelo rápido a 0 °C, menor valor entre os domínios |
| Simulação | GHDL e cocotb na imagem `ci-elf`, núcleo a 100 MHz (período de 10 ns) e a 50 MHz, controlador a 7 ns e a 10 ns |

## 3. Por que o controlador a 142,857 MHz não fecha

O pior caminho do domínio do controlador é a leitura do dado: o pino `DRAM_DQ` até o registrador `dq_in` da célula de entrada e saída. O chip responde um tempo $t_{AC}$ depois da borda do `DRAM_CLK`, e o Quartus mede o caminho contra a segunda borda do controlador depois da que lançou o dado (caminho multiciclo de 2).

| Termo da semente 1 (142,857 MHz, fase de `DRAM_CLK` em 2750 ps) | Valor (ns) |
| :--- | ---: |
| Relação entre a borda de lançamento e a de captura | 11,250 |
| Atraso de relógio até o pino `DRAM_CLK`, menos o até o registrador de captura | -4,030 |
| $t_{AC}$ do chip | 5,400 |
| Atraso do pino até o registrador | 2,425 |
| Incerteza de relógio | 0,140 |
| Folga | -0,745 |

A fase do `DRAM_CLK` desloca os dois lados da conta em sentidos opostos: aumentar a fase em $\delta$ tira $\delta$ da folga da leitura e põe $\delta$ na folga de setup das saídas contra o `DRAM_CLK`. A soma das duas folgas não depende da fase.

| Semente | Controlador (leitura) | `DRAM_CLK` (saídas) | Soma |
| ---: | ---: | ---: | ---: |
| 1 | -0,745 | 0,429 | -0,316 |
| 2 | -0,255 | -0,127 | -0,382 |
| 3 | -0,205 | -0,046 | -0,251 |
| 4 | -0,173 | -0,078 | -0,251 |
| 5 | -0,713 | 0,394 | -0,319 |

A soma é negativa nas cinco sementes, então nenhuma fase fecha o controlador e o `DRAM_CLK` ao mesmo tempo em nenhuma delas (valores do [marco M1](MARCOS.md), seção 3.2). Corrigir o caminho a 142,857 MHz exigiria um relógio de captura próprio com fase independente e mais um cruzamento de domínio, sem ganho de taxa que compense.

## 4. A solução: controlador a 100 MHz

O controlador, o árbitro e o mestre de depuração passam a rodar em 100 MHz, na saída 0 da PLL, e o `DRAM_CLK` na saída 1, também em 100 MHz. O oscilador interno de 1000 MHz da PLL já dá os 100 MHz (divisor 10). A ponte da SDRAM mantém os toggles e os sincronizadores de dois flip-flops: o cruzamento com o núcleo vale para qualquer razão de frequência, e o limite de 10 ns do `.sdc` continua abaixo de duas bordas do controlador (20 ns) e do núcleo (20 ns a 100 MHz).

A relação do caminho de leitura passa de 11,25 ns para $2 T - \varphi = 16{,}0$ ns com $\varphi$ = 4000 ps, e o das saídas contra o `DRAM_CLK` é a própria fase. Os tempos do chip em ciclos vêm de `SDRAM_TCK_PS` (10 000 ps), do `sdram` do `platform.yaml`:

| Tempo do chip | Ciclos a 7 ns | Ciclos a 10 ns |
| :--- | ---: | ---: |
| tRCD e tRP (15 ns) | 3 | 2 |
| tRC (60 ns) e tRFC (63 ns) | 9 | 6 e 7 |
| Acesso de página fechada, ACTIVE até o próximo ACTIVE | 10 | 9 |
| Intervalo entre refreshes | 1116 | 782 |

### 4.1. Fase do `DRAM_CLK`

Duas fases, cinco sementes (três na de 4000 ps), núcleo e busca como no restante deste documento. Com 3000 ps a folga das saídas é a menor do conjunto (0,123 ns), e com 4000 ps as duas folgas ficam em 1,1 ns e 4,0 ns; a fase de 4000 ps é a versionada.

Fase de 3000 ps:

| Semente | ALMs | Registradores | Fmax núcleo (MHz) | Fmax controlador (MHz) | núcleo | busca | controlador | `DRAM_CLK` | JTAG | hold mín. |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8297 | 9387 | 67,05 | 154,8 | 0,907 | 3,830 | 3,540 | 0,679 | 10,089 | 0,117 |
| 2 | 8304 | 9368 | 65,54 | 171,03 | 0,343 | 3,552 | 4,153 | 0,123 | 11,044 | 0,019 |
| 3 | 8322 | 9483 | 63,83 | 161,34 | 1,218 | 2,651 | 3,802 | 0,204 | 9,988 | 0,127 |
| 4 | 8297 | 9470 | 65,33 | 145,6 | 1,451 | 3,530 | 3,132 | 0,172 | 10,263 | 0,078 |
| 5 | 8294 | 9395 | 67,02 | 174,52 | 1,010 | 4,166 | 4,270 | 0,660 | 9,601 | 0,145 |
| Pior | 8322 | 9483 | 63,83 | 145,6 | 0,343 | 2,651 | 3,132 | 0,123 | 9,601 | 0,019 |

Fase de 4000 ps (as sementes 1 a 3 desta rodada, com as fontes anteriores ao renome `BOOT_MEMORY`):

| Semente | ALMs | Registradores | Fmax núcleo (MHz) | Fmax controlador (MHz) | núcleo | busca | controlador | `DRAM_CLK` | JTAG | hold mín. |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8297 | 9375 | 65,29 | 151,91 | 0,873 | 4,009 | 3,417 | 1,679 | 10,145 | 0,129 |
| 2 | 8304 | 9433 | 65,43 | 160,93 | 0,262 | 3,917 | 3,786 | 1,123 | 10,989 | 0,010 |
| 3 | 8322 | 9493 | 63,27 | 166,09 | 1,226 | 2,570 | 3,979 | 1,204 | 10,900 | 0,125 |
| Pior | 8322 | 9493 | 63,27 | 151,91 | 0,262 | 2,570 | 3,417 | 1,123 | 10,145 | 0,010 |

## 5. Resultado

Controlador e `DRAM_CLK` a 100 MHz, fase de 4000 ps, núcleo a 50 MHz com a fase de 8250 ps. As folgas estão em ns e as Fmax em MHz.

| Semente | ALMs | Registradores | Fmax núcleo (MHz) | Fmax controlador (MHz) | núcleo | busca | controlador | `DRAM_CLK` | JTAG | hold mín. |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 8265 | 9404 | 64,7 | 160,72 | 0,558 | 2,896 | 3,778 | 1,678 | 11,227 | 0,130 |
| 2 | 8329 | 9497 | 64,29 | 157,43 | 0,610 | 4,012 | 3,648 | 1,123 | 10,016 | 0,079 |
| 3 | 8293 | 9451 | 65,79 | 162,79 | 1,449 | 2,189 | 3,857 | 1,203 | 9,027 | 0,092 |
| 4 | 8288 | 9437 | 66,11 | 151,63 | 1,342 | 2,904 | 3,405 | 1,172 | 10,539 | 0,116 |
| 5 | 8319 | 9376 | 67,37 | 156,96 | 1,046 | 3,979 | 3,629 | 1,644 | 10,923 | -0,009 |
| Pior | 8329 | 9497 | 64,29 | 151,63 | 0,558 | 2,189 | 3,405 | 1,123 | 9,027 | -0,009 |

| Item | Resultado |
| :--- | :--- |
| Controlador | Folga de setup entre +3,405 e +3,857 ns nas cinco sementes (contra -0,745 a -0,173 ns a 142,857 MHz); o pior caminho passou a ser interno ao mestre de depuração. O caminho de leitura do pino tem folga de +4,0 ns (semente 1) |
| `DRAM_CLK` | Folga de setup entre +1,123 e +1,678 ns (contra -0,127 a +0,429 ns) |
| Núcleo e busca | Folga não negativa nas cinco sementes com a fase de 8250 ps (pior +0,558 ns no núcleo e +2,189 ns na busca) |
| Hold | Positivo em todos os domínios e sementes, exceto o relógio do JTAG (`altera_reserved_tck`) da semente 5, com -0,009 ns no modelo rápido a 0 °C. Ele está no concentrador do JTAG, não na SDRAM, e nas sementes 1 a 4 o menor hold é +0,079 ns |
| Área | 8265 a 8329 ALMs. Com as mesmas fontes e o controlador a 142,857 MHz a semente 1 usa 8319 ALMs e 9354 registradores, contra 8265 e 9404 a 100 MHz, então a mudança não altera a área de forma mensurável |

## 6. Taxa da SDRAM

Os programas `cpi-data`, `sdram-copy`, `sdram-loop`, `cache-sweep`, `code-sweep`, `sdram-memtest`, `sdram-bytes` e `selfmod-repeat` rodam em simulação nos quatro cenários (núcleo a 100 e a 50 MHz, controlador a 7 e a 10 ns) e passam em todos. A tabela dá o tempo simulado até o fim do programa, em ns.

| Programa | 100 MHz, 7 ns | 100 MHz, 10 ns | Variação | 50 MHz, 7 ns | 50 MHz, 10 ns | Variação |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sdram-copy` | 2 337 525 | 2 438 111 | +4,3 % | 4 095 855 | 4 169 991 | +1,8 % |
| `sdram-loop` | 1 414 225 | 1 431 631 | +1,2 % | 2 513 295 | 2 529 311 | +0,6 % |
| `cache-sweep` | 6 607 672 | 6 804 571 | +3,0 % | 12 250 680 | 12 434 821 | +1,5 % |
| `code-sweep` | 15 610 561 | 15 611 351 | 0,0 % | 30 969 632 | 30 970 111 | 0,0 % |
| `sdram-memtest` | 3 382 835 | 3 485 251 | +3,0 % | 6 066 922 | 6 180 551 | +1,9 % |
| `sdram-bytes` | 1 253 995 | 1 257 371 | +0,3 % | 2 246 014 | 2 248 771 | +0,1 % |

Os contadores do Zihpm dos kernels `cpi-data` dão a largura de banda e a latência que o núcleo enxerga. `sdram-stream` varre 8 KiB com 2048 loads e 512 falhas da cache de dados; `sdram-store` faz 256 stores de palavra em cache write-through.

| Medida | 100 MHz, 7 ns | 100 MHz, 10 ns | 50 MHz, 7 ns | 50 MHz, 10 ns |
| :--- | ---: | ---: | ---: | ---: |
| `sdram-stream`, ciclos do núcleo | 31 349 | 33 810 | 27 728 | 29 234 |
| `sdram-stream`, tempo (µs) | 313,5 | 338,1 | 554,6 | 584,7 |
| Largura de banda de leitura em linhas (MB/s) | 26,1 | 24,2 | 14,8 | 14,0 |
| Espera externa por falha de linha (ciclos do núcleo) | 33,2 | 38,0 | 26,1 | 29,1 |
| Espera externa por falha de linha (ns) | 332 | 380 | 523 | 582 |
| `sdram-store`, espera externa por store (ciclos do núcleo) | 14,0 | 15,0 | 10,6 | 11,0 |
| `sdram-store`, ciclos do núcleo | 5381 | 5640 | 4500 | 4620 |
| `sdram-load-use`, ciclos do núcleo (acertos) | 2318 | 2322 | 2317 | 2318 |

O controlador a 10 ns custa 4 a 8 % no tempo de um programa que só varre a SDRAM (`sdram-stream`, `sdram-copy`), 3 % nos que a usam com reuso (`cache-sweep`, `sdram-memtest`) e nada nos que ficam nas caches (`sdram-load-use`, `code-sweep`). Os números de ciclos por instrução dos programas que não usam a SDRAM não mudam. Os valores brutos estão em `dados/sdram-100mhz/`.

## 7. Decisão

A opção escolhida é o controlador a 100 MHz com a ponte de razão 1 para 1, e não a correção do caminho a 142,857 MHz. A medida a favor é a da seção 3 (a soma das folgas é negativa nas cinco sementes, então não há fase que feche) e a da seção 5 (todos os domínios com folga nas cinco sementes). A taxa perdida é a da seção 6, no máximo 8 % do tempo de um programa dominado pela SDRAM, bem abaixo dos 30 % que o plano previa. Como o controlador não depende da frequência do núcleo, o mesmo bitstream vale nos marcos M1 a M4.

## 8. Como reproduzir

| Objetivo | Comando |
| :--- | :--- |
| Compilar uma semente | `quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl <semente>`, numa cópia do repositório |
| Mudar o relógio ou a fase do controlador | Editar `sdram.clock_hz` e `sdram.dram_clk_phase_ps` do `platform.yaml`, `output_clock_frequency0`, `output_clock_frequency1` e `phase_shift1` de `src/cyclone-v/de0-cv/pll/sdram_platform_pll.v`, e rodar `riscv-tools generate-memory-map`; o `check-memory-map` confere que os dois lados batem |
| Simular com outro relógio | `SIM_CLOCK_PERIOD_NS` (período do `CLK`, três vezes o do núcleo) e `SIM_EXTRA_CLOCKS=CLK_MEM:<ns>` com o parâmetro `SDRAM_TCK_PS=<ps>` do topo de simulação |

## 9. Marcos M1 e M2 com o controlador a 100 MHz

As fontes são as do merge com a trilha do núcleo da `onda2` (Core `a826b68`, passos F.P4 e F.P5; Memory `8455a20`; Peripherals `6ed5e07`). A fase do `DRAM_CLK` é a de 4000 ps.

### 9.1. Marco M1: 50 MHz, fase do núcleo em 8250 ps

| Semente | ALMs | Registradores | Fmax núcleo (MHz) | Fmax controlador (MHz) | núcleo | busca | controlador | `DRAM_CLK` | JTAG | hold mín. |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7948 | 9155 | 63,78 | 157,98 | 0,976 | 3,623 | 3,670 | 1,679 | 10,598 | 0,091 |
| 2 | 7943 | 9214 | 65,41 | 163,85 | 0,048 | 3,964 | 3,897 | 1,123 | 11,051 | 0,052 |
| 3 | 7956 | 9222 | 67,14 | 172,06 | 1,260 | 2,496 | 4,188 | 1,203 | 10,767 | 0,122 |
| 4 | 7978 | 9178 | 66,48 | 154,66 | 0,979 | 3,689 | 3,534 | 1,172 | 11,000 | 0,132 |
| 5 | 7911 | 9221 | 62,9 | 145,82 | 0,953 | 3,194 | 3,142 | 1,644 | 10,720 | 0,118 |
| Pior | 7978 | 9222 | 62,9 | 145,82 | 0,048 | 2,496 | 3,142 | 1,123 | 10,598 | 0,052 |

| Condição | Resultado |
| :--- | :--- |
| Folga de setup não negativa em todos os domínios (núcleo, busca, controlador, `DRAM_CLK`, JTAG) | Cumprida nas cinco sementes; a menor é +0,048 ns no núcleo (semente 2) |
| Folga de hold não negativa no modelo rápido a 0 °C | Cumprida nas cinco sementes; a menor é +0,052 ns |
| Suíte de hardware na placa com o bitstream da semente 5 | 127 programas da regressão e 17 programas da `sdram-flash` passam (`sdram-copy`, `sdram-loop`, `cache-sweep`, `code-sweep`, `flash-const`, `sdram-exec-copy`, `selfmod-repeat`, `sdram-memtest`, `sdram-bytes`, `sdram-refresh` e os demais); os três programas de UART por pinos ficam de fora porque a placa não tem UART ligada |

O M1 fecha. A fase de 8250 ps fica versionada na PLL e na seção `pll` do `platform.yaml` depois dessa validação na placa.

### 9.2. Marco M2: 66,667 MHz

Pior das cinco sementes (ns) por fase do núcleo, com o controlador e `DRAM_CLK` como acima.

| Fase do núcleo | Núcleo | Busca | Controlador | `DRAM_CLK` | Hold mín. |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 8500 ps | -0,366 | 0,194 | 3,377 | 1,123 | 0,022 |
| 8625 ps | -0,217 | -0,035 | 3,320 | 1,123 | 0,123 |
| 8875 ps | 0,567 | -0,272 | 3,315 | 1,123 | 0,117 |

O M2 não fecha: o laço da cache de instruções (etiqueta até o PC) e o do núcleo trocam folga com a fase, e nenhuma das três fases deixa os dois com folga não negativa nas cinco sementes (a de 8500 ps falha no núcleo das sementes 2 e 5, a de 8875 ps na busca das sementes 3 e 4 e a de 8625 ps no núcleo da semente 2, com -0,217 ns, e na busca das sementes 3 e 4, com -0,035 ns no pior caso). O controlador e `DRAM_CLK` não limitam mais o marco.

### 9.3. Marcos M3 e M4

O [FRENTE-F-ONDA2.md](FRENTE-F-ONDA2.md) mede o núcleo e a busca a 83,333 MHz e a 100 MHz com os passos F.P4 e F.P5: o núcleo fica em -0,09 a -1,79 ns a 83,333 MHz e o laço de leitura de CSR realimentando a escrita do contador do Zihpm tem 12,3 ns de dados contra os 10 ns do período. O controlador da SDRAM e `DRAM_CLK` deixaram de ser parte do que falta: a 100 MHz eles têm 3,1 ns e 1,1 ns de folga (seção 5). O M3 e o M4 não fecham, e o que falta é só o laço do núcleo.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
