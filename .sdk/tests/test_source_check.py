"""Prevent opaque memory-map errors from uninitialized Git submodules."""

import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rv32_sdk import source_check

ROOT = Path(__file__).resolve().parents[2]


class SourceCheckTest(unittest.TestCase):
    def test_empty_submodule_folders_report_recursive_initialization(self):
        with TemporaryDirectory(prefix="sdk with spaces ") as temp:
            root = Path(temp)
            for name in ("Core", "Memory", "Peripherals", "Common-Components"):
                (root / name).mkdir()
            with self.assertRaisesRegex(
                SystemExit, "submodule update --init --recursive"
            ) as error:
                source_check.check(root)
            self.assertIn("Core/profiles/matrix.yaml", str(error.exception))
            self.assertIn("Run on the host", str(error.exception))

    def test_nested_modules_and_driver_revision_are_checked(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for name in source_check.REQUIRED_SOURCES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            for name in (
                "Core/src/common/src/config_pkg.vhd",
                "Peripherals/src/GPIO/soc/driver/c/driver.yaml",
                "Peripherals/src/GPIO/soc/driver/c/examples/main.c.in",
            ):
                with self.subTest(name=name):
                    path = root / name
                    path.unlink()
                    with self.assertRaises(SystemExit) as error:
                        source_check.check(root)
                    self.assertIn(name, str(error.exception))
                    path.touch()

    def test_complete_source_export_needs_no_git_directory(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for name in source_check.REQUIRED_SOURCES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            self.assertFalse((root / ".git").exists())
            source_check.check(root)

    def test_standalone_preflight_has_no_package_dependencies_or_traceback(
        self,
    ):
        with TemporaryDirectory() as temp:
            result = subprocess.run(
                [
                    sys.executable,
                    "-S",
                    str(ROOT / ".sdk/rv32_sdk/source_check.py"),
                    temp,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("submodule update --init --recursive", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
