"""Verify terminal output, subprocess diagnostics and failure status end to end."""

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]


class QuietOutputTest(unittest.TestCase):
    def invoke(self, root: Path, debug: bool = False, fail: bool = False):
        script = f"""
import sys, subprocess
sys.path.insert(0, {str(ROOT / "scripts")!r})
import rv32_sdk.cli as project

def execute(*args):
    print("tool diagnostic")
    subprocess.run([sys.executable, "-c", "import sys; print('child warning', file=sys.stderr)"], check=True)
    project.emit_program_output(b"hello\\n")
    if {fail!r}:
        raise subprocess.CalledProcessError(7, ["compiler"])
project.execute = execute
sys.argv = ["rv32-project", "--project", {str(root)!r}, "simulate"] + {["--debug"] if debug else []!r}
project.main()
"""
        return subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={**os.environ, "RV32_SDK_ROOT": str(ROOT)},
            check=False,
        )

    def test_default_stdout_excludes_parent_and_child_diagnostics(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rv32.toml").write_text('[project]\nlanguage="c"\n')
            result = self.invoke(root)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "hello\n")
            self.assertEqual(result.stderr, "")
            log = (root / "logs/rv32/simulate-latest.log").read_text()
            self.assertIn("tool diagnostic", log)
            self.assertIn("child warning", log)

    def test_debug_shows_diagnostics_and_program_output(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rv32.toml").write_text('[project]\nlanguage="c"\n')
            result = self.invoke(root, debug=True)
            self.assertEqual(result.returncode, 0)
            self.assertIn("tool diagnostic", result.stdout)
            self.assertIn("hello\n", result.stdout)
            self.assertIn("child warning", result.stderr)

    def test_failure_preserves_stdout_and_exit_code_and_links_full_log(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "rv32.toml").write_text('[project]\nlanguage="c"\n')
            result = self.invoke(root, fail=True)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout, "hello\n")
            self.assertIn("simulate failed", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertIn(
                "Traceback",
                (root / "logs/rv32/simulate-latest.log").read_text(),
            )
