"""Dependency startup may exceed five minutes without missing packages."""

import os
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
WAITER = ROOT / "scripts/wait-for-container-tools.sh"


class ContainerToolsWaitTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.state = self.root / "state"
        self.counter = self.root / "sleeps"
        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        sleep = fake_bin / "sleep"
        sleep.write_text(
            "#!/bin/bash\n"
            "count=0\n"
            'if [[ -f "$TEST_COUNTER" ]]; then read -r count < "$TEST_COUNTER"; fi\n'
            "count=$((count + 1))\n"
            'printf "%s\\n" "$count" > "$TEST_COUNTER"\n'
            'if ((count >= TEST_READY_AT)); then printf "ready\\n" > "$TEST_STATE"; fi\n'
        )
        sleep.chmod(0o755)
        self.env = dict(
            os.environ,
            PATH=str(fake_bin) + os.pathsep + os.environ["PATH"],
            TEST_COUNTER=str(self.counter),
            TEST_STATE=str(self.state),
            TEST_READY_AT="301",
        )

    def run_wait(self, state="preparing", limit="400"):
        if state is not None:
            self.state.write_text(state + "\n")
        return subprocess.run(
            ["bash", str(WAITER), str(self.state), "Clang/libclang"],
            env=dict(self.env, RV32_DEPS_WAIT_SECONDS=limit),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )

    def test_install_longer_than_old_five_minute_limit_completes(self):
        result = self.run_wait()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.counter.read_text().strip(), "301")
        self.assertIn("300s", result.stdout)

    def test_ready_state_does_not_sleep(self):
        result = self.run_wait("ready")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.counter.exists())
        self.assertEqual(result.stdout, "")

    def test_missing_state_leaves_tool_detection_to_caller(self):
        self.assertEqual(self.run_wait(None).returncode, 0)
        self.assertFalse(self.counter.exists())

    def test_install_failure_is_reported_immediately(self):
        result = self.run_wait("failed")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("installation failed", result.stderr)
        self.assertFalse(self.counter.exists())

    def test_timeout_reports_in_progress_not_missing_compiler(self):
        result = self.run_wait(limit="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("still running", result.stderr)
        self.assertNotIn("Rebuild", result.stderr)
        self.assertEqual(self.counter.read_text().strip(), "2")

    def test_partial_state_write_does_not_cause_false_failure(self):
        self.env["TEST_READY_AT"] = "1"
        self.assertEqual(self.run_wait("").returncode, 0)

    def test_invalid_wait_bound_is_rejected(self):
        for value in ("0", "-1", "forever", "99999"):
            with self.subTest(limit=value):
                result = self.run_wait(limit=value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("between 1 and 3600", result.stderr)


if __name__ == "__main__":
    unittest.main()
