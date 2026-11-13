"""Compare efficient storage against the original models."""

import argparse
from pathlib import Path

from benchmarks.embench.run import HERE, command


def check(root: Path, output: Path) -> None:
    """Check byte masks, enables and simultaneous accesses."""
    output.mkdir(parents=True, exist_ok=True)
    (output / "image.hex").write_text(
        "".join(f"{(n * 0x1020304) & 0xFFFFFFFF:08x}\n" for n in range(64))
    )
    sources = [root / "Common-Components/src/utils_pkg.vhd"]
    for kind in ("RAM", "ROM"):
        name = kind.lower()
        path = root / f"Memory/src/{kind}/SoC/{name}_simulation.vhd"
        text = path.read_text()
        reference = output / f"{name}_reference.vhd"
        reference.write_text(
            text.replace(f"{name}_simulation", f"{name}_reference")
        )
        efficient = output / f"{name}_efficient.vhd"
        entity = text.split("architecture rtl of ", 1)[0]
        efficient.write_text(entity + (HERE / f"{name}.vhd.in").read_text())
        sources.extend([reference, efficient])
    top = output / "storage_check.vhd"
    top.write_text((HERE / "storage_check.vhd.in").read_text())
    sources.append(top)
    log = output / "storage.log"
    command(["ghdl", "-a", "--std=08", *map(str, sources)], output, log)
    command(["ghdl", "--elab-run", "--std=08", "storage_check"], output, log)


def main() -> None:
    """Execute the storage equivalence regression independently."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check(args.root.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
