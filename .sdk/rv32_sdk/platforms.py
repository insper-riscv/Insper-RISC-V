"""Prepare private SDK runtimes for the canonical peripheral board platforms."""

import fcntl
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from riscv_tools import board_generate
from riscv_tools.memory_map import write_all
from riscv_tools.memory_map.core import load_platform


def board_choices(sdk: Path) -> dict[str, Path]:
    """Expose only repository-owned canonical board descriptions."""
    return {
        "periph-" + path.parent.name: path
        for path in sorted(
            (sdk / "src/periph-examples").glob("*/platform.yaml")
        )
    }


def identity(board: dict[str, Any]) -> str:
    """Use the board catalog's FPGA identity, never a hard-coded Cyclone V."""
    chain = board["jtag"]["chain"]
    for index, device in enumerate(chain, 1):
        if device.get("fpga"):
            return f"@{index}: {device['name']} (0x{device['idcode']})"
    raise SystemExit("Board has no declared FPGA JTAG identity")


def private_platform(sdk: Path, source: Path, target: Path) -> dict[str, Any]:
    """Keep addresses and board selection while redirecting generated files."""
    data = yaml.safe_load(source.read_text())
    data["profiles"] = str(sdk / "Core/profiles/matrix.yaml")
    data["checks"] = []
    data["config"] = {"rom": "FLASH", "ram": "RAM", "addr_widths": []}
    runtime = target / "runtime"
    original = data.get("generate", {})
    data["generate"] = {
        key: {**value, "path": str(target / Path(value["path"]).name)}
        for key, value in original.items()
        if key in {"vhdl", "config_pkg"}
    }
    data["generate"].update(
        {
            "specs": {
                "path": str(runtime / "rv32im-fpga.specs"),
                "rom": "FLASH",
                "ram": "RAM",
                "ram_limit": "stdout",
            },
            "runtime": {"path": str(runtime / "memory_map.h"), "ram": "RAM"},
            "boot_ld": {"path": str(runtime / "boot_memory.ld")},
            "boot_config_h": {"path": str(runtime / "boot_config.h")},
        }
    )
    return data


def board_config(sdk: Path, source: Path, target: Path) -> dict[str, Any]:
    """Derive build/program settings without borrowing another board's map."""
    data = load_platform(target / "platform.yaml")
    board_name = data["boards"][0]
    board = yaml.safe_load(
        (sdk / "boards" / board_name / "board.yaml").read_text()
    )
    stem = (
        str(data["platform"]).replace("-", "_")
        + "_"
        + board_name.replace("-", "_")
    )
    folder = str(data["platform"]) + "-" + board_name
    project = target / "quartus" / folder
    config = yaml.safe_load(
        (sdk / "src/simulation/modular/config.yaml").read_text()
    )
    runtime = target / "runtime"
    config["memory_map"] = str(target / "platform.yaml")
    config["toolchain"]["specs"] = str(runtime / "rv32im-fpga.specs")
    config["paths"].update(
        sources=[str(runtime / "_exit.c"), str(runtime / "stdio.c")],
        boot_memory=str(runtime / "boot_memory.S"),
        boot_memory_linker_script=str(runtime / "boot_memory.ld"),
    )
    # Physical board tops need external-device models before SoC simulation.
    config["sim"].update(
        vhdl_sources=[],
        parameters={},
        python_path=[],
        run_files={},
        libraries={},
    )
    config["sdk_simulation_supported"] = False
    config["emulator"] = {
        "sources": [str(runtime / "spike_exit.S")],
        "gcc_flags": ["-DRV32_SPIKE"],
    }
    sdram = (
        yaml.safe_load(source.read_text())["memory"]["data"][0]["type"]
        == "sdram"
    )
    config["quartus"] = {
        "project_dir": str(project.relative_to(sdk)),
        "project_name": stem,
        "sof_file": f"output_files/{stem}.sof",
        "jtag_device": identity(board),
        "rom_mif_target": "init.mif",
        "boot_memory_mif_target": "boot_memory_init.mif",
        "rom_write_method": "jtag_loader",
        "rom_mem_instances": [],
        "ram_backend": "sdram_debug" if sdram else "ismce",
        "ram_mem_instance": 0,
        "sdram_debug_instance": 3,
        "generate": {
            "platform": str(source.relative_to(sdk)),
            "out": str((target / "quartus").relative_to(sdk)),
            "boards_dir": "boards",
            "chips_dir": "Memory/chips",
        },
    }
    return config


def ensure_board(sdk: Path, name: str) -> Path:
    """Generate a compile-ready private runtime; never edit tracked RTL files."""
    choices = board_choices(sdk)
    if name not in choices:
        raise SystemExit(f"Unknown peripheral board platform: {name}")
    source = choices[name]
    target = sdk / ".sdk/platforms" / name
    base = sdk / "src/simulation/modular/runtime"
    inputs = [
        source,
        Path(__file__),
        sdk / "src/simulation/modular/config.yaml",
        sdk / "Core/profiles/matrix.yaml",
        sdk / ".sdk/dependencies.json",
        sdk / "boards" / source.parent.name / "board.yaml",
        *(p for p in base.iterdir() if p.is_file()),
    ]
    expected = {
        str(p.relative_to(sdk)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in inputs
    }
    with (sdk / ".sdk/.board-views.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = target / ".sdk-view.json"
        if marker.exists() and json.loads(marker.read_text()) == expected:
            return target
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(base, target / "runtime", dirs_exist_ok=True)
        boot = target / "runtime/boot_memory.S"
        boot.write_text(
            boot.read_text().replace(
                '#include "../../../boot/boot_core.S"',
                '#include "../../../../src/boot/boot_core.S"',
            )
        )
        data = private_platform(sdk, source, target)
        platform = target / "platform.yaml"
        platform.write_text(yaml.safe_dump(data, sort_keys=False))
        write_all(platform, sdk)
        config = board_config(sdk, source, target)
        (target / "config.yaml").write_text(
            yaml.safe_dump(config, sort_keys=False)
        )
        marker.write_text(json.dumps(expected, sort_keys=True) + "\n")
    return target


def prepare_hardware(sdk: Path, project: dict[str, Any]) -> None:
    """Generate the selected board project before the SDK fingerprints it."""
    name = project.get("platform", "internal-mem")
    if name not in board_choices(sdk):
        return
    target = ensure_board(sdk, name)
    config = yaml.safe_load((target / "config.yaml").read_text())
    request = board_generate.request_from_config(
        sdk, config["quartus"]["generate"]
    )
    result = board_generate.build(request)
    if result.problems:
        raise SystemExit(
            "Invalid generated board project: " + "; ".join(result.problems)
        )
