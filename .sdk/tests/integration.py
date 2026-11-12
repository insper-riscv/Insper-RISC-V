"""End-to-end CLI checks; run inside the development image, without an FPGA."""

import subprocess
import tempfile
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]
CLI = SDK / "scripts/rv32-project"


def main():
    """Compile and simulate real programs, checking exact bytes and failures."""
    with tempfile.TemporaryDirectory(prefix="rv32 integration ") as temporary:
        root = Path(temporary)
        (root / "src").mkdir()
        (root / "header files").mkdir()
        (root / "header files/value.h").write_text("int value(void);\n")
        (root / "src/value.c").write_text("int value(void) { return 42; }\n")
        manifest = root / "rv32.toml"
        config = """[project]
name = "integration"
language = "c"
source = "src/main.c"
sources = ["src/value.c"]
include_dirs = ["header files"]
simulation_timeout_cycles = 2000000
"""
        manifest.write_text(config)
        source = root / "src/main.c"

        def run(name, code, expected, *, success=True, debug=False):
            source.write_text(code)
            command = [str(CLI), "--project", str(root), "simulate"]
            if debug:
                command.append("--debug")
            result = subprocess.run(command, capture_output=True, timeout=180)
            assert (result.returncode == 0) == success, (
                name,
                result.returncode,
                result.stderr,
                (root / "logs/rv32/simulate-latest.log").read_text()[-4000:],
            )
            if debug:
                assert b"Simulation limit:" in result.stdout, name
                assert expected in result.stdout, name
            else:
                assert result.stdout == expected, (name, result.stdout[:200])
                if success:
                    assert result.stderr == b"", (name, result.stderr)
                else:
                    assert b"Details:" in result.stderr, name
            print(f"PASS: {name}", flush=True)

        run(
            "headers, second source, malloc and no newline",
            """
#include <stdio.h>
#include <stdlib.h>
#include "value.h"
int main(void) {
    int *p = malloc(sizeof(int));
    if (!p) return 1;
    *p = value(); printf("value=%d", *p); free(p); return 0;
}
""",
            b"value=42",
        )
        run(
            "no stdout and no stale output",
            "int main(void) {return 0;}\n",
            b"",
        )
        run(
            "1200 lines beyond old buffer",
            """
#include <stdio.h>
int main(void) { for(int i=0;i<1200;i++) puts("x"); return 0; }
""",
            b"x\n" * 1200,
        )
        run(
            "debug diagnostics",
            '#include <stdio.h>\nint main(void) {puts("debug");return 0;}\n',
            b"debug\n",
            debug=True,
        )
        run("compiler failure", "invalid C here\n", b"", success=False)
        run(
            "nonzero exit",
            "int main(void) { return 7; }\n",
            b"",
            success=False,
        )
        manifest.write_text(config.replace("2000000", "1000"))
        run(
            "bounded infinite loop",
            "int main(void) {for(;;){};}\n",
            b"",
            success=False,
        )
        print("All 7 CLI integration checks passed.", flush=True)


if __name__ == "__main__":
    main()
