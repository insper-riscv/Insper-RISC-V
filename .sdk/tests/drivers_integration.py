"""Compile vendored C drivers and exercise actual modular CPU/peripheral RTL."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]
CASES = {
    "gpio": b"GPIO constructors, pin indices, read-clear IRQ and two instances: PASS\n",
    "peripherals": b"TIMER, serial/JTAG UART and DISPLAY: PASS\n",
}


def exercise_example(name: str, expected: bytes) -> None:
    """Use the public project command and require exact application output."""
    with tempfile.TemporaryDirectory(prefix="driver app ") as temporary:
        root = Path(temporary) / "app"
        shutil.copytree(
            SDK / "examples" / name,
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
            output = expected
            if name == "peripherals" and profile == "rv32im_zicsr_irq":
                output += b"CLINT and PLIC/GPIO: PASS\n"
            if result.returncode or result.stdout != output or result.stderr:
                print(
                    name,
                    profile,
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )
                log = root / "logs/rv32/simulate-latest.log"
                if log.exists():
                    print(log.read_text()[-8000:])
                raise SystemExit(1)
            print("PASS", name, "C drivers on", profile, flush=True)


def main() -> None:
    """Check both examples on arithmetic and interrupt-capable profiles."""
    for name, expected in CASES.items():
        exercise_example(name, expected)


if __name__ == "__main__":
    main()
