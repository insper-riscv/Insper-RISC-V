"""Real C compiler/GHDL acceptance for every named Core CPU profile."""

import json
import os
import pathlib
import subprocess
import tempfile

sdk = pathlib.Path(__file__).resolve().parents[2]
env = dict(os.environ, RV32_SDK_ROOT=str(sdk))
with tempfile.TemporaryDirectory(prefix="sdk profile ") as temporary:
    root = pathlib.Path(temporary)
    (root / "src").mkdir()
    (root / "src/main.c").write_text(
        '#include <stdio.h>\nvolatile int a=42,b=6; int main(void){int n=a/b; printf("profile=%d\\n",n); return n!=7;}\n'
    )
    rows = []
    for path in sorted((sdk / "Core/profiles").glob("rv32*.yaml")):
        (root / "rv32.toml").write_text(
            '[project]\nname="probe"\nlanguage="c"\ncpu_profile='
            + json.dumps(path.stem)
            + "\n"
        )
        result = subprocess.run(
            [
                str(sdk / "scripts/rv32-project"),
                "--project",
                str(root),
                "simulate",
            ],
            env=env,
            capture_output=True,
            timeout=240,
        )
        if (
            result.returncode
            or result.stdout != b"profile=7\n"
            or result.stderr
        ):
            print(
                path.stem,
                result.returncode,
                result.stdout,
                result.stderr,
                flush=True,
            )
            log = root / "logs/rv32/simulate-latest.log"
            if log.exists():
                print(log.read_text()[-8000:])
            raise SystemExit(1)
        print("PASS", path.stem, flush=True)
        rows.append(path.stem)
