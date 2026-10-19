from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("live_c", ROOT / "scripts" / "live_c.py")
assert SPEC and SPEC.loader
live_c = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = live_c
SPEC.loader.exec_module(live_c)


class LiveCTest(unittest.TestCase):
    def test_parser_accepts_all_commands(self) -> None:
        commands = ["doctor", "setup", "simulate", "spike", "assembly", "stdout"]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(live_c.parser().parse_args([command]).command, command)
        self.assertEqual(
            live_c.parser().parse_args(["fpga", "--mode", "fast"]).mode, "fast"
        )

    def test_riscv_tools_uses_tests_as_root(self) -> None:
        with mock.patch.object(live_c, "run", return_value=0) as invoked:
            live_c.riscv_tools("compile", "--emit", "mif")
        command = invoked.call_args.args[0]
        self.assertEqual(command[-3:], ["compile", "--emit", "mif"])
        self.assertEqual(
            command[command.index("--root") + 1], str(live_c.TESTS)
        )
        self.assertEqual(
            command[command.index("--config") + 1], str(live_c.CONFIG)
        )

    def test_fast_fpga_skips_full_reconfiguration(self) -> None:
        with (
            mock.patch.object(live_c, "doctor"),
            mock.patch.object(live_c, "build"),
            mock.patch.object(live_c, "clear_resume_state"),
            mock.patch.object(live_c, "read_stdout"),
            mock.patch.object(live_c, "riscv_tools", return_value=0) as invoked,
        ):
            live_c.fpga("fast")
        self.assertIn("--skip-reconfigure", invoked.call_args.args)

    def test_full_fpga_does_not_skip_reconfiguration(self) -> None:
        with (
            mock.patch.object(live_c, "doctor"),
            mock.patch.object(live_c, "build"),
            mock.patch.object(live_c, "clear_resume_state"),
            mock.patch.object(live_c, "read_stdout"),
            mock.patch.object(live_c, "riscv_tools", return_value=0) as invoked,
        ):
            live_c.fpga("full")
        self.assertNotIn("--skip-reconfigure", invoked.call_args.args)
        self.assertNotIn("--skip-recompile", invoked.call_args.args)

    def test_spike_builds_the_manifest_it_consumes(self) -> None:
        with (
            mock.patch.object(live_c, "doctor"),
            mock.patch.object(live_c, "require_commands"),
            mock.patch.object(live_c, "build") as build,
            mock.patch.object(live_c, "riscv_tools"),
        ):
            live_c.spike()
        build.assert_called_once_with("mif")

    def test_failed_hardware_run_preserves_exit_status(self) -> None:
        with (
            mock.patch.object(live_c, "doctor"),
            mock.patch.object(live_c, "build"),
            mock.patch.object(live_c, "clear_resume_state"),
            mock.patch.object(live_c, "read_stdout") as read_stdout,
            mock.patch.object(live_c, "riscv_tools", return_value=2),
            self.assertRaises(SystemExit) as raised,
        ):
            live_c.fpga("fast")
        self.assertEqual(raised.exception.code, 2)
        read_stdout.assert_not_called()

    def test_run_raises_when_requested(self) -> None:
        completed = subprocess.CompletedProcess(["false"], 7)
        with (
            mock.patch("subprocess.run", return_value=completed),
            self.assertRaises(subprocess.CalledProcessError) as raised,
        ):
            live_c.run(["false"])
        self.assertEqual(raised.exception.returncode, 7)

    def test_setup_skips_submodule_update_for_archive(self) -> None:
        not_a_checkout = subprocess.CompletedProcess(["git"], 128)
        with (
            mock.patch.object(live_c, "require_commands"),
            mock.patch.object(live_c, "require_layout") as require_layout,
            mock.patch("subprocess.run", return_value=not_a_checkout),
            mock.patch.object(live_c, "run", return_value=0) as invoked,
        ):
            live_c.setup()
        require_layout.assert_called_once_with()
        self.assertEqual(invoked.call_count, 1)
        self.assertEqual(invoked.call_args.args[0][:2], ["uv", "sync"])

    def test_stdout_decoding_is_little_endian(self) -> None:
        words = [
            6,
            0,
            int.from_bytes(b"Hi!\n", "little"),
            int.from_bytes(b"OK\0\0", "little"),
        ]
        text, truncated = live_c.decode_stdout_words(
            words
        )
        self.assertEqual(text, "Hi!\nOK")
        self.assertFalse(truncated)

    def test_stdout_decoding_reports_truncation(self) -> None:
        text, truncated = live_c.decode_stdout_words(
            [8, 1, int.from_bytes(b"abcd", "little")], capacity=4
        )
        self.assertEqual(text, "abcd")
        self.assertTrue(truncated)


if __name__ == "__main__":
    unittest.main()
