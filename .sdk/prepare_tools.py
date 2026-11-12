"""Prepare the SDK's pinned Tools dependency without changing upstream checkouts."""

import fcntl
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


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
        if marker.exists() and json.loads(marker.read_text()) == expected:
            return
        if target.exists():
            raise SystemExit(
                "SDK Tools dependency changed. Move .sdk/tools aside and rerun; it will not be overwritten."
            )
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
                staging.rename(target)
        except (subprocess.SubprocessError, OSError) as error:
            raise SystemExit(f"SDK Tools setup failed; see {log}") from error


if __name__ == "__main__":
    main()
