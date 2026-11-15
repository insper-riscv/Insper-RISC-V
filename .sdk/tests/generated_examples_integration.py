"""Build standalone vendor examples and execute the modular ones on CPU RTL."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]


def invoke(root: Path, action: str) -> bytes:
    """Run the public SDK command and expose diagnostics only on failure."""
    result = subprocess.run(
        [str(SDK / "scripts/rv32-project"), "--project", str(root), action],
        env=dict(os.environ, RV32_SDK_ROOT=str(SDK)),
        capture_output=True,
        timeout=240,
    )
    if result.returncode or result.stderr:
        print(root, action, result.returncode, result.stdout, result.stderr)
        log = root / "logs/rv32" / f"{action}-latest.log"
        if log.exists():
            print(log.read_text()[-8000:])
        raise SystemExit(1)
    return result.stdout


def generate(root: Path, platform: str, profile: str) -> list[Path]:
    """Prepare a parent project and read the generated example project list."""
    shutil.copytree(SDK / "templates/common", root, dirs_exist_ok=True)
    shutil.copytree(SDK / "templates/c", root, dirs_exist_ok=True)
    (root / "rv32.toml").write_text(
        '[project]\nname="examples"\nlanguage="c"\n'
        f'platform="{platform}"\ncpu_profile="{profile}"\n'
        'generate_drivers=true\nsource="src/main.c"\n'
    )
    invoke(root, "drivers")
    manifest = json.loads((root / "vendor/.rv32-drivers.json").read_text())
    return [root / name for name in manifest["example_projects"]]


def main() -> None:
    """Exercise six modular drivers and compile all five DE0-CV examples."""
    with tempfile.TemporaryDirectory(
        prefix="generated driver examples "
    ) as temp:
        folder = Path(temp)
        modular = generate(folder / "modular", "modular", "rv32im_zicsr_irq")
        assert len(modular) == 6
        for root in modular:
            name = root.parent.name
            output = invoke(root, "simulate")
            assert output == f"{name} example: PASS\n".encode(), (name, output)
            child = json.loads(
                (root / "vendor/.rv32-drivers.json").read_text()
            )
            assert child["example_projects"] == []
            print("PASS standalone simulation", name, flush=True)
        invoke(folder / "modular", "drivers")
        internal = generate(folder / "internal", "internal-mem", "auto")
        assert len(internal) == 1
        assert invoke(internal[0], "simulate") == b"UART example: PASS\n"
        invoke(folder / "internal", "drivers")
        print(
            "PASS standalone simulation internal-memory serial UART",
            flush=True,
        )
        physical = generate(folder / "de0-cv", "de0-cv", "auto")
        assert len(physical) == 5
        for root in physical:
            invoke(root, "build")
            print("PASS standalone build", root.parent.name, flush=True)


if __name__ == "__main__":
    main()
