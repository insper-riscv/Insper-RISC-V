"""Editor analysis follows the original sources and the selected target."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from rv32_sdk import editor


class EditorTest(unittest.TestCase):
    def config(self, root):
        source = root / "src/main.c"
        source.parent.mkdir()
        source.write_text(
            "#include <stdint.h>\nint main(void) { return 0; }\n"
        )
        extra = root / "src/another source.c"
        extra.write_text("int auxiliary(void) { return 0; }\n")
        return {
            "toolchain": {"gcc": "riscv32-unknown-elf-gcc"},
            "isa": {"base": "i", "default_ext": ""},
            "quartus": {"default_timeout_s": 15},
            "paths": {
                "sources": [str(extra)],
                "include_dir": str(root / ".rv32/include"),
                "include_dirs": [str(root / "my headers")],
            },
            "sdk_cpu_profile": {"march": "rv32im_zicond"},
        }

    def test_database_uses_original_sources_profile_and_header_directories(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            editor.configure(root, {"language": "c"}, self.config(root), "")
            records = json.loads(
                (root / ".rv32/compile_commands.json").read_text()
            )
            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["file"], str(root / "src/main.c"))
            self.assertIn("-march=rv32im_zicond", records[0]["arguments"])
            self.assertIn(f"-I{root / 'my headers'}", records[0]["arguments"])
            self.assertEqual(
                records[1]["arguments"][-1], str(root / "src/another source.c")
            )

    def test_rust_target_refresh_preserves_user_environment_and_settings(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = self.config(root)
            settings = root / ".vscode/settings.json"
            settings.parent.mkdir()
            original = '// user comment\n{"custom.url":"https://example.org/a//b", "rust-analyzer.cargo.extraEnv":{"MY_ENV":"keep"},}\n'
            settings.write_text(original)
            for target in [
                "riscv32i-unknown-none-elf",
                "riscv32im-unknown-none-elf",
            ]:
                editor.configure(root, {"language": "rust"}, cfg, target)
                actual = json.loads(settings.read_text())
                self.assertEqual(actual["rust-analyzer.cargo.target"], target)
                self.assertTrue(actual["rust-analyzer.cargo.targetDir"])
                self.assertIn("rust-analyzer.server.path", actual)
                self.assertFalse(actual["rust-analyzer.cfg.setTest"])
                self.assertFalse(actual["rust-analyzer.check.allTargets"])
                self.assertTrue(
                    actual["rust-analyzer.cargo.buildScripts.enable"]
                )
                self.assertEqual(
                    actual["rust-analyzer.cargo.extraEnv"]["MY_ENV"], "keep"
                )
                self.assertEqual(
                    actual["custom.url"], "https://example.org/a//b"
                )
            self.assertEqual(
                (root / ".rv32/editor-settings.before.jsonc").read_text(),
                original,
            )

    def test_unchanged_analysis_files_are_not_rewritten_on_each_build(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = self.config(root)
            editor.configure(root, {"language": "c"}, cfg, "")
            paths = [
                root / ".vscode/settings.json",
                root / ".rv32/compile_commands.json",
            ]
            times = [path.stat().st_mtime_ns for path in paths]
            editor.configure(root, {"language": "c"}, cfg, "")
            self.assertEqual(
                times, [path.stat().st_mtime_ns for path in paths]
            )

    def test_existing_container_keeps_other_extensions_and_gets_language_servers(
        self,
    ):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            cfg = self.config(root)
            metadata = root / ".devcontainer/devcontainer.json"
            metadata.parent.mkdir()
            metadata.write_text(
                json.dumps(
                    {
                        "remoteUser": "ubuntu",
                        "customizations": {
                            "vscode": {"extensions": ["my.existing-extension"]}
                        },
                    }
                )
            )
            editor.configure(
                root, {"language": "rust"}, cfg, "riscv32im-unknown-none-elf"
            )
            updated = json.loads(metadata.read_text())
            self.assertEqual(updated["remoteUser"], "ubuntu")
            self.assertEqual(
                updated["customizations"]["vscode"]["extensions"],
                [
                    "my.existing-extension",
                    "llvm-vs-code-extensions.vscode-clangd",
                    "rust-lang.rust-analyzer",
                ],
            )


if __name__ == "__main__":
    unittest.main()
