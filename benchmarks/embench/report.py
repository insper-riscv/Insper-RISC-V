"""Render program/profile tables and PR comparisons."""

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

from benchmarks.embench.records import intact
from benchmarks.embench.run import BUCKETS, SCHEMA

# Fixed high-intensity groups from Table 1, DOI 10.1109/MC.2024.3511352.
# They overlap; membership is fixed so a PR cannot change its own
# groups.
GROUPS = {
    "branching": {
        "huffbench",
        "nsichneu",
        "sglib-combined",
        "slre",
        "tarfind",
        "wikisort",
    },
    "memory": {
        "matmult-int",
        "nsichneu",
        "sglib-combined",
        "slre",
        "statemate",
        "wikisort",
    },
    "compute": {
        "aha-mont64",
        "crc32",
        "md5sum",
        "nettle-aes",
        "nettle-sha256",
    },
}


def geomean(values: list[float]) -> float:
    """Reject nonfinite or nonpositive geometric means."""
    if not values or any(v <= 0 or not math.isfinite(v) for v in values):
        raise ValueError("Geometric mean needs finite positive values")
    return math.exp(sum(map(math.log, values)) / len(values))


def distribution(values: list[float]) -> tuple[float, float]:
    """Summarize the spread across programs in logarithmic space."""
    average = geomean(values)
    spread = math.exp(
        math.sqrt(
            sum((math.log(value) - math.log(average)) ** 2 for value in values)
            / len(values)
        )
    )
    return average, spread


def valid_row(row: dict[str, Any]) -> bool:
    """Require positive measurements and balanced counters."""
    if row.get("status") != "pass":
        return False
    cycles, instructions = row["cycles"], row["instructions"]
    counts = row["operations"]
    if cycles <= 0 or instructions <= 0 or set(counts) != set(BUCKETS):
        raise ValueError("Invalid measurement counters")
    if sum(counts.values()) != instructions or min(counts.values()) < 0:
        raise ValueError("Unbalanced instruction mix")
    if not math.isfinite(row["score_per_mhz"]) or row["score_per_mhz"] <= 0:
        raise ValueError("Invalid Embench score")
    return True


def load(path: Path) -> dict[str, Any]:
    """Reject legacy, duplicate or invalid measurements."""
    data: dict[str, Any] = json.loads(path.read_text())
    if data.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported result schema: {path}")
    if not intact(data):
        raise ValueError(f"Corrupted or unsealed result record: {path}")
    names = [r["program"] for r in data["results"]]
    if len(names) != len(set(names)):
        raise ValueError(f"Duplicate program: {path}")
    for row in data["results"]:
        valid_row(row)
    return data


def compare(base: dict[str, Any], head: dict[str, Any]) -> dict[str, float]:
    """Compare results with identical measurement contracts."""
    if base["provenance"]["contract"] != head["provenance"]["contract"]:
        raise ValueError(
            "Incompatible measurement contracts; rerun both sides"
        )
    if base["suite"] != head["suite"] or base["profile"] != head["profile"]:
        raise ValueError("Cannot compare different suites or profiles")
    before = {r["program"]: r for r in base["results"] if valid_row(r)}
    return {
        r["program"]: 100 * (before[r["program"]]["cycles"] / r["cycles"] - 1)
        for r in head["results"]
        if valid_row(r) and r["program"] in before
    }


def summaries(data: dict[str, Any]) -> list[str]:
    """Suppress aggregate scores for incomplete suites."""
    rows = {r["program"]: r for r in data["results"] if valid_row(r)}
    groups = {"all programs": set(data["suite"]["programs"]), **GROUPS}
    label = (
        "CI index/MHz"
        if data["suite"].get("workload") == "ci"
        else "Embench/MHz"
    )
    lines = [
        f"| Group | Coverage | {label} (GM) | GSD |",
        "|---|---:|---:|---:|",
    ]
    for name, programs in groups.items():
        present = programs & rows.keys()
        coverage = f"{len(present)}/{len(programs)}"
        score, deviation = "incomplete", "—"
        if present == programs:
            values = [
                float(rows[p]["score_per_mhz"]) for p in sorted(programs)
            ]
            average, spread = distribution(values)
            score, deviation = f"{average:.5f}", f"{spread:.3f}"
        lines.append(f"| {name} | {coverage} | {score} | {deviation} |")
    return lines


def comparison_summaries(
    data: dict[str, Any], changes: dict[str, float]
) -> list[str]:
    """Summarize measured PR speed changes for fixed program groups."""
    groups = {"all programs": set(data["suite"]["programs"]), **GROUPS}
    lines = [
        "| Group | Paired coverage | PR speed delta (GM) | GSD |",
        "|---|---:|---:|---:|",
    ]
    for name, programs in groups.items():
        paired = programs & changes.keys()
        delta, spread = "incomplete", "—"
        if paired == programs:
            average, deviation = distribution(
                [changes[p] / 100 + 1 for p in sorted(programs)]
            )
            delta, spread = f"{100 * (average - 1):+.2f}%", f"{deviation:.3f}"
        lines.append(
            f"| {name} | {len(paired)}/{len(programs)} | {delta} | {spread} |"
        )
    return lines


def table(data: dict[str, Any], changes: dict[str, float]) -> list[str]:
    """Show every program, including failed or missing runs."""
    rows = {r["program"]: r for r in data["results"]}
    label = (
        "CI index/MHz"
        if data["suite"].get("workload") == "ci"
        else "Embench/MHz"
    )
    lines = [
        f"| Program | Cycles | Instructions | CPI | IPC | {label} | "
        "Branch % | Memory % | Compute % | Other % | PR speed Δ |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in data["suite"]["programs"]:
        row = rows.get(name)
        if row is None or not valid_row(row):
            status = "not run" if row is None else row["status"]
            lines.append(
                f"| {name} | {status} | — | — | — | — | — | — | — | — | — |"
            )
            continue
        lines.append(format_row(name, row, changes))
    return lines


def format_row(
    name: str, row: dict[str, Any], changes: dict[str, float]
) -> str:
    """Format one verified program row."""
    mix = [100 * row["operations"][b] / row["instructions"] for b in BUCKETS]
    percentages = " | ".join(f"{v:.2f}" for v in mix)
    delta = f"{changes[name]:+.2f}%" if name in changes else "—"
    return (
        f"| {name} | {row['cycles']} | {row['instructions']} | "
        f"{row['cpi']:.3f} | {row['instructions'] / row['cycles']:.3f} | "
        f"{row['score_per_mhz']:.5f} | "
        f"{percentages} | {delta} |"
    )


def counter_summary(data: dict[str, Any]) -> str:
    """Summarize counts only for a complete verified suite."""
    rows = [row for row in data["results"] if valid_row(row)]
    if not rows or {row["program"] for row in rows} != set(
        data["suite"]["programs"]
    ):
        return (
            "Aggregate instruction/IPC metrics unavailable: incomplete suite."
        )
    instructions = sum(row["instructions"] for row in rows)
    cycles = sum(row["cycles"] for row in rows)
    return (
        "Mean retired instructions/program: "
        f"**{instructions / len(rows):,.1f}**; "
        f"weighted IPC (total instructions / total cycles): "
        f"**{instructions / cycles:.4f}**."
    )


def render(data: dict[str, Any], base: dict[str, Any] | None) -> str:
    """Build a self-contained Actions summary for one profile."""
    provenance = data["provenance"]
    changes = compare(base, data) if base is not None else {}
    lines = [
        f"## Embench IoT — `{data['profile']}`",
        "",
        "Simulation: internal ROM/RAM, no caches. "
        "IoT 2.0 development snapshot; all kernels, GSF=1, warmup=1.",
        "",
        "IPC = retired instructions / core cycles. "
        "MIPS = IPC * clock frequency in MHz; FPGA frequency is not "
        "measured by this simulation.",
        "",
        f"Candidate: `{provenance['revision']}`",
        "",
    ]
    if base is not None:
        lines.extend(
            [
                f"Target base: `{base['provenance']['revision']}`",
                "",
                "PR speed Δ = (base cycles / candidate cycles - 1) * 100. "
                "Positive means faster. This is a branch comparison, "
                "separate from the Embench reference score.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "PR speed delta unavailable: no target-base measurements "
                "were supplied. A dash does not mean zero percent.",
                "",
            ]
        )
    if data["suite"].get("workload") == "ci":
        lines.extend(
            [
                "CI workload: one local repetition of each complete kernel. "
                "Score/MHz is an extrapolated CI index, not an official "
                "full-duration Embench score. PR deltas use measured cycles "
                "directly and do not extrapolate.",
                "",
            ]
        )
    lines.extend([counter_summary(data), "", *table(data, changes)])
    if base is not None:
        lines.extend(["", *comparison_summaries(data, changes), ""])
    lines.extend(
        [
            "",
            *summaries(data),
            "",
            "Category summaries use fixed, overlapping high-intensity "
            "groups from the paper's Table 1; these are local diagnostic "
            "summaries, not separate official Embench scores. "
            "Instruction percentages above are measured on this RTL. "
            "GSD describes spread across programs, not run-to-run noise.",
            "",
        ]
    )
    if base is not None:
        lines.extend(
            [
                "### Target-base measurements",
                "",
                counter_summary(base),
                "",
                *table(base, {}),
                "",
            ]
        )
    return "\n".join(lines)


def write_csv(path: Path, data: dict[str, Any]) -> None:
    """Export numeric results without rounding the underlying values."""
    fields = [
        "profile",
        "program",
        "status",
        "revision",
        "workload",
        "backend",
        "configured_mhz",
        "core_domain_fmax_mhz",
        "mips_nominal",
        "elapsed_seconds_nominal",
        "cycles",
        "instructions",
        "cpi",
        "ipc",
        "score_kind",
        "score_per_mhz",
        "local_scale_original",
        "local_scale_executed",
        "global_scale_factor",
    ]
    fields.extend(
        f"{bucket}_{unit}"
        for bucket in BUCKETS
        for unit in ("instructions", "percent")
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in data["results"]:
            writer.writerow(csv_row(data, row, fields))


def csv_row(
    data: dict[str, Any], row: dict[str, Any], fields: list[str]
) -> dict[str, Any]:
    """Keep score kinds, scale factors and units explicit."""
    value = {key: row[key] for key in fields if key in row}
    value.update(
        {
            "profile": data["profile"],
            "backend": data.get("backend", "simulation"),
            "configured_mhz": data.get("configured_mhz"),
            "core_domain_fmax_mhz": data.get("timing", {}).get(
                "core_domain_fmax_mhz"
            ),
            "revision": data["provenance"]["revision"],
            "workload": data["suite"].get("workload"),
            "global_scale_factor": data["suite"].get("global_scale_factor"),
            "local_scale_original": row.get("scale", {}).get("original"),
            "local_scale_executed": row.get("scale", {}).get("executed"),
        }
    )
    if row.get("status") == "pass":
        value["ipc"] = row["instructions"] / row["cycles"]
    for bucket, count in row.get("operations", {}).items():
        value[bucket + "_instructions"] = count
        value[bucket + "_percent"] = 100 * count / row["instructions"]
    return value


def main() -> None:
    """Render a single result or its PR comparison as Markdown."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    candidate = load(args.candidate)
    base = load(args.base) if args.base else None
    args.output.write_text(render(candidate, base))
    write_csv(args.output.with_suffix(".csv"), candidate)


if __name__ == "__main__":
    main()
