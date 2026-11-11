# KPIs e Embench — medição e evidências

Branch local: `kpi-benchmarks`. O runner usa o SDK revisado, na plataforma
`internal-mem`. Não programa a FPGA automaticamente e não modifica o upstream.

Na raiz deste checkout, dentro do ambiente de desenvolvimento:

```bash
# Primeira vez: baixa e verifica a release fixada do Embench 1.0.
scripts/rv32-bench fetch .sdk/vendor/embench

# Teste curto da instrumentação, sem baixar Embench:
scripts/rv32-bench run --benchmarks smoke --backend simulate \
  --cycles 200000 --output build/kpis/smoke-01

# Compila os três workloads iniciais e registra tamanhos de seções:
scripts/rv32-bench run --backend build --output build/kpis/build-01

# Mede um workload real em simulação (pode demorar):
scripts/rv32-bench run --benchmarks edn --backend simulate \
  --output build/kpis/edn-01

# Hardware previamente programado com o SDK correspondente:
scripts/rv32-bench run --backend fpga-fast --repeats 5 \
  --cpu-hz 50000000 --output build/kpis/fpga-01
```

O valor de `--cpu-hz` é um exemplo: informe o clock REAL da configuração
usada. Sem essa opção, os ciclos e CPI são registrados, mas o tempo fica nulo.
O runner exige diretório de saída vazio para preservar experimentos anteriores.

Saídas: `results.json`, `results.csv`, logs por execução e projetos reproduzíveis.
Metadados incluem commit e alterações rastreadas do SDK, submódulos, GCC, hashes
fontes/harness/runner/ELF, backend, aquecimento, escala e tamanho das seções.
As linhas `built` significam somente compilação; `passed` exige execução com
verificação do próprio algoritmo. Falha, ausência/duplicidade da medição e timeout
não produzem resultados válidos. O timeout termina também os processos filhos.

## Escopo e interpretação

- O runner aceita os 19 workloads da release fixada; os três padrões são: `crc32`, `edn`, `matmult-int`, da release Embench 1.0,
  commit `0466a18e4f6b47e19598d7c6ba72916d54b68f65`.
- Os algoritmos permanecem intactos. Wrappers definem `CPU_MHZ=1` (escala de
  trabalho, independente do clock real) e mantêm warnings conhecidos como
  warnings nos logs. GCC usa a política atual do SDK: RV32IM/ILP32, `-Os`, C23.
- Há uma chamada `warm_caches(1)` antes da região medida; na plataforma sem
  caches isso não cria uma cache. A inicialização e a verificação ficam fora.
- `mcycle` e `minstret` são lidos com high/low/high, protegendo rollover em RV32.
  Os snapshots não são simultâneos: o custo da instrumentação e do fence está
  incluído nos resultados brutos. O teste `smoke` valida o caminho de medição;
  NÃO representa o desempenho do processador e NÃO é um benchmark de CPI ideal.
- Ainda NÃO há score oficial Embench, agregação da suíte completa, subtração de
  overhead, perfil HPM, comparação estatística, consumo ou certificação de Fmax.
  Não apresentar estes resultados como Embench/MHz ou score oficial.
- O código do Embench é baixado separadamente, com seus avisos/licenças originais;
  os workloads selecionados declaram GPL-3.0-or-later. O harness novo é Apache-2.0;
  isso não altera as licenças das fontes upstream nem do executável combinado.

## Timing e relatório

`scripts/kpi_report.py` agora grava `schema_version=2`:
`kpi1_configured_clock.configured_mhz` vem do PLL;
`kpi1_clock_mhz.fmax_mhz` vem SOMENTE do relatório STA. Relatório STA ausente
significa Fmax desconhecida, mesmo que o PLL esteja configurado. O parser ainda
resume o menor domínio não-JTAG: consulte `all_clocks` e `clock_name`, pois isso
não identifica automaticamente o domínio da CPU e não comprova fechamento de
setup/hold/CDC. Não compare automaticamente a frequência do schema antigo com
Fmax do schema novo.

Próximas etapas: executar/validar toda a suíte, medir overhead, permitir política
explícita de otimização, extrair timing por domínio/corner/semente e recursos
pós-fit, e comparar duas revisões com workloads/flags/memória equivalentes.

No schema 2, `kpi1_resources.block_memory_bits` registra bits de memória do
relatório fitter. O campo antigo `m9k_blocks` foi removido, pois contava bits,
não blocos. O resumo por clock agora conserva o pior valor encontrado para
cada nome hierárquico, inclusive quando há múltiplos corners.

Com relatórios Quartus existentes, é possível extrair o JSON com:

```bash
python3 scripts/kpi_report.py \
  --quartus-dir src/simulation/internal-mem/quartus \
  --output build/kpis/quartus.json
```

Esse script legado também avalia testes/conformidade: sem os respectivos dados,
pode sair com código 1 mesmo tendo extraído timing/recursos. Verifique os campos
individualmente; ausência de relatório não é zero utilização nem timing aprovado.
Ele não executa uma nova compilação do Quartus.

Em máquinas com várias placas, fixe explicitamente o cabo:
`--jtag-hardware "USB-Blaster [1-2]"`. A seleção entra nos projetos gerados e nos
metadados; o SDK também exige que o chip desse cabo corresponda ao esperado.

As primeiras medições reais (15 execuções verificadas, três workloads) estão em
[resultados físicos de 2026-11-10](results/2026-11-10/README.md).

## Evidências de evolução

O [dossiê auditável](results/evidence-2026-11-10/README.md) contém comparação
RTL antes/depois com binários idênticos, controles negativos, regressões, logs
e hashes. Inclui uma [seção em inglês para o relatório](results/evidence-2026-11-10/report-section.md).
Os ganhos são específicos de reuso aritmético; há uma regressão no kernel
load-use. Não há demonstração de aceleração geral das aplicações.

Foram compilados 18 dos 19 workloads; `cubic` excedeu a FLASH disponível.
Quatro algoritmos adicionais passaram por execução funcional curta em RTL.
A rodada física ampliada foi concluída: **54/54 execuções aprovadas, 18 workloads
com três repetições cada**, com contadores idênticos por workload. Consulte os
[resultados e condições](results/evidence-2026-11-10/physical-expanded/README.md).
O procedimento está em `evidence/run_extended.sh`; antes de executá-lo, confirme
a identidade do cabo/chip e programe o bitstream correspondente a este SDK.
As 15 medições físicas anteriores usam o harness anterior e ficam separadas.
