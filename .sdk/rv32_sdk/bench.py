"""Reproducible raw Embench workloads and counter smoke checks for the SDK."""

import argparse
import csv
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]
REVISION = "0466a18e4f6b47e19598d7c6ba72916d54b68f65"
URL = "https://github.com/embench/embench-iot.git"
WORKLOADS = (
    "aha-mont64",
    "crc32",
    "cubic",
    "edn",
    "huffbench",
    "matmult-int",
    "minver",
    "nbody",
    "nettle-aes",
    "nettle-sha256",
    "nsichneu",
    "picojpeg",
    "qrduino",
    "sglib-combined",
    "slre",
    "st",
    "statemate",
    "ud",
    "wikisort",
)


def output(command, **kwargs):
    """Run a bounded metadata command."""
    return subprocess.check_output(
        command, text=True, timeout=30, **kwargs
    ).strip()


def execute_sdk(command, timeout):
    """Bound the entire compiler/simulator process group, including children."""
    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            raise
        return subprocess.CompletedProcess(
            command, process.returncode, stdout, stderr
        )


def check_source(source):
    """Require the exact, unmodified upstream release before copying sources."""
    if output(["git", "-C", str(source), "rev-parse", "HEAD"]) != REVISION:
        raise ValueError(f"Embench must be pinned to {REVISION}")
    if output(
        [
            "git",
            "-C",
            str(source),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ]
    ):
        raise ValueError("Embench checkout has local modifications")


def parse_measurement(stdout):
    """Reject missing, duplicate, invalid or unverified measurements."""
    matches = re.findall(
        r"^RV32BENCH cycles=(\d+) instructions=(\d+) verified=([01])$",
        stdout,
        re.M,
    )
    if len(matches) != 1:
        raise ValueError("Expected exactly one RV32BENCH record")
    cycles, instructions, verified = map(int, matches[0])
    if not verified or cycles <= 0 or instructions <= 0:
        raise ValueError("Invalid counters or failed benchmark verification")
    return {
        "cycles": cycles,
        "instructions": instructions,
        "cpi": cycles / instructions,
    }


def prepare_project(destination, name, source, cycles, hardware=None):
    """Create a standalone SDK project, preserving upstream workload files."""
    destination.mkdir(parents=True, exist_ok=True)
    support = SDK / ".sdk/benchmarks"
    sources = []
    source_dir = destination / "src"
    source_dir.mkdir(exist_ok=True)
    includes = [str(support)]
    if name == "smoke":
        sources.append(str(support / "smoke.c"))
    else:
        check_source(source)
        includes.extend([str(source / "support"), str(source / "src" / name)])
        # Define scale in a separate translation-unit wrapper, never edit upstream.
        for number, original in enumerate(
            sorted((source / "src" / name).glob("*.c"))
        ):
            wrapper = source_dir / f"workload{number}.c"
            wrapper.write_text(
                "/* Upstream warnings remain visible in logs; do not alter algorithms. */\n"
                '#pragma GCC diagnostic warning "-Wunused-variable"\n'
                '#pragma GCC diagnostic warning "-Wunused-parameter"\n'
                '#pragma GCC diagnostic warning "-Wmaybe-uninitialized"\n'
                '#pragma GCC diagnostic warning "-Wunused-but-set-variable"\n'
                '#pragma GCC diagnostic warning "-Wabsolute-value"\n'
                '#pragma GCC diagnostic warning "-Wunterminated-string-initialization"\n'
                '#pragma GCC diagnostic warning "-Wmisleading-indentation"\n'
                + (
                    "#define bool embench_legacy_bool\n"
                    if name == "wikisort"
                    else ""
                )
                + "#define CPU_MHZ 1\n#include "
                + json.dumps(str(original))
                + "\n"
            )
            sources.append(str(wrapper))
        if not sources:
            raise ValueError(f"No workload sources for {name}")
        sources.append(str(source / "support/beebsc.c"))
    (source_dir / "main.c").write_bytes((support / "main.c").read_bytes())
    (destination / "rv32.toml").write_text(
        '[project]\nname = "'
        + name
        + '"\nlanguage = "c"\nsource = "src/main.c"\n'
        + "sources = "
        + json.dumps(sources)
        + "\ninclude_dirs = "
        + json.dumps(includes)
        + f"\nsimulation_timeout_cycles = {cycles}\ntimeout_seconds = 120\n"
    )
    if hardware is not None:
        with (destination / "rv32.toml").open("a") as manifest:
            manifest.write("jtag_hardware = " + json.dumps(hardware) + "\n")
    return hashlib.sha256(
        b"".join(
            Path(path).read_bytes()
            for path in (
                [str(support / "smoke.c")]
                if name == "smoke"
                else [
                    *sorted((source / "src" / name).glob("*.c")),
                    source / "support/beebsc.c",
                    source / "support/support.h",
                    source / "support/beebsc.h",
                ]
            )
        )
        + (support / "main.c").read_bytes()
        + (support / "counters.h").read_bytes()
    ).hexdigest()


def run(args):
    """Run workloads and save failed runs as failures, never as valid scores."""
    if args.cpu_hz is not None and args.cpu_hz <= 0:
        raise ValueError("--cpu-hz must be positive")
    if args.repeats < 1 or args.cycles < 1 or args.timeout < 1:
        raise ValueError("Repeats and simulation cycles must be positive")
    root = args.output.resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError(
            "Output directory must be empty; previous results are preserved"
        )
    root.mkdir(parents=True, exist_ok=True)
    source = args.source.resolve()
    names = args.benchmarks
    if names != ["smoke"]:
        check_source(source)
    report = {
        "schema": 1,
        "runner_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "sdk_tracked_diff": output(["git", "-C", str(SDK), "diff", "HEAD"]),
        "created_utc": datetime.now(UTC).isoformat(),
        "sdk_commit": output(["git", "-C", str(SDK), "rev-parse", "HEAD"]),
        "sdk_dirty": bool(
            output(["git", "-C", str(SDK), "status", "--porcelain"])
        ),
        "submodules": output(
            ["git", "-C", str(SDK), "submodule", "status", "--recursive"]
        ),
        "gcc": output(["riscv32-unknown-elf-gcc", "--version"]),
        "backend": args.backend,
        "jtag_hardware": args.jtag_hardware,
        "cpu_hz_user_supplied": args.cpu_hz,
        "platform": "internal-mem",
        "compiler_policy": "SDK optimize_flags: -Os, RV32IM/ILP32, C23; exact commands in per-project logs",
        "counter_overhead_subtracted": False,
        "warmup_calls": 1,
        "cpu_mhz_scale": 1,
        "embench_revision": REVISION,
        "official_embench_score": False,
        "runs": [],
    }
    for name in names:
        project = root / "projects" / name
        digest = prepare_project(
            project, name, source, args.cycles, args.jtag_hardware
        )
        for repetition in range(args.repeats):
            action = (
                ["fpga", "--mode", "fast"]
                if args.backend == "fpga-fast"
                else [args.backend]
            )
            record = {
                "benchmark": name,
                "repetition": repetition,
                "source_sha256": digest,
                "status": "failed",
            }
            try:
                result = execute_sdk(
                    [
                        str(SDK / "scripts/rv32-project"),
                        "--project",
                        str(project),
                        *action,
                    ],
                    timeout=args.timeout,
                )
                log = root / f"{name}-{repetition}.log"
                log.write_text(result.stdout + "\nSTDERR:\n" + result.stderr)
                record["log"] = str(log)
                if result.returncode:
                    raise ValueError(
                        f"SDK exited with {result.returncode}; see {log}"
                    )
                if args.backend != "build":
                    record.update(parse_measurement(result.stdout))
                    record["seconds"] = (
                        record["cycles"] / args.cpu_hz if args.cpu_hz else None
                    )
                elf = next((project / "build").rglob(f"{name}.elf"))
                record["elf_sha256"] = hashlib.sha256(
                    elf.read_bytes()
                ).hexdigest()
                record["size_sections"] = output(
                    ["riscv32-unknown-elf-size", "-A", str(elf)]
                )
                record["sections_bytes"] = {
                    name: int(size)
                    for name, size in re.findall(
                        r"^(\.\S+)\s+(\d+)\s+\d+",
                        record["size_sections"],
                        re.M,
                    )
                }
                record["status"] = (
                    "built" if args.backend == "build" else "passed"
                )
            except (
                ValueError,
                OSError,
                StopIteration,
                subprocess.SubprocessError,
            ) as error:
                record["error"] = str(error)
            report["runs"].append(record)
            (root / "results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            print(f"{name} [{repetition}]: {record['status']}", flush=True)
    fields = [
        "benchmark",
        "repetition",
        "status",
        "cycles",
        "instructions",
        "cpi",
        "seconds",
        "error",
    ]
    with (root / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report["runs"])
    return int(any(item["status"] == "failed" for item in report["runs"]))


def main():
    """Fetch pinned sources explicitly, or run a selected benchmark subset."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch")
    fetch.add_argument("destination", type=Path)
    execute = commands.add_parser("run")
    execute.add_argument(
        "--source", type=Path, default=SDK / ".sdk/vendor/embench"
    )
    execute.add_argument(
        "--benchmarks",
        nargs="+",
        choices=["smoke", *WORKLOADS],
        default=["crc32", "edn", "matmult-int"],
    )
    execute.add_argument(
        "--backend",
        choices=["build", "simulate", "fpga-fast"],
        default="build",
    )
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument("--cpu-hz", type=int)
    execute.add_argument(
        "--jtag-hardware", help="Exact cable name from jtagconfig"
    )
    execute.add_argument("--repeats", type=int, default=1)
    execute.add_argument("--cycles", type=int, default=100_000_000)
    execute.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    try:
        if args.command == "fetch":
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--branch",
                    "embench-1.0",
                    "--depth",
                    "1",
                    URL,
                    str(args.destination),
                ],
                check=True,
                timeout=180,
            )
            check_source(args.destination)
            return 0
        return run(args)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Benchmark error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
