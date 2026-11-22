"""Check benchmark origins against current and legacy platform maps."""

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from benchmarks.embench.run import HERE, Experiment, memory_bases, read_yaml


class PlatformTests(unittest.TestCase):
    """Use the same normalized memory map as the linker and RTL."""

    def resolve(self, platform: dict[str, Any]) -> tuple[int, int]:
        """Resolve a standalone platform fixture through real Tools."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "platform.yaml").write_text(json.dumps(platform))
            exp = Experiment(root, root, root, {"platform": "."}, {})
            return memory_bases(exp)

    def test_current_modular_platform(self) -> None:
        """Accept the main platform without the removed regions key."""
        root = HERE.parents[1]
        suite = read_yaml(HERE / "suite.yaml")
        exp = Experiment(root, root, root, suite, {})
        self.assertNotIn("regions", read_yaml(exp.platform / "platform.yaml"))
        self.assertEqual(memory_bases(exp), (0x1000, 0x100000))

    def test_legacy_region_names(self) -> None:
        """Keep the old ROM origin rather than padding it as FLASH."""
        self.assertEqual(
            self.resolve(
                {
                    "regions": [
                        {"name": "ROM", "base": 0x800, "size": "30K"},
                        {"name": "RAM", "base": 0x8000, "size": "160K"},
                    ],
                    "config": {"rom": "ROM", "ram": "RAM"},
                }
            ),
            (0x800, 0x8000),
        )

    def test_config_selects_regions_and_evaluates_addresses(self) -> None:
        """Follow configured names instead of a hard-coded ROM alias."""
        platform = {
            "regions": [
                {"name": "ROM", "base": 0, "size": "4K"},
                {"name": "CODE", "base": "4K", "size": "60K"},
                {"name": "DATA", "base": "64K", "size": "64K"},
            ],
            "config": {"rom": "CODE", "ram": "DATA"},
        }
        self.assertEqual(self.resolve(platform), (0x1000, 0x10000))

    def test_unknown_region_is_not_silently_zero(self) -> None:
        """Reject missing regions instead of assuming address zero."""
        with self.assertRaises(KeyError):
            self.resolve(
                {
                    "regions": [
                        {"name": "RAM", "base": 0x8000, "size": "32K"}
                    ],
                    "config": {"rom": "MISSING", "ram": "RAM"},
                }
            )


if __name__ == "__main__":
    unittest.main()
