# Primeiras medições físicas — 2026-11-10

Executadas na Cyclone V 5CEBA4F23C7, USB-Blaster [1-2], clock nominal de
50 MHz conforme PLL/SDC do bitstream usado. As 15 execuções terminaram com
verificação do algoritmo aprovada e sem stderr. Cinco repetições por workload.
As contagens foram idênticas nas cinco repetições de cada programa.

| Workload | Ciclos (mediana) | Instruções (mediana) | CPI bruto | Tempo calculado (ms) | Validação |
|---|---:|---:|---:|---:|---:|
| crc32 | 10,973,051 | 3,834,037 | 2.8620 | 219.461 | 5/5 |
| edn | 26,124,182 | 4,194,143 | 6.2287 | 522.484 | 5/5 |
| matmult-int | 18,167,362 | 3,962,066 | 4.5853 | 363.347 | 5/5 |

O tempo é ciclos / 50.000.000; não é cronometragem pelo host. Não inclui
compilação, transferência JTAG, inicialização, aquecimento ou impressão.
O overhead dos snapshots/fence NÃO foi descontado; snapshots não são simultâneos.

Configuração: Embench 1.0 (`0466a18e4f6b47e19598d7c6ba72916d54b68f65`),
workloads sem alterações, escala CPU_MHZ=1 (independente do clock nominal),
um aquecimento, GCC 16.1.0, RV32IM/ILP32, -Os, C23, plataforma internal-mem,
sem caches. Não são um score oficial Embench nem uma comparação entre CPUs.
A dimensão inteira de cada algoritmo e seu verificador original foram executados.

## Identidade e relatórios do hardware

SOF SHA-256: `a007bc325b1d99410a2454f50b41f2cb166c0e68d3a897548a84e6d1151c8aed`.
O checksum do SOF programado coincide com o da compilação cujos relatórios foram
coletados. Quartus Prime 25.1std.0 Build 1129, Lite Edition.

- ALMs: 6.263 / 18.480.
- Registradores: 6.001.
- Memória: 2.392.064 / 3.153.920 bits; 288 / 308 blocos RAM.
- DSPs: 0 / 66; PLLs: 1 / 4.
- Fmax reportada no domínio do núcleo, slow 85 °C: 66,56 MHz.
  Esse número considera caminhos de mesmo clock, não é o clock usado no benchmark.
- Setup do núcleo nesse corner a 50 MHz: +1,507 ns.

Há I/Os sem restrições temporais no relatório (incluindo JTAG, reset e LEDs).
Portanto não apresentar o resumo como certificação completa de timing/CDC ou
máxima frequência de operação garantida do SoC.

## Arquivos e reprodução

`results.csv` contém as 15 linhas; `summary.json` preserva medianas, intervalos,
hashes e seções dos ELFs. Os arquivos completos de resultados, logs e relatórios
Quartus estão localmente em `publication-review/kpi-hardware-results/`.
O pacote completo também permanece em
`~/dev/riscv/kpi-benchmarks-20261110/` no workstation, separado do SDK instalado.

```bash
scripts/rv32-bench run --backend fpga-fast \
  --jtag-hardware "USB-Blaster [1-2]" --repeats 5 \
  --cpu-hz 50000000 --timeout 180 --output /caminho/novo-experimento
```

Somente a Cyclone V foi programada. A DE2-115 não foi usada.
Sem commits, merges ou pushes nesta etapa de KPIs.

## Relação com o timeout em simulação

O `edn` mediu 26.124.182 ciclos na região de interesse; a tentativa anterior de
simulação tinha limite de 20 milhões de ciclos totais, além do timeout de parede
de 600 s. Esse orçamento de ciclos já era insuficiente para o workload completo,
mesmo sem contar inicialização/aquecimento. O default do runner é 100 milhões;
para repetir esse workload no GHDL será necessário também ampliar o tempo real.
A medição física elimina a dúvida sobre execução e verificação do algoritmo.
