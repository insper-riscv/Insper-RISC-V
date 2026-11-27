"""Upgrade the generated Tools cache without losing the previous checkout."""

import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "sdk_prepare_tools",
    Path(__file__).resolve().parents[1] / "prepare_tools.py",
)
assert SPEC and SPEC.loader
prepare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare)


class PrepareToolsTest(unittest.TestCase):
    def setUp(self):
        root = Path(
            self.enterContext(
                TemporaryDirectory(prefix="SDK cache with spaces ")
            )
        )
        self.sdk = root / ".sdk"
        (self.sdk / "patches").mkdir(parents=True)
        self.origin = root / "upstream"
        self.origin.mkdir()
        self.git("init", "--quiet")
        (self.origin / "compat.txt").write_text("original\n")
        (self.origin / "payload.txt").write_text("first\n")
        self.first = self.commit()
        (self.origin / "payload.txt").write_text("second\n")
        self.second = self.commit()
        (self.sdk / "patches/tools-sdk.patch").write_text(
            "diff --git a/compat.txt b/compat.txt\n"
            "--- a/compat.txt\n+++ b/compat.txt\n"
            "@@ -1 +1 @@\n-original\n+patched\n"
        )
        self.addCleanup(patch.stopall)
        patch.object(prepare, "ROOT", self.sdk).start()
        self.select(self.first)

    def git(self, *arguments):
        return subprocess.check_output(
            ["git", *arguments], cwd=self.origin, text=True
        ).strip()

    def commit(self):
        self.git("add", ".")
        self.git(
            "-c",
            "user.name=SDK Test",
            "-c",
            "user.email=sdk@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "--quiet",
            "-m",
            "fixture",
        )
        return self.git("rev-parse", "HEAD")

    def select(self, revision):
        (self.sdk / "dependencies.json").write_text(
            json.dumps(
                {"tools": {"url": str(self.origin), "revision": revision}}
            )
        )

    def test_fresh_install_applies_patch_and_matching_cache_is_noop(self):
        prepare.main()
        target = self.sdk / "tools"
        self.assertEqual((target / "compat.txt").read_text(), "patched\n")
        self.assertEqual((target / "payload.txt").read_text(), "first\n")
        with patch.object(prepare.subprocess, "run") as run:
            prepare.main()
        run.assert_not_called()
        self.assertEqual(list(self.sdk.glob(".tools-backup-*")), [])

    def test_revision_upgrade_preserves_edited_and_untracked_files(self):
        prepare.main()
        target = self.sdk / "tools"
        (target / "payload.txt").write_text("local changes\n")
        (target / "user-notes.txt").write_text("keep me\n")
        self.select(self.second)
        prepare.main()
        self.assertEqual((target / "payload.txt").read_text(), "second\n")
        self.assertEqual((target / "compat.txt").read_text(), "patched\n")
        backups = list(self.sdk.glob(".tools-backup-*/tools"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(
            (backups[0] / "payload.txt").read_text(), "local changes\n"
        )
        self.assertEqual(
            (backups[0] / "user-notes.txt").read_text(), "keep me\n"
        )

    def test_patch_upgrade_and_corrupt_marker_are_recoverable(self):
        prepare.main()
        patch_file = self.sdk / "patches/tools-sdk.patch"
        patch_file.write_text(
            patch_file.read_text().replace("+patched", "+new patch")
        )
        prepare.main()
        target = self.sdk / "tools"
        self.assertEqual((target / "compat.txt").read_text(), "new patch\n")
        (target / ".rv32-sdk.json").write_text("incomplete json")
        prepare.main()
        self.assertEqual((target / "compat.txt").read_text(), "new patch\n")
        self.assertEqual(len(list(self.sdk.glob(".tools-backup-*"))), 2)

    def test_failed_download_or_patch_leaves_current_cache_untouched(self):
        for failure in ("fetch", "patch"):
            with self.subTest(failure=failure):
                self.select(self.first)
                prepare.main()
                target = self.sdk / "tools"
                before = (target / ".rv32-sdk.json").read_bytes()
                if failure == "fetch":
                    self.select("f" * 40)
                else:
                    (self.sdk / "patches/tools-sdk.patch").write_text(
                        "invalid patch\n"
                    )
                with self.assertRaisesRegex(SystemExit, "Tools setup failed"):
                    prepare.main()
                self.assertEqual(
                    (target / ".rv32-sdk.json").read_bytes(), before
                )
                self.assertEqual(
                    (target / "payload.txt").read_text(), "first\n"
                )
                self.assertEqual(list(self.sdk.glob(".tools-backup-*")), [])

    def test_activation_failure_restores_previous_checkout(self):
        target = self.sdk / "tools"
        target.mkdir()
        (target / "notes").write_text("keep me")
        with self.assertRaises(OSError):
            prepare.activate(
                self.sdk / "missing staging", target, io.StringIO()
            )
        self.assertEqual((target / "notes").read_text(), "keep me")
