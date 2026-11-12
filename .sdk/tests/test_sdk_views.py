"""Keep SDK-specific behavior from changing the processor's standard platform."""

import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import rv32_sdk.cli as sdk

ROOT = Path(__file__).resolve().parents[2]


class SdkViewsTest(unittest.TestCase):
    def test_upstream_runtime_inputs_have_not_drifted(self):
        inputs = json.loads((ROOT / ".sdk/platform-inputs.json").read_text())
        for path, digest in inputs.items():
            self.assertEqual(
                hashlib.sha256((ROOT / path).read_bytes()).hexdigest(),
                digest,
                path,
            )

    def test_simulation_stdio_mode_is_explicit(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for simulation, requested, expected in [
                (False, False, 1),
                (True, False, 0),
                (True, True, 1),
            ]:
                sdk.write_config(
                    root,
                    {"language": "c", "simulation_uart_stdio": requested},
                    simulation=simulation,
                )
                self.assertIn(
                    f"= {expected}u;",
                    (root / ".rv32/stdio-mode.c").read_text(),
                )

    def test_jtag_selects_matching_chip_not_first_cable(self):
        output = "1) USB-Blaster [1-3]\n  020F70DD   10CL120\n2) USB-Blaster [1-2]\n  02B050DD   5CE\n"
        with patch.object(
            sdk.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, output, ""),
        ):
            self.assertEqual(
                sdk.detect_jtag_hardware("@1: 5CE (0x02B050DD)"),
                "USB-Blaster [1-2]",
            )
            with self.assertRaises(SystemExit):
                sdk.detect_jtag_hardware(
                    "@1: 5CE (0x02B050DD)", "USB-Blaster [1-3]"
                )

    def test_jtag_missing_chip_never_falls_back(self):
        output = "1) USB-Blaster [1-3]\n  020F70DD   10CL120\n"
        with patch.object(
            sdk.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, output, ""),
        ):
            with self.assertRaises(SystemExit):
                sdk.detect_jtag_hardware("@1: 5CE (0x02B050DD)")

    def test_fixed_isa_feature_must_be_enabled_in_config_package(self):
        original = Path.read_text

        def disabled_m(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path.name == "config_pkg.vhd":
                import re

                text = re.sub(
                    r"(constant\s+HAS_M\s*:\s*boolean\s*:=\s*)true",
                    r"\1false",
                    text,
                    flags=re.I,
                )
            return text

        with TemporaryDirectory() as directory:
            root = Path(directory)
            sdk.write_config(root, {"language": "c"})
            with patch.object(Path, "read_text", disabled_m):
                with self.assertRaisesRegex(SystemExit, "HAS_M"):
                    sdk.write_config(root, {"language": "c"})
