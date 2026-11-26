import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from rv32_sdk import sof_cache


class SofCacheTest(unittest.TestCase):
    def test_hardware_changes_invalidate_but_application_does_not(self):
        with TemporaryDirectory() as temp:
            sdk = Path(temp)
            cfg = {
                "memory": {"ram_words": 10},
                "quartus": {
                    "project_dir": "src/simulation/internal-mem/quartus",
                    "rom_mif_target": "init.mif",
                },
            }
            for name in [
                "Core/cpu.vhd",
                "Memory/ip.qip",
                "Memory/ram.mif",
                "src/simulation/internal-mem/pll.v",
                "src/simulation/internal-mem/quartus/design.qsf",
                "src/simulation/internal-mem/runtime/boot_memory.S",
                "src/simulation/internal-mem/runtime/boot_memory.ld",
            ]:
                path = sdk / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("original")
            key = sof_cache.fingerprint(sdk, cfg, "25.1")
            for path in list(sdk.rglob("*")):
                if path.is_file():
                    path.write_text("changed")
                    self.assertNotEqual(
                        key, sof_cache.fingerprint(sdk, cfg, "25.1"), str(path)
                    )
                    path.write_text("original")
            (sdk / "src/simulation/internal-mem/quartus/init.mif").write_text(
                "application"
            )
            (
                sdk
                / "src/simulation/internal-mem/quartus/boot_memory_init.mif"
            ).write_text("generated")
            (sdk / "main.c").write_text("changed application")
            self.assertEqual(key, sof_cache.fingerprint(sdk, cfg, "25.1"))
            self.assertNotEqual(key, sof_cache.fingerprint(sdk, cfg, "26.1"))
            cfg["memory"]["ram_words"] = 20
            self.assertNotEqual(key, sof_cache.fingerprint(sdk, cfg, "25.1"))

    def test_corruption_missing_and_valid_roundtrip(self):
        with (
            TemporaryDirectory() as temp,
            patch.dict(os.environ, {"RV32_SOF_CACHE_DIR": temp}),
        ):
            src = Path(temp) / "input.sof"
            src.write_bytes(b"bitstream")
            dest = Path(temp) / "output.sof"
            self.assertFalse(sof_cache.restore("key", dest))
            sof_cache.store("key", src)
            self.assertTrue(sof_cache.restore("key", dest))
            self.assertEqual(dest.read_bytes(), b"bitstream")
            (Path(temp) / "key/design.sof").write_bytes(b"corrupt")
            self.assertFalse(sof_cache.restore("key", dest))
            sof_cache.store("key", src)
            (Path(temp) / "key/manifest.json").write_text("{}")
            self.assertFalse(sof_cache.restore("key", dest))

    def test_cache_identity_survives_sdk_relocation(self):
        import shutil

        with TemporaryDirectory() as temp:
            root = Path(temp)
            first = root / "first"
            (first / "src/simulation/platform").mkdir(parents=True)
            (first / "src/simulation/platform/core.vhd").write_text("hardware")
            second = root / "second"
            shutil.copytree(first, second)
            cfg = {
                "memory": {},
                "quartus": {
                    "project_dir": str(first / "src/simulation/platform"),
                    "rom_mif_target": "init.mif",
                },
            }
            before = sof_cache.fingerprint(first, cfg, "25.1")
            cfg["quartus"]["project_dir"] = str(
                second / "src/simulation/platform"
            )
            self.assertEqual(
                before, sof_cache.fingerprint(second, cfg, "25.1")
            )

    def test_c_driver_edits_do_not_invalidate_but_gpio_rtl_does(self):
        with TemporaryDirectory() as temp:
            sdk = Path(temp)
            c_header = sdk / "Peripherals/src/GPIO/soc/driver/c/gpio.h"
            c_header.parent.mkdir(parents=True)
            c_header.write_text("driver v1")
            rtl = sdk / "Peripherals/src/GPIO/soc/gpio.vhd"
            rtl.write_text("hardware v1")
            cfg = {
                "memory": {},
                "quartus": {
                    "project_dir": "quartus",
                    "rom_mif_target": "init.mif",
                },
            }
            before = sof_cache.fingerprint(sdk, cfg, "test")
            c_header.write_text("driver v2")
            self.assertEqual(before, sof_cache.fingerprint(sdk, cfg, "test"))
            rtl.write_text("hardware v2")
            self.assertNotEqual(
                before, sof_cache.fingerprint(sdk, cfg, "test")
            )
