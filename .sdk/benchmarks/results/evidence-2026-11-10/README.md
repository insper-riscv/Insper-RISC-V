# Evidências de evolução do processador — 2026-11-10

## Conclusão sustentada pelos testes

Há **ganhos específicos de ciclos e de correção**, não uma demonstração de que
qualquer programa ficou mais rápido. Os microbenchmarks abaixo foram executados
nos dois RTLs: não são estimativas obtidas contando instruções no arquivo fonte.
São medições em GHDL; não são uma comparação física entre duas versões da FPGA.

| Microbenchmark, mesma sequência binária | Antes | Atual | Redução de ciclos | Speedup a mesmo clock |
|---|---:|---:|---:|---:|
| Cadeia de 128 ADDI dependentes | 131 | 131 | 0% | 1,0000× |
| MULHU + MUL, mesmos operandos, com espaçamento | 100 | 68 | 32,00% | 1,4706× |
| DIVU + REMU, mesmos operandos, com espaçamento | 104 | 70 | 32,69% | 1,4857× |
| MULHU + MUL, operandos diferentes, mesmo espaçamento | 100 | 100 | 0% | 1,0000× |
| DIVU + REMU, operandos diferentes, mesmo espaçamento | 104 | 104 | 0% | 1,0000× |
| Laço de 64 load-use/store/branch | 513 | 577 | **−12,48%** | **0,8891×** |

Cada linha acima tem três execuções independentes por versão, com nova elaboração
do RTL. As contagens se repetiram exatamente. Todos os resultados dessas linhas
conferiram com valores calculados independentemente em Python. A regressão de
load-use foi mantida na tabela e não entra como ganho.

Os pares com espaçamento incluem **24 NOPs**. Isso é deliberado: permite comparar
casos nos quais ambas as versões calculam a resposta correta. Não extrapolar
1,47× ou 1,49× para aplicações inteiras. Nos controles com operandos diferentes,
o ganho desaparece; isso, junto aos testes unitários do bloco de fusão, sustenta
a interpretação de que a economia vem do reaproveitamento do resultado M.
Não se calculou média geral desses kernels escolhidos para diagnóstico.

## Versões e controle experimental

- Base: `2115e4c8f49f75f9ef045bb59cf375c36f02b3ca`, de 26/05/2026. É o último
  commit no primeiro pai de main encontrado antes de 01/07/2026 no histórico
  disponível; não é uma declaração de que existe uma tag formal de entrega.
- Atual: árvore RTL vinculada ao SDK `3cc70ad2`, com Core
  `eab41af8fb6464ca22819ac06bdb0a3c63f9c313`. As alterações desta etapa são
  instrumentação/documentação; o RTL não foi modificado.
- O snapshot preliminar dos KPIs de 19/05 também foi investigado. Até 26/05,
  a diferença no arquivo do pipeline é apenas um comentário. Mesmo assim,
  a tabela final foi reexecutada usando a revisão de 26/05, sem inferir equivalência.
- Cada fonte VHDL da base foi confrontada byte a byte com `git show COMMIT:PATH`.
  Os manifestos registram hashes das fontes antigas e atuais, do monitor e do driver.
- Cada kernel usa os **mesmos bytes de instrução** nas duas versões. Endereços de
  carga: PC inicial 0 na base, FLASH 0x1000 na atual, com salto mínimo de boot.
  O código usa branches relativos e endereços de dados explícitos; os hashes
  das instruções, os checksums esperados e os ciclos estão nos arquivos brutos.
- Os dois tops originais usam clock de três fases, a mesma base virtual de 10 ns,
  ROM síncrona e leitura de RAM síncrona. O monitor conta bordas de clock do núcleo,
  entre stores nos marcadores de início e fim; não usa CSRs inexistentes na base.
- As capacidades dos modelos de memória são diferentes. A base tem RAM simulada
  de 512 palavras com alias nos bits baixos; a atual usa o mapa maior atual.
  Estes kernels tocam somente os marcadores 0x8100–0x8108 e dados 0x8200–0x8207,
  que não colidem na base. Isto controla o pequeno conjunto de trabalho, não
  reproduz diferenças de capacidade, contenção ou caches de aplicações completas.
- Boot, preparação dos dados, compilação e tempo do computador ficam fora da
  janela. A contagem inclui o protocolo de término; o controle ADDI verifica
  128 operações mais três ciclos do término em ambas as versões.

`comparisons/summary.json` e `comparison.csv` foram gerados por auditor automático
que rejeita fontes/protocolos diferentes entre repetições, binários distintos,
respostas erradas, variantes ausentes e contagens inválidas. Ele preserva empates
e regressões. Os testes do auditor incluem tentativa de produzir um ganho com
checksum errado e comparação de programas diferentes: ambas são rejeitadas.

## Evidências de correção e custo do Zicclsm

A medição atual cobre **14 kernels** e confere os bytes lidos/escritos com um
modelo little-endian independente. Os valores são intervalos entre marcadores,
não a latência isolada de uma instrução.

| Operação atual | Offset | Ciclos | Resultado |
|---|---|---:|---|
| LW | 0 | 6 | correto |
| LW | 1, 2 ou 3 | 7 | correto |
| LHU | 0, 1 ou 2 | 6 | correto |
| LHU | 3 | 7 | correto |
| SW, seguido da conferência de duas palavras | 0 | 9 | correto |
| SW, mesma conferência | 1 ou 3 | 10 | correto |
| SH, mesma conferência | 0 ou 1 | 9 | correto |
| SH, mesma conferência | 3 | 10 | correto |

Isso sustenta o custo de **um ciclo adicional ao cruzar a palavra**, nos cenários
medidos. Não significa que qualquer memória externa ou tamanho tenha esse custo.
No contraste histórico, `LW` desalinhado entre palavras devolveu 0x01020304 na
base e o valor esperado 0x08010203 na atual. Tratar isso como capacidade acrescentada:
a plataforma antiga não oferecia o mesmo contrato de acessos desalinhados.

Também foram repetidos casos de operações M consecutivas sem NOPs. A base não
produziu o checksum esperado; a atual produziu. Com espaçamento, ambas passaram.
Essas falhas históricas estão em `capabilities/results.json`, sem calcular speedup
a partir de uma resposta incorreta. São observações do ambiente RTL reconstruído,
não uma recertificação completa da implementação anterior.

## Regressões existentes do RTL

Foram executados **19 testes cocotb** já existentes no Core, todos aprovados:

| Grupo | Casos aprovados |
|---|---:|
| MuldivFusion | 5 |
| MisalignedUnit | 5 |
| CoreMisaligned | 3 |
| CoreMisalignedHalf | 1 |
| CoreFenceI | 3 |
| CoreFenceIDcache | 2 |

É necessário executar `make configs` no Core antes dos testes de perfis. A primeira
invocação encontrou um perfil ainda não gerado; os testes afetados foram executados
após essa preparação. Os transcripts mantêm essa ocorrência. Esses testes são
evidência de funcionamento do protocolo de FENCE.I/flush e misalignment, não uma
medição de aceleração de aplicações nem teste de caches habilitadas na FPGA.
Os **42 testes do SDK/auditoria** são contabilizados separadamente e também passaram.

## Mais programas: o que realmente foi executado

1. As medições físicas anteriores continuam válidas: **15 execuções completas**,
   três workloads (`crc32`, `edn`, `matmult-int`), cinco repetições, nominalmente
   a 50 MHz. Estão em `physical-previous/`. Não há ainda os mesmos workloads na base
   histórica; portanto não existe speedup geracional Embench medido.
2. A compilação foi ampliada para **todos os 19 workloads do Embench 1.0**.
   **18 compilaram**; `cubic` excedeu a FLASH desta configuração em 19.196 bytes.
   A falha foi preservada, sem alterar a memória ou omitir o caso.
3. Foram executados adicionalmente, em GHDL, SHA-256 (`nettle-sha256`), expressões
   regulares (`slre`), máquina de estados (`statemate`) e Huffman (`huffbench`).
   Cada um executou uma iteração interna do algoritmo original e passou pelo
   verificador original. São **testes funcionais curtos**, não a carga completa
   padronizada nem novos resultados de performance do Embench.
4. SHA-256/slre/statemate fizeram uma chamada de aquecimento. Huffman atingiu o
   timeout de 180 s com aquecimento + uma iteração; uma segunda tentativa sem
   aquecimento passou. Ambas as tentativas estão registradas.
5. A saída do harness foi compactada para reduzir código de formatação fora da
   região medida; algoritmos upstream permanecem intactos. Warnings conhecidos
   são mantidos nos logs, e `wikisort` recebe um alias pré-processado para seu
   typedef `bool` legado sob C23. O novo harness foi validado por execução RTL.
   Seus resultados futuros devem ficar em dataset separado do harness anterior.

**Atualização após reconexão ao laboratório:** a rodada física ampliada foi
concluída, com **54/54 execuções aprovadas de 18 workloads**, três repetições cada.
As contagens por workload foram idênticas. O bitstream coincide com o anterior;
os três workloads sobrepostos reproduziram exatamente ciclos e instruções.
Consulte [resultados, condições e auditoria física](physical-expanded/README.md).
O dataset usa o novo harness e permanece separado das 15 medições anteriores.
`cubic` continua excluído por exceder a memória. Não há score oficial da suíte.

## Alegações para o relatório

Pode-se afirmar: redução de 32% e 32,69% dos ciclos nos dois kernels específicos
com reuso, sob simulação controlada; resultado correto em 14 cenários de alinhamento
com um ciclo extra nos casos medidos de cruzamento; aprovação dos grupos RTL listados;
e execução física validada dos 18 workloads da rodada ampliada.

Não se pode afirmar: aceleração geral da CPU; 1,47× no Embench; ganho de frequência
em relação aos 83 MHz históricos; score oficial da suíte completa; medição de energia;
ou que a comparação histórica inteira já ocorreu em FPGA. O load-use piorou
neste teste e deve aparecer na discussão dos trade-offs.

## Reprodução e integridade

Dentro do ambiente de desenvolvimento, na raiz do SDK local:

```bash
mkdir -p /tmp/rv32-before
# Em nova pasta vazia; não altera a branch nem o RTL atual.
git archive 2115e4c8f49f75f9ef045bb59cf375c36f02b3ca | tar -x -C /tmp/rv32-before
source scripts/env.sh
uv run --project .sdk python .sdk/benchmarks/evidence/compare_rtl.py \
  /tmp/rv32-before /tmp/comparison-new-1 \
  alu-chain load-use mul-pair-separated div-rem-separated \
  mul-pair-different div-rem-different
# Repetir em pastas novas para obter comparison-new-2 e comparison-new-3.
uv run --project .sdk python -m rv32_sdk.evidence \
  /tmp/comparison-new-1/results.json /tmp/comparison-new-2/results.json \
  /tmp/comparison-new-3/results.json --output /tmp/audit-new

cd Core
make configs
python tests/python/runner.py MuldivFusion
python tests/python/runner.py MisalignedUnit
python tests/python/runner.py CoreMisaligned
python tests/python/runner.py CoreMisalignedHalf
python tests/python/runner.py CoreFenceI
python tests/python/runner.py CoreFenceIDcache
```

O driver atual inclui também os casos de alinhamento e validação de argumentos;
as versões exatas de driver/monitor usadas nas medições foram preservadas em
`protocol/` e conferidas contra os hashes dos JSONs. Os fontes ASM, bytes e ELFs
estão junto aos resultados. `SHA256SUMS.json` cobre os artefatos do dossiê.

Nenhum RTL foi editado; nenhuma branch foi mesclada; nenhum commit ou push foi
feito nesta etapa. Tudo permanece local na branch `kpi-benchmarks`.

Para auditar somente os resultados arquivados (Python padrão, sem FPGA):

```bash
python3 verify.py --restore /tmp/rv32-evidence-restored
cd /tmp/rv32-evidence-restored
python3 protocol/audit_comparisons.py comparisons/repetition-1.json \
  comparisons/repetition-2.json comparisons/repetition-3.json \
  --output /tmp/rv32-audit-reproduced
```

O arquivo de hashes detecta alterações após o empacotamento; não representa
uma assinatura externa ou certificação independente. O auditor e seus testes
estão preservados em `protocol/`.

Os fontes históricos são armazenados como `.py.snapshot`, preservando seus bytes
e hashes originais. `snapshot-paths.json` registra a mudança de nomes e o hash do
manifesto anterior. Isso os distingue do código Python ativo na análise de CI.
`verify.py --restore` primeiro verifica a integridade e depois cria uma cópia
externa com os nomes `.py` originais e um manifesto recalculado para esses nomes.
O destino deve ser novo; nenhum diretório existente é sobrescrito. Os resultados
brutos e os fontes históricos não foram alterados por esta migração.
