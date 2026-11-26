"""Container extension setup must not race Dev Containers' language packs."""

import json
import os
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/install-vscode-extension.sh"

FAKE_SERVER = """#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

state = Path(os.environ["RV32_TEST_STATE"])
args = sys.argv[1:]
with (state / "calls.jsonl").open("a") as log:
    log.write(json.dumps(args) + "\\n")
installed = state / "installed"
if "--list-extensions" in args:
    if installed.exists():
        print(installed.read_text())
elif "--install-extension" in args:
    if "--do-not-include-pack-dependencies" not in args:
        print("ENOTEMPTY: competing language extension install", file=sys.stderr)
        sys.exit(1)
    if os.environ.get("RV32_TEST_INSTALL_FAIL"):
        print("RV32 VSIX installation failed", file=sys.stderr)
        sys.exit(2)
    time.sleep(0.15)
    installed.write_text("insper-riscv.rv32-development@42.0.0")
else:
    sys.exit(3)
"""


class ContainerExtensionInstallTest(unittest.TestCase):
    def fixture(self, root):
        sdk = root / "sdk"
        (sdk / "share").mkdir(parents=True)
        with zipfile.ZipFile(sdk / "share/rv32-development.vsix", "w") as vsix:
            vsix.writestr("extension/package.json", json.dumps({"version": "42.0.0"}))
        agent = root / "agent"
        server = agent / "bin/test/bin/code-server"
        server.parent.mkdir(parents=True)
        server.write_text(FAKE_SERVER)
        server.chmod(0o755)
        return {
            **os.environ,
            "RV32_SDK_ROOT": str(sdk),
            "VSCODE_AGENT_FOLDER": str(agent),
            "RV32_TEST_STATE": str(root),
        }

    def calls(self, root):
        return [
            json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()
        ]

    def test_installs_only_rv32_without_pack_dependencies(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.fixture(root)
            subprocess.run(["bash", str(SCRIPT)], env=env, check=True)
            installs = [
                call for call in self.calls(root) if "--install-extension" in call
            ]
            self.assertEqual(len(installs), 1)
            self.assertIn("--do-not-include-pack-dependencies", installs[0])

    def test_post_create_and_post_attach_do_not_install_concurrently(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.fixture(root)
            first = subprocess.Popen(["bash", str(SCRIPT)], env=env)
            second = subprocess.Popen(["bash", str(SCRIPT)], env=env)
            self.assertEqual(first.wait(timeout=15), 0)
            self.assertEqual(second.wait(timeout=15), 0)
            installs = [
                call for call in self.calls(root) if "--install-extension" in call
            ]
            self.assertEqual(len(installs), 1)

    def test_installed_version_is_idempotent(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.fixture(root)
            (root / "installed").write_text("insper-riscv.rv32-development@42.0.0")
            subprocess.run(["bash", str(SCRIPT)], env=env, check=True)
            self.assertFalse(
                any("--install-extension" in call for call in self.calls(root))
            )

    def test_real_rv32_install_failure_is_not_suppressed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            env = self.fixture(root)
            env["RV32_TEST_INSTALL_FAIL"] = "1"
            result = subprocess.run(
                ["bash", str(SCRIPT)], env=env, capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("RV32 VSIX installation failed", result.stderr)
            self.assertFalse((root / "installed").exists())


if __name__ == "__main__":
    unittest.main()
