"""Read the complete configured stdout region, including a partial final word."""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["RV32_SDK_ROOT"] = str(ROOT)
spec = importlib.util.spec_from_file_location(
    "sdk_long_output", ROOT / ".sdk/rv32_sdk/cli.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LongOutputTest(unittest.TestCase):
    def capture(self, payload, truncated=False):
        data = payload + b"\0" * (-len(payload) % 4)
        words = [
            int.from_bytes(data[i : i + 4], "little")
            for i in range(0, len(data), 4)
        ]
        cfg = {
            "memory": {"ram_base": 0x8000},
            "quartus": {"jtag_device": "device"},
        }
        with (
            patch.object(module, "doctor"),
            patch.object(module, "write_config"),
            patch.object(module, "load_config", return_value=cfg),
            patch.object(module, "detect_jtag_hardware", return_value="cable"),
            patch.object(module, "JtagLink"),
            patch.object(module.ram_target, "target_from_config"),
            patch.object(
                module.ram_target,
                "read_words",
                side_effect=[[len(payload), int(truncated)], words],
            ) as read,
            patch.object(module, "emit_program_output") as emit,
        ):
            if truncated:
                with self.assertRaisesRegex(
                    SystemExit, "output is incomplete"
                ):
                    module.read_stdout(ROOT, {"language": "c"})
            else:
                module.read_stdout(ROOT, {"language": "c"})
            emit.assert_called_once_with(payload)
            self.assertEqual(read.call_args_list[0].args[-1], 2)
            if payload:
                self.assertEqual(
                    read.call_args_list[1].args[-1], (len(payload) + 3) // 4
                )
            else:
                self.assertEqual(read.call_count, 1)

    def test_matrix_exceeds_legacy_one_kilobyte_buffer(self):
        line = b"[ " + b"".join(f"{i} ".encode() for i in range(100)) + b"]\n"
        self.capture(line * 100)

    def test_partial_last_word_is_not_padded_in_output(self):
        self.capture(b"x" * 65535)

    def test_overflow_reports_incomplete_output(self):
        self.capture(b"x" * 65536, truncated=True)

    def test_empty_output_requires_no_payload_read(self):
        with patch.object(module, "emit_program_output"):
            # read_stdout deliberately does not emit anything for an empty buffer.
            cfg = {
                "memory": {"ram_base": 0x8000},
                "quartus": {"jtag_device": "device"},
            }
            with (
                patch.object(module, "doctor"),
                patch.object(module, "write_config"),
                patch.object(module, "load_config", return_value=cfg),
                patch.object(module, "detect_jtag_hardware"),
                patch.object(module, "JtagLink"),
                patch.object(module.ram_target, "target_from_config"),
                patch.object(
                    module.ram_target, "read_words", return_value=[0, 0]
                ) as read,
            ):
                module.read_stdout(ROOT, {"language": "c"})
                self.assertEqual(read.call_count, 1)
