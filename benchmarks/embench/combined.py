"""Join measurements without mixing simulation and FPGA platforms."""

import argparse
import json
from pathlib import Path
from typing import Any

from benchmarks.embench import ci, report, run


def metrics(data: dict[str, Any]) -> tuple[float, float, float]:
    """Use mean retired instructions and workload-weighted IPC."""
    rows = [row for row in data["results"] if report.valid_row(row)]
    instructions = sum(row["instructions"] for row in rows)
    cycles = sum(row["cycles"] for row in rows)
    if not rows or not cycles:
        raise ValueError("No complete measurements")
    return instructions / len(rows), instructions / cycles, cycles


def speed_changes(
    base: dict[str, Any] | None, candidate: dict[str, Any]
) -> dict[str, float]:
    """Compare elapsed hardware time or simulated core cycles."""
    if base is None:
        return {}
    changes = report.compare(base, candidate)
    if candidate.get("backend") == "fpga":
        ratio = candidate["configured_mhz"] / base["configured_mhz"]
        changes = {
            name: ((value / 100 + 1) * ratio - 1) * 100
            for name, value in changes.items()
        }
    return changes


def program_table(
    data: dict[str, Any], changes: dict[str, float]
) -> list[str]:
    """Show physical throughput only when a board clock is available."""
    backend = data.get("backend", "simulation")
    mhz = data.get("configured_mhz") if backend == "fpga" else None
    lines: list[str] = []
    for row in data["results"]:
        if not report.valid_row(row):
            lines.append(
                f"| {row['program']} | {backend} | {row['status']} | "
                "— | — | — | — | — | — | — | — | — | — | — |"
            )
            continue
        lines.append(program_row(row, backend, mhz, changes))
    return lines


def program_row(
    row: dict[str, Any],
    backend: str,
    mhz: float | None,
    changes: dict[str, float],
) -> str:
    """Format verified work and optional physical throughput."""
    ipc = row["instructions"] / row["cycles"]
    mips = f"{ipc * mhz:.3f}" if mhz else "—"
    elapsed = f"{row['cycles'] / (mhz * 1000):.3f}" if mhz else "—"
    clock = f"{mhz:.6f}" if mhz else "—"
    delta = (
        f"{changes[row['program']]:+.2f}%"
        if row["program"] in changes
        else "—"
    )
    mix = " | ".join(
        f"{100 * row['operations'][name] / row['instructions']:.2f}"
        for name in run.BUCKETS
    )
    return (
        f"| {row['program']} | {backend} | {row['cycles']} | "
        f"{row['instructions']} | {ipc:.4f} | {mips} | {elapsed} | "
        f"{clock} | {row['score_per_mhz']:.5f} | {mix} | {delta} |"
    )


def profile(name: str, args: argparse.Namespace) -> tuple[str, bool]:
    """Require both backends and both PR sides."""
    lines = [f"## `{name}`", ""]
    tables: list[str] = []
    failed = False
    for backend, root in (
        ("simulation", args.simulation),
        ("fpga", args.hardware),
    ):
        head_paths = list((root / "candidate" / name).rglob("results.json"))
        base_paths = list((root / "base" / name).rglob("results.json"))
        if not head_paths or (args.compare and not base_paths):
            lines.append(f"**FAIL — {backend}: missing measurements.**\n")
            failed = True
            continue
        head = ci.combine(head_paths)
        base = ci.combine(base_paths) if args.compare else None
        require_pair(head, base, args)
        if head.get("backend", "simulation") != backend:
            raise ValueError("Artifact backend does not match its directory")
        changes = speed_changes(base, head)
        tables.extend(program_table(head, changes))
        section, bad = backend_summary(head, base, changes)
        lines.extend(section)
        failed = failed or bad
        report.write_csv(root / "candidate" / name / "results.csv", head)
    lines.extend(
        [
            "### Combined program measurements",
            "",
            "| Program | Backend | Cycles | Instructions | IPC | MIPS | "
            "Time ms | CPU MHz | Index/MHz | Branch % | Memory % | "
            "Compute % | Other % | PR speed Δ |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
            "---:|---:|---:|---:|",
            *tables,
            "",
        ]
    )
    return "\n".join(lines), failed


def require_revision(data: dict[str, Any], expected: str | None) -> None:
    """Reject measurements from an unplanned revision."""
    if expected is None or data["provenance"]["revision"] != expected:
        raise ValueError("Measurement revision does not match the PR plan")


def require_pair(
    head: dict[str, Any],
    base: dict[str, Any] | None,
    args: argparse.Namespace,
) -> None:
    """Check exact candidate and target revisions independently."""
    require_revision(head, args.revisions.get("candidate"))
    if base is not None:
        require_revision(base, args.revisions.get("base"))


def complete(data: dict[str, Any]) -> bool:
    """Require successful verification of every declared program."""
    return ci.complete(data) and all(
        report.valid_row(row) for row in data["results"]
    )


def backend_summary(
    head: dict[str, Any],
    base: dict[str, Any] | None,
    changes: dict[str, float],
) -> tuple[list[str], bool]:
    """Summarize one platform and its own base measurements."""
    backend = head.get("backend", "simulation")
    lines = [
        f"### {backend}",
        "",
        f"Candidate: `{head['provenance']['revision']}`",
        "",
    ]
    failed = not complete(head)
    if base is not None:
        lines.extend(
            [f"PR target base: `{base['provenance']['revision']}`", ""]
        )
        failed = failed or not complete(base)
    if complete(head):
        mean, ipc, _ = metrics(head)
        lines.append(
            f"Mean retired instructions/program: **{mean:,.1f}**; "
            f"weighted IPC: **{ipc:.4f}**."
        )
        score = report.geomean(
            [row["score_per_mhz"] for row in head["results"]]
        )
        lines.append(
            f"Overall suite index/MHz (geometric mean): **{score:.5f}**."
        )
        if backend == "fpga":
            lines.append(
                "Overall suite index at configured clock: "
                f"**{score * head['configured_mhz']:.5f}**."
            )
    if backend == "fpga":
        lines.extend(hardware_summary(head))
    lines.extend(["", *report.summaries(head), ""])
    if base is not None:
        lines.extend([*report.comparison_summaries(head, changes), ""])
    return lines, failed


def hardware_summary(data: dict[str, Any]) -> list[str]:
    """Separate configured frequency, timing Fmax and measured work."""
    timing = data["timing"]
    return [
        "",
        f"Configured CPU clock: **{data['configured_mhz']:.6f} MHz**; "
        "restricted intra-core Fmax: "
        f"**{timing['core_domain_fmax_mhz']:.2f} MHz**; "
        "minimum multicorner slack: "
        f"**{timing['minimum_slack_ns']:.3f} ns**.",
        "",
        "Three physical repetitions; median cycles and deterministic "
        "instruction counts. Fmax belongs to the instrumented build "
        "and excludes cross-clock paths.",
    ]


def aggregate(args: argparse.Namespace) -> None:
    """Publish partial evidence and fail on missing measurements."""
    expected = json.loads(args.plan.read_text())
    args.revisions = expected.get("revisions", {})
    lines = [
        "# Embench — simulation + FPGA",
        "",
        "Simulation uses internal ROM/RAM without caches. FPGA uses "
        "the DE0-CV "
        "with SDRAM, emulated FLASH and 4 KiB I/D caches. Results are "
        "separate "
        "platform measurements; no hardware/simulation speedup is claimed.",
        "",
        "IPC = retired instructions/cycles. MIPS = IPC * configured CPU MHz; "
        "time = cycles/configured clock. CPU MHz comes from the generated PLL "
        "configuration, checked by multicorner timing, "
        "not an oscilloscope measurement. "
        "Fmax is an estimate, not the operating clock.",
        "",
        "PR speed Δ compares the same backend against the exact PR base "
        "(elapsed time on FPGA; cycles in simulation). Positive means faster. "
        "A dash means unavailable, never zero. CI index is an estimate from "
        "one local repetition, not an official full-duration Embench score.",
        "",
    ]
    failed = False
    for name in expected["profiles"]:
        text, bad = profile(name, args)
        lines.append(text)
        failed = failed or bad
    text = "\n".join(lines)
    args.output.write_text(text)
    ci.publish_summary(text)
    if failed:
        raise SystemExit(1)


def main() -> None:
    """Expose the final Actions table generator."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("simulation", "hardware", "plan", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--compare", action="store_true")
    aggregate(parser.parse_args())


if __name__ == "__main__":
    main()
