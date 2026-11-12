# Guias

Os guias dizem como fazer uma tarefa de ponta a ponta com este repositório.

| Guia | Para que serve |
| :--- | :--- |
| [placa.md](placa.md) | Compilar o projeto do Quartus, programar uma placa e rodar programas nela, com a regra de compilar e programar no mesmo shell |
| [adicionar-placa.md](adicionar-placa.md) | Acrescentar uma placa nova: ficha, pacote de placa, família e chip, plataforma, validador, calibração, níveis N0 a N4 e identificação pelo JTAG |
| [simulacao.md](simulacao.md) | Simular o topo de hardware com as memórias reais do Quartus no GHDL |
| [kpis.md](kpis.md) | Gerar e comparar os relatórios de KPI (clock, cobertura de testes e instruções suportadas) |
| [nova-arquitetura.md](nova-arquitetura.md) | Criar uma plataforma nova a partir do modelo `src/simulation/template/`, do mapa de memória à certificação e à placa |

As plataformas em si, com mapa de memória, boot e runtime, estão em [../platform/](../platform/README.md). Os defeitos já diagnosticados estão em [../bugs/](../bugs).
