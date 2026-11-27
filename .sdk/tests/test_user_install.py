"""Exercise SDK registration against real host paths and Docker placeholders."""

import os
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rv32_sdk import source_check

ROOT = Path(__file__).resolve().parents[2]


class UserInstallTest(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(TemporaryDirectory()))
        self.home = self.folder / "home"
        self.home.mkdir()
        self.data = self.home / ".local/share"
        self.data.mkdir(parents=True)
        self.link = self.data / "rv32-sdk"
        self.sdk = self.folder / "SDK checkout"
        for name in source_check.REQUIRED_SOURCES:
            target = self.sdk / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch()
        scripts = self.sdk / "scripts"
        scripts.mkdir()
        shutil.copyfile(
            ROOT / "scripts/install-user.sh", scripts / "install-user.sh"
        )
        (scripts / "container-start.sh").write_text(
            "#!/bin/bash\nsleep infinity\n"
        )
        checker = self.sdk / ".sdk/rv32_sdk/source_check.py"
        checker.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / ".sdk/rv32_sdk/source_check.py", checker)
        self.env = dict(
            os.environ,
            HOME=str(self.home),
            XDG_DATA_HOME=str(self.data),
            XDG_CACHE_HOME=str(self.home / ".cache"),
        )

    def install(self, *arguments):
        return subprocess.run(
            ["bash", str(self.sdk / "scripts/install-user.sh"), *arguments],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def assert_registered(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.link.resolve(), self.sdk.resolve())
        self.assertTrue((self.link / "scripts/container-start.sh").is_file())

    def test_fresh_registration_is_idempotent(self):
        self.assert_registered(self.install())
        self.assert_registered(self.install())

    def test_empty_docker_placeholder_becomes_sdk_link(self):
        self.link.mkdir()
        self.assert_registered(self.install())
        self.assertTrue(self.link.is_symlink())

    def test_nested_link_from_old_installer_is_preserved_and_rejected(self):
        self.link.mkdir()
        nested = self.link / self.sdk.name
        nested.symlink_to(self.sdk)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Move it aside", result.stderr)
        self.assertTrue(nested.is_symlink())
        self.assertNotIn("RV32 SDK:", result.stdout)

    def test_nonempty_registration_preserves_user_files(self):
        self.link.mkdir()
        original = self.link / "program.c"
        original.write_text("keep this program")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(original.read_text(), "keep this program")
        self.assertFalse((self.link / self.sdk.name).exists())

    def test_regular_file_is_preserved(self):
        self.link.write_text("keep this file")
        self.assertNotEqual(self.install().returncode, 0)
        self.assertEqual(self.link.read_text(), "keep this file")

    def test_broken_link_is_repaired(self):
        self.link.symlink_to(self.folder / "missing")
        self.assert_registered(self.install())

    def test_previous_sdk_link_is_updated(self):
        previous = self.folder / "previous SDK"
        previous.mkdir()
        self.link.symlink_to(previous)
        self.assert_registered(self.install())
        self.assertTrue(previous.is_dir())

    def test_checkout_at_registration_path_stays_in_place(self):
        self.sdk.rename(self.link)
        self.sdk = self.link
        self.assert_registered(self.install())
        self.assertFalse(self.link.is_symlink())
        self.assertFalse((self.link / self.link.name).exists())

    def quartus_paths(self):
        quartus = self.folder / "Quartus installation"
        quartus.mkdir()
        target = self.data / "rv32-quartus"
        target.mkdir()
        return quartus, target

    def test_empty_quartus_placeholder_is_replaced(self):
        quartus, target = self.quartus_paths()
        self.assert_registered(self.install("--quartus", str(quartus)))
        self.assertTrue(target.is_symlink())
        self.assertEqual(target.resolve(), quartus)

    def test_nonempty_quartus_directory_is_preserved(self):
        quartus, target = self.quartus_paths()
        original = target / "keep.txt"
        original.write_text("keep")
        self.assertNotEqual(
            self.install("--quartus", str(quartus)).returncode, 0
        )
        self.assertEqual(original.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
