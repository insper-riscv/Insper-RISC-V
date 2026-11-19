"""Cross-compile generated examples and build projects for every physical map.

Run with the SDK environment: uv run --project .sdk python
.sdk/tests/new_peripherals_integration.py. Requires the pinned multilib GCC,
Rust RV32I/IM targets and libclang; no FPGA or Quartus is invoked.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from test_new_peripherals import all_devices

from rv32_sdk import drivers, platforms, rust_support

SDK = Path(__file__).resolve().parents[2]


def run(command: list[str], root: Path) -> None:
    """Fail on compiler diagnostics and retain the command in the audit log."""
    print("+", *command, flush=True)
    subprocess.run(command, cwd=root, check=True, timeout=240)


def generated_examples(root: Path) -> None:
    """Check every new C/Rust example against its generated platform metadata."""
    shutil.copytree(SDK / "templates/rust", root, dirs_exist_ok=True)
    project = {"language": "rust", "generate_drivers": True}
    files, meta = drivers.plan(SDK, project, all_devices(root))
    drivers.install(root, files, meta)
    rust_support.install_dependencies(root, project, meta["rust_dependencies"])
    manifest = root / "Cargo.toml"
    with manifest.open("a") as target:
        for example in meta["example_projects"]:
            name = Path(example).parent.name.lower().replace("_", "-")
            target.write(
                f'\n[[bin]]\nname = "{name}-example"\npath = "{example}/src/main.rs"\n'
            )
    for target in ("riscv32i-unknown-none-elf", "riscv32im-unknown-none-elf"):
        run(["cargo", "check", "--bins", "--target", target, "-j", "2"], root)
    cfiles, cmeta = drivers.plan(
        SDK, {"language": "c"}, root / "platform.yaml"
    )
    croot = root / "c"
    croot.mkdir()
    drivers.install(croot, cfiles, cmeta)
    include = ["-I" + str(croot / path) for path in cmeta["include_dirs"]]
    for example in cmeta["example_projects"]:
        source = croot / example / "src/main.c"
        run(
            [
                "riscv32-unknown-elf-gcc",
                "-std=c23",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-march=rv32i",
                "-mabi=ilp32",
                *include,
                "-I" + str(croot / ".rv32/include"),
                "-c",
                str(source),
                "-o",
                str(croot / "example.o"),
            ],
            croot,
        )
    print(
        "PASS: 18 generated examples in C and Rust (both Rust RV32 targets)",
        flush=True,
    )


def board_projects(root: Path) -> None:
    """Use public entry points for all board/language combinations."""
    for board in platforms.board_choices(SDK):
        for language in ("c", "rust"):
            destination = root / f"{board}-{language}"
            run(
                [
                    str(SDK / "scripts/rv32-new"),
                    language,
                    str(destination),
                    "--platform",
                    board,
                ],
                root,
            )
            run(
                [
                    str(SDK / "scripts/rv32-project"),
                    "--project",
                    str(destination),
                    "build",
                    "--debug",
                ],
                root,
            )
            meta = json.loads(
                (destination / "vendor/.rv32-drivers.json").read_text()
            )
            assert meta["sources"], board
            print("PASS board project:", board, language, flush=True)


def main() -> None:
    """Keep compiler outputs outside application source trees."""
    os.environ["RV32_SDK_ROOT"] = str(SDK)
    os.environ["CARGO_BUILD_JOBS"] = "2"
    with TemporaryDirectory(prefix="rv32-new-peripherals-") as temp:
        root = Path(temp)
        generated_examples(root / "examples")
        board_projects(root)


if __name__ == "__main__":
    main()
