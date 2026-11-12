"""Test physical accounting, reports and runner isolation."""

import argparse
import copy
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from benchmarks.embench import (
    combined,
    hardware_build,
    hardware_host,
    run,
    test_reporting,
)
from benchmarks.embench import hardware_measure as measure


def response(values: list[int], status: int = 1) -> str:
    """Encode an observer scan independently from its parser."""
    words = [measure.MAGIC, status]
    for value in values:
        words.extend([value & 0xFFFFFFFF, value >> 32])
    return "METRICS=" + "".join(f"{word:08x}" for word in reversed(words))


class HardwareTests(unittest.TestCase):
    """Reject corrupt measurements and preserve hardware profiles."""

    def test_pending_scan_is_not_a_result(self) -> None:
        """Do not score an unfinished measurement region."""
        self.assertIsNone(measure.decode_frame("METRICS=" + "0" * 112))

    def test_wide_counters(self) -> None:
        """Keep all 64 bits when a run exceeds a 32-bit cycle count."""
        data = measure.decode_frame(response([2**34, 8, 3, 2, 3, 0]))
        self.assertIsNotNone(data)
        if data is not None:
            self.assertEqual(data["cycles"], 2**34)
            self.assertEqual(data["instructions"], 8)

    def test_bad_frames_fail(self) -> None:
        """Reject traps, malformed scans and unbalanced counters."""
        invalid = [
            "METRICS=0",
            response([10, 8, 3, 2, 3, 0], status=5),
            response([10, 8, 3, 2, 2, 0]),
            response([0, 0, 0, 0, 0, 0]),
        ]
        for text in invalid:
            with self.subTest(response=text), self.assertRaises(ValueError):
                measure.decode_frame(text)

    def test_median_and_determinism(self) -> None:
        """Keep deterministic instructions and median cycles."""
        samples = [
            {"cycles": cycles, "instructions": 8, "operations": {"compute": 8}}
            for cycles in (100, 102, 1000)
        ]
        result = measure.summarize(samples)
        self.assertEqual(result["cycles"], 102)
        self.assertEqual(result["instructions"], 8)
        samples[2]["instructions"] = 9
        with self.assertRaisesRegex(ValueError, "different instructions"):
            measure.summarize(samples)

    def test_profile_keeps_board_caches(self) -> None:
        """Keep board caches and UART when applying Core defaults."""
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config_pkg.vhd"
            text = "\n".join(
                f"constant {name} : boolean := false;"
                for name in ("HAS_DCACHE", "HAS_UART", "HAS_ZICSR")
            )
            config.write_text(text)
            (config.parent / "platform_config.vhd").write_text(
                text.replace("false", "true")
            )
            restored = hardware_build.restore_platform(config)
            self.assertIn("HAS_DCACHE : boolean := true", restored)
            self.assertIn("HAS_UART : boolean := true", restored)
            self.assertIn("HAS_ZICSR : boolean := false", restored)

    def test_compiler_has_no_host_access(self) -> None:
        """Require bounded, offline compiler containers."""
        arguments = hardware_host.docker([hardware_host.IMAGE], "none")
        for option in (
            "--memory=8g",
            "--memory-swap=8g",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
        ):
            self.assertIn(option, arguments)
        self.assertNotIn("--privileged", arguments)
        self.assertFalse(any("docker.sock" in value for value in arguments))

    def test_verifier_failure_does_not_restart_jtag(self) -> None:
        """A normal failure must not stop other users' JTAG daemon."""
        with (
            patch.object(
                hardware_host,
                "execute",
                side_effect=RuntimeError("verifier failed"),
            ),
            patch.object(hardware_host.subprocess, "run") as recovery,
            self.assertRaises(RuntimeError),
        ):
            hardware_host.jtag_execute(["not-executed"], 1)
        recovery.assert_not_called()

    def test_jtag_hang_uses_requested_recovery(self) -> None:
        """A confirmed JTAG timeout invokes the lab recovery command."""
        with (
            patch.object(
                hardware_host,
                "execute",
                side_effect=hardware_host.subprocess.TimeoutExpired("test", 1),
            ),
            patch.object(hardware_host.subprocess, "run") as recovery,
            self.assertRaises(hardware_host.subprocess.TimeoutExpired),
        ):
            hardware_host.jtag_execute(["not-executed"], 1)
        self.assertEqual(
            recovery.call_args.args[0],
            ["/usr/bin/sudo", "-n", "killall", "jtagd"],
        )


class CombinedTests(unittest.TestCase):
    """Keep physical speed, IPC and incomplete coverage unambiguous."""

    def test_stale_revision_is_rejected(self) -> None:
        """Reject stale cached revisions."""
        with self.assertRaisesRegex(ValueError, "revision"):
            combined.require_revision(
                {"provenance": {"revision": "old"}}, "new"
            )

    def test_weighted_ipc(self) -> None:
        """Weight IPC by measured work."""
        data = {
            "results": [
                {
                    "program": "a",
                    "status": "pass",
                    "cycles": 100,
                    "instructions": 50,
                    "operations": {
                        "branching": 0,
                        "memory": 0,
                        "compute": 50,
                        "other": 0,
                    },
                    "score_per_mhz": 1,
                },
                {
                    "program": "b",
                    "status": "pass",
                    "cycles": 900,
                    "instructions": 90,
                    "operations": {
                        "branching": 0,
                        "memory": 0,
                        "compute": 90,
                        "other": 0,
                    },
                    "score_per_mhz": 1,
                },
            ]
        }
        mean, ipc, _ = combined.metrics(data)
        self.assertEqual(mean, 70)
        self.assertAlmostEqual(ipc, 0.14)

    def test_clock_changes_physical_speed(self) -> None:
        """Include the PLL frequency in physical speed comparisons."""
        fixture = test_reporting.ReportingTests()
        fixture.setUp()
        base: dict[str, Any] = dict(
            fixture.data, backend="fpga", configured_mhz=50
        )
        head = copy.deepcopy(base)
        head["configured_mhz"] = 100
        head["results"][0]["cycles"] = 80
        self.assertAlmostEqual(
            combined.speed_changes(base, head)["crc32"], 150
        )

    def test_missing_hardware_fails(self) -> None:
        """Require physical artifacts separately from simulation."""
        fixture = test_reporting.ReportingTests()
        fixture.setUp()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sim/candidate/rv32im"
            target.mkdir(parents=True)
            run.write_json(target / "results.json", fixture.data)
            plan = root / "plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "profiles": ["rv32im"],
                        "revisions": {"candidate": "abc"},
                    }
                )
            )
            args = argparse.Namespace(
                simulation=root / "sim",
                hardware=root / "fpga",
                plan=plan,
                output=root / "summary.md",
                compare=False,
            )
            with self.assertRaises(SystemExit):
                combined.aggregate(args)
            text = args.output.read_text()
            self.assertIn("fpga: missing measurements", text)
            self.assertIn("simulation", text)


if __name__ == "__main__":
    unittest.main()
