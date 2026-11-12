"""Generate an SDK-only runtime view without modifying normal processor platforms."""

import fcntl
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml


def ensure_internal_mem(sdk: Path) -> Path:
    """Build the pinned runtime view once, preserving upstream stdio and tests."""
    home = sdk / ".sdk"
    inputs = json.loads((home / "platform-inputs.json").read_text())
    for name, digest in inputs.items():
        if hashlib.sha256((sdk / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(
                f"SDK platform input changed: {name}; refresh the SDK platform integration before using it"
            )
    patch = home / "patches/platform-sdk.patch"
    expected = {
        "inputs": inputs,
        "patch": hashlib.sha256(patch.read_bytes()).hexdigest(),
    }
    destination = home / "platforms/internal-mem"
    with (home / ".views.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = destination / ".sdk-view.json"
        if marker.exists() and json.loads(marker.read_text()) == expected:
            return destination
        base = sdk / "src/simulation/internal-mem"
        with tempfile.TemporaryDirectory(
            prefix=".platform-", dir=home
        ) as temporary:
            stage = Path(temporary) / "internal-mem"
            shutil.copytree(base / "runtime", stage / "runtime")
            shutil.copytree(
                base / "testbench",
                stage / "testbench",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            log = home / ".views-bootstrap.log"
            with log.open("w") as output:
                subprocess.run(
                    ["git", "apply", "--no-index", str(patch)],
                    cwd=stage,
                    check=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
                platform = yaml.safe_load((base / "platform.yaml").read_text())
                platform["reserved"]["stdout"] = {
                    "base": platform["reserved"]["tohost"]["base"] - 65536 - 8,
                    "size": "64K+8",
                }
                platform["checks"] = []
                platform["generate"] = {
                    key: {
                        **value,
                        "path": str(
                            stage / "runtime" / Path(value["path"]).name
                        ),
                    }
                    for key, value in platform["generate"].items()
                    if key in ("specs", "boot_ld", "runtime")
                }
                platform_file = stage / "platform.yaml"
                platform_file.write_text(
                    yaml.safe_dump(platform, sort_keys=False)
                )
                subprocess.run(
                    [
                        "riscv-tools",
                        "--root",
                        str(sdk),
                        "generate-memory-map",
                        "--platform",
                        str(platform_file),
                    ],
                    check=True,
                    stdout=output,
                    stderr=subprocess.STDOUT,
                )
            # Remove temporary generator paths from comments for reproducible outputs.
            for source in (stage / "runtime").iterdir():
                text = source.read_text()
                text = text.replace(str(stage), str(destination)).replace(
                    str(stage.relative_to(sdk)), ".sdk/platforms/internal-mem"
                )
                source.write_text(text)
            for value in platform["generate"].values():
                value["path"] = (
                    ".sdk/platforms/internal-mem/runtime/"
                    + Path(value["path"]).name
                )
            platform_file.write_text(yaml.safe_dump(platform, sort_keys=False))
            (stage / "config.yaml").write_text(
                yaml.safe_dump(
                    {
                        "extends": "../../../src/simulation/internal-mem/config.yaml",
                        "memory_map": "platform.yaml",
                        "toolchain": {
                            "specs": ".sdk/platforms/internal-mem/runtime/rv32im-fpga.specs"
                        },
                        "paths": {
                            "boot_memory": ".sdk/platforms/internal-mem/runtime/boot_memory.S",
                            "boot_memory_linker_script": ".sdk/platforms/internal-mem/runtime/boot_memory.ld",
                        },
                        "sim": {
                            "python_path": [".sdk/platforms/internal-mem"]
                        },
                    },
                    sort_keys=False,
                )
            )
            (stage / ".sdk-view.json").write_text(
                json.dumps(expected, sort_keys=True) + "\n"
            )
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                shutil.rmtree(destination)
            stage.rename(destination)
    return destination


def ensure_modular(sdk: Path) -> Path:
    """Create a simulation-only GPIO-capable runtime without touching main."""
    home = sdk / ".sdk"
    for name, digest in json.loads(
        (home / "platform-inputs.json").read_text()
    ).items():
        if hashlib.sha256((sdk / name).read_bytes()).hexdigest() != digest:
            raise SystemExit(
                f"SDK platform input changed: {name}; refresh the SDK integration"
            )
    base = sdk / "src/simulation/modular"
    destination = home / "platforms/modular"
    tracked = [
        p
        for directory in (base / "runtime", base / "testbench")
        for p in directory.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    expected = {
        str(p.relative_to(sdk)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [
            base / "platform.yaml",
            base / "config.yaml",
            Path(__file__),
            *tracked,
        ]
    }
    with (home / ".views.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = destination / ".sdk-view.json"
        if marker.exists() and json.loads(marker.read_text()) == expected:
            return destination
        with tempfile.TemporaryDirectory(
            prefix=".modular-", dir=home
        ) as temporary:
            stage = Path(temporary) / "modular"
            shutil.copytree(base / "runtime", stage / "runtime")
            shutil.copytree(
                base / "testbench",
                stage / "testbench",
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            stdio = stage / "runtime/stdio.c"
            text = stdio.read_text()
            old = "static constexpr uint32_t STDOUT_SIZE = 1024u;"
            if text.count(old) != 1:
                raise SystemExit(
                    "Modular stdout integration changed; refresh the SDK view"
                )
            stdio.write_text(
                text.replace(
                    old,
                    "static constexpr uint32_t STDOUT_SIZE = RV32_TOHOST_ADDR - RV32_STDOUT_BASE - 8u;",
                )
            )
            bench = stage / "testbench/test_c_program.py"
            text = bench.read_text()
            # SDK modular applications use internal memories and the stable
            # public RAM observation ports, not optimized internal net names.
            text = text.replace(
                '    if getattr(dut, f"{enable}_wren").value != 1:',
                '    if enable != "ram":\n        return None\n    enable = "o_ram"\n    if getattr(dut, f"{enable}_wren").value != 1:',
            )
            text = text.replace(
                'gate = "ram_en" if enable == "ram" else "mem_advance"',
                'gate = "o_ram_en" if enable == "o_ram" else "mem_advance"',
            )
            hook = '''

def export_stdout(image: RamImage) -> None:
    """Export only actual RAM stdout from the program under test."""
    target = os.environ.get("RV32_SIM_STDOUT_FILE")
    if not target:
        return
    base = int(os.environ["STDOUT_ADDR"], 0) - RAM_BASE
    count = sum(image.ram_bytes.get(base + i, 0) << (8 * i) for i in range(4))
    if image.ram_bytes.get(base + 4, 0):
        Path(target + ".truncated").write_text("1")
    capacity = int(os.environ["RV32_STDOUT_CAPACITY"])
    Path(target).write_bytes(bytes(image.ram_bytes.get(base + 8 + i, 0) for i in range(min(count, capacity))))

'''
            if text.count("def finish_pass(") != 1:
                raise SystemExit("Modular testbench integration changed")
            text = text.replace("def finish_pass(", hook + "def finish_pass(")
            text = text.replace(
                "    if GOLDEN_PATH is None:",
                "    export_stdout(image)\n    if GOLDEN_PATH is None:",
            )
            text = text.replace(
                '        message = f"test signalled FAIL',
                '        export_stdout(image)\n        message = f"test signalled FAIL',
            )
            text = text.replace(
                '    message = f"timed out',
                '    export_stdout(image)\n    message = f"timed out',
            )
            bench.write_text(text)
            platform = yaml.safe_load((base / "platform.yaml").read_text())
            platform["reserved"]["stdout"] = {
                "base": platform["reserved"]["tohost"]["base"] - 65536 - 8,
                "size": "64K+8",
            }
            # This top sizes memories in bytes through its map package, not addr_width.
            platform["config"]["addr_widths"] = []
            platform["checks"] = []
            platform["generate"] = {
                key: {
                    **value,
                    "path": str(stage / "runtime" / Path(value["path"]).name),
                }
                for key, value in platform["generate"].items()
                if key in ("specs", "boot_ld", "runtime")
            }
            platform_file = stage / "platform.yaml"
            platform_file.write_text(yaml.safe_dump(platform, sort_keys=False))
            with (home / ".modular-bootstrap.log").open("w") as log:
                subprocess.run(
                    [
                        "riscv-tools",
                        "--root",
                        str(sdk),
                        "generate-memory-map",
                        "--platform",
                        str(platform_file),
                    ],
                    check=True,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
            for source in (stage / "runtime").iterdir():
                source.write_text(
                    source.read_text()
                    .replace(str(stage), str(destination))
                    .replace(
                        str(stage.relative_to(sdk)), ".sdk/platforms/modular"
                    )
                )
            for value in platform["generate"].values():
                value["path"] = (
                    ".sdk/platforms/modular/runtime/"
                    + Path(value["path"]).name
                )
            platform_file.write_text(yaml.safe_dump(platform, sort_keys=False))
            (stage / "config.yaml").write_text(
                yaml.safe_dump(
                    {
                        "extends": "../../../src/simulation/modular/config.yaml",
                        "memory_map": "platform.yaml",
                        "toolchain": {
                            "specs": ".sdk/platforms/modular/runtime/rv32im-fpga.specs"
                        },
                        "paths": {
                            "boot_memory": ".sdk/platforms/modular/runtime/boot_memory.S",
                            "boot_memory_linker_script": ".sdk/platforms/modular/runtime/boot_memory.ld",
                        },
                        "sim": {"python_path": [".sdk/platforms/modular"]},
                    },
                    sort_keys=False,
                )
            )
            (stage / ".sdk-view.json").write_text(
                json.dumps(expected, sort_keys=True) + "\n"
            )
            destination.parent.mkdir(exist_ok=True)
            if destination.exists():
                shutil.rmtree(destination)
            stage.rename(destination)
    return destination


def modular_storage(sdk: Path, root: Path, config: dict) -> None:
    """Use compact variable storage with the original synchronous port contract."""
    folder = root / ".rv32/storage"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("ram", "rom"):
        source = sdk / (f"Memory/src/{name.upper()}/SoC/{name}_simulation.vhd")
        entity = source.read_text().split("architecture rtl of ", 1)[0]
        target = folder / source.name
        target.write_text(
            entity + (sdk / f".sdk/models/{name}.vhd.in").read_text()
        )
        config["sim"]["vhdl_sources"] = [
            str(target) if Path(p) == source else p
            for p in config["sim"]["vhdl_sources"]
        ]
