# Rodada física ampliada — 2026-11-10

**54/54 execuções aprovadas: 18 workloads, três repetições cada.** Todos os
programas passaram pelo verificador original e produziram exatamente um registro
válido, sem stderr. Para cada workload, ciclos e instruções foram idênticos nas
três repetições. Isso mostra repetibilidade nesta configuração determinística;
não é uma estimativa de variabilidade entre placas ou frequências.

Cyclone V 5CEBA4F23C7, cabo `USB-Blaster [1-2]`, IDCODE `02B050DD`.
O SOF programado tem SHA-256
`a007bc325b1d99410a2454f50b41f2cb166c0e68d3a897548a84e6d1151c8aed`,
idêntico ao usado na rodada anterior e nos relatórios Quartus preservados em
`../physical-previous/quartus/`. O clock de 50 MHz é o nominal configurado no PLL;
não houve medição externa de frequência. O Core não foi alterado.

Embench 1.0 fixado em `0466a18e4f6b47e19598d7c6ba72916d54b68f65`,
compilador/flags registrados no JSON e logs de cada projeto. `CPU_MHZ=1` define
somente a escala de trabalho. Uma chamada de aquecimento antecede a região medida.
As leituras dos contadores e fence têm overhead não subtraído; verificação e
formatação/saída ficam fora da região. Não há caches nesta configuração.
`cubic` não foi executado: excedeu a FLASH, com falha de compilação preservada em
`../transcripts/`. Não há score oficial agregado da suíte.

| Workload | Ciclos (mediana) | Instruções | CPI | Tempo a 50 MHz nominal (ms) |
|---|---:|---:|---:|---:|
| aha-mont64 | 6541779 | 4583676 | 1.4272 | 130.836 |
| crc32 | 10973051 | 3834037 | 2.8620 | 219.461 |
| edn | 26124182 | 4194143 | 6.2287 | 522.484 |
| huffbench | 4666718 | 2736985 | 1.7051 | 93.334 |
| matmult-int | 18167362 | 3962066 | 4.5853 | 363.347 |
| minver | 10374693 | 5375217 | 1.9301 | 207.494 |
| nbody | 7774417 | 3026861 | 2.5685 | 155.488 |
| nettle-aes | 5393074 | 4588234 | 1.1754 | 107.861 |
| nettle-sha256 | 4803274 | 4285488 | 1.1208 | 96.065 |
| nsichneu | 3853093 | 2001633 | 1.9250 | 77.062 |
| picojpeg | 9259093 | 4236835 | 2.1854 | 185.182 |
| qrduino | 7153293 | 3014667 | 2.3728 | 143.066 |
| sglib-combined | 4643736 | 2657173 | 1.7476 | 92.875 |
| slre | 4460461 | 2904037 | 1.5360 | 89.209 |
| st | 9855867 | 3825365 | 2.5765 | 197.117 |
| statemate | 2698606 | 1606586 | 1.6797 | 53.972 |
| ud | 10949108 | 3570896 | 3.0662 | 218.982 |
| wikisort | 3333101 | 1490578 | 2.2361 | 66.662 |

CRC-32, EDN e matmult-int reproduziram exatamente os ciclos e instruções das cinco
repetições anteriores, apesar do novo formatador compacto fora da região medida.
Os datasets permanecem separados porque os hashes de harness/ELF mudaram.
Não interpretar essa coincidência como regra universal sobre layouts de código.

## Auditoria e reprodução

`results.json`/CSV e os 54 logs são os dados brutos. `elf/` preserva os binários;
`project-protocol/` preserva manifestos, wrappers, configuração e comandos de
compilação. Os caminhos absolutos são os do ambiente de execução, não caminhos
portáveis prontos para executar em outra máquina. A reconstrução usa o runner
arquivado e a release upstream fixada; não pressupõe binários idênticos sob outro
caminho, compilador ou versão de SDK. Fontes upstream e licenças:
https://github.com/embench/embench-iot/tree/0466a18e4f6b47e19598d7c6ba72916d54b68f65

A partir da raiz do dossiê, restaure os scripts históricos em uma pasta nova:

```bash
python3 verify.py --restore /tmp/rv32-evidence-restored
cd /tmp/rv32-evidence-restored/physical-expanded
python3 protocol/audit_physical.py .
```

A auditoria confirma 54 registros de 18 workloads, três repetições por programa,
verificação aprovada, concordância log/JSON, CPI/tempo, hash do runner e hash dos
ELFs. Os hashes de fontes dos 54 registros também foram recalculados contra o
checkout upstream local fixado e o harness testado antes do empacotamento.
Tentativas de inserir uma falha, adulterar contadores e corromper um ELF foram
rejeitadas (`audit-validation.txt`). O teste físico inicial dos contadores passou
com 48 ciclos / 16 instruções, iguais à simulação.

O procedimento completo executado está em `run-expanded-physical.sh` e o runner
em `protocol/run_extended.sh`; requer o SDK/ambiente registrado e uma placa
exclusivamente disponível no cabo confirmado. Não seleciona a DE2-115.

Estes resultados caracterizam a versão atual. Não comparam aplicações na FPGA
histórica e não ampliam os ganhos específicos RTL para um ganho geral da CPU.
