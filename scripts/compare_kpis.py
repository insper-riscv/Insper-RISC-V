#!/usr/bin/env python3
r"""Compara os KPIs da versão base (2025.2) com os da atual (2026.1).

Uso:
  # 1. Gerar o JSON da versão base (uma vez, e commitar):
  python3 scripts/kpi_report.py \
    --quartus-dir  <repo_base>/TopLevel/platforms/internal-mem/quartus \
    --cocotb-log   /dev/null \
    --testbench-dirs <repo_base>/tests \
    --output       docs/baseline_2025_2.json

  # 2. Gerar o JSON da versão atual:
  python3 scripts/kpi_report.py --output docs/current_2026_1.json

  # 3. Comparar:
  python3 scripts/compare_kpis.py \
    --baseline docs/baseline_2025_2.json \
    --current  docs/current_2026_1.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Os relatórios são JSON: um objeto cujos valores têm tipos variados.
type Json = dict[str, Any]

# Largura de cada coluna de valor da tabela impressa.
COL_W = 22
# Largura da coluna de rótulos da tabela impressa.
LABEL_W = 28


def load(path: str) -> Json:
    """Lê um relatório JSON ou encerra com erro se ele não existir."""
    report = Path(path)
    if not report.exists():
        print(f"ERRO: arquivo não encontrado: {report}", file=sys.stderr)
        sys.exit(1)
    return json.loads(report.read_text(encoding="utf-8"))


def fmt(val: object, fmt_str: str = "{}", na: str = "N/A") -> str:
    """Formata um valor, ou devolve o texto de ausência se for None."""
    return fmt_str.format(val) if val is not None else na


def delta_str(
    old: float | None,
    new: float | None,
    unit: str = "",
    higher_is_better: bool = True,
) -> str:
    """Devolve a variação entre dois valores com seta e marca."""
    if old is None or new is None:
        return ""
    diff = new - old
    if diff == 0:
        return "  (=)"
    arrow = "↑" if diff > 0 else "↓"
    good = (diff > 0) == higher_is_better
    sign = "+" if diff > 0 else ""
    mark = "✓" if good else "✗"
    return f"  {arrow} {sign}{diff:.2f}{unit} {mark}"


def row(label: str, base: object, current: object, change: str = "") -> None:
    """Imprime uma linha da tabela de comparação."""
    print(
        f"  {label:<{LABEL_W}} {base!s:<{COL_W}} {current!s:<{COL_W}} {change}"
    )


def _coverage_cell(kpi: Json) -> str:
    """Formata a célula de cobertura de um relatório."""
    total = kpi.get("total", 0)
    if not total:
        return "N/A"
    pct = fmt(kpi.get("coverage_pct"), "{:.1f}%")
    return f"{kpi.get('passed', '?')}/{total} ({pct})"


def _isa_cell(kpi: Json, key: str) -> str:
    """Formata a célula de instruções cobertas de uma extensão."""
    covered = len(kpi.get(f"{key}_covered", []))
    return (
        f"{covered}/{kpi.get(f'{key}_total', '?')} "
        f"({kpi.get(f'{key}_pct', '?')}%)"
    )


def _compare_clock(base: Json, current: Json) -> None:
    """Imprime a comparação do KPI 1."""
    print("\n  [KPI 1] Clock do Sistema")
    base_f = base.get("fmax_mhz")
    current_f = current.get("fmax_mhz")
    row(
        "Fmax (MHz)",
        fmt(base_f, "{:.2f} MHz"),
        fmt(current_f, "{:.2f} MHz"),
        delta_str(base_f, current_f, " MHz"),
    )


def _compare_coverage(base: Json, current: Json) -> None:
    """Imprime a comparação do KPI 2."""
    print("\n  [KPI 2] Cobertura de Testes (cocotb)")
    base_pct = base.get("coverage_pct")
    current_pct = current.get("coverage_pct")
    change = (
        delta_str(base_pct, current_pct, "%")
        if base_pct and current_pct
        else ""
    )
    row(
        "Testes passaram (%)",
        _coverage_cell(base),
        _coverage_cell(current),
        change,
    )


def _compare_instructions(base: Json, current: Json) -> None:
    """Imprime a comparação do KPI 3."""
    print("\n  [KPI 3] Instruções Suportadas")
    row(
        "Total (instrução/suportadas)",
        base.get("ratio", "N/A"),
        current.get("ratio", "N/A"),
        delta_str(
            base.get("total_covered"), current.get("total_covered"), " instr"
        ),
    )
    row("RV32I (%)", _isa_cell(base, "rv32i"), _isa_cell(current, "rv32i"))
    row(
        "RV32M (%)",
        _isa_cell(base, "rv32m"),
        _isa_cell(current, "rv32m"),
        delta_str(base.get("rv32m_pct"), current.get("rv32m_pct"), "%"),
    )


def main() -> None:
    """Lê os dois relatórios e imprime a tabela de comparação."""
    parser = argparse.ArgumentParser(
        description="Compara KPIs entre duas versões do processador"
    )
    parser.add_argument(
        "--baseline", required=True, help="JSON da versão base (2025.2)"
    )
    parser.add_argument(
        "--current", required=True, help="JSON da versão atual (2026.1)"
    )
    args = parser.parse_args()

    base = load(args.baseline)
    curr = load(args.current)
    sep = "=" * 70

    print(f"\n{sep}")
    print(f"  COMPARAÇÃO DE KPIs, {base['project']}")
    print(f"  Baseline : {base['generated_at']}  ({args.baseline})")
    print(f"  Atual    : {curr['generated_at']}  ({args.current})")
    print(sep)
    row("Métrica", "2025.2 (base)", "2026.1 (atual)", "Variação")
    print("─" * 70)

    base_kpis = base["kpis"]
    curr_kpis = curr["kpis"]
    _compare_clock(
        base_kpis.get("kpi1_clock_mhz", {}),
        curr_kpis.get("kpi1_clock_mhz", {}),
    )
    _compare_coverage(
        base_kpis.get("kpi2_test_coverage", {}),
        curr_kpis.get("kpi2_test_coverage", {}),
    )
    _compare_instructions(
        base_kpis.get("kpi3_instructions", {}),
        curr_kpis.get("kpi3_instructions", {}),
    )
    print(f"\n{sep}\n")


if __name__ == "__main__":
    main()
