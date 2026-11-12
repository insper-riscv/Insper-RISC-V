"""Peripheral generation must follow maps and preserve project-owned files."""

import json
import tomllib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from rv32_sdk import cli, drivers

ROOT = Path(__file__).resolve().parents[2]


class DriversTest(unittest.TestCase):
    def test_modular_map_generates_two_instances_and_enabled_drivers(self):
        files, metadata = drivers.plan(
            ROOT,
            {"cpu_profile": "rv32im"},
            ROOT / "src/simulation/modular/platform.yaml",
        )
        self.assertEqual(
            {Path(source).parent.name for source in metadata["sources"]},
            {"DISPLAY", "GPIO", "TIMER", "UART"},
        )
        self.assertEqual(
            metadata["sources"].count("vendor/GPIO/rv32_gpio.c"), 1
        )
        self.assertIn(b"0x90000000", files["rv32_platform.h"])
        self.assertIn(b"0xA0000000", files["rv32_platform.h"])
        self.assertIn(
            b"RV32_GPIO_SWITCHES_BASE", files["GPIO/rv32_gpio_config.h"]
        )
        self.assertIn(b"RV32_GPIO_KEYS_IRQ", files["GPIO/rv32_gpio_config.h"])

    def test_each_enabled_driver_has_an_independent_example(self):
        project = {"platform": "modular", "cpu_profile": "rv32im_zicsr_irq"}
        platform = ROOT / "src/simulation/modular/platform.yaml"
        files, metadata = drivers.plan(ROOT, project, platform)
        self.assertEqual(len(metadata["example_projects"]), 6)
        for example in metadata["example_projects"]:
            prefix = example.removeprefix("vendor/")
            for name in (
                "rv32.toml",
                "src/main.c",
                ".devcontainer/devcontainer.json",
                ".devcontainer/compose.yaml",
                ".vscode/tasks.json",
                ".clang-format",
            ):
                self.assertIn(prefix + "/" + name, files)
            config = tomllib.loads(files[prefix + "/rv32.toml"].decode())[
                "project"
            ]
            self.assertEqual(config["platform"], "modular")
            self.assertEqual(config["cpu_profile"], "rv32im_zicsr_irq")
            self.assertFalse(config["generate_driver_examples"])
            child, child_meta = drivers.plan(ROOT, config, platform)
            self.assertEqual(child_meta["example_projects"], [])
            self.assertFalse(any("/example/" in name for name in child))
            self.assertNotIn(b"@", files[prefix + "/src/main.c"])
        self.assertFalse(
            any("/example/" in name for name in metadata["sources"])
        )

    def test_example_generation_can_be_disabled_and_edits_survive(self):
        platform = ROOT / "src/simulation/modular/platform.yaml"
        files, metadata = drivers.plan(
            ROOT, {"generate_driver_examples": False}, platform
        )
        self.assertEqual(metadata["example_projects"], [])
        self.assertFalse(any("/example/" in name for name in files))
        with self.assertRaisesRegex(SystemExit, "generate_driver_examples"):
            drivers.plan(ROOT, {"generate_driver_examples": "yes"}, platform)
        with TemporaryDirectory() as temp:
            files, metadata = drivers.plan(ROOT, {}, platform)
            root = Path(temp)
            drivers.install(root, files, metadata)
            example = root / "vendor/GPIO/example/src/main.c"
            example.write_text("// user example\n")
            with self.assertRaisesRegex(SystemExit, "was edited"):
                drivers.install(root, files, metadata)
            self.assertEqual(example.read_text(), "// user example\n")

    def test_legacy_slot_four_is_serial_not_jtag(self):
        files, metadata = drivers.plan(
            ROOT, {}, ROOT / "src/simulation/internal-mem/platform.yaml"
        )
        self.assertEqual(metadata["example_projects"], ["vendor/UART/example"])
        self.assertIn(
            b"RV32_UART_SERIAL, 16", files["UART/example/src/main.c"]
        )

    def test_jtag_and_flash_examples_use_the_actual_backend_and_no_erase(self):
        files, metadata = drivers.plan(
            ROOT,
            {"platform": "de0-cv"},
            ROOT / "src/cyclone-v/de0-cv/platform.yaml",
        )
        self.assertIn("vendor/FLASH/example", metadata["example_projects"])
        uart = files["UART/example/src/main.c"]
        self.assertIn(b"RV32_UART_JTAG, 64", uart)
        flash = files["FLASH/example/src/main.c"]
        self.assertIn(b"rv32_flash_busy", flash)
        self.assertNotIn(b"rv32_flash_submit", flash)

    def test_uart_only_platform_does_not_invent_gpio(self):
        files, metadata = drivers.plan(
            ROOT, {}, ROOT / "src/cyclone-v/fpga-uart-jtag/platform.yaml"
        )
        self.assertEqual(metadata["sources"], ["vendor/UART/rv32_uart.c"])
        self.assertIn("UART/rv32_uart_config.h", files)
        self.assertFalse(any(name.startswith("GPIO/") for name in files))
        self.assertIn(b"0xC0000000", files["rv32_platform.h"])
        self.assertNotIn(b"GPIO", files["rv32_platform.h"])

    def test_absolute_address_uses_canonical_map_resolver(self):
        with TemporaryDirectory() as temp:
            platform = yaml.safe_load(
                (
                    ROOT / "src/simulation/internal-mem/platform.yaml"
                ).read_text()
            )
            platform["profiles"] = str(ROOT / "Core/profiles/matrix.yaml")
            platform["peripherals"] = [
                {"name": "GPIO", "base": 0xA0000000, "id": 2, "size": 64}
            ]
            path = Path(temp) / "platform.yaml"
            path.write_text(yaml.safe_dump(platform))
            files, _ = drivers.plan(ROOT, {}, path)
            self.assertIn(
                b"RV32_PERIPH_GPIO_BASE UINT32_C(0xA0000000)",
                files["rv32_platform.h"],
            )

    def test_edited_driver_is_not_overwritten_and_other_files_survive(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            files, metadata = drivers.plan(
                ROOT, {}, ROOT / "src/simulation/modular/platform.yaml"
            )
            drivers.install(root, files, metadata)
            custom = root / "vendor/custom.c"
            custom.write_text("user source")
            modified = root / "vendor/GPIO/rv32_gpio.c"
            modified.write_text("my edits")
            before = (root / "vendor/.rv32-drivers.json").read_bytes()
            with self.assertRaisesRegex(SystemExit, "was edited"):
                drivers.install(root, files, metadata)
            self.assertEqual(modified.read_text(), "my edits")
            self.assertEqual(custom.read_text(), "user source")
            self.assertEqual(
                (root / "vendor/.rv32-drivers.json").read_bytes(), before
            )

    def test_regeneration_removes_only_old_owned_files(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            files, metadata = drivers.plan(
                ROOT, {}, ROOT / "src/simulation/modular/platform.yaml"
            )
            drivers.install(root, files, metadata)
            custom = root / "vendor/GPIO/custom.h"
            custom.write_text("user header")
            files, metadata = drivers.plan(
                ROOT, {}, ROOT / "src/simulation/internal-mem/platform.yaml"
            )
            drivers.install(root, files, metadata)
            self.assertFalse((root / "vendor/GPIO/rv32_gpio.c").exists())
            self.assertEqual(custom.read_text(), "user header")
            self.assertEqual(
                json.loads((root / "vendor/.rv32-drivers.json").read_text())[
                    "sources"
                ],
                ["vendor/UART/rv32_uart.c"],
            )

    def test_unmanaged_and_symlink_paths_are_rejected(self):
        for symlink in (False, True):
            with self.subTest(symlink=symlink), TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "vendor").mkdir()
                if symlink:
                    (root / "vendor/rv32_platform.h").symlink_to(
                        root / "untouched"
                    )
                else:
                    (root / "vendor/rv32_platform.h").write_text("custom")
                files, metadata = drivers.plan(
                    ROOT,
                    {},
                    ROOT / "src/simulation/internal-mem/platform.yaml",
                )
                with self.assertRaises(SystemExit):
                    drivers.install(root, files, metadata)
        for value in ("../escape", "/absolute"):
            with self.assertRaises(SystemExit):
                drivers.relative_file(value)

    def test_build_links_driver_and_invalid_flag_is_rejected(self):
        with TemporaryDirectory() as temp, patch.object(cli, "SDK", ROOT):
            root = Path(temp)
            cfg = cli.load_config(
                cli.write_config(
                    root,
                    {
                        "language": "c",
                        "platform": "modular",
                        "cpu_profile": "rv32im",
                        "generate_drivers": True,
                    },
                    simulation=True,
                )
            )
            self.assertIn(
                str(root / "vendor/GPIO/rv32_gpio.c"), cfg["paths"]["sources"]
            )
            self.assertIn(
                str(root / "vendor/GPIO"), cfg["paths"]["include_dirs"]
            )
            for value in (1, "yes"):
                with self.assertRaises(SystemExit):
                    cli.write_config(
                        root, {"language": "c", "generate_drivers": value}
                    )
            with self.assertRaisesRegex(SystemExit, "simulation-only"):
                cli.fpga(
                    root, {"language": "c", "platform": "modular"}, "fast"
                )

    def test_irq_source_id_is_not_the_peripheral_slot_id(self):
        files, _ = drivers.plan(
            ROOT, {}, ROOT / "src/simulation/modular/platform.yaml"
        )
        self.assertIn(
            b"RV32_PERIPH_SWITCHES_IRQ UINT32_C(3)", files["rv32_platform.h"]
        )
        self.assertIn(
            b"RV32_PERIPH_KEYS_IRQ UINT32_C(4)", files["rv32_platform.h"]
        )

    def test_interrupt_fabric_follows_the_actual_cpu_profile(self):
        files, metadata = drivers.plan(
            ROOT,
            {"cpu_profile": "rv32im_zicsr_irq"},
            ROOT / "src/simulation/modular/platform.yaml",
        )
        self.assertIn("vendor/CLINT/rv32_clint.c", metadata["sources"])
        self.assertIn("vendor/PLIC/rv32_plic.c", metadata["sources"])
        files, metadata = drivers.plan(
            ROOT,
            {"cpu_profile": "rv32im"},
            ROOT / "src/simulation/modular/platform.yaml",
        )
        self.assertNotIn("vendor/CLINT/rv32_clint.c", metadata["sources"])
        self.assertNotIn("PLIC/rv32_plic.h", files)
        self.assertIn(b"RV32_PERIPH_PLIC_BASE", files["rv32_platform.h"])

    def test_flash_controller_and_console_irq_aliases(self):
        files, metadata = drivers.plan(
            ROOT, {}, ROOT / "src/cyclone-v/de0-cv/platform.yaml"
        )
        self.assertIn("vendor/FLASH/rv32_flash.c", metadata["sources"])
        self.assertIn(
            b"RV32_FLASH_FLASH_CTRL_BASE", files["FLASH/rv32_flash_config.h"]
        )
        self.assertIn(
            b"RV32_PERIPH_FLASH_CTRL_IRQ UINT32_C(6)",
            files["rv32_platform.h"],
        )
        self.assertIn(
            b"RV32_PERIPH_UART_IRQ UINT32_C(2)", files["rv32_platform.h"]
        )
        self.assertNotIn("GPIO/rv32_gpio.c", files)

    def test_driver_base_follows_changed_platform_offset(self):
        with TemporaryDirectory() as temp:
            platform = yaml.safe_load(
                (ROOT / "src/simulation/modular/platform.yaml").read_text()
            )
            platform["profiles"] = str(ROOT / "Core/profiles/matrix.yaml")
            switches = platform["peripherals"][1]
            switches.pop("offset")
            switches["base"] = 0x90000100
            switches["padding"] -= 0x100
            path = Path(temp) / "platform.yaml"
            path.write_text(yaml.safe_dump(platform))
            files, _ = drivers.plan(ROOT, {}, path)
            self.assertIn(
                b"RV32_PERIPH_SWITCHES_BASE UINT32_C(0x90000100)",
                files["rv32_platform.h"],
            )
            self.assertNotIn(b"0x90000000", files["rv32_platform.h"])

    def test_too_small_window_and_corrupt_ownership_are_rejected(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            platform = yaml.safe_load(
                (
                    ROOT / "src/simulation/internal-mem/platform.yaml"
                ).read_text()
            )
            platform["profiles"] = str(ROOT / "Core/profiles/matrix.yaml")
            platform["peripherals"] = [
                {"name": "GPIO", "base": 0xA0000000, "id": 2, "size": 32}
            ]
            path = root / "platform.yaml"
            path.write_text(yaml.safe_dump(platform))
            with self.assertRaisesRegex(SystemExit, "too small"):
                drivers.plan(ROOT, {}, path)
            (root / "vendor").mkdir()
            outside = root / "outside.h"
            outside.write_text("user data")
            (root / "vendor/.rv32-drivers.json").write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "files": {
                            "../outside.h": drivers.digest(
                                outside.read_bytes()
                            )
                        },
                    }
                )
            )
            files, metadata = drivers.plan(
                ROOT, {}, ROOT / "src/simulation/internal-mem/platform.yaml"
            )
            with self.assertRaisesRegex(SystemExit, "Unsafe"):
                drivers.install(root, files, metadata)
            self.assertEqual(outside.read_text(), "user data")
