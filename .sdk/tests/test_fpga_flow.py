"""SDK FPGA operations must use the current HTIF/loader API without implicit synthesis."""

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["RV32_SDK_ROOT"] = str(ROOT)
spec = importlib.util.spec_from_file_location(
    "sdk_fpga", ROOT / ".sdk/rv32_sdk/cli.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FpgaFlowTest(unittest.TestCase):
    def invoke(self, mode, result=1, cached=True):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = root / "build/real/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                json.dumps(
                    [
                        {
                            "name": "app",
                            "mif": "build/real/app.mif",
                            "timeout_s": 15,
                        }
                    ]
                )
            )
            cfg = {
                "quartus": {
                    "project_dir": str(
                        ROOT / "src/simulation/internal-mem/quartus"
                    ),
                    "sof_file": "output_files/core_fpga_test.sof",
                    "jtag_device": "device",
                    "project_name": "test",
                    "stale_cache_dirs": [],
                    "rom_mif_target": "rom.mif",
                    "boot_memory_mif_target": "boot.mif",
                }
            }
            cfg.update(
                {
                    "toolchain": {},
                    "paths": {},
                    "isa": {"base": "rv32i"},
                    "memory": {"boot_memory_words": 1024},
                }
            )
            with (
                patch.object(module.boot_memory, "build_boot_memory") as boot,
                patch.object(module.bin_to_image, "bin_to_mif"),
                patch.object(module, "doctor"),
                patch.object(module, "build"),
                patch.object(module, "load_config", return_value=cfg),
                patch.object(
                    module, "detect_jtag_hardware", return_value="cable"
                ),
                patch.object(
                    module.sof_cache, "fingerprint", return_value="key"
                ),
                patch.object(
                    module.sof_cache, "restore", return_value=cached
                ) as restore,
                patch.object(module.sof_cache, "store") as store,
                patch.object(
                    module.quartus_program, "program_only"
                ) as program,
                patch.object(
                    module.quartus_program, "full_reconfigure"
                ) as synth,
                patch.object(
                    module, "run_test_via_jtag", return_value=result
                ) as run,
                patch.object(module, "read_stdout") as stdout,
            ):
                error = None
                try:
                    module.fpga_locked(root, {"language": "c"}, mode)
                except SystemExit as exc:
                    error = str(exc)
                return {
                    "boot_options": boot.call_args.args[-1]
                    if boot.called
                    else None,
                    "restore": restore.call_count,
                    "store": store.call_count,
                    "program": program.call_count,
                    "synth": synth.call_count,
                    "run_root": run.call_args.args[-1],
                    "root": root,
                    "stdout": stdout.call_count,
                    "error": error,
                }

    def test_fast_uses_loader_without_programming_or_synthesis(self):
        result = self.invoke("fast")
        self.assertEqual(result["program"], 0)
        self.assertEqual(result["synth"], 0)
        self.assertEqual(result["restore"], 0)
        self.assertEqual(result["run_root"], result["root"])
        self.assertIsNone(result["error"])

    def test_cache_hit_programs_without_synthesis(self):
        result = self.invoke("full")
        self.assertEqual(result["program"], 1)
        self.assertEqual(result["synth"], 0)
        self.assertEqual(result["store"], 1)

    def test_failure_and_timeout_never_trigger_implicit_reprogramming(self):
        for value in [None, 3]:
            result = self.invoke("fast", value)
            self.assertIsNotNone(result["error"])
            self.assertEqual(result["program"], 0)
            self.assertEqual(result["synth"], 0)
            self.assertEqual(result["stdout"], 1)

    def test_cache_miss_uses_current_boot_memory_api(self):
        result = self.invoke("full", cached=False)
        self.assertIsInstance(
            result["boot_options"], module.boot_memory.BootMemoryOptions
        )
        self.assertEqual(result["synth"], 1)
        self.assertEqual(result["program"], 0)
        self.assertEqual(result["store"], 1)
