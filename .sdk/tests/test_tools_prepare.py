"""Tools dependency upgrades preserve the previous checkout and roll back."""

import importlib.util
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

PREPARE = Path(__file__).resolve().parents[1] / "prepare_tools.py"
spec = importlib.util.spec_from_file_location("sdk_prepare_upgrade", PREPARE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ToolsActivationTest(unittest.TestCase):
    def test_upgrade_preserves_modified_old_checkout(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "tools"
            old.mkdir()
            (old / "local-change.txt").write_text("preserve me")
            staged = root / "staging"
            staged.mkdir()
            (staged / "new-version.txt").write_text("new")
            with patch.object(module, "ROOT", root):
                module.activate(staged, old, io.StringIO())
            self.assertTrue((old / "new-version.txt").is_file())
            saved = list(root.glob(".tools-backup-*/tools/local-change.txt"))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0].read_text(), "preserve me")

    def test_activation_failure_restores_previous_checkout(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "tools"
            old.mkdir()
            (old / "original.txt").write_text("old")
            staged = root / "staging"
            staged.mkdir()
            rename = Path.rename

            def fail_staging(path, target):
                if path == staged:
                    raise OSError("activation failed")
                return rename(path, target)

            with (
                patch.object(module, "ROOT", root),
                patch.object(Path, "rename", fail_staging),
            ):
                with self.assertRaisesRegex(OSError, "activation failed"):
                    module.activate(staged, old, io.StringIO())
            self.assertEqual((old / "original.txt").read_text(), "old")
            self.assertTrue(staged.is_dir())


if __name__ == "__main__":
    unittest.main()
