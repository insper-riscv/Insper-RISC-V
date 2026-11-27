"""Peripheral board projects must include their off-SoC hardware sources."""

import unittest
from pathlib import Path

import yaml
from riscv_tools import board_generate

ROOT = Path(__file__).resolve().parents[2]


class PeripheralBoardSourcesTest(unittest.TestCase):
    def test_de0_cv_fetch_precedes_core_capture(self):
        platform = yaml.safe_load(
            (ROOT / "src/periph-examples/de0-cv/platform.yaml").read_text()
        )
        clocks = platform["clocks"]
        self.assertEqual(clocks["fetch"]["mhz"], clocks["core"]["mhz"])
        period_ps = 1_000_000 / clocks["core"]["mhz"]
        separation = (
            clocks["core"]["phase_ps"] - clocks["fetch"]["phase_ps"]
        ) % period_ps
        self.assertGreater(separation, 0)
        self.assertLess(separation, period_ps)

    def test_de0_cv_keyboard_mouse_and_sd_are_in_source_closure(self):
        project = ROOT / "build/source-list-regression"
        sources = board_generate.sources_of(
            ROOT, ["Insper-RISC-V/periph_de0_cv_board"], project
        )
        resolved = {(project / source).resolve() for source in sources}
        expected = [
            "Peripherals/src/PS2/host/ps2_host.vhd",
            "Peripherals/src/PS2/keyboard/ps2_keyboard.vhd",
            "Peripherals/src/PS2/mouse/ps2_mouse_top.vhd",
            "Peripherals/src/SD/native/sd_native.vhd",
        ]
        for source in expected:
            with self.subTest(source=source):
                self.assertIn((ROOT / source).resolve(), resolved)


if __name__ == "__main__":
    unittest.main()
