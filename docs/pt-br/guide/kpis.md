# Scripts de KPI

Os dois scripts rodam da raiz do repositório.

## 1. Como usar

```bash
# 1. Gerar os KPIs da versão atual
python3 scripts/kpi_report.py --output docs/current_2026_1.json

# 2. Comparar com o baseline do grupo anterior
python3 scripts/compare_kpis.py \
  --baseline docs/baseline_2025_2.json \
  --current  docs/current_2026_1.json
```

## 2. O que cada KPI mede

| KPI | Medida |
| :--- | :--- |
| 1 | Frequência do clock da CPU |
| 2 | Cobertura de testes cocotb, em porcentagem de testes passando |
| 3 | Instruções suportadas de RV32I e RV32M |

## 3. Arquivos

| Arquivo | Papel |
| :--- | :--- |
| `docs/baseline_2025_2.json` | Foto do grupo anterior, que não se edita |
| `docs/current_2026_1.json` | Gerado pelo `kpi_report.py` |
| `scripts/kpi_pipeline.json` | Descrição do pipeline de KPIs |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
