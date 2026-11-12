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


if __name__ == "__main__":
    main()
