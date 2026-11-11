"""A configured PLL frequency must never substitute for measured Fmax."""

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[2] / "scripts/kpi_report.py"
spec = importlib.util.spec_from_file_location("kpi_clock_report", PATH)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ClockReportTest(TestCase):
    def test_pll_without_timing_report_has_no_fmax(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "quartus").mkdir()
            (root / "pll").mkdir()
            (root / "pll/pll_0002.v").write_text(
                'output_clock_frequency0("50 MHz")'
            )
            args = SimpleNamespace(
                quartus_dir=str(root / "quartus"),
                sta_rpt="missing.sta.rpt",
                fit_rpt="missing.fit.rpt",
                testbench_dirs=[],
            )
            with patch.object(report, "_coverage", return_value={}):
                result = report.build_report(args)
            self.assertIsNone(result["kpis"]["kpi1_clock_mhz"]["fmax_mhz"])
            self.assertEqual(
                result["kpis"]["kpi1_configured_clock"]["configured_mhz"], 50
            )

    def test_hierarchical_clock_names_and_multiple_corners(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "timing.sta.rpt"
            source.write_text(
                "; 62.5 MHz ; 62.5 MHz ; u_pll|core_clk ;\n"
                "; 68.0 MHz ; 68.0 MHz ; u_pll|core_clk ;\n"
                "; 10.0 MHz ; 10.0 MHz ; sld|tck ;\n"
            )
            parsed = report.parse_fmax(source)
            self.assertEqual(parsed["fmax_mhz"], 62.5)
            self.assertEqual(parsed["clock_name"], "u_pll|core_clk")
            self.assertEqual(parsed["all_clocks"]["u_pll|core_clk"], 62.5)

    def test_memory_bits_are_not_reported_as_block_count(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "fit.rpt"
            source.write_text(
                "; Total block memory bits ; 12,288 / 100,000 ;\n"
            )
            result = report.parse_resource_utilization(source)
            self.assertNotIn("m9k_blocks", result)
            self.assertEqual(result["block_memory_bits"]["used"], 12288)
