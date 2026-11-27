"""Regressions for missing DE0-CV Quartus project generation."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rv32_sdk import platforms


class HardwarePreparationTest(unittest.TestCase):
    def test_generator_change_invalidates_private_runtime(self):
        """A cached map cannot outlive the generator that defines its bus."""
        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory)
            source = sdk / "src/periph-examples/de0-cv/platform.yaml"
            module = sdk / ".sdk/rv32_sdk/platforms.py"
            required = [
                source,
                module,
                sdk / "src/simulation/modular/config.yaml",
                sdk / "Core/profiles/matrix.yaml",
                sdk / ".sdk/dependencies.json",
                sdk / "boards/de0-cv/board.yaml",
                sdk / "src/simulation/modular/runtime/boot_memory.S",
            ]
            generators = [
                sdk / f".sdk/tools/src/riscv_tools/{part}/core.py"
                for part in ("memory_map", "top_generator", "board_ports")
            ]
            for path in required + generators:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("initial\n")
            with (
                patch.object(platforms, "__file__", str(module)),
                patch.object(platforms, "board_choices", return_value={"periph-de0-cv": source}),
                patch.object(platforms, "private_platform", return_value={}),
                patch.object(platforms, "board_config", return_value={}),
                patch.object(platforms, "write_all") as generate,
            ):
                platforms.ensure_board(sdk, "periph-de0-cv")
                platforms.ensure_board(sdk, "periph-de0-cv")
                self.assertEqual(generate.call_count, 1)
                for count, path in enumerate(generators, 2):
                    path.write_text("changed\n")
                    platforms.ensure_board(sdk, "periph-de0-cv")
                    self.assertEqual(generate.call_count, count)

    def check_generation(self, name):
        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory)
            target = sdk / "src/cyclone-v/de0-cv"
            target.mkdir(parents=True)
            (target / "config.yaml").write_text(
                "quartus:\n  generate:\n    platform: src/cyclone-v/de0-cv/platform.yaml\n    out: build\n"
            )
            folder = sdk / "build/de0-cv-de0-cv"
            folder.mkdir(parents=True)
            qsf = folder / "de0_cv_de0_cv.qsf"
            qsf.write_text(
                "set_global_assignment -name TOP_LEVEL_ENTITY de0_cv_de0_cv_top\nset_global_assignment -name NUM_PARALLEL_PROCESSORS ALL\n"
            )
            choices = {"periph-de0-cv": target / "platform.yaml"}
            result = SimpleNamespace(problems=[], folder=folder)
            with (
                patch.object(platforms, "board_choices", return_value=choices),
                patch.object(
                    platforms, "ensure_board", return_value=target
                ) as ensure,
                patch.object(
                    platforms.board_generate,
                    "request_from_config",
                    return_value="request",
                ) as request,
                patch.object(
                    platforms.board_generate, "build", return_value=result
                ) as build,
            ):
                platforms.prepare_hardware(sdk, {"platform": name})
                request.assert_called_once_with(
                    sdk,
                    {
                        "platform": "src/cyclone-v/de0-cv/platform.yaml",
                        "out": "build",
                    },
                )
                build.assert_called_once_with("request")
                self.assertEqual(
                    ensure.call_count, int(name.startswith("periph-"))
                )
                self.assertIn("NUM_PARALLEL_PROCESSORS 2", qsf.read_text())
                self.assertIn(
                    "TOP_LEVEL_ENTITY de0_cv_de0_cv_top", qsf.read_text()
                )

    def test_de0_cv_generates_before_compile(self):
        self.check_generation("de0-cv")

    def test_peripheral_board_still_generates(self):
        self.check_generation("periph-de0-cv")

    def test_simulation_platforms_do_not_generate(self):
        with (
            patch.object(platforms, "board_choices", return_value={}),
            patch.object(platforms.board_generate, "build") as build,
        ):
            for name in ("modular", "internal-mem"):
                platforms.prepare_hardware(Path("/unused"), {"platform": name})
            build.assert_not_called()

    def test_generation_problems_stop_before_compilation(self):
        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory)
            target = sdk / "src/cyclone-v/de0-cv"
            target.mkdir(parents=True)
            (target / "config.yaml").write_text("quartus:\n  generate: {}\n")
            with (
                patch.object(platforms, "board_choices", return_value={}),
                patch.object(platforms.board_generate, "request_from_config"),
                patch.object(
                    platforms.board_generate,
                    "build",
                    return_value=SimpleNamespace(problems=["invalid pin"]),
                ),
            ):
                with self.assertRaisesRegex(SystemExit, "invalid pin"):
                    platforms.prepare_hardware(sdk, {"platform": "de0-cv"})


if __name__ == "__main__":
    unittest.main()
