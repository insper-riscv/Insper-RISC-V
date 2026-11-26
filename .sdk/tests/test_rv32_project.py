from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / ".sdk" / "tools" / "src"))
os.environ["RV32_SDK_ROOT"] = str(ROOT)
SPEC = importlib.util.spec_from_file_location(
    "rv32_project", ROOT / ".sdk" / "rv32_sdk" / "cli.py"
)
assert SPEC and SPEC.loader
rv32_project = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rv32_project)


class ExternalProjectTest(unittest.TestCase):
    def test_header_directories_resolve_from_project_root(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            (root / "include").mkdir()
            (root / "vendor headers").mkdir()
            config = rv32_project.load_config(
                rv32_project.write_config(
                    root,
                    {
                        "language": "c",
                        "include_dirs": ["include", "vendor headers"],
                    },
                )
            )
            from riscv_tools.cli.toolchain import build_setup

            expected = [root / "include", root / "vendor headers"]
            self.assertEqual(build_setup(config, root).include_dirs, expected)

    def test_invalid_header_directories_are_rejected(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            for value in ["include", [3], [""], ["does-not-exist"]]:
                with self.subTest(value=value), self.assertRaises(SystemExit):
                    rv32_project.write_config(
                        root, {"language": "c", "include_dirs": value}
                    )

    def test_c_project_uses_external_build_paths(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            project_root = Path(directory)
            (project_root / "src").mkdir()
            (project_root / "src" / "main.c").write_text(
                "int main(void){return 0;}\n"
            )
            (project_root / "rv32.toml").write_text(
                '[project]\nname="demo"\nlanguage="c"\nsource="src/main.c"\n'
            )
            project = rv32_project.read_project(project_root)
            config_path = rv32_project.write_config(project_root, project)
            rv32_project.prepare_c_source(project_root, project)
            config = rv32_project.load_config(config_path)

            self.assertEqual(
                Path(config["paths"]["build_dir"]), project_root / "build"
            )
            self.assertTrue(
                (
                    project_root / ".rv32" / "sources" / "c" / "demo" / "src.c"
                ).is_file()
            )
            self.assertTrue(Path(config["paths"]["sources"][0]).is_absolute())

    def test_simulation_cycle_limit_is_persisted_in_generated_config(
        self,
    ) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            project = {"language": "c"}
            config = rv32_project.load_config(
                rv32_project.write_config(root, project)
            )
            self.assertEqual(
                config["sim"]["env"]["SIM_TIMEOUT_CYCLES"], "2000000"
            )
            project["simulation_timeout_cycles"] = 4000000
            config = rv32_project.load_config(
                rv32_project.write_config(root, project)
            )
            self.assertEqual(
                config["sim"]["env"]["SIM_TIMEOUT_CYCLES"], "4000000"
            )

    def test_invalid_simulation_cycle_limit_is_rejected(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            for value in [0, -1, True, "2000000", 1.5]:
                with self.subTest(value=value), self.assertRaises(SystemExit):
                    rv32_project.write_config(
                        Path(directory),
                        {"language": "c", "simulation_timeout_cycles": value},
                    )

    def test_empty_stdout_ignores_old_payload_bytes(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            output = io.StringIO()
            project = {"language": "c"}
            # Old RAM payload exists, but the boot ROM cleared length/truncated.
            words = [0, 0, 0x4F4C4C45] + [0] * 255
            with (
                patch.object(rv32_project, "doctor"),
                patch.object(
                    rv32_project, "detect_jtag_hardware", return_value="cable"
                ),
                patch.object(
                    rv32_project.ram_target, "read_words", return_value=words
                ),
                redirect_stdout(output),
            ):
                rv32_project.read_stdout(Path(directory), project)
            self.assertEqual(output.getvalue(), "")

    def test_stdout_text_is_decoded_in_little_endian_byte_order(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            output = io.StringIO()
            words = [3, 0, 0x000A6948] + [0] * 255
            with (
                patch.object(rv32_project, "doctor"),
                patch.object(
                    rv32_project, "detect_jtag_hardware", return_value="cable"
                ),
                patch.object(
                    rv32_project.ram_target,
                    "read_words",
                    side_effect=[words[:2], words[2:]],
                ),
                redirect_stdout(output),
            ):
                rv32_project.read_stdout(Path(directory), {"language": "c"})
            self.assertEqual(output.getvalue(), "Hi\n")

    def test_explicit_project_argument_overrides_environment(self) -> None:
        os.environ["RV32_PROJECT_ROOT"] = "/ignored"
        try:
            selected = rv32_project.project_root(str(ROOT))
        finally:
            os.environ.pop("RV32_PROJECT_ROOT")
        self.assertEqual(selected, ROOT)

    def test_templates_define_both_languages(self) -> None:
        c_project = rv32_project.read_project(ROOT / "templates" / "c")
        rust_project = rv32_project.read_project(ROOT / "templates" / "rust")
        self.assertEqual(c_project["language"], "c")
        self.assertEqual(rust_project["language"], "rust")
        self.assertTrue(
            (ROOT / "templates" / "rust" / "src" / "main.rs").is_file()
        )

    def test_external_container_uses_registered_sdk_without_build(
        self,
    ) -> None:
        compose = (
            ROOT / "templates" / "common" / ".devcontainer" / "compose.yaml"
        ).read_text()
        self.assertIn("image:", compose)
        self.assertNotIn("    build:", compose)
        self.assertIn("${HOME}/.local/share/rv32-sdk", compose)
        self.assertNotIn("RV32_SDK_ROOT:?", compose)
        self.assertIn("${HOME}/.cache/rv32:/home/ubuntu/.cache", compose)
        self.assertIn("RV32_SOF_CACHE_DIR: /home/ubuntu/.cache/sof", compose)
        self.assertNotIn(":/home/ubuntu/.cache/rv32/sof", compose)

    def test_rust_linker_discards_bare_metal_suppression_flags(self) -> None:
        with TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "linker-arguments.txt"
            fake_gcc = Path(directory) / "fake-gcc"
            fake_gcc.write_text(
                '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$RV32_LINKER_TEST_OUTPUT"\n'
            )
            fake_gcc.chmod(0o755)
            env = {
                **os.environ,
                "RV32_GCC": str(fake_gcc),
                "RV32_RUST_SPECS": "/sdk/platform.specs",
                "RV32_RUST_EXIT_OBJ": "/sdk/exit.o",
                "RV32_RUST_STDIO_OBJ": "/sdk/stdio.o",
                "RV32_LINKER_TEST_OUTPUT": str(output),
            }
            subprocess.run(
                [
                    str(ROOT / "scripts" / "rv32-rust-linker"),
                    "-nostartfiles",
                    "-nodefaultlibs",
                    "-nostdlib",
                    "app.o",
                ],
                env=env,
                check=True,
            )
            arguments = output.read_text().splitlines()
            self.assertNotIn("-nostartfiles", arguments)
            self.assertNotIn("-nodefaultlibs", arguments)
            self.assertNotIn("-nostdlib", arguments)
            self.assertIn("--specs=/sdk/platform.specs", arguments)
            self.assertIn("app.o", arguments)
            self.assertEqual(arguments[-2:], ["/sdk/exit.o", "/sdk/stdio.o"])


if __name__ == "__main__":
    unittest.main()
