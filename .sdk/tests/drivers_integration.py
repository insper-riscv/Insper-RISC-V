"""Compile the vendored C driver and exercise the real modular CPU/GPIO RTL."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]
EXPECTED = (
    b"GPIO set/clear/toggle, pins, IRQ read-clear and two instances: PASS\n"
)


def main() -> None:
    """Verify arithmetic and interrupt-capable CPU configurations with exact output."""
    with tempfile.TemporaryDirectory(prefix="gpio app ") as temporary:
        root = Path(temporary) / "app"
        shutil.copytree(
            SDK / "examples/gpio",
            root,
            ignore=shutil.ignore_patterns(".rv32", "build", "logs", "vendor"),
        )
        original = (root / "rv32.toml").read_text()
        for profile in ("rv32i", "rv32im", "rv32im_zicsr_irq"):
            (root / "rv32.toml").write_text(
                original.replace(
                    'cpu_profile = "rv32im"', f'cpu_profile = "{profile}"'
                )
            )
            result = subprocess.run(
                [
                    str(SDK / "scripts/rv32-project"),
                    "--project",
                    str(root),
                    "simulate",
                ],
                env=dict(os.environ, RV32_SDK_ROOT=str(SDK)),
                capture_output=True,
                timeout=240,
            )
            if result.returncode or result.stdout != EXPECTED or result.stderr:
                print(profile, result.returncode, result.stdout, result.stderr)
                log = root / "logs/rv32/simulate-latest.log"
                if log.exists():
                    print(log.read_text()[-8000:])
                raise SystemExit(1)
            print("PASS GPIO C driver on", profile, flush=True)


if __name__ == "__main__":
    main()
