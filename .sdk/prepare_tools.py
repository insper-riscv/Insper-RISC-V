"""Prepare the SDK's pinned Tools dependency without changing upstream checkouts."""

import fcntl
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parent


def activate(staging: Path, target: Path, output: TextIO) -> None:
    """Keep the old checkout until its replacement is ready, then preserve it."""
    previous = None
    if target.exists() or target.is_symlink():
        backup = Path(tempfile.mkdtemp(prefix=".tools-backup-", dir=ROOT))
        previous = backup / "tools"
        target.rename(previous)
        print(
            f"Previous Tools preserved at {previous}", file=output, flush=True
        )
    try:
        staging.rename(target)
    except OSError:
        if previous is not None:
            previous.rename(target)
            print(
                "Restored previous Tools after activation failure", file=output
            )
        raise


def main() -> None:
    """Fetch the pinned revision and apply the reviewed SDK compatibility patch."""
    dependency = json.loads((ROOT / "dependencies.json").read_text())["tools"]
    patch = ROOT / "patches/tools-sdk.patch"
    expected = {
        **dependency,
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
    }
    target = ROOT / "tools"
    with (ROOT / ".tools-prepare.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = target / ".rv32-sdk.json"
        try:
            if json.loads(marker.read_text()) == expected:
                return
        except OSError, ValueError:
            # An incomplete/old cache is replaced only after a successful build.
            pass
        log = ROOT / ".tools-bootstrap.log"
        try:
            with (
                tempfile.TemporaryDirectory(
                    prefix=".tools-", dir=ROOT
                ) as temporary,
                log.open("w") as output,
            ):
                staging = Path(temporary) / "tools"
                staging.mkdir()
                commands = [
                    ["git", "init", "--quiet"],
                    ["git", "remote", "add", "origin", dependency["url"]],
                    [
                        "git",
                        "fetch",
                        "--quiet",
                        "--depth",
                        "1",
                        "origin",
                        dependency["revision"],
                    ],
                    ["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"],
                    ["git", "apply", "--check", str(patch)],
                    ["git", "apply", str(patch)],
                ]
                for command in commands:
                    subprocess.run(
                        command,
                        cwd=staging,
                        stdout=output,
                        stderr=subprocess.STDOUT,
                        check=True,
                        timeout=180,
                    )
                (staging / ".rv32-sdk.json").write_text(
                    json.dumps(expected, sort_keys=True) + "\n"
                )
                activate(staging, target, output)
        except (subprocess.SubprocessError, OSError) as error:
            with log.open("a") as output:
                print(f"Tools preparation failed: {error}", file=output)
            raise SystemExit(f"SDK Tools setup failed; see {log}") from error


if __name__ == "__main__":
    main()
