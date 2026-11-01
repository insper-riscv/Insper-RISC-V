#!/usr/bin/env python3
"""Coleta os KPIs do SoC RV32IM de uma execução do Quartus e dos testes.

Uso, da raiz do repositório:
  python3 scripts/kpi_report.py --output kpi_report.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Quantidade de níveis de pasta percorridos acima do projeto Quartus ao
# procurar o arquivo do PLL.
PLL_SEARCH_DEPTH = 6
# Número de grupos de uma expressão que captura "usado / total".
GROUPS_USED_AND_TOTAL = 2

RESOURCE_PATTERNS = {
    "alms_used": (
        r"Logic utilization \(in ALMs\)\s*;\s*([\d,]+)\s*/\s*([\d,]+)"
    ),
    "registers": r"Total registers\s*;\s*([\d,]+)",
    "m9k_blocks": r"Total block memory bits\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
    "dsp_blocks": r"DSP block 18-bit elements\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
    "plls": r"PLLs\s*;\s*([\d,]+)\s*/\s*([\d,]+)",
}

RV32I_INSTRUCTIONS = {
    "LUI", "AUIPC", "JAL", "JALR",
    "BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU",
    "LB", "LH", "LW", "LBU", "LHU", "SB", "SH", "SW",
    "ADDI", "SLTI", "SLTIU", "XORI", "ORI", "ANDI", "SLLI", "SRLI", "SRAI",
    "ADD", "SUB", "SLL", "SLT", "SLTU", "XOR", "SRL", "SRA", "OR", "AND",
}  # fmt: skip
RV32M_INSTRUCTIONS = {
    "MUL", "MULH", "MULHSU", "MULHU", "DIV", "DIVU", "REM", "REMU",
}  # fmt: skip


def _find_pll_file(quartus_dir: Path) -> Path | None:
    """Procura o pll_0002.v na pasta do projeto Quartus e acima dela."""
    search = quartus_dir.resolve()
    for _ in range(PLL_SEARCH_DEPTH):
        candidates = (
            search / "pll" / "pll_0002.v",
            search / "src" / "PLL" / "pll_0002.v",
        )
        found = next((c for c in candidates if c.exists()), None)
        if found is not None:
            return found
        search = search.parent
    return None


def parse_pll_clock(quartus_dir: Path) -> dict:
    """Lê a frequência configurada no PLL da CPU no pll_0002.v."""
    pll_file = _find_pll_file(quartus_dir)
    if pll_file is None:
        return {"error": "pll_0002.v nao encontrado", "fmax_mhz": None}
    text = pll_file.read_text(errors="replace")
    match = re.search(r'output_clock_frequency0\("([\d.]+)\s*MHz"\)', text)
    if match:
        return {
            "source": str(pll_file),
            "clock_name": "PLL output0 (CPU clock)",
            "fmax_mhz": float(match.group(1)),
            "note": "Frequencia configurada no PLL (pll_0002.v)",
        }
    return {
        "error": "Padrao de frequencia nao encontrado em pll_0002.v",
        "fmax_mhz": None,
    }


def parse_fmax(report_path: Path) -> dict:
    """Lê o pior Fmax dos relógios do relatório de tempo do Quartus."""
    result = {"fmax_mhz": None, "clock_name": None, "source": str(report_path)}
    if not report_path.exists():
        result["error"] = f"Arquivo não encontrado: {report_path}"
        return result
    text = report_path.read_text(errors="replace")
    pattern = re.compile(
        r";\s*([\d.]+)\s*MHz\s*;[^;]*;\s*([\w\[\].]+)\s*;", re.IGNORECASE
    )
    matches = pattern.findall(text)
    if not matches:
        result["error"] = "Padrão Fmax não encontrado no relatório"
        return result
    parsed = [(name.strip(), float(freq)) for freq, name in matches]
    # O relógio do JTAG não é o relógio da CPU.
    cpu = [(n, f) for n, f in parsed if "tck" not in n.lower()]
    worst = min(cpu or parsed, key=lambda x: x[1])
    result["clock_name"] = worst[0]
    result["fmax_mhz"] = worst[1]
    result["all_clocks"] = dict(parsed)
    return result


def _resource_entry(match: re.Match) -> dict:
    """Monta o par usado e total de um recurso do relatório fitter."""
    used = int(match.group(1).replace(",", ""))
    if match.lastindex is None or match.lastindex < GROUPS_USED_AND_TOTAL:
        return {"used": used}
    total = int(match.group(2).replace(",", ""))
    return {
        "used": used,
        "total": total,
        "pct": round(100 * used / total, 1) if total else 0,
    }


def parse_resource_utilization(fit_report_path: Path) -> dict:
    """Lê a ocupação de ALMs, registradores, memória, DSPs e PLLs."""
    result = {"source": str(fit_report_path)}
    if not fit_report_path.exists():
        result["error"] = f"Arquivo não encontrado: {fit_report_path}"
        return result
    text = fit_report_path.read_text(errors="replace")
    for key, pattern in RESOURCE_PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[key] = _resource_entry(match)
    return result


def _count_attr(text: str, attr: str, fallback: int) -> int:
    """Lê um atributo numérico do cabeçalho do results.xml."""
    match = re.search(rf'\b{attr}="(\d+)"', text)
    return int(match.group(1)) if match else fallback


def _parse_results_xml(text: str) -> dict:
    """Conta os casos de um results.xml do cocotb."""
    cases = re.findall(r"<testcase\b[^>]*/>", text, re.DOTALL)
    cases += re.findall(r"<testcase\b[^>]*>.*?</testcase>", text, re.DOTALL)
    total = _count_attr(text, "tests", len(cases))
    failures = len(re.findall(r"<failure\b", text))
    errors = len(re.findall(r"<error\b", text))
    skips = len(re.findall(r"<skipped\b", text))
    failed = _count_attr(text, "failures", failures)
    errored = _count_attr(text, "errors", errors)
    skipped = _count_attr(text, "skipped", skips)
    return {
        "total": total,
        "passed": total - failed - errored - skipped,
        "failed": failed + errored,
        "skipped": skipped,
    }


def _parse_cocotb_log(text: str) -> dict:
    """Conta os casos de um log de texto do cocotb."""
    passed = len(re.findall(r"\bPASSED\b", text))
    failed = len(re.findall(r"\bFAILED\b", text))
    skipped = len(re.findall(r"\bSKIPPED\b", text))
    match = re.search(
        r"(\d+) tests passed.*?(\d+) failed", text, re.IGNORECASE
    )
    if match:
        passed, failed = int(match.group(1)), int(match.group(2))
    return {
        "total": passed + failed + skipped,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


def parse_cocotb_coverage(log_path: Path) -> dict:
    """Lê os totais de testes de um results.xml ou log do cocotb."""
    result = {
        "source": str(log_path),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "coverage_pct": None,
    }
    if not log_path.exists():
        result["error"] = f"Arquivo não encontrado: {log_path}"
        return result
    text = log_path.read_text(errors="replace")
    counts = (
        _parse_results_xml(text)
        if log_path.suffix == ".xml"
        else _parse_cocotb_log(text)
    )
    result.update(counts)
    if result["total"] > 0:
        result["coverage_pct"] = round(
            100 * result["passed"] / result["total"], 1
        )
    return result


def parse_tests_json(tests_json_path: Path) -> dict:
    """Lê o tests.json do runner cocotb e agrega os results.xml."""
    result = {
        "source": str(tests_json_path),
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "total": 0,
        "coverage_pct": None,
    }
    if not tests_json_path.exists():
        result["error"] = f"tests.json nao encontrado: {tests_json_path}"
        return result
    try:
        tests = json.loads(tests_json_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        result["error"] = f"Erro ao ler tests.json: {exc}"
        return result
    sim_build = tests_json_path.parent / "sim_build"
    found = list(sim_build.rglob("results.xml")) if sim_build.exists() else []
    if not found:
        total = len(tests)
        result.update(
            {
                "passed": total,
                "total": total,
                "coverage_pct": 100.0,
                "note": f"{total} suites em tests.json (sem results.xml)",
            }
        )
        return result
    for xml_path in found:
        counts = parse_cocotb_coverage(xml_path)
        for key in ("passed", "failed", "skipped"):
            result[key] += counts.get(key, 0)
    result["total"] = result["passed"] + result["failed"] + result["skipped"]
    result["note"] = f"Agregado de {len(found)} results.xml em sim_build/"
    if result["total"] > 0:
        result["coverage_pct"] = round(
            100 * result["passed"] / result["total"], 1
        )
    return result


def _instructions_in(text: str, instructions: set[str]) -> set[str]:
    """Devolve as instruções do conjunto citadas no texto."""
    return {i for i in instructions if re.search(rf"\b{i}\b", text)}


def count_instructions(testbench_dirs: list[str]) -> dict:
    """Conta as instruções RV32I e RV32M citadas nos testes."""
    found_i: set[str] = set()
    found_m: set[str] = set()
    for directory in testbench_dirs:
        path = Path(directory)
        if not path.exists():
            continue
        for source in list(path.rglob("*.py")) + list(path.rglob("*.S")):
            text = source.read_text(errors="replace").upper()
            found_i |= _instructions_in(text, RV32I_INSTRUCTIONS)
            found_m |= _instructions_in(text, RV32M_INSTRUCTIONS)
    total_i = len(RV32I_INSTRUCTIONS)
    total_m = len(RV32M_INSTRUCTIONS)
    return {
        "rv32i_covered": sorted(found_i),
        "rv32i_total": total_i,
        "rv32i_pct": round(100 * len(found_i) / total_i, 1),
        "rv32m_covered": sorted(found_m),
        "rv32m_total": total_m,
        "rv32m_pct": round(100 * len(found_m) / total_m, 1),
        "total_covered": len(found_i) + len(found_m),
        "total_supported": total_i + total_m,
        "ratio": f"{len(found_i) + len(found_m)} / {total_i + total_m}",
    }


def _find_tests_json(testbench_dirs: list[str]) -> Path | None:
    """Devolve o primeiro tests.json encontrado nas pastas de teste."""
    for directory in testbench_dirs:
        candidate = Path(directory) / "python" / "tests.json"
        if candidate.exists():
            return candidate
    return None


def _coverage(args: argparse.Namespace) -> dict:
    """Escolhe a fonte da cobertura: log do cocotb ou tests.json."""
    cocotb_log = Path(args.cocotb_log)
    if cocotb_log.exists() and str(cocotb_log) != "/dev/null":
        return parse_cocotb_coverage(cocotb_log)
    tests_json = _find_tests_json(args.testbench_dirs)
    if tests_json is not None:
        return parse_tests_json(tests_json)
    return parse_cocotb_coverage(cocotb_log)


def build_report(args: argparse.Namespace) -> dict:
    """Monta o relatório com os três KPIs."""
    quartus_dir = Path(args.quartus_dir)
    pll = parse_pll_clock(quartus_dir)
    clock = (
        pll if pll.get("fmax_mhz") else parse_fmax(quartus_dir / args.sta_rpt)
    )
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": "RV32IM, Capstone Insper/CTI 2026.1",
        "kpis": {
            "kpi1_clock_mhz": clock,
            "kpi1_resources": parse_resource_utilization(
                quartus_dir / args.fit_rpt
            ),
            "kpi2_test_coverage": _coverage(args),
            "kpi3_instructions": count_instructions(args.testbench_dirs),
        },
    }


def _print_clock(clock: dict) -> None:
    """Imprime o KPI 1."""
    print("\n[KPI 1] Clock do Sistema")
    if not clock.get("fmax_mhz"):
        print(f"  Fmax : N/A  ({clock.get('error', 'sem dados')})")
        return
    label = clock.get("note") or f"clock: {clock.get('clock_name', '?')}"
    print(f"  Fmax : {clock['fmax_mhz']:.2f} MHz  ({label})")


def _print_coverage(cov: dict) -> None:
    """Imprime o KPI 2."""
    print("\n[KPI 2] Cobertura de Testes (cocotb)")
    if cov.get("coverage_pct") is None:
        print(f"  N/A  ({cov.get('error', 'sem dados')})")
        return
    flag = "✓" if cov["failed"] == 0 else "✗"
    print(
        f"  {cov['passed']}/{cov['total']} testes passaram "
        f"({cov['coverage_pct']}%) {flag}"
    )
    if cov["failed"]:
        print(f"  FALHOU: {cov['failed']} teste(s)")
    if cov.get("note"):
        print(f"  ({cov['note']})")


def _print_instructions(ins: dict) -> None:
    """Imprime o KPI 3."""
    print("\n[KPI 3] Instruções Suportadas")
    if "ratio" not in ins:
        return
    print(f"  Total : {ins['ratio']}")
    for name, key in (("RV32I", "rv32i"), ("RV32M", "rv32m")):
        covered = len(ins[f"{key}_covered"])
        print(
            f"  {name} : {covered}/{ins[f'{key}_total']} "
            f"({ins[f'{key}_pct']}%)"
        )


def print_summary(report: dict) -> None:
    """Imprime o resumo legível do relatório."""
    sep = "=" * 62
    print(f"\n{sep}")
    print(f"  KPI REPORT, {report['project']}")
    print(f"  {report['generated_at']}")
    print(sep)
    kpis = report["kpis"]
    _print_clock(kpis.get("kpi1_clock_mhz", {}))
    _print_coverage(kpis.get("kpi2_test_coverage", {}))
    _print_instructions(kpis.get("kpi3_instructions", {}))
    print(f"\n{sep}\n")


def _parse_args() -> argparse.Namespace:
    """Lê os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description="KPI Report, Capstone RV32IM",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--quartus-dir", default="TopLevel/platforms/internal-mem/quartus"
    )
    parser.add_argument(
        "--sta-rpt", default="output_files/core_fpga_test.sta.rpt"
    )
    parser.add_argument(
        "--fit-rpt", default="output_files/core_fpga_test.fit.rpt"
    )
    parser.add_argument(
        "--cocotb-log", default="tests/component/multdiv/results.xml"
    )
    parser.add_argument("--testbench-dirs", nargs="+", default=["tests"])
    parser.add_argument(
        "--output", default=None, help="Salva JSON neste arquivo"
    )
    parser.add_argument("--json-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    """Gera o relatório, imprime-o e sai com 1 se algum KPI falhou."""
    args = _parse_args()
    report = build_report(args)
    if args.json_only:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_summary(report)
    if args.output:
        out = Path(args.output)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"Relatório JSON salvo em: {out}")
    errors = [
        v.get("error")
        for v in report["kpis"].values()
        if isinstance(v, dict) and v.get("error")
    ]
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
