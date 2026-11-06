# Frente F na Onda 2: passos F.P4 e F.P5 e o marco M3

🌐 [Português](FRENTE-F-ONDA2.md) · [English](../../../en/platform/timing/FRENTE-F-ONDA2.md)

## 1. Escopo

Este documento mede a `de0-cv` com os passos F.P4 (classificação do endereço registrada em EX/MEM) e F.P5 (laço da busca e cache de instruções) e confere o marco M3 (relógio do núcleo entre 80 e 100 MHz). Os passos estão descritos em `Core/docs/pt-br/timing/P4_*.md` e `P5_*.md` e em `Memory/docs/pt-br/cache/icache.md`. A referência é o pior cenário do Quartus: modelo lento a 85 °C no setup, modelo rápido a 0 °C no hold.

## 2. Condições da medição

| Item | Valor |
| :--- | :--- |
| Quartus | Prime 25.1std Build 1129 Lite, na workstation PC1 |
| Dispositivo | 5CEBA4F23C7 (Cyclone V) |
| Topo e projeto | `core_fpga_sdram_flash`, `src/cyclone-v/de0-cv/de0-cv.qsf`, `.sdc` versionado |
| Modo | `HIGH PERFORMANCE EFFORT`, pelo `de0-cv_synth.tcl` |
| Relógios | Saídas 2 (busca, fase 0) e 3 (núcleo, fase indicada) da PLL na frequência indicada; o controlador da SDRAM e `DRAM_CLK` ficam em 142,857 MHz; só a cópia de trabalho muda, o repositório não |
| Frequência do marco | 83,333 MHz (divisor 12 do VCO de 1000 MHz), a menor frequência realizável pela PLL acima de 80 MHz |
| Pares de relógios | `c3` é o relógio do núcleo, `c2` o da busca; `c2>c3` é o caminho da cache de instruções ao PC, `c3>c2` o do PC à cache |

Os resumos e os piores caminhos por par estão em `dados/frente-f-onda2/`.

## 3. Resultado a 83,333 MHz, fase do núcleo em 6000 ps, sementes 1 a 5

| Domínio | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo (`c3`) | -0,698 | -1,786 | -0,475 | -0,086 | -1,322 | -1,786 |
| Busca (`c2`) | 0,003 | 0,266 | -0,294 | -0,762 | -0,186 | -0,762 |
| Controlador da SDRAM | -0,742 | -0,255 | -0,205 | -0,173 | -0,728 | -0,742 |
| `DRAM_CLK` | 0,426 | -0,127 | -0,046 | -0,078 | 0,410 | -0,127 |
| JTAG | 9,990 | 10,658 | 8,803 | 9,898 | 8,300 | 8,300 |
| Menor hold, modelo rápido a 0 °C | 0,123 | 0,130 | 0,136 | 0,086 | 0,102 | 0,086 |
| ALMs | 8 940 | 8 947 | 9 159 | 9 162 | 8 941 | 9 162 |

O M3 não fecha: o núcleo e a busca ficam negativos em todas as sementes menos uma, e o controlador da SDRAM e `DRAM_CLK` (passo F.P6, outra trilha) continuam negativos.

## 4. Antes e depois dos passos, semente 1

| Medida | Antes (Core `8a828cc`, Memory `1160ae1`) | Depois |
| :--- | ---: | ---: |
| 83,333 MHz, fase 6000: pior par | -1,039 ns (`c3>c2`, PC até o bit de validade) | -0,698 ns (`c2>c3`, tag até o PC) |
| 83,333 MHz, fase 6000: núcleo para núcleo | -0,639 ns | -0,289 ns |
| 100 MHz, fase 5000: núcleo para núcleo | -2,453 ns (12,2 ns de dados) | -2,687 ns (12,5 ns de dados) |
| 100 MHz: PC até a cache | -2,610 ns (7,1 ns de dados) | fora dos 400 piores caminhos |
| ALMs a 100 MHz (fase 5000) | 9 636 | 9 281 |

## 5. O que limita o resto

| Caminho (modelo lento, 100 MHz) | Dados | Leitura |
| :--- | ---: | :--- |
| Leitura de CSR realimentando a escrita de CSR: contador do Zihpm, multiplexador de 29 contadores, `csr_file`, contador de destino | 12,3 ns | Nove níveis de lógica com roteamento de 1,3 a 1,9 ns entre os níveis; o laço é um `csrrs`, `csrrc` ou `csrrw` sobre um contador |
| `r_we_ok`, `r_fwd_match_rs*` e `r_imm` até os registradores de contagem e o PC | 12,0 a 12,4 ns | A confirmação da instrução em EX chega a todos os contadores |
| Tag da cache de instruções até a habilitação do PC | 4,2 a 5,0 ns | 2,5 ns são da saída da RAM de tag, o resto é o acerto e a habilitação do PC |

Nenhum desses é um passo pequeno: o primeiro exige tirar a escrita dos contadores do mesmo ciclo da leitura (com adiantamento ou parada para o `csr` seguinte), e o último exige que a cache de instruções entregue o acerto já registrado, o que muda o contrato de busca e coloca a leitura da cache num estágio próprio.

## 6. Veredito

| Marco | Resultado |
| :--- | :--- |
| M3 (80 MHz) | Não fecha. Pior folga do núcleo -1,786 ns e da busca -0,762 ns em 83,333 MHz; SDRAM e `DRAM_CLK` também negativos |
| M4 (100 MHz) | Não fecha. O laço do núcleo tem perto de 12,3 ns de dados contra os 10 ns do período |

O último marco com o núcleo fechado continua sendo o M1 de [MARCOS.md](MARCOS.md) (50 MHz com a fase do núcleo em 8250 ps); o que impede o M1 de fechar é só o controlador da SDRAM.

## 7. Leitura registrada do Zihpm (passo F.P6c)

O passo F.P6c (`Core/docs/pt-br/timing/P6_LEITURA_REGISTRADA_DO_ZIHPM.md`) tira o multiplexador dos 29 contadores do laço leitura-escrita de CSR. A tabela dá a semente 1 a 100 MHz e as cinco sementes a 83,333 MHz (fase 6000 ps); a lista de caminhos por número de níveis está em [CAMINHOS-POR-NIVEIS.md](CAMINHOS-POR-NIVEIS.md).

| Medida | Antes de F.P6c | Depois |
| :--- | ---: | ---: |
| 100 MHz, fase 5000, núcleo para núcleo | -2,687 ns | -2,053 ns |
| 100 MHz, fase 6000, núcleo para núcleo | -2,549 ns | -1,393 ns (11,2 ns de dados) |
| Níveis de lógica do banco do Zihpm (máximo) | 10 | 8 |

| Domínio a 83,333 MHz | S1 | S2 | S3 | S4 | S5 | Pior |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| Núcleo (`c3`) | -0,549 | -1,837 | -0,275 | -0,439 | -0,825 | -1,837 |
| Busca (`c2`) | 0,118 | -0,087 | -0,308 | -0,333 | -0,035 | -0,333 |
| Controlador da SDRAM | -0,745 | -0,255 | -0,204 | -0,173 | -0,713 | -0,745 |
| `DRAM_CLK` | 0,429 | -0,127 | -0,047 | -0,078 | 0,394 | -0,127 |
| Menor hold, modelo rápido | 0,009 | 0,092 | 0,089 | 0,056 | 0,118 | 0,009 |
| ALMs | 9 067 | 9 062 | 9 062 | 9 005 | 9 045 | 9 067 |

O M3 continua aberto: o pior caminho do núcleo a 83,333 MHz passa a ser o da tag da cache de instruções até o PC (4,0 a 4,2 ns de dados mais 2,4 ns de defasagem do relógio da RAM), seguido pelo contador do Zihpm somando a si mesmo e pela confirmação da instrução (`r_we_ok`) que chega aos contadores, ao PC e à classificação do endereço. O custo do passo é um ciclo por instrução CSR que acessa o banco do Zihpm.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../../LICENSE).
