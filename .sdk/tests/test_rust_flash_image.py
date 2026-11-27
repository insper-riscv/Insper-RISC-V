"""Rust banked-image packaging uses the same boot contract as C."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from riscv_tools import flash_image
from riscv_tools.rom_writer.core import mif_words

from rv32_sdk import cli


class RustFlashImageTest(unittest.TestCase):
    def test_de0_cv_preserves_both_sdram_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = cli.load_config(
                cli.write_config(
                    Path(directory), {"platform": "de0-cv", "language": "rust"}
                )
            )
            windows = cfg["memory"]["sdram_windows"]
            self.assertEqual(windows["FLASH"]["offset"], 0x1000)
            self.assertEqual(windows["RAM"]["offset"], 32 * 1024 * 1024)
            self.assertEqual(cfg["quartus"]["rom_write_method"], "sdram_debug")

    def package(self, root, banked, origin=0):
        executable = root / "firmware.elf"
        executable.write_bytes(b"ELF stub")
        payload = bytes.fromhex("1300000067800000")
        cfg = {
            "toolchain": {"objcopy": "objcopy"},
            "memory": {
                "rom_base": 4096,
                "rom_words": 16384,
                "rom_origin": origin,
            },
            "quartus": {"default_timeout_s": 15},
            "sim": {"hex_format": "words"},
        }
        if banked:
            cfg["flash_image"] = {"bank": "A", "version": 7}
            cfg["flash"] = {
                "banks": [{"name": "A", "base": 4096, "size": 65536}]
            }

        def objcopy(command, **kwargs):
            Path(command[-1]).write_bytes(payload)

        with (
            patch.object(cli, "load_config", return_value=cfg),
            patch.object(cli, "cargo_elf", return_value=executable),
            patch.object(cli, "run", side_effect=objcopy),
        ):
            cli.package_rust(
                root, {"name": "app"}, root / "config.yaml", "mif"
            )
        return payload, root / "build/real"

    def test_banked_image_has_valid_header_and_payload_at_bank_offset(self):
        with tempfile.TemporaryDirectory() as directory:
            payload, out = self.package(Path(directory), True)
            packed = (out / "app.image.bin").read_bytes()
            flash_image.verify(packed)
            self.assertEqual(packed[flash_image.HEADER_SIZE :], payload)
            words = mif_words(out / "app.mif")
            image = b"".join(w.to_bytes(4, "little") for w in words)
            self.assertEqual(image[4096 : 4096 + len(packed)], packed)

    def test_nonbanked_image_keeps_raw_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            payload, out = self.package(Path(directory), False)
            words = mif_words(out / "app.mif")
            image = b"".join(w.to_bytes(4, "little") for w in words)
            self.assertEqual(image[4096 : 4096 + len(payload)], payload)
            self.assertFalse((out / "app.image.bin").exists())

    def test_separate_flash_origin_does_not_add_boot_padding(self):
        with tempfile.TemporaryDirectory() as directory:
            payload, out = self.package(Path(directory), False, origin=4096)
            words = mif_words(out / "app.mif")
            self.assertEqual(words[0], int.from_bytes(payload[:4], "little"))


if __name__ == "__main__":
    unittest.main()
