"""Generate an SDK-only runtime view without modifying normal processor platforms."""

import fcntl
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml


def ensure_internal_mem(sdk: Path) -> Path:
    """Build the pinned runtime view once, preserving upstream stdio and tests."""
    home = sdk / ".sdk"
    inputs = json.loads((home / "platform-inputs.json").read_text())
    for name, digest in inputs.items():
        if hashlib.sha256((sdk / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(
                f"SDK platform input changed: {name}; refresh the SDK platform integration before using it"
            )
    patch = home / "patches/platform-sdk.patch"
    expected = {
        "inputs": inputs,
        "patch": hashlib.sha256(patch.read_bytes()).hexdigest(),
    }
    destination = home / "platforms/internal-mem"
    with (home / ".views.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = destination / ".sdk-view.json"
        if marker.exists() and json.loads(marker.read_text()) == expected:
            return destination
        base = sdk / "src/simulation/internal-mem"
        with tempfile.TemporaryDirectory(
            prefix=".platform-", dir=home
        ) as temporary:
            stage = Path(temporary) / "internal-mem"
            shutil.copytree(base / "runtime", stage / "runtime")
            shutil.copytree(
                base / "testbench",
                stage / "testbench",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            log = home / ".views-bootstrap.log"
            with log.open("w") as output:
                subprocess.run(
                    ["git", "apply", "--no-index", str(patch)],
                    cwd=stage,
                    check=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
                platform = yaml.safe_load((base / "platform.yaml").read_text())
                platform["reserved"]["stdout"] = {
                    "base": platform["reserved"]["tohost"]["base"] - 65536 - 8,
                    "size": "64K+8",
                }
                platform["checks"] = []
                platform["generate"] = {
                    key: {
                        **value,
                        "path": str(
                            stage / "runtime" / Path(value["path"]).name
                        ),
                    }
                    for key, value in platform["generate"].items()
                    if key in ("specs", "boot_ld", "runtime")
                }
                platform_file = stage / "platform.yaml"
                platform_file.write_text(
                    yaml.safe_dump(platform, sort_keys=False)
                )
                subprocess.run(
                    [
                        "riscv-tools",
                        "--root",
                        str(sdk),
                        "generate-memory-map",
                        "--platform",
                        str(platform_file),
                    ],
                    check=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
            # Remove temporary generator paths from comments for reproducible outputs.
            for source in (stage / "runtime").iterdir():
                text = source.read_text()
                text = text.replace(str(stage), str(destination)).replace(
                    str(stage.relative_to(sdk)), ".sdk/platforms/internal-mem"
                )
                source.write_text(text)
            for value in platform["generate"].values():
                value["path"] = (
                    ".sdk/platforms/internal-mem/runtime/"
                    + Path(value["path"]).name
                )
            platform_file.write_text(yaml.safe_dump(platform, sort_keys=False))
            (stage / "config.yaml").write_text(
                yaml.safe_dump(
                    {
                        "extends": "../../../src/simulation/internal-mem/config.yaml",
                        "memory_map": "platform.yaml",
                        "toolchain": {
                            "specs": ".sdk/platforms/internal-mem/runtime/rv32im-fpga.specs"
                        },
                        "paths": {
                            "boot_memory": ".sdk/platforms/internal-mem/runtime/boot_memory.S",
                            "boot_memory_linker_script": ".sdk/platforms/internal-mem/runtime/boot_memory.ld",
                        },
                        "sim": {
                            "python_path": [".sdk/platforms/internal-mem"]
                        },
                    },
                    sort_keys=False,
                )
            )
            (stage / ".sdk-view.json").write_text(
                json.dumps(expected, sort_keys=True) + "\n"
            )
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                shutil.rmtree(destination)
            stage.rename(destination)
    return destination
