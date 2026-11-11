"""Validate benchmark measurements before they enter a report."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rv32_sdk.bench import parse_measurement, prepare_project


class BenchmarkTest(unittest.TestCase):
    def test_exact_verified_measurement(self):
        self.assertEqual(
            parse_measurement(
                "RV32BENCH cycles=100 instructions=50 verified=1\n"
            ),
            {"cycles": 100, "instructions": 50, "cpi": 2.0},
        )

    def test_invalid_or_duplicate_measurements_are_rejected(self):
        for text in [
            "",
            "RV32BENCH cycles=0 instructions=5 verified=1",
            "RV32BENCH cycles=5 instructions=0 verified=1",
            "RV32BENCH cycles=5 instructions=2 verified=0",
            "RV32BENCH cycles=5 instructions=2 verified=1\n" * 2,
        ]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_measurement(text)

    def test_smoke_project_does_not_need_embench(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            digest = prepare_project(root, "smoke", root / "missing", 200000)
            self.assertEqual(len(digest), 64)
            self.assertIn(
                "simulation_timeout_cycles = 200000",
                (root / "rv32.toml").read_text(),
            )

    def test_timeout_kills_the_sdk_process_group(self):
        import subprocess
        import sys

        from rv32_sdk.bench import execute_sdk

        with self.assertRaises(subprocess.TimeoutExpired):
            execute_sdk(
                [sys.executable, "-c", "import time; time.sleep(30)"], 0.05
            )

    def test_previous_results_are_never_overwritten(self):
        from types import SimpleNamespace

        from rv32_sdk.bench import run

        with TemporaryDirectory() as directory:
            root = Path(directory)
            sentinel = root / "results.json"
            sentinel.write_text("previous experiment")
            args = SimpleNamespace(
                cpu_hz=None, repeats=1, cycles=1000, timeout=10, output=root
            )
            with self.assertRaisesRegex(
                ValueError, "Output directory must be empty"
            ):
                run(args)
            self.assertEqual(sentinel.read_text(), "previous experiment")

    def test_selected_cable_is_written_to_project(self):
        import tomllib

        with TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_project(
                root, "smoke", root / "missing", 1000, "USB-Blaster [1-2]"
            )
            parsed = tomllib.loads((root / "rv32.toml").read_text())
            self.assertEqual(
                parsed["project"]["jtag_hardware"], "USB-Blaster [1-2]"
            )
