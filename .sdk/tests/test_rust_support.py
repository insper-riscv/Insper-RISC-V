"""Ensure Rust vendoring follows profiles and never overwrites user Cargo code."""

import json
import shutil
import tomllib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rv32_sdk import drivers

SDK = Path(__file__).resolve().parents[2]
PLATFORM = SDK / "src/simulation/modular/platform.yaml"


class RustSupportTest(unittest.TestCase):
    def project(self, root):
        shutil.copytree(SDK / "templates/rust", root, dirs_exist_ok=True)
        return {
            "language": "rust",
            "platform": "modular",
            "cpu_profile": "rv32im_zicsr_irq",
        }

    def test_generated_rust_crates_headers_and_examples(self):
        files, metadata = drivers.plan(
            SDK,
            {
                "language": "rust",
                "platform": "modular",
                "cpu_profile": "rv32im_zicsr_irq",
            },
            PLATFORM,
        )
        self.assertEqual(len(metadata["rust_dependencies"]), 7)
        self.assertEqual(len(metadata["example_projects"]), 6)
        for name in ("GPIO", "TIMER", "CLINT", "PLIC", "UART", "DISPLAY"):
            self.assertIn(
                f"{name}/rust/insper-riscv-{name.lower()}/Cargo.toml", files
            )
            self.assertIn(
                f"{name}/rust/insper-riscv-{name.lower()}-sys/build.rs", files
            )
            self.assertIn(f"{name}/example/src/main.rs", files)
            config = tomllib.loads(
                files[f"{name}/example/rv32.toml"].decode()
            )["project"]
            self.assertEqual(config["language"], "rust")
            self.assertFalse(config["generate_driver_examples"])
            self.assertIn(
                f"{name}/example/.devcontainer/devcontainer.json", files
            )
        uart = files["UART/rv32_uart_platform.h"].decode()
        self.assertIn("RV32_UART_SERIAL_BACKEND RV32_UART_SERIAL", uart)
        self.assertIn("RV32_UART_JTAG_BACKEND RV32_UART_JTAG", uart)

    def test_profile_switch_updates_only_managed_dependencies(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.project(root)
            cargo = root / "Cargo.toml"
            cargo.write_text(
                cargo.read_text()
                + '# User dependency stays intact\ncustom = "1"\n'
            )
            drivers.generate(SDK, root, project, PLATFORM)
            first = cargo.read_text()
            self.assertIn("insper-riscv-clint =", first)
            self.assertIn('custom = "1"', first)
            drivers.generate(SDK, root, project, PLATFORM)
            self.assertEqual(cargo.read_text(), first)
            project["cpu_profile"] = "rv32im"
            drivers.generate(SDK, root, project, PLATFORM)
            current = cargo.read_text()
            self.assertNotIn("insper-riscv-clint =", current)
            self.assertNotIn("insper-riscv-plic =", current)
            self.assertIn('custom = "1"', current)
            self.assertFalse(
                (
                    root / "vendor/CLINT/rust/insper-riscv-clint/src/lib.rs"
                ).exists()
            )

    def test_user_edits_to_generated_code_or_managed_dependencies_are_preserved(
        self,
    ):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.project(root)
            drivers.generate(SDK, root, project, PLATFORM)
            cargo = root / "Cargo.toml"
            before = cargo.read_text()
            driver = root / "vendor/GPIO/rust/insper-riscv-gpio/src/lib.rs"
            driver.write_text("// User code\n")
            with self.assertRaisesRegex(SystemExit, "was edited"):
                drivers.generate(SDK, root, project, PLATFORM)
            self.assertEqual(cargo.read_text(), before)
            self.assertEqual(driver.read_text(), "// User code\n")
        with TemporaryDirectory() as temp:
            root = Path(temp)
            project = self.project(root)
            drivers.generate(SDK, root, project, PLATFORM)
            cargo = root / "Cargo.toml"
            cargo.write_text(
                cargo.read_text().replace("vendor/rv32-runtime", "my-runtime")
            )
            before = cargo.read_text()
            with self.assertRaisesRegex(SystemExit, "dependency was edited"):
                drivers.generate(SDK, root, project, PLATFORM)
            self.assertEqual(cargo.read_text(), before)
            self.assertIsInstance(
                json.loads(
                    (root / ".rv32/rust-dependencies.json").read_text()
                ),
                dict,
            )
