"""Copy untrusted sources inside the offline compiler container."""

import argparse
import json
import shutil
from pathlib import Path

from benchmarks.embench import hardware_build, run


def main() -> None:
    """Copy read-only inputs inside the isolated compiler."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--workload", choices=("ci", "full"), required=True)
    args = parser.parse_args()
    target = Path("/work/target")
    shutil.copytree("/input", target, symlinks=True)
    options = argparse.Namespace(
        root=target,
        upstream=Path("/upstream"),
        output=Path("/work/build"),
        profile=args.profile,
        workload=args.workload,
        programs=None,
    )
    if not (target / "Core/profiles" / f"{args.profile}.yaml").is_file():
        write_absent(options)
        return
    previous = Path("/previous/hardware-manifest.json")
    if previous.is_file():
        identity = hardware_build.identity(target)
        old = json.loads(previous.read_text(encoding="utf-8"))
        if (
            old["profile"] == args.profile
            and old["provenance"]["source_sha256"] == identity["source_sha256"]
            and old["provenance"]["contract"] == identity["contract"]
            and old["suite"]["workload"] == args.workload
        ):
            shutil.copytree("/previous", options.output)
            (options.output / "results.json").unlink(missing_ok=True)
            old["provenance"] = identity
            run.write_json(options.output / previous.name, old)
            return
    hardware_build.build(options)


def write_absent(args: argparse.Namespace) -> None:
    """Record a named profile absent from this revision."""
    suite = run.read_yaml(run.HERE / "suite.yaml")
    suite.update(platform=str(hardware_build.PLATFORM), workload=args.workload)
    args.output.mkdir()
    run.write_json(
        args.output / "results.json",
        {
            "schema": 1,
            "backend": "fpga",
            "profile": args.profile,
            "profile_available": False,
            "suite": suite,
            "provenance": hardware_build.identity(args.root),
            "results": [
                {"program": name, "status": "profile unavailable"}
                for name in suite["programs"]
            ],
        },
    )


if __name__ == "__main__":
    main()
