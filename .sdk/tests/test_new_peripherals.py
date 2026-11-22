"""Contracts for canonical peripheral variants and generated project ownership."""

import tomllib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from riscv_tools.memory_map.core import load_platform, peripheral_list

from rv32_sdk import driver_metadata, drivers, platforms

ROOT = Path(__file__).resolve().parents[2]


def all_devices(root: Path) -> Path:
    """A compile-only map; it does not claim these devices share a board."""
    data = yaml.safe_load(
        (ROOT / "src/simulation/internal-mem/platform.yaml").read_text()
    )
    data["profiles"] = str(ROOT / "Core/profiles/matrix.yaml")
    data["checks"] = []
    entries = {}
    for index, (_descriptor, spec) in enumerate(drivers.descriptors(ROOT)):
        if not spec.get("instance_api"):
            continue
        entry = {
            "kind": spec["kinds"][0],
            "base": 0x81000000 + index * 0x100000,
            "size": "1M",
        }
        if spec["name"] == "MOUSE":
            entry["device"] = "mouse"
        if spec["name"] == "ADC":
            entry["chip"] = "adc128s022"
        if spec["name"] == "SPI":
            entry["cs_count"] = 2
        entries[spec["name"]] = entry
    data["peripherals"] = entries
    path = root / "platform.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path


class NewPeripheralsTest(unittest.TestCase):
    def test_all_new_families_generate_c_rust_dependencies_and_projects(self):
        with TemporaryDirectory() as temp:
            path = all_devices(Path(temp))
            for language in ("c", "rust"):
                files, meta = drivers.plan(ROOT, {"language": language}, path)
                self.assertEqual(
                    len(meta["sources"]), 19
                )  # USB has two C files.
                self.assertEqual(len(meta["example_projects"]), 18)
                for example in meta["example_projects"]:
                    prefix = example.removeprefix("vendor/")
                    config = tomllib.loads(
                        files[prefix + "/rv32.toml"].decode()
                    )["project"]
                    self.assertFalse(config["generate_driver_examples"])
                    self.assertIn(
                        prefix + "/.devcontainer/devcontainer.json", files
                    )
                    self.assertIn(prefix + "/.vscode/tasks.json", files)
                if language == "rust":
                    from rv32_sdk.rust_support import dependencies

                    deps = dependencies(files)
                    self.assertEqual(len(deps), 19)  # plus runtime
                    self.assertIn("insper-riscv-sd-spi", deps)
                    self.assertFalse(
                        any(name.endswith("-sys") for name in deps)
                    )

    def test_every_canonical_external_device_has_one_driver(self):
        specs = [spec for _, spec in drivers.descriptors(ROOT)]
        for name, path in platforms.board_choices(ROOT).items():
            platform = load_platform(path)
            for item in peripheral_list(platform):
                if item.get("kind"):
                    matches = [
                        s["name"]
                        for s in specs
                        if driver_metadata.matches(s, item)
                    ]
                    self.assertEqual(len(matches), 1, (name, item, matches))

    def test_board_views_preserve_map_and_generate_both_languages(self):
        for name, path in platforms.board_choices(ROOT).items():
            source = path.read_bytes()
            target = platforms.ensure_board(ROOT, name)
            self.assertEqual(path.read_bytes(), source)
            for language in ("c", "rust"):
                files, meta = drivers.plan(
                    ROOT,
                    {"language": language, "platform": name},
                    target / "platform.yaml",
                )
                self.assertTrue(meta["sources"])
                self.assertIn("rv32_platform.h", files)
            config = yaml.safe_load((target / "config.yaml").read_text())
            self.assertFalse(config["sdk_simulation_supported"])
            self.assertTrue((target / "runtime/boot_memory.ld").is_file())

    def test_adc_variants_gpio_groups_and_duplicate_instances(self):
        def generated(board):
            path = platforms.ensure_board(ROOT, board) / "platform.yaml"
            return drivers.plan(ROOT, {"platform": board}, path)[0]

        files = generated("periph-de10-lite")
        self.assertIn(
            b"RV32_ADC_BACKEND {1}", files["ADC/rv32_adc_platform.h"]
        )
        self.assertIn(
            b"RV32_ADC_CHANNELS {18}", files["ADC/rv32_adc_platform.h"]
        )
        files = generated("periph-de0-nano")
        self.assertIn(
            b"RV32_ADC_BACKEND {0}", files["ADC/rv32_adc_platform.h"]
        )
        self.assertIn(
            b"RV32_ADC_CHANNELS {8}", files["ADC/rv32_adc_platform.h"]
        )
        files = generated("periph-mkr-vidor-4000")
        self.assertIn(
            b"RV32_GPIO_GROUP_WIDTHS {7, 7, 25}",
            files["GPIO/rv32_gpio_platform.h"],
        )
        self.assertIn(
            b"RV32_PERIPH_GPIO_BASE + 128u", files["GPIO/rv32_gpio_platform.h"]
        )
        files = generated("periph-de2-115")
        self.assertIn(
            b"RV32_ETH_INSTANCE_COUNT 2", files["ETH/rv32_eth_platform.h"]
        )
        self.assertIn(
            b"RV32_I2C_INSTANCE_COUNT 2", files["I2C/rv32_i2c_platform.h"]
        )
        self.assertIn(
            b"RV32_UART_SERIAL_BACKEND RV32_UART_SERIAL",
            files["UART/rv32_uart_platform.h"],
        )
        self.assertNotIn(b"chip_hold_reset", files["USB/example/src/main.c"])

    def test_new_driver_edits_are_not_overwritten(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            files, meta = drivers.plan(
                ROOT, {"language": "rust"}, all_devices(root)
            )
            drivers.install(root, files, meta)
            path = root / "vendor/ADC/rv32_adc.c"
            path.write_text("user driver changes\n")
            before = (root / "vendor/.rv32-drivers.json").read_bytes()
            with self.assertRaisesRegex(SystemExit, "was edited"):
                drivers.install(root, files, meta)
            self.assertEqual(path.read_text(), "user driver changes\n")
            self.assertEqual(
                (root / "vendor/.rv32-drivers.json").read_bytes(), before
            )
