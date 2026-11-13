"""Rust binding failures should identify missing host tools before Cargo panics."""

import os
import subprocess
import unittest
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]


class RustBuildDependenciesTest(unittest.TestCase):
    def test_missing_compiler_reports_rebuild_and_native_host_options(self):
        result = subprocess.run(
            ["bash", str(SDK / "scripts/rust-build-deps.sh"), "--check"],
            env=dict(os.environ, CLANG_PATH="rv32-test-missing-clang"),
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Clang and libclang", result.stderr)
        self.assertIn("Rebuild the Dev Container", result.stderr)
        self.assertIn("LIBCLANG_PATH", result.stderr)
        self.assertEqual(result.stdout, "")
