"""Content-addressed bitstreams for the SDK's internal-memory platform."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

GENERATED = {
    ".git",
    "db",
    "incremental_db",
    "output_files",
    "tools",
    "tests",
    "docs",
    "__pycache__",
    ".venv",
    "build",
    "logs",
}
SUFFIXES = {
    ".vhd",
    ".vhdl",
    ".v",
    ".sv",
    ".vh",
    ".svh",
    ".qsf",
    ".qpf",
    ".qip",
    ".ip",
    ".qsys",
    ".sdc",
    ".tcl",
    ".mif",
    ".hex",
    ".coe",
    ".qdf",
    ".yaml",
    ".s",
    ".ld",
    ".h",
}


def cache_root() -> Path:
    return Path(
        os.environ.get(
            "RV32_SOF_CACHE_DIR",
            str(
                Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
                / "rv32"
                / "sof"
            ),
        )
    )


def fingerprint(sdk: Path, cfg: dict, version: str | None = None) -> str:
    if version is None:
        version = subprocess.check_output(
            ["quartus_sh", "--version"], text=True, timeout=20
        )
    digest = hashlib.sha256()
    quartus_cfg = dict(cfg["quartus"])
    quartus_cfg["project_dir"] = (
        "<project-profile>"
        if cfg.get("sdk_cpu_profile")
        else str(
            (sdk / cfg["quartus"]["project_dir"])
            .resolve()
            .relative_to(sdk.resolve())
        )
    )
    digest.update(
        json.dumps(
            {
                "schema": 6,
                "cpu_profile": cfg.get("sdk_cpu_profile"),
                "hardware_inputs": cfg.get("sdk_hardware_inputs"),
                "quartus": version,
                "memory": cfg["memory"],
                "quartus_config": quartus_cfg,
            },
            sort_keys=True,
        ).encode()
    )
    project_dir = (sdk / cfg["quartus"]["project_dir"]).resolve()
    dynamic = {
        project_dir / cfg["quartus"]["rom_mif_target"],
        project_dir
        / cfg["quartus"].get("boot_memory_mif_target", "boot_memory_init.mif"),
    }
    for tree in (
        "Core",
        "Memory",
        "Peripherals",
        "Common-Components",
        "src",
        ".sdk/platforms",
    ):
        for directory, dirs, files in os.walk(sdk / tree):
            dirs[:] = sorted(
                d
                for d in dirs
                if d not in GENERATED
                and not (
                    d == "simulation" and Path(directory).name == "quartus"
                )
            )
            for name in sorted(files):
                path = Path(directory) / name
                if (
                    path.suffix.lower() not in SUFFIXES
                    or path.resolve() in dynamic
                ):
                    continue
                digest.update(str(path.relative_to(sdk)).encode() + b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
    profile_builder = sdk / ".sdk/rv32_sdk/cpu_profiles.py"
    if profile_builder.is_file():
        digest.update(b"cpu-profile-builder\0" + profile_builder.read_bytes())
    # Build-flow changes may change the synthesized ROM or compiler invocation.
    for relative in (
        "boot_memory/core.py",
        "quartus_program/core.py",
        "orchestrator/jtag_run.py",
    ):
        path = sdk / ".sdk/tools/src/riscv_tools" / relative
        if path.is_file():
            digest.update(relative.encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def restore(key: str, destination: Path) -> bool:
    entry = cache_root() / key
    try:
        data = (entry / "design.sof").read_bytes()
        metadata = json.loads((entry / "manifest.json").read_text())
        if not data or metadata != {
            "key": key,
            "sha256": hashlib.sha256(data).hexdigest(),
        }:
            return False
    except OSError, ValueError:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return True


def store(key: str, source: Path) -> None:
    data = source.read_bytes()
    if not data:
        raise ValueError("Quartus produced an empty bitstream")
    root = cache_root()
    root.mkdir(parents=True, exist_ok=True)
    entry = root / key
    with tempfile.TemporaryDirectory(dir=root) as temporary:
        temp = Path(temporary)
        (temp / "design.sof").write_bytes(data)
        (temp / "manifest.json").write_text(
            json.dumps(
                {"key": key, "sha256": hashlib.sha256(data).hexdigest()}
            )
        )
        # Callers hold the shared hardware lock, including across projects.
        entry.mkdir(exist_ok=True)
        os.replace(temp / "design.sof", entry / "design.sof")
        os.replace(temp / "manifest.json", entry / "manifest.json")
