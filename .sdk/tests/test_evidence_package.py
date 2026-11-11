"""Check evidence integrity and restore the original runnable audit protocols."""

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

ROOT = (
    Path(__file__).resolve().parents[1]
    / "benchmarks/results/evidence-2026-11-10"
)
spec = importlib.util.spec_from_file_location(
    "package_integrity", ROOT / "verify.py"
)
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class EvidencePackageTest(TestCase):
    def test_restored_protocols_keep_bytes_and_audit_both_datasets(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            restored = root / "evidence"
            package.restore(ROOT, restored)
            migration = json.loads((ROOT / "snapshot-paths.json").read_text())
            for item in migration["snapshots"]:
                data = (restored / item["original_path"]).read_bytes()
                self.assertEqual(
                    hashlib.sha256(data).hexdigest(), item["sha256"]
                )
            for command in [
                [
                    str(
                        restored
                        / "physical-expanded/protocol/audit_physical.py"
                    ),
                    str(restored / "physical-expanded"),
                ],
                [
                    str(restored / "protocol/audit_comparisons.py"),
                    *[
                        str(restored / "comparisons" / f"repetition-{i}.json")
                        for i in (1, 2, 3)
                    ],
                    "--output",
                    str(root / "audit"),
                ],
            ]:
                result = subprocess.run(
                    [sys.executable, *command],
                    text=True,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            package.verify(restored)
            package.verify(ROOT)

    def test_tampering_with_a_raw_measurement_is_rejected(self):
        with TemporaryDirectory() as temporary:
            copied = Path(temporary) / "evidence"
            shutil.copytree(
                ROOT, copied, ignore=shutil.ignore_patterns("__pycache__")
            )
            path = copied / "comparisons/repetition-1.json"
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                package.verify(copied)

    def test_restoration_does_not_overwrite_existing_directory(self):
        with TemporaryDirectory() as temporary:
            destination = Path(temporary)
            marker = destination / "keep.txt"
            marker.write_text("keep")
            with self.assertRaises(FileExistsError):
                package.restore(ROOT, destination)
            self.assertEqual(marker.read_text(), "keep")

    def test_restoration_cannot_recurse_into_the_source_package(self):
        with self.assertRaisesRegex(ValueError, "outside the evidence"):
            package.restore(ROOT, ROOT / "nested-copy")
