"""Compute complete CI scores against frozen main inputs."""

from typing import Any

from benchmarks.embench import report


def profile_score(
    base: dict[str, Any], head: dict[str, Any]
) -> dict[str, Any]:
    """Require paired coverage for every suite program."""
    expected = set(head["suite"]["programs"])
    changes = report.compare(base, head)
    if set(changes) != expected:
        raise ValueError(
            "Overall score requires complete paired program coverage"
        )
    for data in (base, head):
        rows = data["results"]
        if len(rows) != len(expected) or any(
            not report.valid_row(row) for row in rows
        ):
            raise ValueError("Overall score requires every verifier to pass")
    ratio = report.geomean(
        [1 + changes[name] / 100 for name in sorted(expected)]
    )
    return {
        "profile": head["profile"],
        "programs": len(expected),
        "base_score_per_mhz": report.geomean(
            [row["score_per_mhz"] for row in base["results"]]
        ),
        "head_score_per_mhz": report.geomean(
            [row["score_per_mhz"] for row in head["results"]]
        ),
        "relative_index": 100 * ratio,
        "delta_percent": 100 * (ratio - 1),
    }


def matched_profile(
    name: str,
    expected: dict[str, Any],
    paired: dict[str, tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any] | None:
    """Score only a verified pair of the expected suite."""
    if name not in paired:
        return None
    before, head = paired[name]
    if (
        before["profile"] != name
        or head["profile"] != name
        or set(head["suite"]["programs"]) != set(expected["programs"])
    ):
        return None
    try:
        return profile_score(before, head)
    except ValueError, KeyError, ZeroDivisionError:
        return None


def calculate(
    expected: dict[str, Any],
    paired: dict[str, tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    """Normalize main=100, with equal program and profile weights."""
    document: dict[str, Any] = {
        "schema": 1,
        "pull_request_number": expected.get("pull_request_number"),
        "status": "incomplete",
        "baseline_branch": "main",
        "baseline_sha": expected["revisions"].get("base"),
        "candidate_sha": expected["revisions"]["candidate"],
        "workload": "ci",
        "baseline_index": 100,
        "relative_index": None,
        "delta_percent": None,
        "profiles": [],
        "expected_profiles": len(expected["profiles"]),
        "formula": (
            "100 * GM_profiles(GM_programs(main_cycles / candidate_cycles))"
        ),
    }
    for name in expected["profiles"]:
        item = matched_profile(name, expected, paired)
        if item is not None:
            document["workload"] = paired[name][1]["suite"].get(
                "workload", "ci"
            )
            document["profiles"].append(item)
    if (
        document["profiles"]
        and len(document["profiles"]) == document["expected_profiles"]
    ):
        ratios = [
            item["relative_index"] / 100 for item in document["profiles"]
        ]
        ratio = report.geomean(ratios)
        document.update(
            status="complete",
            relative_index=100 * ratio,
            delta_percent=100 * (ratio - 1),
            base_score_per_mhz=report.geomean(
                [item["base_score_per_mhz"] for item in document["profiles"]]
            ),
            head_score_per_mhz=report.geomean(
                [item["head_score_per_mhz"] for item in document["profiles"]]
            ),
        )
    return document


def markdown(document: dict[str, Any]) -> str:
    """Render the aggregate with its baseline provenance."""
    base, head = document.get("baseline_sha"), document["candidate_sha"]
    label = (
        "Embench CI index/MHz"
        if document["workload"] == "ci"
        else "Embench/MHz"
    )
    lines = [
        "## Overall benchmark score",
        "",
        f"Comparing candidate `{head}` to `main` at `{base}` "
        "(the previous main snapshot for automatic merge runs).",
        "",
    ]
    if document["status"] == "complete":
        lines.extend(
            [
                f"**Overall score: {document['head_score_per_mhz']:.5f} "
                f"{label}** · main: **{document['base_score_per_mhz']:.5f}**",
                "",
            ]
        )
        lines.append(
            f"**Overall index: {document['relative_index']:.2f}** "
            "· main = 100 · "
            f"**{document['delta_percent']:+.2f}%** speed change."
        )
    else:
        lines.append(
            "**Overall index unavailable:** complete, compatible measurements "
            "are required for every profile/program on both sides."
        )
    lines.extend(
        [
            "",
            f"| CPU profile | main {label} | Candidate {label} "
            "| Speed change |",
            "|---|---:|---:|---:|",
        ]
    )
    lines.extend(
        f"| `{item['profile']}` | {item['base_score_per_mhz']:.5f} | "
        f"{item['head_score_per_mhz']:.5f} | "
        f"{item['delta_percent']:+.2f}% |"
        for item in document["profiles"]
    )
    lines.extend(
        [
            "",
            "Higher is faster. Geometric means give each program equal "
            "weight within its profile, then each profile equal weight. "
            "This is a simulated cycles-based index; it is not measured FPGA "
            "clock speed or MIPS. The shortened CI workload is not an "
            "official full Embench score.",
            "",
        ]
    )
    return "\n".join(lines)
