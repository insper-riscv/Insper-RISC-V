"""Plan Actions batches and publish verified results."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from benchmarks.embench import report, run
from benchmarks.embench.provenance import cache_key, capture, metadata

FULL_BATCH = 3
MAX_MATRIX_JOBS = 256
SUMMARY_BYTES = 900000


def profiles(root: Path, scope: str) -> list[str]:
    """Read named profiles or expand the Core matrix."""
    names = {p.stem for p in (root / "Core/profiles").glob("rv32*.yaml")}
    if scope == "all":
        names.update(
            capture(
                [
                    "riscv-tools",
                    "profiles",
                    "--spec",
                    str(root / "Core/profiles/matrix.yaml"),
                    "--format",
                    "names",
                ],
                root,
            ).splitlines()
        )
    if not names:
        raise ValueError("No CPU profiles found")
    return sorted(names)


def emit(name: str, value: object) -> None:
    """Publish compact data to a GitHub Actions step output."""
    text = (
        value
        if isinstance(value, str)
        else json.dumps(value, separators=(",", ":"))
    )
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as stream:
            stream.write(f"{name}={text}\n")
    else:
        print(f"{name}={text}")


def plan(args: argparse.Namespace) -> None:
    """Plan both sides, including added and removed profiles."""
    names = set(profiles(args.candidate, args.scope))
    if args.base:
        names.update(profiles(args.base, args.scope))
    names = sorted(names)
    width = FULL_BATCH if args.scope == "all" else 1
    programs = run.read_yaml(run.HERE / "suite.yaml")["programs"]
    batches = make_batches(names, programs, width, args.workload)
    if len(batches) > MAX_MATRIX_JOBS:
        raise ValueError(
            "Full workload exceeds the Actions matrix limit; "
            "select named profiles or use the CI workload"
        )
    emit("matrix", {"include": batches})
    emit("hardware", {"profile": names if args.scope == "named" else []})
    revisions = {
        "candidate": capture(["git", "rev-parse", "HEAD"], args.candidate)
    }
    if args.base:
        revisions["base"] = capture(["git", "rev-parse", "HEAD"], args.base)
    args.output.write_text(
        json.dumps(
            {
                "profiles": names,
                "batches": batches,
                "revisions": revisions,
            }
        )
    )


def make_batches(
    names: list[str], programs: list[str], width: int, workload: str
) -> list[dict[str, Any]]:
    """Bound full-workload jobs and batch generated profiles."""
    if workload == "full":
        batches = [
            {
                "id": i * len(programs) + j,
                "profiles": [name],
                "programs": [program],
            }
            for i, name in enumerate(names)
            for j, program in enumerate(programs)
        ]
    else:
        batches = [
            {
                "id": i // width,
                "profiles": names[slice(i, i + width)],
                "programs": programs,
            }
            for i in range(0, len(names), width)
        ]
    return batches


def keys(args: argparse.Namespace) -> None:
    """Key each side independently for result reuse."""
    names = json.loads(args.profiles)
    for side in ("candidate", "base"):
        root = getattr(args, side)
        if not root:
            continue
        identity = metadata(root)
        identity["contract"]["workload"] = args.workload
        payload = [cache_key(identity, profile) for profile in names]
        payload.append(args.programs)
        key = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
        emit(side, "embench-v1-" + key)


def unavailable(
    root: Path,
    profile: str,
    destination: Path,
    workload: str,
    programs: list[str],
) -> None:
    """Represent an added/removed profile without inventing a score."""
    destination.mkdir(parents=True, exist_ok=True)
    suite = run.read_yaml(run.HERE / "suite.yaml")
    suite["workload"] = workload
    identity = metadata(root)
    identity["contract"]["workload"] = workload
    run.write_json(
        destination / "results.json",
        {
            "schema": run.SCHEMA,
            "profile": profile,
            "suite": suite,
            "provenance": identity,
            "results": [
                {"program": p, "status": "profile unavailable"}
                for p in programs
            ],
        },
    )


def execute(args: argparse.Namespace) -> None:
    """Run one bounded batch serially."""
    failed = False
    for side in ("base", "candidate"):
        root = getattr(args, side)
        if not root:
            continue
        available = set(profiles(root, args.scope))
        for profile in json.loads(args.profiles):
            if execute_profile(args, (side, root, available), profile):
                failed = True
    if failed:
        raise SystemExit(1)


def execute_profile(
    args: argparse.Namespace, target: tuple[str, Path, set[str]], profile: str
) -> bool:
    """Execute one side/profile, preserving unavailable variants."""
    side, root, available = target
    destination = args.output / side / profile
    if args.workload == "full":
        selected = json.loads(args.programs)
        if len(selected) != 1:
            raise ValueError("Full batches require one program")
        destination = destination / selected[0]
    if profile not in available:
        unavailable(
            root,
            profile,
            destination,
            args.workload,
            json.loads(args.programs),
        )
        return False
    arguments = [
        sys.executable,
        "-m",
        "benchmarks.embench.run",
        "--root",
        str(root),
        "--upstream",
        str(args.upstream),
        "--output",
        str(destination),
        "--profile",
        profile,
        "--reuse",
        "--workload",
        args.workload,
    ]
    for program in json.loads(args.programs):
        arguments.extend(["--program", program])
    status = subprocess.run(  # noqa: S603
        arguments,
        check=False,
        timeout=21500,
    )
    return status.returncode != 0


def combine(paths: list[Path]) -> dict[str, Any]:
    """Join full-workload shards without losing failed rows."""
    documents = [report.load(path) for path in sorted(paths)]
    result = documents[0]
    for data in documents[1:]:
        if any(
            result[key] != data[key]
            for key in ("profile", "suite", "provenance")
        ):
            raise ValueError("Inconsistent benchmark shards")
        result["results"].extend(data["results"])
    names = [row["program"] for row in result["results"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate benchmark shards")
    return result


def complete(data: dict[str, Any]) -> bool:
    """Require a record for each program and reject failed verifiers."""
    names = {row["program"] for row in data["results"]}
    return names == set(data["suite"]["programs"]) and not any(
        row["status"] == "failed" for row in data["results"]
    )


def profile_summary(name: str, args: argparse.Namespace) -> tuple[str, bool]:
    """Render one profile or a missing-artifact failure."""
    head = args.input / "candidate" / name
    base = args.input / "base" / name
    head_paths = list(head.rglob("results.json"))
    base_paths = list(base.rglob("results.json"))
    if not head_paths or (args.compare and not base_paths):
        return f"## `{name}` - missing results (FAIL)\n", True
    candidate = combine(head_paths)
    before = combine(base_paths) if args.compare else None
    text = report.render(candidate, before)
    report.write_csv(head / "results.csv", candidate)
    failed = not complete(candidate) or (
        before is not None and not complete(before)
    )
    return text, failed


def aggregate(args: argparse.Namespace) -> None:
    """Require expected artifacts and publish tables."""
    expected: dict[str, Any] = json.loads(args.plan.read_text())
    sections = [
        "# Embench processor benchmarks",
        "",
        "Scores use the pinned Embench reference, not an old "
        "version of this processor. Full JSON/CSV and logs are "
        "attached to this run.",
        "",
    ]
    failed = False
    for name in expected["profiles"]:
        section, bad = profile_summary(name, args)
        sections.append(section)
        failed = failed or bad
    text = "\n".join(sections)
    args.output.write_text(text)
    publish_summary(text)
    if failed:
        raise SystemExit(1)


def publish_summary(text: str) -> None:
    """Keep large manual matrices below GitHub's summary size limit."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    if len(text.encode()) > SUMMARY_BYTES:
        preview = "\n## ".join(text.split("\n## ", 6)[:6])
        text = (
            "The complete matrix exceeds GitHub's summary size limit. "
            "Download the embench-summary artifact for every table. "
            "The preview below contains only the first profiles.\n\n" + preview
        )
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(text)


def main() -> None:
    """Expose the steps used by the Actions workflow."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for name in ("plan", "keys", "execute"):
        sub = commands.add_parser(name)
        sub.add_argument("--candidate", type=Path, required=True)
        sub.add_argument("--base", type=Path)
        sub.add_argument("--scope", choices=("named", "all"), default="named")
        sub.add_argument("--workload", choices=("ci", "full"), default="ci")
        if name == "plan":
            sub.add_argument("--output", type=Path, required=True)
        else:
            sub.add_argument("--profiles", required=True)
            sub.add_argument("--programs", required=True)
        if name == "execute":
            sub.add_argument("--upstream", type=Path, required=True)
            sub.add_argument("--output", type=Path, required=True)
    sub = commands.add_parser("aggregate")
    sub.add_argument("--input", type=Path, required=True)
    sub.add_argument("--plan", type=Path, required=True)
    sub.add_argument("--compare", action="store_true")
    sub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"plan": plan, "keys": keys, "execute": execute, "aggregate": aggregate}[
        args.action
    ](args)


if __name__ == "__main__":
    main()
