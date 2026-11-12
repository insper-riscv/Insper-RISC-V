"""Peripheral generation must follow maps and preserve project-owned files."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from rv32_sdk import cli, drivers

ROOT = Path(__file__).resolve().parents[2]


class DriversTest(unittest.TestCase):
    def test_modular_map_generates_two_instances_and_one_driver(self):
        files, metadata = drivers.plan(
            ROOT,
            {"cpu_profile": "rv32im"},
            ROOT / "src/simulation/modular/platform.yaml",
        )
        self.assertEqual(metadata["sources"], ["vendor/GPIO/rv32_gpio.c"])
        self.assertIn(b"0x90000000", files["rv32_platform.h"])
        self.assertIn(b"0xA0000000", files["rv32_platform.h"])
        self.assertIn(
            b"RV32_GPIO_SWITCHES_BASE", files["GPIO/rv32_gpio_config.h"]
        )
        self.assertIn(b"RV32_GPIO_KEYS_IRQ", files["GPIO/rv32_gpio_config.h"])

    def test_uart_only_platform_does_not_invent_gpio(self):
        files, metadata = drivers.plan(
            ROOT, {}, ROOT / "src/cyclone-v/fpga-uart-jtag/platform.yaml"
        )
        self.assertEqual(metadata["sources"], [])
        self.assertEqual(set(files), {"rv32_platform.h"})
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
                [],
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
