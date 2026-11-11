"""Audit controlled baseline/current measurements before reporting a speedup."""

import argparse
import csv
import json
import statistics
from pathlib import Path

BASELINE = "2115e4c8f49f75f9ef045bb59cf375c36f02b3ca"


def audit_comparisons(paths):
    """Reject different programs, failed answers or changing source snapshots."""
    groups = {}
    reference = None
    for path in paths:
        report = json.loads(Path(path).read_text())
        if report["baseline_commit"] != BASELINE:
            raise ValueError("Unexpected historical baseline")
        identity = {
            key: report[key]
            for key in [
                "baseline_commit",
                "current_commit",
                "baseline_source_hashes",
                "current_source_hashes",
                "runner_sha256",
                "monitor_sha256",
            ]
        }
        if reference is None:
            reference = identity
        if reference != identity:
            raise ValueError("Source/protocol changed between repetitions")
        pairs = {}
        for row in report["runs"]:
            key = row["kernel"]
            pair = pairs.setdefault(key, {})
            if row["variant"] in pair:
                raise ValueError("Duplicate variant in a repetition")
            pair[row["variant"]] = row
        for name, pair in pairs.items():
            if set(pair) != {"baseline", "current"}:
                raise ValueError("Missing baseline or current measurement")
            old, new = pair["baseline"], pair["current"]
            if old["binary_sha256"] != new["binary_sha256"]:
                raise ValueError(
                    "Different instruction bytes cannot be compared"
                )
            if old["expected"] != new["expected"]:
                raise ValueError("Different expected results")
            for row in [old, new]:
                if (
                    not row["verified"]
                    or not row["simulation_passed"]
                    or row["checksum"] != row["expected"]
                ):
                    raise ValueError(
                        "Incorrect answer is not a performance result"
                    )
                if type(row["cycles"]) is not int or row["cycles"] <= 0:
                    raise ValueError("Invalid cycle count")
            entry = groups.setdefault(
                name,
                {
                    "baseline_cycles": [],
                    "current_cycles": [],
                    "binary_sha256": old["binary_sha256"],
                },
            )
            if entry["binary_sha256"] != old["binary_sha256"]:
                raise ValueError("Program changed between repetitions")
            entry["baseline_cycles"].append(old["cycles"])
            entry["current_cycles"].append(new["cycles"])
    if not groups or any(
        len(row["baseline_cycles"]) != len(paths) for row in groups.values()
    ):
        raise ValueError("Empty or inconsistent kernel sets")
    rows = []
    for name, entry in groups.items():
        old = statistics.median(entry["baseline_cycles"])
        new = statistics.median(entry["current_cycles"])
        rows.append(
            dict(
                kernel=name,
                repetitions=len(paths),
                baseline_median=old,
                current_median=new,
                baseline_min=min(entry["baseline_cycles"]),
                baseline_max=max(entry["baseline_cycles"]),
                current_min=min(entry["current_cycles"]),
                current_max=max(entry["current_cycles"]),
                speedup_same_clock=old / new,
                cycle_reduction_pct=100 * (old - new) / old,
                binary_sha256=entry["binary_sha256"],
            )
        )
    return {
        "scope": "Controlled RTL simulation; not whole-system FPGA speedup",
        "identity": reference,
        "comparisons": rows,
    }


def main():
    """Write an auditable summary, retaining ties and regressions."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("measurements", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = audit_comparisons(args.measurements)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "summary.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    rows = report["comparisons"]
    with (args.output / "comparison.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(
            f"{row['kernel']}: {row['baseline_median']} -> {row['current_median']} cycles; {row['speedup_same_clock']:.4f}x"
        )


if __name__ == "__main__":
    main()
