"""Fingerprint the measurement contract and processor inputs."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
SOURCE_DIRS = ("src", "Core", "Memory", "Peripherals", "Common-Components")
SOURCE_SUFFIXES = {
    ".vhd",
    ".vhdl",
    ".yaml",
    ".yml",
    ".S",
    ".h",
    ".c",
    ".specs",
    ".ld",
    ".sh",
    ".json",
    ".hex",
    ".mif",
}
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "build",
    "sim_build",
    "db",
    "incremental_db",
    "output_files",
    "__pycache__",
}


def capture(arguments: list[str], root: Path) -> str:
    """Read a bounded tool identity or Git metadata value."""
    return subprocess.check_output(  # noqa: S603
        arguments, cwd=root, text=True, timeout=30
    ).strip()


def hash_files(root: Path, paths: list[Path]) -> str:
    """Hash sorted names and bytes, making renames significant."""
    result = hashlib.sha256()
    for path in sorted(paths):
        result.update(str(path.relative_to(root)).encode())
        result.update(b"\0")
        result.update(path.read_bytes())
        result.update(b"\0")
    return result.hexdigest()


def source_key(root: Path) -> str:
    """Include tracked RTL, profiles, platform maps and runtime."""
    paths: list[Path] = []
    for name in SOURCE_DIRS:
        for directory, folders, files in (root / name).walk():
            folders[:] = [
                folder for folder in folders if folder not in EXCLUDED_DIRS
            ]
            paths.extend(
                directory / file
                for file in files
                if Path(file).suffix in SOURCE_SUFFIXES
            )
    if not paths:
        raise ValueError("No processor inputs found")
    return hash_files(root, paths)


def contract(root: Path) -> dict[str, str]:
    """Identify the adapter and exact tools used."""
    paths = [
        p for p in HERE.iterdir() if p.suffix in {".py", ".in", ".c", ".yaml"}
    ]
    return {
        "adapter_sha256": hash_files(HERE, paths),
        "gcc": capture(
            ["riscv32-unknown-elf-gcc", "--version"], root
        ).splitlines()[0],
        "ghdl": capture(["ghdl", "--version"], root).splitlines()[0],
        "tools": Path("/opt/riscv-tools/.tag")
        .read_text(encoding="utf-8")
        .strip(),
        "image": os.environ.get("EMBENCH_IMAGE", "local"),
        "picolibc": Path("/opt/riscv-foundation/riscv32-elf/.picolibc.tag")
        .read_text(encoding="utf-8")
        .strip(),
        "memory": "modular/internal-ROM/internal-RAM/no-caches",
        "workload": "ci",
        "measurement": "retire-PC-markers/core-clock/v1",
    }


def metadata(root: Path) -> dict[str, Any]:
    """Separate target revision from its content fingerprint."""
    return {
        "revision": capture(["git", "rev-parse", "HEAD"], root),
        "submodules": "\n".join(
            " ".join(line.split()[:2])
            for line in capture(
                ["git", "submodule", "status", "--recursive"], root
            ).splitlines()
        ),
        "source_sha256": source_key(root),
        "contract": contract(root),
    }


def cache_key(value: dict[str, Any], profile: str) -> str:
    """Build a cache key from measured inputs."""
    payload = [value["source_sha256"], value["contract"], profile]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
