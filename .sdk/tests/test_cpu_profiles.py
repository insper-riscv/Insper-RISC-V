"""Exact CPU profiles must change hardware and software together."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from rv32_sdk import cli, cpu_profiles, sof_cache

ROOT = Path(__file__).resolve().parents[2]


class CpuProfilesTest(unittest.TestCase):
    def test_all_named_profiles_preserve_memory_and_uart(self):
        with TemporaryDirectory() as directory, patch.object(cli, "SDK", ROOT):
            root = Path(directory)
            baseline = cli.load_config(
                cli.write_config(root, {"language": "c"})
            )
            for path in sorted((ROOT / "Core/profiles").glob("rv32*.yaml")):
                with self.subTest(profile=path.stem):
                    cfg = cli.load_config(
                        cli.write_config(
                            root, {"language": "c", "cpu_profile": path.stem}
                        )
                    )
                    self.assertEqual(cfg["memory"], baseline["memory"])
                    package = next(
                        Path(p).read_text()
                        for p in cfg["sim"]["vhdl_sources"]
                        if Path(p).name == "config_pkg.vhd"
                    )
                    self.assertRegex(
                        package, r"constant HAS_UART\s*: boolean := true"
                    )
                    expected = cpu_profiles.selected(
                        ROOT, {"cpu_profile": path.stem}
                    )
                    for flag, value in expected["flags"].items():
                        self.assertRegex(
                            package,
                            rf"constant {flag}\s*:\s*boolean\s*:=\s*{str(value).lower()}",
                        )
                    qsf = (
                        Path(cfg["quartus"]["project_dir"])
                        / "core_fpga_test.qsf"
                    )
                    self.assertIn(
                        str(root / ".rv32/cpu/config_pkg.vhd"), qsf.read_text()
                    )
            self.assertEqual(cfg["isa"]["base"], "i")

    def test_reduced_counter_generics_reach_both_tops(self):
        with TemporaryDirectory() as directory, patch.object(cli, "SDK", ROOT):
            root = Path(directory)
            cfg = cli.load_config(
                cli.write_config(
                    root,
                    {
                        "language": "c",
                        "cpu_profile": "rv32im_zicclsm_zicntr_zihpm_zifencei_reduced",
                    },
                )
            )
            self.assertEqual(cfg["sim"]["parameters"]["HPM_COUNTERS"], 4)
            self.assertEqual(cfg["sim"]["parameters"]["HPM_WIDTH"], 40)
            top = (root / ".rv32/cpu/core_fpga_test.vhd").read_text()
            self.assertRegex(top, r"hpm_counters\s*:[^;]+:= 4;")
            self.assertRegex(top, r"hpm_width\s*:[^;]+:= 40")

    def test_invalid_profile_and_source_extension_rejected(self):
        for value in [
            None,
            True,
            "../rv32im",
            "rv64im",
            "rv32e",
            "rv32im_fake",
        ]:
            with self.subTest(value=value), self.assertRaises(SystemExit):
                cpu_profiles.selected(ROOT, {"cpu_profile": value})
        profile = cpu_profiles.selected(ROOT, {"cpu_profile": "rv32i"})
        with self.assertRaises(SystemExit):
            cpu_profiles.prepare_source(
                "// RV32_EXT: M\nint main(void){return 0;}", profile
            )

    def test_auto_preserves_default_and_rust_selects_safe_target(self):
        self.assertIsNone(cpu_profiles.selected(ROOT, {}))
        self.assertIsNone(cpu_profiles.selected(ROOT, {"cpu_profile": "auto"}))
        with patch.object(cli, "SDK", ROOT):
            self.assertEqual(
                cli.rust_target({"cpu_profile": "rv32i"}),
                "riscv32i-unknown-none-elf",
            )
            self.assertEqual(
                cli.rust_target({"cpu_profile": "rv32im"}),
                "riscv32im-unknown-none-elf",
            )

    def test_bitstream_key_changes_only_with_hardware(self):
        with TemporaryDirectory() as directory, patch.object(cli, "SDK", ROOT):
            root = Path(directory)

            def key(name):
                cfg = cli.load_config(
                    cli.write_config(
                        root, {"language": "c", "cpu_profile": name}
                    )
                )
                return sof_cache.fingerprint(ROOT, cfg, version="test")

            before = key("rv32i")
            (root / "main.c").write_text("arbitrary C change")
            self.assertEqual(key("rv32i"), before)
            self.assertNotEqual(key("rv32im"), before)
