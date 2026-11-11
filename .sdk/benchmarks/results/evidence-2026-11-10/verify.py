"""Verify evidence bytes and restore historical scripts in a separate directory."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def inventory(root):
    """Hash every packaged file except the checksum ledger itself."""
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and p.name != "SHA256SUMS.json"
        and "__pycache__" not in p.parts
    }


def verify(root):
    """Reject missing, unexpected or modified evidence files."""
    manifest = json.loads((root / "SHA256SUMS.json").read_text())
    if manifest != inventory(root):
        raise ValueError("Evidence inventory or SHA-256 mismatch")
    print(f"Verified {len(manifest)} evidence files")


def restore(root, destination):
    """Copy verified evidence to a new directory and restore script names."""
    verify(root)
    destination = destination.resolve()
    if destination.is_relative_to(root.resolve()):
        raise ValueError(
            "Restore destination must be outside the evidence directory"
        )
    shutil.copytree(
        root, destination, ignore=shutil.ignore_patterns("__pycache__")
    )
    for path in destination.rglob("*.py.snapshot"):
        target = path.with_suffix("")
        if target.exists():
            raise ValueError(f"Restored path already exists: {target}")
        path.rename(target)
    (destination / "SHA256SUMS.json").write_text(
        json.dumps(inventory(destination), indent=2) + "\n"
    )
    verify(destination)


def main():
    """Validate this package or materialize a runnable copy without overwrites."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restore",
        type=Path,
        help="new external directory for runnable scripts",
    )
    args = parser.parse_args()
    if args.restore:
        restore(ROOT, args.restore)
    else:
        verify(ROOT)


if __name__ == "__main__":
    main()
