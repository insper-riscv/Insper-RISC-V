"""Prevent invalid before/after speedup claims."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from rv32_sdk.evidence import BASELINE, audit_comparisons


class EvidenceTest(TestCase):
    def report(self):
        base = dict(
            kernel="example",
            verified=True,
            simulation_passed=True,
            checksum=42,
            expected=42,
            binary_sha256="0" * 64,
        )
        return dict(
            baseline_commit=BASELINE,
            current_commit="current",
            baseline_source_hashes={"a": "old"},
            current_source_hashes={"a": "new"},
            runner_sha256="r",
            monitor_sha256="m",
            runs=[
                dict(base, variant="baseline", cycles=100),
                dict(base, variant="current", cycles=120),
            ],
        )

    def audit(self, report):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "results.json"
            path.write_text(json.dumps(report))
            return audit_comparisons([path])

    def test_regression_is_preserved(self):
        result = self.audit(self.report())["comparisons"][0]
        self.assertLess(result["cycle_reduction_pct"], 0)

    def test_wrong_answer_is_never_a_speedup(self):
        report = self.report()
        report["runs"][1]["checksum"] = 0
        with self.assertRaisesRegex(ValueError, "Incorrect answer"):
            self.audit(report)

    def test_different_programs_are_rejected(self):
        report = self.report()
        report["runs"][1]["binary_sha256"] = "1" * 64
        with self.assertRaisesRegex(ValueError, "instruction bytes"):
            self.audit(report)
