# DE10-Nano e DE0-Nano-SoC

## 1. Referência

As duas placas Terasic têm um Cyclone V SoC, com o processador ARM (HPS) ao lado do FPGA. O pacote de cada uma está em `boards/de10-nano/` e `boards/de0-nano-soc/`. O formato do pacote está em [formato.md](formato.md) e a tabela das placas em [placas.md](placas.md).

| Placa | Dispositivo no Quartus | IDCODE do FPGA | ALMs | Blocos M10K |
| :--- | :--- | :--- | ---: | ---: |
| `de10-nano` | `5CSEBA6U23I7` | `02D020DD` | 41910 | 557 |
| `de0-nano-soc` | `5CSEMA4U23C6` | `02D010DD` | 15094 | 246 |

O nome do dispositivo no Quartus não leva o sufixo `N` da peça comercial (`5CSEMA4U23C6N`): o Quartus 25.1 recusa esse nome com os erros 125095 e 281000. Os IDCODEs vêm do banco de dispositivos do Quartus (`pgm_parts.txt`) e não de uma leitura das placas.

## 2. Família no Quartus

A família `cyclone-v-soc` usa o nome `Cyclone V` no Quartus, porque o Lite não lista `Cyclone V SoC`. As duas placas sintetizam com `quartus_map` sem o HPS: o fabric é programado por JTAG e o ARM fica fora do projeto.

## 3. Cadeia JTAG com o HPS

O USB-Blaster II embutido na placa expõe duas partes na mesma cadeia.

| Posição | Nome no `jtagconfig` | IDCODE |
| :---: | :--- | :--- |
| 1 | `SOCVHPS` (DAP do ARM) | `4BA00477` |
| 2 | `5CSE(BA6\|MA6)/..` na DE10-Nano e `5CSE(BA4\|MA4)/..` na DE0-Nano-SoC | `02D020DD` e `02D010DD` |

O Tools compara a cadeia lida com `jtag.chain` do pacote pela regra V17, e as duas placas se distinguem só pelo IDCODE do FPGA, pois dividem cabo, HPS e IDs USB. A identidade do dispositivo do FPGA usa a posição `@2` (`@2: 5CSE(BA6|MA6)/.. (0x02D020DD)`), que é o argumento de `quartus_pgm` e de `quartus_stp`.

O Quartus pode falhar com o erro 209025 (silicon ID) ao programar. A correção relatada em fóruns é tirar o HPS da cadeia no programador, e o `riscv-tools board doctor` só sugere isso, nunca altera a cadeia.

## 4. Cabo USB-Blaster II

| ID USB | Estado do cabo |
| :--- | :--- |
| `09fb:6010` | Antes da carga do firmware pelo `jtagd` |
| `09fb:6810` | Depois da carga; o `jtagconfig` lista o cabo como `DE-SoC [USB-1]` |

O nome do cabo não leva o sufixo `[bus-porta]`, e por isso a porta USB não vem do nome. O `board doctor` avisa do firmware ainda não carregado e do ID `6810` sem cabo `DE-SoC` na lista. O `board scan` mostra a placa que a USB revela sem cadeia legível, por exemplo com o cabo em `6010`.

## 5. Console

O console do SoC é a JTAG UART (`console.default: jtag`) pelo nó de Virtual JTAG do fabric. O Virtual JTAG fica atrás do FPGA na cadeia, e o Tools o alcança pela posição `@2`, sem tratar o HPS. A UART USB da placa pertence ao HPS e não chega ao fabric; `ARDUINO_IO[0]` (RXD) e `ARDUINO_IO[1]` (TXD) servem a um adaptador externo se o backend `pinos` for escolhido.

## 6. Memória e a DDR3 do HPS

### 6.1. A decisão

Nenhuma das duas placas tem memória ligada ao fabric. O pacote declara só memória emulada em M10K (decisão DM4): cerca de 696 KB na DE10-Nano e 307 KB na DE0-Nano-SoC, menos caches e banco de registradores. O perfil do ACT4 com 1 MB de RAM não cabe nesses blocos.

### 6.2. Caminhos para a DDR3 do HPS

A DDR3 de 1 GB pertence ao controlador rígido do HPS. O fabric só a usa depois que o preloader (U-Boot SPL) calibrou o controlador.

| Caminho | O que é | Efeito |
| :--- | :--- | :--- |
| Porta FPGA-to-SDRAM | Porta Avalon-MM ou AXI do controlador de DDR3, direto do fabric | Menor latência e maior vazão; é o caminho do exemplo da Terasic (`terasic_hps_ddr3`) |
| Ponte FPGA-to-HPS (F2H) | Escravo AXI do HPS com mestre no fabric, pelo L3 | Alcança toda a memória do HPS, com a latência do L3 e o filtro do firewall |

As duas exigem o componente HPS no Platform Designer, a configuração dos pinos da DDR3 e um preloader gerado a partir do handoff do projeto, gravado no cartão microSD. Sem o preloader o controlador não calibra e a porta não responde.

### 6.3. Custo de um backend

| Item | Consequência |
| :--- | :--- |
| Componente HPS e Qsys | Entidade nova de fornecedor em `altera/` do Memory, fora do `soc` |
| Preloader no microSD | O fluxo de bring-up passa a exigir um cartão e um software ARM |
| Latência variável | O backend precisa do contrato K2 com `latency` variável e burst, como o da SDRAM |
| Esquema | Uma chave nova em `memories` e uma regra do validador para o preloader |
| Teste | Só com a placa viva e o cabo USB-Blaster II funcionando |

### 6.4. Conclusão do estudo

O backend só se justifica se a DE10-Nano precisar rodar o perfil de 1 MB. A recomendação é manter a decisão DM4 (memória emulada) e retomar o estudo se o laboratório quiser esse perfil nessa placa. Os valores deste capítulo sobre as pontes e o preloader vêm do manual da placa (seções 5.4 e 7.3 da ficha) e do conhecimento da arquitetura do HPS, e precisam ser conferidos no manual de referência do Cyclone V HPS, que não está em `Docs/`.

## 7. Níveis de suporte

| Nível | Critério | O que vale para as duas placas |
| :--- | :--- | :--- |
| N0 | `board generate` e `quartus_map` sem erro | O perfil `rv32i` com RAM emulada sintetiza nas duas (3279 registradores e 295 424 bits de memória) |
| N1 | Ajuste e análise de tempo | `quartus_fit` e `quartus_sta` sobre o mesmo projeto |
| N2 | Placa viva | Exige o cabo USB-Blaster II enumerando |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
