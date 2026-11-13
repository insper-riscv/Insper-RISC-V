"""Test score integrity, comparisons and profile selection."""

import argparse
import copy
import json
import math
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, override
from unittest.mock import patch

from benchmarks.embench import ci, report, run
from benchmarks.embench.provenance import cache_key, hash_files, source_key


class ReportingTests(unittest.TestCase):
    """Reject misleading and incompatible measurements."""

    @override
    def setUp(self) -> None:
        """Create an internally consistent synthetic fixture."""
        self.data: dict[str, Any] = {
            "schema": 1,
            "profile": "rv32im",
            "provenance": {
                "revision": "abc",
                "source_sha256": "rtl",
                "contract": {"tool": "fixed"},
            },
            "suite": {"programs": ["crc32", "aha-mont64"]},
            "results": [
                {
                    "program": p,
                    "status": "pass",
                    "cycles": 100,
                    "instructions": 50,
                    "cpi": 2.0,
                    "score_per_mhz": 2.0,
                    "operations": {
                        "branching": 10,
                        "memory": 15,
                        "compute": 25,
                        "other": 0,
                    },
                }
                for p in ("crc32", "aha-mont64")
            ],
        }

    def test_simulation_aggregate_needs_no_hardware(self) -> None:
        """Publish both PR sides without physical artifacts."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for side in ("candidate", "base"):
                folder = root / side / "rv32im"
                folder.mkdir(parents=True)
                run.write_json(folder / "results.json", self.data)
            plan = root / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "profiles": ["rv32im"],
                        "revisions": {"candidate": "abc", "base": "abc"},
                        "available": {
                            "candidate": ["rv32im"],
                            "base": ["rv32im"],
                        },
                        "programs": self.data["suite"]["programs"],
                    }
                )
            )
            args = argparse.Namespace(
                input=root, plan=plan, compare=True, output=root / "summary.md"
            )
            with patch("benchmarks.embench.ci.publish_summary"):
                ci.aggregate(args)
            text = args.output.read_text()
            self.assertIn("Target-base measurements", text)
            self.assertIn("Mean retired instructions/program: **50.0**", text)
            self.assertIn("**0.5000**", text)
            self.assertIn("+0.00%", text)
            self.assertTrue((root / "candidate/rv32im/results.csv").is_file())
            (root / "base/rv32im/results.json").unlink()
            with (
                patch("benchmarks.embench.ci.publish_summary"),
                self.assertRaises(SystemExit),
            ):
                ci.aggregate(args)
            self.assertIn("missing results (FAIL)", args.output.read_text())

    def test_simulation_artifact_identity_is_checked(self) -> None:
        """Preserve provenance gates without a hardware backend."""
        expected: dict[str, Any] = {
            "revisions": {"candidate": "abc"},
            "available": {"candidate": ["rv32im"]},
            "programs": self.data["suite"]["programs"],
        }
        ci.validate_simulation(self.data, "rv32im", "candidate", expected)
        for field, value in (
            ("backend", "fpga"),
            ("profile", "rv32i"),
            ("provenance", {"revision": "stale"}),
            ("suite", {"programs": ["crc32"]}),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.data)
                changed[field] = value
                with self.assertRaises(ValueError):
                    ci.validate_simulation(
                        changed, "rv32im", "candidate", expected
                    )
        absent = copy.deepcopy(self.data)
        for row in absent["results"]:
            row["status"] = "profile unavailable"
        with self.assertRaisesRegex(ValueError, "availability"):
            ci.validate_simulation(absent, "rv32im", "candidate", expected)
        expected["available"]["candidate"] = []
        ci.validate_simulation(absent, "rv32im", "candidate", expected)
        self.assertTrue(ci.acceptable(absent))
        self.data["results"][0]["status"] = "unfinished"
        self.assertFalse(ci.acceptable(self.data))

    def test_weighted_ipc_uses_total_counts(self) -> None:
        """Weight IPC using total instructions and cycles."""
        self.data["results"][0]["cycles"] = 300
        text = report.counter_summary(self.data)
        self.assertIn("**0.2500**", text)
        self.data["results"].pop()
        self.assertIn("unavailable", report.counter_summary(self.data))

    def test_identical_inputs_have_zero_delta(self) -> None:
        """Identical timing must produce zero speedup."""
        changed = copy.deepcopy(self.data)
        changed["provenance"]["revision"] = "def"
        self.assertEqual(set(report.compare(self.data, changed).values()), {0})

    def test_speed_delta_uses_inverse_cycles(self) -> None:
        """Check speedup for a 20 percent cycle reduction."""
        changed = copy.deepcopy(self.data)
        changed["results"][0]["cycles"] = 80
        self.assertAlmostEqual(report.compare(self.data, changed)["crc32"], 25)

    def test_mixed_toolchain_is_not_comparable(self) -> None:
        """Do not silently attribute a compiler change to the RTL."""
        changed = copy.deepcopy(self.data)
        changed["provenance"]["contract"]["tool"] = "different"
        with self.assertRaisesRegex(ValueError, "contracts"):
            report.compare(self.data, changed)

    def test_failures_are_not_numeric_scores(self) -> None:
        """A failed verifier produces no speedup or valid suite."""
        self.data["results"][0] = {"program": "crc32", "status": "failed"}
        self.assertNotIn("crc32", report.compare(self.data, self.data))
        self.assertIn(
            "| all programs | 1/2 | incomplete |",
            "\n".join(report.summaries(self.data)),
        )

    def test_partial_run_has_no_full_suite_score(self) -> None:
        """Reject aggregate scores with missing programs."""
        self.data["results"].pop()
        self.assertIn(
            "| all programs | 1/2 | incomplete |",
            "\n".join(report.summaries(self.data)),
        )

    def test_unbalanced_mix_is_rejected(self) -> None:
        """Every counted instruction belongs to exactly one bucket."""
        self.data["results"][0]["operations"]["other"] = 1
        with self.assertRaisesRegex(ValueError, "Unbalanced"):
            report.valid_row(self.data["results"][0])

    def test_nonfinite_score_is_rejected(self) -> None:
        """NaN must never propagate into a published benchmark score."""
        self.data["results"][0]["score_per_mhz"] = math.nan
        with self.assertRaisesRegex(ValueError, "Invalid Embench"):
            report.valid_row(self.data["results"][0])

    def test_geometric_summary(self) -> None:
        """Check geometric rather than arithmetic score aggregation."""
        self.assertAlmostEqual(report.geomean([1.0, 9.0]), 3.0)
        with self.assertRaises(ValueError):
            report.geomean([0.0])

    def test_cache_ignores_commit_but_not_rtl_or_contract(self) -> None:
        """Require identical inputs before reusing results."""
        first = self.data["provenance"]
        changed = copy.deepcopy(first)
        changed["revision"] = "def"
        self.assertEqual(
            cache_key(first, "rv32im"), cache_key(changed, "rv32im")
        )
        changed["source_sha256"] = "new-rtl"
        self.assertNotEqual(
            cache_key(first, "rv32im"), cache_key(changed, "rv32im")
        )
        self.assertNotEqual(
            cache_key(first, "rv32im"), cache_key(first, "rv32i")
        )

    def test_hash_detects_changes_and_renames(self) -> None:
        """File bytes and relative names both participate in the key."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "one.vhd"
            path.write_text("first")
            first = hash_files(root, [path])
            path.write_text("changed")
            self.assertNotEqual(first, hash_files(root, [path]))
            renamed = path.rename(root / "two.vhd")
            self.assertNotEqual(first, hash_files(root, [renamed]))

    def test_compiler_uses_enabled_extensions(self) -> None:
        """Keep M and Zmmul compiler targets distinct."""
        self.assertEqual(
            run.compiler_isa({"extensions": ["I", "M"]}), "rv32im"
        )
        self.assertEqual(
            run.compiler_isa({"extensions": ["I", "Zmmul"]}), "rv32i_zmmul"
        )
        self.assertEqual(
            run.compiler_isa({"extensions": ["I", "M", "Zicond"]}),
            "rv32im_zicond",
        )

    def test_cache_detects_corruption(self) -> None:
        """Reject changed measurements in the result cache."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "results.json"
            exp = run.Experiment(
                root, root, root, self.data["suite"], self.data["provenance"]
            )
            run.write_json(path, self.data)
            programs = self.data["suite"]["programs"]
            self.assertIsNotNone(run.reusable(path, exp, "rv32im", programs))
            self.assertIsNone(run.reusable(path, exp, "rv32i", programs))
            damaged = json.loads(path.read_text())
            damaged["results"][0]["cycles"] += 1
            path.write_text(json.dumps(damaged))
            self.assertIsNone(run.reusable(path, exp, "rv32im", programs))
            with self.assertRaisesRegex(ValueError, "Corrupted"):
                report.load(path)
            path.write_text("{")
            self.assertIsNone(run.reusable(path, exp, "rv32im", programs))

    def test_duplicate_shards_are_rejected(self) -> None:
        """Reject duplicate benchmark artifacts."""
        with tempfile.TemporaryDirectory() as temporary:
            paths = [Path(temporary) / f"result-{i}.json" for i in range(2)]
            for path in paths:
                run.write_json(path, self.data)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                ci.combine(paths)

    def test_plan_uses_profile_yamls_and_shards_full_mode(self) -> None:
        """Discover profiles and split full-mode jobs."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "Core/profiles"
            folder.mkdir(parents=True)
            for name in ("rv32i", "rv32im"):
                (folder / f"{name}.yaml").write_text("profile: " + name)
            args = argparse.Namespace(
                candidate=root,
                base=None,
                scope="named",
                workload="ci",
                output=root / "plan.json",
            )
            with (
                patch("benchmarks.embench.ci.emit"),
                patch("benchmarks.embench.ci.capture", return_value="a" * 40),
            ):
                ci.plan(args)
                planned = json.loads(args.output.read_text())
                self.assertEqual(planned["profiles"], ["rv32i", "rv32im"])
                self.assertEqual(len(planned["batches"]), 2)
                args.workload = "full"
                ci.plan(args)
            planned = json.loads(args.output.read_text())
            self.assertEqual(len(planned["batches"]), 38)
            self.assertTrue(
                all(len(b["programs"]) == 1 for b in planned["batches"])
            )

    def test_source_key_covers_scripts_and_untracked_sources(self) -> None:
        """Invalidate results when generators or new RTL change."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "Core/formal"
            directory.mkdir(parents=True)
            script = directory / "config_variant.sh"
            script.write_text("original")
            initial = source_key(root)
            script.write_text("changed")
            updated = source_key(root)
            self.assertNotEqual(initial, updated)
            (directory / "new.vhd").write_text("entity new")
            self.assertNotEqual(updated, source_key(root))

    def test_timeout_terminates_descendant_process(self) -> None:
        """Do not leave simulator children running after a timeout."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = (
                "import subprocess,sys,time;from pathlib import Path;"
                "p=subprocess.Popen([sys.executable,'-c',"
                "'import time;time.sleep(20)']);"
                "Path('child.pid').write_text(str(p.pid));time.sleep(20)"
            )
            with self.assertRaises(subprocess.TimeoutExpired):
                run.command(
                    [sys.executable, "-c", script],
                    root,
                    root / "timeout.log",
                    timeout=1,
                )
            pid = int((root / "child.pid").read_text())
            status = Path(f"/proc/{pid}/status")
            # SIGKILL delivery is asynchronous. The direct parent can
            # exit before its child has been scheduled.
            deadline = time.monotonic() + 5
            while True:
                try:
                    state = status.read_text(encoding="utf-8")
                except FileNotFoundError:
                    break  # Reaped by the host's init process.
                if "State:\tZ" in state:
                    break  # Terminated, awaiting reaping by container PID 1.
                if time.monotonic() >= deadline:
                    self.fail(
                        f"Child {pid} survived process-group kill: {state}"
                    )
                time.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
