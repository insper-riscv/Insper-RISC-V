# Validação local e física — 2026-11-10

Branch `kpi-benchmarks`, baseada no SDK revisado `3cc70ad2`.
Nenhum commit, merge ou push desta etapa.

Passaram:
- 42 testes de regressão: medição, timeout com limpeza dos filhos,
  preservação de resultados, seleção do cabo, PLL/Fmax, clocks/corners e RAM.
- Ruff lint/format e análise de dependências do SDK.
- Download e verificação da release fixada pelo subcomando `fetch`.
- Compilação RV32IM de `crc32`, `edn` e `matmult-int` sem alterar algoritmos.
- Duas execuções completas do teste de instrumentação `smoke` em GHDL.
- Teste curto dos contadores na Cyclone V, com os mesmos 48 ciclos / 16
  instruções da simulação (medida de instrumentação, não score de CPU).
- Cinco execuções completas de CADA workload na Cyclone V USB-Blaster [1-2]:
  15/15 aprovações pelo verificador original, 15/15 medições válidas e sem stderr.
- Hash do runner no JSON igual ao arquivo local; ELF constante por workload.
- SOF programado igual, byte a byte, ao SOF da compilação Quartus cujos relatórios
  de timing/recursos foram coletados (comparação SHA-256).

Resultados e condições: [medições físicas](results/2026-11-10/README.md).
Os cinco resultados por workload foram idênticos nesta configuração sem caches.
Não há score oficial agregado da suíte Embench ou caracterização de overhead.

A tentativa anterior de `edn` em GHDL excedeu 600 segundos e permaneceu marcada
como falha, sem score inventado. Seu limite de 20 milhões de ciclos também era
inferior aos 26.124.182 ciclos medidos na região do algoritmo na FPGA. O runner
atual permite configurar os limites e encerra todo o grupo de processos no timeout;
um teste intencional de 10 segundos confirmou a limpeza.

A DE2-115 e as instalações estáveis foram preservadas. A cópia de testes está
separada no workstation, em ~/dev/riscv/kpi-benchmarks-20261110/.

## Ampliação das evidências

O [dossiê de evolução](results/evidence-2026-11-10/README.md) preserva:

- 36 execuções comparativas em RTL: seis kernels, duas versões, três repetições.
- 12 execuções comparativas adicionais de capacidades e controles.
- 14 execuções atuais de alinhamento, com respostas verificadas independentemente.
- 19 testes existentes do Core aprovados, incluindo reuso, Zicclsm e FENCE.I.
- 18/19 workloads Embench compilados e quatro novos algoritmos verificados em
  execuções funcionais curtas; a falha por tamanho de `cubic` e o timeout
  inicial de Huffman foram preservados.
- Auditoria que rejeita respostas erradas e binários diferentes, incluindo
  testes dessas rejeições. Empates e regressões permanecem nos resultados.

A ampliação física também foi concluída: 54/54 execuções aprovadas, 18 workloads
com três repetições cada e contadores idênticos por workload. O auditor conferiu
logs, registros, runner e ELFs; três adulterações intencionais foram rejeitadas.
As 15 medições físicas anteriores permanecem em dataset separado.
Não foi medido ganho geral de aplicações em relação à versão histórica.
