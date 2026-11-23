"""Opt-in real C/Rust export, cross-compilation and relocation check.

Run in the SDK tooling image with the RISC-V compiler, Rust targets and libclang.
The output directory must be new; it retains the generated projects as evidence.
"""

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import yaml

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
audit = args.output.resolve()
if audit.is_relative_to(root):
    parser.error("--output must be outside the SDK checkout")
audit.mkdir(parents=True, exist_ok=False)
spec = importlib.util.spec_from_file_location(
    "exporter", root / ".sdk/export_workspace.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
archive = audit / "sdk.tar.gz"
mod.bundle(root, archive)
unpack = audit / "bundle"
unpack.mkdir(exist_ok=True)
with tarfile.open(archive) as t:
    t.extractall(unpack, filter="data")
source = unpack / "sdk"
env = dict(
    os.environ,
    UV_PROJECT_ENVIRONMENT=str(audit / "python-env"),
    UV_CACHE_DIR=str(audit / "uv-cache"),
    CARGO_BUILD_JOBS="2",
)
env.pop("PYTHONPATH", None)


def run(args, cwd):
    print("+", *map(str, args), flush=True)
    result = subprocess.run(
        list(map(str, args)),
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=480,
    )
    logs = audit / "logs"
    logs.mkdir(exist_ok=True)
    (logs / f"build-{len(list(logs.glob('*.log'))) + 1}.log").write_text(
        result.stdout
    )
    print(result.stdout[-12000:], flush=True)
    if result.returncode:
        raise RuntimeError(f"exit {result.returncode}")


for language in ("c", "rust"):
    project = audit / (language + " project")
    hardware = project / "Insper-RISC-V"
    assert not project.exists()
    shutil.copytree(
        root,
        hardware,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "tools",
            "__pycache__",
            ".board-views",
            ".board-views.lock",
            "target",
            "build",
            "*.egg-info",
            ".ruff_cache",
            ".tools-backup-*",
        ),
    )
    mod.hardware(
        source,
        project,
        hardware,
        [
            "new-project",
            "--new",
            "test-" + language,
            "--board",
            "de2-115",
            "--repo",
            str(hardware),
            "--no-generate",
        ],
    )
    manifest = yaml.safe_load((project / "project.yaml").read_text())
    print("manifest", manifest, flush=True)
    platform = next(
        p
        for p in (hardware / "src").glob("*/*/platform.yaml")
        if "created by `riscv-tools new-project`" in p.read_text()
    )
    data = yaml.safe_load(platform.read_text())
    data["peripherals"] = {
        "CLINT": {"base": 0xE0000000, "size": "64K"},
        "PLIC": {"base": 0xF0000000, "size": "4M"},
        "LEDS": {
            "kind": "gpio",
            "role": "leds",
            "base": 0x80001000,
            "groups": [list(range(18))],
        },
        "EXTRA": {
            "kind": "gpio",
            "role": "gpio",
            "base": 0x80002000,
            "groups": [[8, 9]],
        },
    }
    platform.write_text(yaml.safe_dump(data, sort_keys=False))
    result = mod.create(
        source,
        project,
        hardware,
        str(platform.relative_to(hardware)),
        language,
    )
    print(json.dumps(result), flush=True)
    header = (project / "vendor/rv32_platform.h").read_text()
    assert "0x80001000" in header and "0x80002000" in header
    run(
        [
            "bash",
            hardware / "scripts/rv32-project",
            "--debug",
            "--project",
            project,
            "build",
        ],
        hardware,
    )
    # A second location must invalidate absolute generated paths and remain buildable.
    moved = project.with_name(language + " moved")
    assert not moved.exists()
    project.rename(moved)
    hardware = moved / "Insper-RISC-V"
    run(
        [
            "bash",
            hardware / "scripts/rv32-project",
            "--debug",
            "--project",
            moved,
            "build",
        ],
        hardware,
    )
    run(
        [
            "bash",
            hardware / "scripts/rv32-project",
            "--project",
            moved / "vendor/GPIO/example",
            "build",
        ],
        hardware,
    )
    print(language, "EXPORT, RELOCATION AND CHILD EXAMPLE PASS", flush=True)
(audit / "result.json").write_text(
    json.dumps(
        {
            "status": "passed",
            "languages": ["c", "rust"],
            "checks": [
                "hardware creation",
                "two GPIO instances",
                "cross compilation",
                "relocation",
                "GPIO child example",
            ],
        },
        indent=2,
    )
    + "\n"
)
print("ALL INTEGRATION CHECKS PASSED", flush=True)
