"""Validate generated Rust runtime, alloc and every available peripheral on RTL."""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]


def invoke(root: Path, action: str, expected: bytes | None = None) -> None:
    result = subprocess.run(
        [str(SDK / "scripts/rv32-project"), "--project", str(root), action],
        env=dict(os.environ, RV32_SDK_ROOT=str(SDK), CARGO_BUILD_JOBS="2"),
        capture_output=True,
        timeout=300,
    )
    if (
        result.returncode
        or result.stderr
        or (expected is not None and result.stdout != expected)
    ):
        print(
            root,
            action,
            result.returncode,
            result.stdout,
            result.stderr,
            flush=True,
        )
        log = root / "logs/rv32" / f"{action}-latest.log"
        if log.exists():
            print(log.read_text()[-16000:], flush=True)
        raise SystemExit(1)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="rust-addons-", dir=SDK) as temp:
        root = Path(temp)
        runtime = root / "runtime"
        for folder in (SDK / "templates/common", SDK / "templates/rust"):
            shutil.copytree(folder, runtime, dirs_exist_ok=True)
        for profile in ("rv32i", "rv32im"):
            (runtime / "rv32.toml").write_text(
                '[project]\nname="runtime"\nlanguage="rust"\nplatform="modular"\n'
                f'cpu_profile="{profile}"\ngenerate_drivers=true\ngenerate_driver_examples=false\n'
                "simulation_timeout_cycles=4000000\n"
            )
            invoke(
                runtime,
                "simulate",
                b"Hello from an RV32 Rust project.\nvalues = [1, 2, 3, 4]\n",
            )
            print(
                "PASS generated runtime, Vec/String and main on",
                profile,
                flush=True,
            )
        app = root / "peripherals"
        shutil.copytree(
            SDK / "examples/peripherals/rust",
            app,
            ignore=shutil.ignore_patterns(
                "vendor", ".rv32", "build", "logs", "target"
            ),
        )
        invoke(
            app,
            "simulate",
            b"Rust heap: [1, 2, 3, 4]\nRust peripherals: PASS\n",
        )
        print("PASS combined Rust peripherals on rv32im_zicsr_irq", flush=True)
        metadata = json.loads((app / "vendor/.rv32-drivers.json").read_text())
        for relative in metadata["example_projects"]:
            child = app / relative
            name = child.parent.name
            invoke(child, "simulate", f"{name} Rust example: PASS\n".encode())
            print("PASS generated Rust example", name, flush=True)
        physical = root / "physical"
        shutil.copytree(SDK / "templates/rust", physical)
        (physical / "rv32.toml").write_text(
            '[project]\nname="physical"\nlanguage="rust"\nplatform="de0-cv"\ngenerate_drivers=true\n'
        )
        invoke(physical, "drivers")
        metadata = json.loads(
            (physical / "vendor/.rv32-drivers.json").read_text()
        )
        for relative in metadata["example_projects"]:
            invoke(physical / relative, "build")
            print(
                "PASS generated physical-platform Rust build",
                Path(relative).parent.name,
                flush=True,
            )
        # Check the panic policy as source/target compilation; do not run an
        # intentional infinite loop on the user's machine or mark a timeout PASS.
        runtime_source = (
            SDK / ".sdk/rust/rv32-runtime/src/lib.rs"
        ).read_text()
        assert (
            "#[panic_handler]" in runtime_source and "loop {" in runtime_source
        )
        assert "PanicInfo" in runtime_source


if __name__ == "__main__":
    main()
