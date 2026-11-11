"""Prevent apparent frequency gains caused by mixing KPI report semantics."""

import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/compare_kpis.py"


class CompareReportTest(TestCase):
    def compare(self, old_schema, new_schema):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for name, schema, frequency in [
                ("baseline", old_schema, 50),
                ("current", new_schema, 66.56),
            ]:
                report = dict(
                    project="test",
                    generated_at="test",
                    kpis={"kpi1_clock_mhz": {"fmax_mhz": frequency}},
                )
                if schema is not None:
                    report["schema_version"] = schema
                path = root / (name + ".json")
                path.write_text(json.dumps(report))
                paths.append(str(path))
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--baseline",
                    paths[0],
                    "--current",
                    paths[1],
                ],
                text=True,
                capture_output=True,
                timeout=30,
            )

    def test_mixed_legacy_schema_cannot_claim_frequency_gain(self):
        result = self.compare(None, 2)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Regenerate baseline", result.stderr)

    def test_two_legacy_reports_still_have_ambiguous_frequency(self):
        result = self.compare(1, 1)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_unknown_future_schema_is_rejected(self):
        self.assertNotEqual(self.compare(2, 3).returncode, 0)

    def test_sta_reports_with_matching_current_schema_are_compared(self):
        result = self.compare(2, 2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("66.56 MHz", result.stdout)
