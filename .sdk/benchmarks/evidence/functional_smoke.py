"""Verify one original inner iteration in GHDL; never report an Embench score."""

import json
import sys
from pathlib import Path

from rv32_sdk.bench import SDK, execute_sdk, parse_measurement, prepare_project


def main():
    """Exercise complete algorithms with their original verifier at short scale."""
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    records = []
    for name in sys.argv[2:] or [
        "nettle-sha256",
        "slre",
        "statemate",
        "huffbench",
    ]:
        project = root / name
        prepare_project(project, name, SDK / ".sdk/vendor/embench", 2_000_000)
        wrapper = project / "src/workload0.c"
        with wrapper.open("a") as source:
            source.write(
                "\nint evidence_once(void) { return benchmark_body(1); }\n"
            )
        main_file = project / "src/main.c"
        main_file.write_text(
            main_file.read_text()
            .replace(
                "extern int benchmark(void);",
                "extern int evidence_once(void);",
            )
            .replace(
                "int value = benchmark();", "int value = evidence_once();"
            )
        )
        if name == "huffbench":
            main_file.write_text(
                main_file.read_text().replace(
                    "warm_caches(1);", "/* correctness-only: no warm-up */"
                )
            )
        record = dict(
            workload=name,
            scope="Functional verification of one inner iteration; not full-scale benchmark performance",
            status="failed",
            warmup_calls=0 if name == "huffbench" else 1,
            body_iterations=1,
        )
        try:
            result = execute_sdk(
                [
                    str(SDK / "scripts/rv32-project"),
                    "--project",
                    str(project),
                    "simulate",
                ],
                180,
            )
            (root / f"{name}.log").write_text(
                result.stdout + "\nSTDERR:\n" + result.stderr
            )
            assert result.returncode == 0, result.stderr
            record["instrumentation_record"] = parse_measurement(result.stdout)
            record["status"] = "passed"
        except Exception as error:
            record["error"] = str(error)
        records.append(record)
        (root / "results.json").write_text(
            json.dumps(records, indent=2) + "\n"
        )
        print("FUNCTIONAL", name, record["status"], flush=True)
    if any(row["status"] != "passed" for row in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
