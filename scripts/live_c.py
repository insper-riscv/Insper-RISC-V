#!/usr/bin/env python3
"""VS Code-oriented single-program frontend for the RV32 toolchain."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def env_path(name: str, default: Path) -> Path:
    """Return an absolute path from the environment or a repository default."""
    return Path(os.environ.get(name, default)).expanduser().resolve()


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ROOT = env_path("RV32_ROOT", DEFAULT_ROOT)
TESTS = env_path("RV32_TESTS_ROOT", ROOT / "Tests")
LIVE = env_path("RV32_LIVE_ROOT", ROOT / "Live")
CONFIG = env_path("RV32_CONFIG", LIVE / "config.yaml")
PLATFORM = env_path(
    "RV32_PLATFORM", ROOT / "TopLevel" / "platforms" / "internal-mem" / "platform.yaml"
)
LIVE_BUILD = LIVE / "build"
HARDWARE_TOOLS = ["quartus_sh", "quartus_pgm", "quartus_stp", "jtagconfig"]


def configure_path() -> None:
    """Expose configured tool installations without machine-specific paths."""
    bin_dirs: list[str] = []
    toolchain_root = os.environ.get("RV32_TOOLCHAIN_ROOT")
    quartus_root = os.environ.get("QUARTUS_ROOTDIR")
    if toolchain_root:
        bin_dirs.append(str(Path(toolchain_root).expanduser() / "bin"))
    if quartus_root:
        bin_dirs.append(str(Path(quartus_root).expanduser() / "bin"))
    if bin_dirs:
        os.environ["PATH"] = os.pathsep.join([*bin_dirs, os.environ.get("PATH", "")])


configure_path()


def run(command: list[str], *, cwd: Path = TESTS, check: bool = True) -> int:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result.returncode


def riscv_tools(*args: str, check: bool = True) -> int:
    return run(
        [
            "uv",
            "run",
            "riscv-tools",
            "--config",
            str(CONFIG),
            "--root",
            str(TESTS),
            *args,
        ],
        check=check,
    )


def require_layout() -> None:
    required = [
        ROOT / "Core",
        ROOT / "Memory",
        ROOT / "TopLevel",
        TESTS / "tools" / "Tools",
        LIVE / "c" / "live" / "src.c",
        CONFIG,
        PLATFORM,
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        names = "\n".join(f"  - {p.relative_to(ROOT)}" for p in missing)
        raise SystemExit(
            "Incomplete RV32 checkout. Run `git submodule update --init "
            f"--recursive`. Missing:\n{names}"
        )


def inside_container() -> bool:
    return Path("/.dockerenv").exists() or bool(os.environ.get("REMOTE_CONTAINERS"))


def require_commands(commands: list[str]) -> None:
    missing = [command for command in commands if shutil.which(command) is None]
    if missing:
        raise SystemExit("Missing required command(s): " + ", ".join(missing))


def probe_jtag() -> None:
    """Require a visible USB-Blaster and a lockable JTAG chain."""
    probe = subprocess.run(
        ["jtagconfig"], capture_output=True, text=True, check=False
    )
    output = (probe.stdout + probe.stderr).strip()
    print("JTAG:")
    print(output or "  no output")

    if probe.returncode:
        raise SystemExit("jtagconfig failed")
    if "USB-Blaster" not in output:
        raise SystemExit("jtagconfig found no USB-Blaster")

    lowered = output.lower()
    errors = (
        "bad port name",
        "unable to lock chain",
        "chain broken",
    )
    if any(error in lowered for error in errors):
        raise SystemExit(
            "The JTAG cable is visible, but the chain is unavailable. "
            "Start jtagd with jtagconfig on the host and try again."
        )


def doctor(require_hardware: bool = False) -> None:
    require_layout()
    require_commands(["uv", "riscv32-unknown-elf-gcc", "riscv32-unknown-elf-objcopy"])
    print(f"RV32 root: {ROOT}")
    print(f"Tests root: {TESTS}")
    print(f"Live config: {CONFIG}")
    print("Environment:", "container" if inside_container() else "host/SSH")

    if shutil.which("ghdl"):
        print("Simulation: available")
    else:
        print("Simulation: unavailable (ghdl not found)")

    missing_hardware = [
        tool for tool in HARDWARE_TOOLS if shutil.which(tool) is None
    ]
    if missing_hardware:
        print("FPGA: unavailable; missing " + ", ".join(missing_hardware))
    else:
        location = "mounted host Quartus" if inside_container() else "host Quartus"
        print(f"FPGA tooling: available through {location}")

    if require_hardware:
        require_commands(HARDWARE_TOOLS)
        probe_jtag()


def setup() -> None:
    require_commands(["git", "uv"])
    git_checkout = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if git_checkout:
        run(["git", "submodule", "update", "--init", "--recursive"], cwd=ROOT)
    else:
        require_layout()
        print("Archive checkout detected; using the bundled repository contents.")
    run(["uv", "sync", "--project", str(TESTS)], cwd=ROOT)
    print("Workspace ready. Run `RV32: Check environment` next.")


def generate_header() -> None:
    riscv_tools("generate-header")


def build(emit: str) -> None:
    require_layout()
    generate_header()
    riscv_tools("compile", "--emit", emit)


def clear_resume_state() -> None:
    (LIVE_BUILD / "real" / "run_progress.json").unlink(missing_ok=True)


def simulate() -> None:
    doctor()
    require_commands(["ghdl"])
    build("hex")
    riscv_tools("sim")


def spike() -> None:
    doctor()
    require_commands(["spike"])
    # spike-run consumes the real/manifest.json produced by the MIF build;
    # it still runs the ELF in Spike and does not require Quartus or a board.
    build("mif")
    riscv_tools("spike-run", "--only", "live")


def assembly() -> None:
    doctor()
    build("asm")
    print(f"Assembly written under {LIVE_BUILD / 'asm'}")


def fpga(mode: str) -> None:
    doctor(require_hardware=True)
    build("mif")
    clear_resume_state()
    args = ["run", "--only", "live", "--wait-for-hardware"]
    if mode == "fast":
        args.append("--skip-reconfigure")
    elif mode == "reprogram":
        args.append("--skip-recompile")
    status = riscv_tools(*args, check=False)
    if status:
        raise SystemExit(status)
    try:
        read_stdout()
    except Exception as exc:  # stdout is useful but must not hide the run result
        print(f"Could not read stdout: {exc}", file=sys.stderr)


def decode_stdout_words(words: list[int], capacity: int = 1024) -> tuple[str, bool]:
    """Decode the length/truncated header and little-endian payload words."""
    if len(words) < 2:
        raise ValueError("stdout read returned fewer than two header words")
    length = min(words[0], capacity)
    payload = b"".join(word.to_bytes(4, "little") for word in words[2:])[:length]
    return payload.decode("utf-8", errors="replace"), bool(words[1])


def read_stdout() -> None:
    doctor(require_hardware=True)
    # Imports intentionally live here: this script is launched through the
    # Tests uv environment, where riscv-tools and PyYAML are installed.
    from riscv_tools import mem_edit  # pylint: disable=import-outside-toplevel
    from riscv_tools.jtag import (  # pylint: disable=import-outside-toplevel
        JtagLink,
        detect_jtag_hardware,
    )
    from riscv_tools.settings import (  # pylint: disable=import-outside-toplevel
        load_config,
    )
    import yaml  # pylint: disable=import-outside-toplevel

    cfg = load_config(CONFIG)
    platform_cfg = yaml.safe_load(PLATFORM.read_text(encoding="utf-8"))
    stdout_cfg = platform_cfg["reserved"]["stdout"]
    stdout_base = int(stdout_cfg["base"])
    stdout_bytes = 1024
    ram_base = int(cfg["memory"]["ram_base"])
    word_offset = (stdout_base - ram_base) // 4
    word_count = 2 + (stdout_bytes // 4)
    link = JtagLink(
        hardware_name=detect_jtag_hardware(),
        device_name=cfg["quartus"]["jtag_device"],
    )
    words = mem_edit.read_words(
        link, int(cfg["quartus"]["ram_mem_instance"]), word_offset, word_count
    )
    output, truncated = decode_stdout_words(words, stdout_bytes)
    print("\n--- FPGA stdout ---")
    print(output, end="")
    if output and not output.endswith("\n"):
        print()
    if truncated:
        print("[stdout truncated after 1024 bytes]", file=sys.stderr)
    print("--- end stdout ---")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("setup")
    sub.add_parser("simulate")
    sub.add_parser("spike")
    sub.add_parser("assembly")
    sub.add_parser("stdout")
    fpga_parser = sub.add_parser("fpga")
    fpga_parser.add_argument(
        "--mode", choices=["full", "fast", "reprogram"], required=True
    )
    return result


def main() -> None:
    args = parser().parse_args()
    actions = {
        "doctor": doctor,
        "setup": setup,
        "simulate": simulate,
        "spike": spike,
        "assembly": assembly,
        "stdout": read_stdout,
    }
    if args.command == "fpga":
        fpga(args.mode)
    else:
        actions[args.command]()


if __name__ == "__main__":
    main()
