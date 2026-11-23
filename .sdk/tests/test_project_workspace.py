"""Custom hardware maps must drive the portable SDK and every generated example."""

import importlib.util
import io
import json
import shutil
import tarfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from rv32_sdk import cli, drivers, platforms

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "workspace_export", ROOT / ".sdk/export_workspace.py"
)
assert SPEC and SPEC.loader
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


class ProjectPlatformTest(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "platform.yaml"
        self.data = yaml.safe_load(
            (ROOT / "src/periph-examples/de2-115/platform.yaml").read_text()
        )
        self.data["platform"] = "custom-hardware"
        self.data["profiles"] = str(ROOT / "Core/profiles/matrix.yaml")
        self.data["peripherals"]["GPIO_EXTRA"] = {
            "kind": "gpio",
            "role": "gpio",
            "base": 0x81000000,
            "groups": [[8, 9]],
        }
        self.source.write_text(yaml.safe_dump(self.data, sort_keys=False))
        self.project = {
            "platform": "project",
            "platform_file": str(self.source.relative_to(ROOT)),
            "cpu_profile": "auto",
            "language": "rust",
            "sdk_relative_root": "Insper-RISC-V",
        }

    def test_actual_addresses_instances_and_child_projects_follow_the_custom_map(
        self,
    ):
        view = platforms.ensure_project(ROOT, self.project)
        files, metadata = drivers.plan(
            ROOT, self.project, view / "platform.yaml"
        )
        self.assertIn(
            b"RV32_PERIPH_GPIO_EXTRA_BASE UINT32_C(0x81000000)",
            files["rv32_platform.h"],
        )
        self.assertIn(
            b"RV32_PERIPH_GPIO_EXTRA_BASE", files["GPIO/rv32_gpio_platform.h"]
        )
        self.assertIn(
            '"insper-riscv-gpio"', json.dumps(metadata["rust_dependencies"])
        )
        child = files["GPIO/example/rv32.toml"].decode()
        self.assertIn('platform = "project"', child)
        self.assertIn(self.project["platform_file"], child)
        self.assertIn("../../../Insper-RISC-V", child)
        self.assertIn(
            b"../../../../Insper-RISC-V:/opt/rv32-sdk:cached",
            files["GPIO/example/.devcontainer/compose.yaml"],
        )
        before = self.source.read_bytes()
        self.data["peripherals"]["GPIO_EXTRA"]["base"] = 0x82000000
        self.source.write_text(yaml.safe_dump(self.data, sort_keys=False))
        self.assertNotEqual(before, self.source.read_bytes())
        view = platforms.ensure_project(ROOT, self.project)
        refreshed, _ = drivers.plan(ROOT, self.project, view / "platform.yaml")
        self.assertIn(b"0x82000000", refreshed["rv32_platform.h"])
        self.assertNotIn(b"0x81000000", refreshed["rv32_platform.h"])

    def test_rust_and_c_runtime_isa_follow_the_selected_core(self):
        with patch.object(cli, "SDK", ROOT):
            for multiply in (False, True):
                self.data["core"] = {
                    "type": 32,
                    "base": "I",
                    "extensions": ["M"] if multiply else [],
                }
                self.data.pop("interrupts", None)
                self.data["memory"]["instructions"][0].pop("cache", None)
                self.data["memory"]["instructions"][0]["on_bus"] = False
                self.data["memory"]["instructions"][0]["type"] = "onchip"
                self.source.write_text(
                    yaml.safe_dump(self.data, sort_keys=False)
                )
                target = cli.rust_target(self.project)
                self.assertEqual(
                    target,
                    "riscv32im-unknown-none-elf"
                    if multiply
                    else "riscv32i-unknown-none-elf",
                )
                view = platforms.ensure_project(ROOT, self.project)
                config = yaml.safe_load((view / "config.yaml").read_text())
                self.assertEqual(
                    config["sdk_cpu_profile"]["march"],
                    "rv32im" if multiply else "rv32i",
                )

    def test_heap_limit_respects_earlier_reserved_memory_and_rejects_external_mailboxes(
        self,
    ):
        self.data["reserved"]["scratch"] = {"base": 0x40001000, "size": 16}
        self.source.write_text(yaml.safe_dump(self.data))
        view = platforms.ensure_project(ROOT, self.project)
        private = yaml.safe_load((view / "platform.yaml").read_text())
        self.assertEqual(private["generate"]["specs"]["ram_limit"], "scratch")
        self.data["reserved"]["stdout"]["base"] = 0x30000000
        self.source.write_text(yaml.safe_dump(self.data))
        with self.assertRaisesRegex(SystemExit, "inside the data"):
            platforms.ensure_project(ROOT, self.project)

    def test_paths_profiles_and_unsupported_abis_are_rejected(self):
        for value in ("../outside/platform.yaml", "/tmp/platform.yaml"):
            with self.assertRaises(SystemExit):
                platforms.project_source(
                    ROOT, dict(self.project, platform_file=value)
                )
        with self.assertRaisesRegex(SystemExit, "auto"):
            platforms.ensure_project(
                ROOT, dict(self.project, cpu_profile="rv32im")
            )
        self.data["core"]["base"] = "E"
        self.source.write_text(yaml.safe_dump(self.data))
        with self.assertRaisesRegex(SystemExit, "RV32I"):
            platforms.ensure_project(ROOT, self.project)

    def test_cache_tracks_sdk_location_and_simulation_is_explicitly_unavailable(
        self,
    ):
        view = platforms.ensure_project(ROOT, self.project)
        marker = json.loads((view / ".sdk-view.json").read_text())
        self.assertEqual(marker["sdk_root"], str(ROOT.resolve()))
        with (
            patch.object(cli, "SDK", ROOT),
            self.assertRaisesRegex(SystemExit, "no complete"),
        ):
            cli.simulate(self.folder, self.project)


class HardwareTemplateTest(unittest.TestCase):
    def test_current_board_template_registers_without_a_simulation_top(self):
        from riscv_tools.new_project import ProjectSpec, create_platform
        from riscv_tools.new_project.template import find_template

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (
                "boards",
                "Core/profiles",
                "src/periph-examples/de2-115",
                "src/cyclone-iv-e/de2-115",
            ):
                shutil.copytree(ROOT / name, root / name)
            shutil.copy2(ROOT / "paths.yaml", root / "paths.yaml")
            template = find_template(root, "de2-115")
            self.assertEqual(
                template.folder, Path("src/periph-examples/de2-115")
            )
            created = create_platform(
                root, ProjectSpec(name="custom", board="de2-115")
            )
            data = yaml.safe_load((root / created.platform).read_text())
            self.assertEqual(data["top"], "Insper-RISC-V/custom_board")
            paths = yaml.safe_load((root / "paths.yaml").read_text())
            # The paths document owns a component map under the repository name.
            text = (root / "paths.yaml").read_text()
            self.assertIn("  custom_board:", text)
            self.assertIn("  custom_map:", text)
            self.assertIn(
                "custom_map",
                text.split("  custom_board:", 1)[1].split("sources:", 1)[0],
            )
            self.assertIsInstance(paths, dict)


class WorkspaceExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="software workspace ")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "sdk"
        self.project = root / "my project"
        self.hardware = self.project / "Insper-RISC-V"
        self.hardware.mkdir(parents=True)
        (self.hardware / "platform.yaml").write_text("platform: fixture\n")
        (self.project / "project.yaml").write_text("name: fixture\n")
        (self.project / "README.md").write_text(
            "Hardware documentation stays\n"
        )
        (self.hardware / "version.txt").write_text("previous SDK\n")
        self.source.mkdir()
        (self.source / "version.txt").write_text("new SDK\n")
        for language, suffix in (("c", "c"), ("rust", "rs")):
            folder = self.source / "templates" / language
            (folder / "src").mkdir(parents=True)
            (folder / "src" / ("main." + suffix)).write_text("// starter\n")
            (folder / "rv32.toml").write_text(
                f'[project]\nlanguage = "{language}"\ncpu_profile = "auto"\n'
            )
            (folder / "README.md").write_text("Software documentation\n")
        common = self.source / "templates/common/.devcontainer"
        common.mkdir(parents=True)
        (common / "compose.yaml").write_text(
            'volumes:\n  - "${HOME}/.local/share/rv32-sdk:/opt/rv32-sdk:cached"\n'
        )
        manifest = {
            "schema": 1,
            "sdk_revision": "fixture",
            "files": {
                "version.txt": {
                    "sha256": exporter.digest(
                        (self.source / "version.txt").read_bytes()
                    ),
                    "mode": 0o644,
                }
            },
        }
        (self.source / "SDK-MANIFEST.json").write_text(json.dumps(manifest))

    def generate(self, hardware, application, environment):
        vendor = application / "vendor"
        vendor.mkdir()
        (vendor / ".rv32-drivers.json").write_text(
            json.dumps({"sources": ["vendor/GPIO/rv32_gpio.c"]})
        )
        (application / ".rv32").mkdir()

    def create(self, language="rust"):
        return exporter.create(
            self.source, self.project, self.hardware, "platform.yaml", language
        )

    def test_complete_application_preserves_hardware_docs_and_uses_local_sdk(
        self,
    ):
        with patch.object(exporter, "run_drivers", side_effect=self.generate):
            result = self.create()
        self.assertEqual(result["drivers"], ["GPIO"])
        self.assertEqual(
            (self.project / "README.md").read_text(),
            "Hardware documentation stays\n",
        )
        self.assertEqual(
            (self.hardware / "version.txt").read_text(), "new SDK\n"
        )
        self.assertIn(
            'platform = "project"', (self.project / "rv32.toml").read_text()
        )
        self.assertIn(
            "../Insper-RISC-V:/opt/rv32-sdk:cached",
            (self.project / ".devcontainer/compose.yaml").read_text(),
        )
        self.assertTrue((self.project / "SOFTWARE.md").is_file())
        self.assertEqual(
            json.loads((self.project / ".rv32/platformapp.json").read_text())[
                "language"
            ],
            "rust",
        )
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.create()

    def test_c_creation_uses_the_c_starter(self):
        with patch.object(exporter, "run_drivers", side_effect=self.generate):
            self.create("c")
        self.assertTrue((self.project / "src/main.c").is_file())
        self.assertFalse((self.project / "src/main.rs").exists())

    def test_existing_source_is_never_replaced(self):
        (self.project / "src").mkdir()
        (self.project / "src/main.rs").write_text("user source")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            self.create()
        self.assertEqual(
            (self.project / "src/main.rs").read_text(), "user source"
        )
        self.assertEqual(
            (self.hardware / "version.txt").read_text(), "previous SDK\n"
        )

    def test_failure_rolls_back_overlay_and_publishes_no_partial_application(
        self,
    ):
        with (
            patch.object(
                exporter,
                "run_drivers",
                side_effect=RuntimeError("invalid platform"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.create()
        self.assertEqual(
            (self.hardware / "version.txt").read_text(), "previous SDK\n"
        )
        self.assertFalse((self.project / "rv32.toml").exists())
        self.assertFalse((self.project / "src/main.rs").exists())

    def test_corrupt_bundle_and_escaping_paths_are_refused(self):
        (self.source / "version.txt").write_text("corrupted")
        with self.assertRaisesRegex(ValueError, "Corrupt"):
            self.create()
        with self.assertRaises(ValueError):
            exporter.safe_target(self.hardware, "../escape")
        outside = Path(self.temp.name) / "outside"
        outside.mkdir()
        (self.hardware / "link").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            exporter.safe_target(self.hardware, "link/source.c")

    def test_sdk_bundle_is_reproducible_and_every_member_has_a_digest(self):
        first, second = (
            Path(self.temp.name) / "first.tgz",
            Path(self.temp.name) / "second.tgz",
        )
        exporter.bundle(ROOT, first)
        exporter.bundle(ROOT, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with tarfile.open(fileobj=io.BytesIO(first.read_bytes())) as archive:
            manifest = json.load(archive.extractfile("sdk/SDK-MANIFEST.json"))
            for name, spec in manifest["files"].items():
                self.assertEqual(
                    exporter.digest(archive.extractfile("sdk/" + name).read()),
                    spec["sha256"],
                )
