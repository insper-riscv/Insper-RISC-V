#!/usr/bin/env python3
"""Create an independent C or Rust project from the RV32 SDK templates."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

SDK_ROOT = Path(__file__).resolve().parents[2]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("language", choices=["c", "rust"])
    result.add_argument("destination", type=Path)
    return result


def main() -> None:
    args = parser().parse_args()
    destination = args.destination.expanduser().resolve()
    common = SDK_ROOT / "templates" / "common"
    template = SDK_ROOT / "templates" / args.language
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"Destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(common, destination, dirs_exist_ok=True)
    shutil.copytree(template, destination, dirs_exist_ok=True)
    print(f"Created {args.language.upper()} project at {destination}")
    print("Open the directory in VS Code and reopen it in the Dev Container.")


if __name__ == "__main__":
    main()
