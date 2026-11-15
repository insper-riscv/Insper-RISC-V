#!/usr/bin/env python3
"""Build and run an external C or Rust project on the RV32 platform."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import tomllib
import traceback
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

import yaml
from riscv_tools import (
    bin_to_image,
    boot_memory,
    quartus_program,
    ram_target,
)
from riscv_tools import compiler as compiler_mod
from riscv_tools.jtag import JtagLink
from riscv_tools.jtag.hardware import idcode_of, parse_jtagconfig, same_idcode
from riscv_tools.memory_map.expressions import evaluate
from riscv_tools.orchestrator import run_test_via_jtag
from riscv_tools.settings import deep_merge, load_config

from rv32_sdk import cpu_profiles, drivers, sof_cache, source_check, views

RUST_TARGET = "riscv32im-unknown-none-elf"
HARDWARE_TOOLS = ["quartus_sh", "quartus_pgm", "quartus_stp", "jtagconfig"]
PROGRAM_OUTPUT: TextIO | None = None


def emit_program_output(payload: bytes) -> None:
    sink = PROGRAM_OUTPUT if PROGRAM_OUTPUT is not None else sys.stdout
    if hasattr(sink, "buffer"):
        sink.buffer.write(payload)
    else:
        sink.write(payload.decode("utf-8", errors="replace"))
    sink.flush()


@contextmanager
def diagnostic_log(path: Path, debug: bool) -> Iterator[None]:
    if debug:
        yield
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as log:
        sys.stdout.flush()
        sys.stderr.flush()
        saved_out, saved_err = os.dup(1), os.dup(2)
        try:
            os.dup2(log.fileno(), 1)
            os.dup2(log.fileno(), 2)
            yield
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(saved_out, 1)
            os.dup2(saved_err, 2)
            os.close(saved_out)
            os.close(saved_err)


def env_path(name: str, default: Path | None = None) -> Path:
    value = os.environ.get(name)
    if value:
        return Path(value).expanduser().resolve()
    if default is not None:
        return default.expanduser().resolve()
    raise SystemExit(f"{name} is not set")


SDK = env_path("RV32_SDK_ROOT", Path(__file__).resolve().parents[2])


def rust_target(project: dict[str, Any]) -> str:
    selected = cpu_profiles.selected(SDK, project)
    return selected["rust_target"] if selected else RUST_TARGET


def platform_dir(project: dict[str, Any]) -> Path:
    selected = project.get("platform", "internal-mem")
    if selected == "internal-mem":
        views.ensure_internal_mem(SDK)
    elif selected == "modular":
        views.ensure_modular(SDK)
    choices = {
        "internal-mem": SDK / ".sdk/platforms/internal-mem",
        "de0-cv": SDK / "src/cyclone-v/de0-cv",
        "modular": SDK / ".sdk/platforms/modular",
    }
    if selected not in choices:
        raise SystemExit(
            "project.platform must be internal-mem, modular or de0-cv"
        )
    return choices[selected]


def project_root(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return env_path("RV32_PROJECT_ROOT", Path.cwd())


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, text=True, check=False)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def require_commands(commands: list[str]) -> None:
    missing = [
        command for command in commands if shutil.which(command) is None
    ]
    if missing:
        raise SystemExit("Missing required command(s): " + ", ".join(missing))


def read_project(root: Path) -> dict[str, Any]:
    source_check.check(SDK)
    path = root / "rv32.toml"
    if not path.is_file():
        raise SystemExit(
            f"Missing {path}; create the project with `rv32-new`."
        )
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise SystemExit(f"{path} needs a [project] table")
    language = project.get("language")
    if language not in {"c", "rust"}:
        raise SystemExit("project.language must be `c` or `rust`")
    cpu_profiles.selected(SDK, project)
    return project


def project_name(project: dict[str, Any]) -> str:
    name = str(project.get("name", "app"))
    allowed = "-_abcdefghijklmnopqrstuvwxyz0123456789"
    if not name or any(character not in allowed for character in name.lower()):
        raise SystemExit(
            "project.name may contain only letters, digits, `-` and `_`"
        )
    return name


def generated_paths(root: Path) -> dict[str, Path]:
    state = root / ".rv32"
    return {
        "state": state,
        "config": state / "config.yaml",
        "include": state / "include",
        "c_dir": state / "sources" / "c",
        "asm_dir": state / "sources" / "asm",
        "build": root / "build",
        "logs": root / "logs",
    }


def write_config(
    root: Path, project: dict[str, Any], *, simulation: bool = False
) -> Path:
    source_check.check(SDK)
    cycles = project.get("simulation_timeout_cycles", 2_000_000)
    if type(cycles) is not int or cycles <= 0:
        raise SystemExit(
            "project.simulation_timeout_cycles must be a positive integer"
        )
    paths = generated_paths(root)
    paths["include"].mkdir(parents=True, exist_ok=True)
    paths["c_dir"].mkdir(parents=True, exist_ok=True)
    paths["asm_dir"].mkdir(parents=True, exist_ok=True)

    include_dirs = project.get("include_dirs", [])
    if not isinstance(include_dirs, list) or any(
        not isinstance(item, str) or not item.strip() for item in include_dirs
    ):
        raise SystemExit(
            "project.include_dirs must be a list of non-empty directory paths"
        )
    include_paths = [(root / item).resolve() for item in include_dirs]
    for directory in include_paths:
        if not directory.is_dir():
            raise SystemExit(f"Header directory does not exist: {directory}")
    enabled = project.get("generate_drivers", False)
    if not isinstance(enabled, bool):
        raise SystemExit("project.generate_drivers must be true or false")
    generated_sources = []
    if enabled:
        generated = drivers.generate(
            SDK, root, project, platform_dir(project) / "platform.yaml"
        )
        include_paths.extend(root / p for p in generated["include_dirs"])
        if project["language"] == "c":
            generated_sources = [root / p for p in generated["sources"]]
    uart_stdio = project.get("simulation_uart_stdio", False)
    if not isinstance(uart_stdio, bool):
        raise SystemExit("project.simulation_uart_stdio must be true or false")
    mode_source = paths["state"] / "stdio-mode.c"
    mode_text = (
        "#include <stdint.h>\nvolatile uint32_t rv32_stdio_uart_enabled = "
        + str(int(not simulation or uart_stdio))
        + "u;\n"
    )
    if not mode_source.exists() or mode_source.read_text() != mode_text:
        mode_source.write_text(mode_text)
    runtime = platform_dir(project) / "runtime"
    extra_sources = [
        root / str(item) for item in project.get("sources", [])
    ] + generated_sources
    extra_sources = list(
        dict.fromkeys(path.resolve() for path in extra_sources)
    )
    data = {
        "extends": str(platform_dir(project) / "config.yaml"),
        "paths": {
            "include_dir": str(paths["include"]),
            "include_dirs": [str(directory) for directory in include_paths],
            "build_dir": str(paths["build"]),
            "c_dir": str(paths["c_dir"]),
            "asm_dir": str(paths["asm_dir"]),
            "sources": [
                str(runtime / "_exit.c"),
                str(runtime / "stdio.c"),
                str(mode_source),
                *[str(path.resolve()) for path in extra_sources],
            ],
        },
        "sim": {
            "env": {
                "SIM_TIMEOUT_CYCLES": str(cycles),
                "RV32_SIM_STDOUT_FILE": str(paths["state"] / "sim-stdout.bin"),
                "RV32_STDOUT_CAPACITY": str(
                    evaluate(
                        yaml.safe_load(
                            (
                                platform_dir(project) / "platform.yaml"
                            ).read_text()
                        )["reserved"]["stdout"]["size"]
                    )
                    - 8
                ),
            }
        },
        "run_log": {"logs_dir": str(paths["logs"])},
    }
    base = load_config(platform_dir(project) / "config.yaml")

    def absolute(value: str) -> str:
        return str((SDK / value).resolve())

    data["toolchain"] = {"specs": absolute(base["toolchain"]["specs"])}
    for key in ("boot_memory", "boot_memory_linker_script"):
        data["paths"][key] = absolute(base["paths"][key])
    data["quartus"] = {
        "project_dir": absolute(
            base["quartus"]["project_dir"] or ".rv32/simulation-only"
        )
    }
    data["sim"]["vhdl_sources"] = [
        absolute(value) for value in base["sim"]["vhdl_sources"]
    ]
    data["sim"]["python_path"] = [
        absolute(value) for value in base["sim"]["python_path"]
    ]
    data["sim"]["libraries"] = {
        key: [absolute(value) for value in values]
        for key, values in base["sim"].get("libraries", {}).items()
    }
    data["sim"]["run_files"] = {
        key: absolute(value)
        for key, value in base["sim"].get("run_files", {}).items()
    }
    if base.get("freq_sweep", {}).get("pll_file"):
        data["freq_sweep"] = {
            "pll_file": absolute(base["freq_sweep"]["pll_file"])
        }
    data = deep_merge(base, data)
    data.pop("extends", None)
    selected = cpu_profiles.selected(SDK, project)
    if selected is not None:
        cpu_profiles.apply(SDK, root, platform_dir(project), data, selected)
    if project.get("platform") == "modular":
        views.modular_storage(SDK, root, data)
    # Tools knows more optional ISA switches than every pinned platform top.
    # Disabled switches may be omitted; enabled unsupported features are errors.
    declared = None
    fixed_enabled = set()
    for source in data["sim"]["vhdl_sources"]:
        if Path(source).name == "config_pkg.vhd":
            fixed_enabled.update(
                name.lower()
                for name in re.findall(
                    r"\bconstant\s+(HAS_\w+)\s*:\s*boolean\s*:=\s*true\s*;",
                    Path(source).read_text(),
                    re.I,
                )
            )
    entity = re.compile(
        r"\bentity\s+"
        + re.escape(data["sim"]["toplevel"])
        + r"\s+is(.*?)\bport\s*\(",
        re.I | re.S,
    )
    for source in data["sim"]["vhdl_sources"]:
        match = entity.search(Path(source).read_text())
        if match:
            declared = {
                name.lower()
                for name in re.findall(r"^\s*(\w+)\s*:", match.group(1), re.M)
            }
            break
    if declared is not None:
        filtered = {}
        for name, value in data["sim"]["parameters"].items():
            if name.lower() in declared:
                filtered[name] = value
            elif (
                value is not False
                and str(value).lower() != "false"
                and name.lower() not in fixed_enabled
            ):
                raise SystemExit(
                    f"Platform top does not support enabled generic {name}"
                )
        data["sim"]["parameters"] = filtered
    paths["config"].write_text(yaml.safe_dump(data, sort_keys=False))
    return paths["config"]


def tool(config: Path, *arguments: str, check: bool = True) -> int:
    result = run(
        [
            "riscv-tools",
            "--config",
            str(config),
            "--root",
            str(config.parent.parent),
            *arguments,
        ],
        cwd=SDK,
        check=check,
    )
    return result.returncode


def prepare_c_source(root: Path, project: dict[str, Any]) -> None:
    source = (root / str(project.get("source", "src/main.c"))).resolve()
    if not source.is_file():
        raise SystemExit(f"C source does not exist: {source}")
    destination = generated_paths(root)["c_dir"] / project_name(project)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source.parent, destination)
    copied_source = destination / source.name
    canonical_source = destination / "src.c"
    if copied_source != canonical_source:
        copied_source.replace(canonical_source)
    selected = cpu_profiles.selected(SDK, project)
    if selected is not None:
        canonical_source.write_text(
            cpu_profiles.prepare_source(canonical_source.read_text(), selected)
        )


def compile_runtime(root: Path, config: Path) -> dict[str, str]:
    cfg = load_config(config)
    specs = Path(cfg["toolchain"]["specs"]).resolve()
    runtime = platform_dir(read_project(root)) / "runtime"
    output = generated_paths(root)["state"] / "rust-runtime"
    output.mkdir(parents=True, exist_ok=True)
    objects: dict[str, str] = {}
    march = cfg.get("sdk_cpu_profile", {}).get("march", "rv32im")
    stamp = output / ".march"
    changed = not stamp.exists() or stamp.read_text() != march
    for stem in ("_exit", "stdio", "mode"):
        source = (
            (generated_paths(root)["state"] / "stdio-mode.c")
            if stem == "mode"
            else runtime / f"{stem}.c"
        )
        object_path = output / f"{stem}.o"
        object_is_stale = (
            changed
            or not object_path.exists()
            or object_path.stat().st_mtime
            < max(
                source.stat().st_mtime,
                specs.stat().st_mtime,
                *(header.stat().st_mtime for header in runtime.glob("*.h")),
            )
        )
        if object_is_stale:
            run(
                [
                    str(cfg["toolchain"]["gcc"]),
                    "-march=" + march,
                    "-mabi=ilp32",
                    "-std=c23",
                    "-Os",
                    "-ffunction-sections",
                    "-fdata-sections",
                    f"--specs={specs}",
                    "-c",
                    str(source),
                    "-o",
                    str(object_path),
                ],
                cwd=root,
            )
        objects[stem] = str(object_path)
    stamp.write_text(march)
    return {
        "RV32_RUST_MARCH": march,
        "RV32_RUST_SPECS": str(specs),
        "RV32_RUST_EXIT_OBJ": objects["_exit"],
        "RV32_RUST_STDIO_OBJ": objects["stdio"],
        "RV32_RUST_MODE_OBJ": objects["mode"],
    }


def cargo_elf(root: Path, project: dict[str, Any], config: Path) -> Path:
    manifest = (root / str(project.get("manifest", "Cargo.toml"))).resolve()
    if not manifest.is_file():
        raise SystemExit(f"Rust manifest does not exist: {manifest}")
    if project.get("generate_drivers", False):
        run(["bash", str(SDK / "scripts/rust-build-deps.sh")], cwd=root)
    env = dict(os.environ)
    env.update(compile_runtime(root, config))
    if project.get("generate_drivers", False):
        for name in (
            "GPIO",
            "TIMER",
            "CLINT",
            "PLIC",
            "UART",
            "DISPLAY",
            "FLASH",
        ):
            key = f"RV32_{name}_CONFIG_DIR"
            env.pop(key, None)
            directory = root / "vendor" / name
            if (directory / f"rv32_{name.lower()}_platform.h").is_file():
                env[key] = str(directory.resolve())
    env["RV32_GCC"] = (
        shutil.which("riscv32-unknown-elf-gcc") or "riscv32-unknown-elf-gcc"
    )
    target = rust_target(project)
    env["CARGO_TARGET_" + target.upper().replace("-", "_") + "_LINKER"] = str(
        SDK / "scripts" / "rv32-rust-linker"
    )
    # The built-in target normally invokes rust-lld directly. This project
    # deliberately uses GCC as a linker driver so the existing picolibc specs,
    # startup object and memory map are shared with C applications.
    rustflags = env.get("RUSTFLAGS", "")
    runtime_hash = hashlib.sha256()
    for key in (
        "RV32_RUST_SPECS",
        "RV32_RUST_EXIT_OBJ",
        "RV32_RUST_STDIO_OBJ",
        "RV32_RUST_MODE_OBJ",
    ):
        runtime_hash.update(Path(env[key]).read_bytes())
    runtime_hash.update((SDK / "scripts/rv32-rust-linker").read_bytes())
    # Cargo cannot otherwise notice changes to externally linked platform objects.
    stamp = runtime_hash.hexdigest()[:24]
    env["RUSTFLAGS"] = (
        f"{rustflags} -C linker-flavor=gcc -C metadata=rv32sdk{stamp}".strip()
    )
    command = [
        "cargo",
        "build",
        "--release",
        "--manifest-path",
        str(manifest),
        "--target",
        target,
        "--target-dir",
        str(generated_paths(root)["build"] / "cargo"),
        "--message-format=json-render-diagnostics",
    ]
    print("+", " ".join(command), flush=True)
    process = subprocess.Popen(
        command,
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    executable: Path | None = None
    assert process.stdout is not None
    for line in process.stdout:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            print(line, end="")
            continue
        rendered = message.get("message", {}).get("rendered")
        if rendered:
            print(rendered, end="", file=sys.stderr)
        if message.get("reason") == "compiler-artifact" and message.get(
            "executable"
        ):
            executable = Path(message["executable"])
    status = process.wait()
    if status:
        raise subprocess.CalledProcessError(status, command)
    if executable is None:
        raise SystemExit("Cargo produced no executable artifact")
    return executable


def package_rust(
    root: Path,
    project: dict[str, Any],
    config: Path,
    emit: str,
) -> None:
    cfg = load_config(config)
    name = project_name(project)
    executable = cargo_elf(root, project, config)
    output = generated_paths(root)["build"] / (
        "real" if emit == "mif" else "sim"
    )
    output.mkdir(parents=True, exist_ok=True)
    elf = output / f"{name}.elf"
    binary = output / f"{name}.bin"
    shutil.copy2(executable, elf)
    run(
        [
            str(cfg["toolchain"]["objcopy"]),
            "-O",
            "binary",
            str(elf),
            str(binary),
        ],
        cwd=root,
    )

    flash_pad_words = int(cfg["memory"]["rom_base"]) // 4
    entry: dict[str, Any] = {
        "name": name,
        "march": cfg.get("sdk_cpu_profile", {}).get("march", "rv32im"),
        "kind": "unit",
        "lang": "Rust",
    }
    if emit == "mif":
        image = output / f"{name}.mif"
        bin_to_image.bin_to_mif(
            binary,
            image,
            depth=flash_pad_words + int(cfg["memory"]["rom_words"]),
            pad_words=flash_pad_words,
        )
        entry["mif"] = str(image)
        entry["timeout_s"] = float(
            project.get("timeout_seconds", cfg["quartus"]["default_timeout_s"])
        )
    else:
        image = output / f"{name}.hex"
        if cfg["sim"]["hex_format"] == "verilog":
            compiler_mod.elf_to_verilog_hex(cfg["toolchain"], elf, image)
        else:
            bin_to_image.bin_to_hex(binary, image, pad_words=flash_pad_words)
        entry["hex"] = str(image)
    (output / "manifest.json").write_text(json.dumps([entry], indent=2) + "\n")
    print(f"Wrote {output / 'manifest.json'}")


def build(root: Path, project: dict[str, Any], emit: str) -> None:
    config = write_config(root, project, simulation=emit == "hex")
    if project["language"] == "c":
        prepare_c_source(root, project)
        tool(config, "generate-header")
        tool(config, "compile", "--emit", emit)
    else:
        package_rust(root, project, config, emit)


def detect_jtag_hardware(device_name: str, cable: str | None = None) -> str:
    """Select only a cable containing the project's chip; never fall back to another board."""
    result = subprocess.run(
        ["jtagconfig"], capture_output=True, text=True, check=False, timeout=20
    )
    print("JTAG:\n" + result.stdout)
    if result.returncode:
        raise SystemExit("Unable to list the JTAG cables")
    wanted = idcode_of(device_name)
    if wanted is None:
        raise SystemExit("The project needs a JTAG device IDCODE")
    matches = [
        entry
        for entry in parse_jtagconfig(result.stdout)
        if not entry.broken
        and any(same_idcode(device.idcode, wanted) for device in entry.devices)
        and (cable is None or entry.name == cable)
    ]
    if not matches:
        raise SystemExit(
            f"No healthy JTAG cable contains the project device {wanted}"
        )
    if len(matches) != 1:
        raise SystemExit(
            "Several matching boards are connected; set project.jtag_hardware to the desired cable name"
        )
    return matches[0].name


def probe_jtag(device_name: str, cable: str | None = None) -> None:
    print("Selected JTAG cable:", detect_jtag_hardware(device_name, cable))


def doctor(
    root: Path,
    project: dict[str, Any],
    require_hardware: bool = False,
) -> None:
    required = [
        SDK / "Core",
        SDK / "src",
        SDK / ".sdk" / "tools",
        SDK / "Common-Components",
        SDK / "Peripherals",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise SystemExit("Incomplete RV32 SDK: " + missing_text)
    require_commands(
        [
            "riscv-tools",
            "riscv32-unknown-elf-gcc",
            "riscv32-unknown-elf-objcopy",
        ]
    )
    selected = cpu_profiles.selected(SDK, project)
    if selected is not None and "m" not in selected["extensions"]:
        variants = subprocess.check_output(
            ["riscv32-unknown-elf-gcc", "--print-multi-lib"], text=True
        ).splitlines()
        if len(variants) < 2:
            raise SystemExit(
                "This single-variant toolchain cannot validate libraries for a CPU without M. Rebuild with the SDK's pinned multilib Dev Container image."
            )
    if project["language"] == "rust":
        require_commands(["cargo", "rustc", "rustup"])
        installed = subprocess.run(
            ["rustup", "target", "list", "--installed"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.splitlines()
        target = rust_target(project)
        if target not in installed:
            raise SystemExit(
                f"Missing Rust target; run `rustup target add {target}`"
            )
    print(f"SDK: {SDK}")
    print(f"Project: {root}")
    print(f"Language: {project['language']}")
    print(
        "Simulation:", "available" if shutil.which("ghdl") else "unavailable"
    )
    missing_hardware = [
        tool_name
        for tool_name in HARDWARE_TOOLS
        if not shutil.which(tool_name)
    ]
    hardware_status = "available"
    if missing_hardware:
        hardware_status = "missing " + ", ".join(missing_hardware)
    print("FPGA:", hardware_status)
    if require_hardware:
        require_commands(HARDWARE_TOOLS)
        cfg = load_config(write_config(root, project))
        probe_jtag(cfg["quartus"]["jtag_device"], project.get("jtag_hardware"))


def setup(root: Path, project: dict[str, Any]) -> None:
    run(["uv", "sync", "--project", str(SDK / ".sdk")], cwd=SDK)
    if project["language"] == "rust":
        require_commands(["rustup"])
        if project.get("generate_drivers", False):
            run(["bash", str(SDK / "scripts/rust-build-deps.sh")], cwd=root)
        run(["rustup", "target", "add", rust_target(project)], cwd=root)
    config = write_config(root, project)
    if project["language"] == "c":
        tool(config, "generate-header")
    doctor(root, project)


def simulate(root: Path, project: dict[str, Any]) -> None:
    doctor(root, project)
    require_commands(["ghdl"])
    output = generated_paths(root)["state"] / "sim-stdout.bin"
    output.unlink(missing_ok=True)
    truncated = Path(str(output) + ".truncated")
    truncated.unlink(missing_ok=True)
    build(root, project, "hex")
    cycles = project.get("simulation_timeout_cycles", 2_000_000)
    print(
        f"Simulation limit: {cycles:,} cycles (project.simulation_timeout_cycles)"
    )
    try:
        status = tool(generated_paths(root)["config"], "sim", check=False)
    finally:
        if output.is_file():
            emit_program_output(output.read_bytes())
    if status:
        raise SystemExit(status)
    if truncated.is_file():
        raise SystemExit(
            "Program stdout exceeded its RAM buffer; output is incomplete."
        )


def fpga(root: Path, project: dict[str, Any], mode: str) -> None:
    if project.get("platform") == "modular":
        raise SystemExit(
            "The modular SDK platform is simulation-only; select an FPGA platform before programming."
        )
    cache = sof_cache.cache_root()
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / ".hardware.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fpga_locked(root, project, mode)


def fpga_locked(root: Path, project: dict[str, Any], mode: str) -> None:
    doctor(root, project, require_hardware=True)
    build(root, project, "mif")
    config = generated_paths(root)["config"]
    cfg = load_config(config)
    key = sof_cache.fingerprint(SDK, cfg)
    project_dir = (SDK / cfg["quartus"]["project_dir"]).resolve()
    sof = project_dir / cfg["quartus"]["sof_file"]
    link = JtagLink(
        detect_jtag_hardware(
            cfg["quartus"]["jtag_device"], project.get("jtag_hardware")
        ),
        cfg["quartus"]["jtag_device"],
    )
    manifest = generated_paths(root)["build"] / "real/manifest.json"
    entries = json.loads(manifest.read_text())
    entry = next(
        item for item in entries if item["name"] == project_name(project)
    )
    name, _ = cpu_profiles.hardware_stamp(link.hardware_name, key)
    programming_record = sof_cache.cache_root() / (".programmed-" + name)
    if (
        cfg.get("sdk_cpu_profile")
        and mode == "fast"
        and (
            not programming_record.exists()
            or programming_record.read_text() != key
        )
    ):
        raise SystemExit(
            "Selected CPU profile has not been programmed on this cable. Use Program FPGA first."
        )
    if mode != "fast":
        programming_record.parent.mkdir(parents=True, exist_ok=True)
        programming_record.unlink(missing_ok=True)
    if mode != "fast":
        cached = sof_cache.restore(key, sof)
        if mode == "reprogram" and not cached:
            raise SystemExit(
                "No verified SOF cache for this hardware. Use Program FPGA first."
            )
        print(
            "SOF cache: "
            + ("hit (no synthesis)" if cached else "miss (compiling hardware)")
        )
        if cached:
            quartus_program.program_only(
                link.hardware_name, project_dir, cfg["quartus"]["sof_file"]
            )
        else:
            output = generated_paths(root)["build"] / "boot_memory"
            boot_memory.build_boot_memory(
                cfg["toolchain"],
                cfg["paths"],
                SDK,
                output,
                boot_memory.BootMemoryOptions(base=cfg["isa"]["base"]),
            )
            boot_mif = output / "boot_memory.mif"
            bin_to_image.bin_to_mif(
                output / "boot_memory.bin",
                boot_mif,
                depth=cfg["memory"]["boot_memory_words"],
            )
            started = time.time_ns()
            try:
                quartus_program.full_reconfigure(
                    project=quartus_program.QuartusProject(
                        hardware_name=link.hardware_name,
                        project_dir=project_dir,
                        project_name=cfg["quartus"]["project_name"],
                        sof_file=cfg["quartus"]["sof_file"],
                        stale_cache_dirs=cfg["quartus"]["stale_cache_dirs"],
                    ),
                    rom=quartus_program.MifInit(
                        target=cfg["quartus"]["rom_mif_target"],
                        path=root / entry["mif"],
                    ),
                    boot_memory=quartus_program.MifInit(
                        target=cfg["quartus"]["boot_memory_mif_target"],
                        path=boot_mif,
                    ),
                )
            except subprocess.CalledProcessError as error:
                # A programming failure must not discard a fresh successful synthesis.
                if (
                    "Quartus Prime Full Compilation was successful"
                    in (error.stdout or "")
                    and sof.is_file()
                    and sof.stat().st_mtime_ns >= started
                    and sof_cache.fingerprint(SDK, cfg) == key
                ):
                    sof_cache.store(key, sof)
                raise
        if sof_cache.fingerprint(SDK, cfg) != key:
            raise SystemExit(
                "Hardware changed during programming; rerun Program FPGA."
            )
        sof_cache.store(key, sof)
        programming_record.write_text(key)
    entry["timeout_s"] = float(
        project.get("timeout_seconds", entry["timeout_s"])
    )
    value = run_test_via_jtag(cfg, link, entry, root)
    read_stdout(root, project)
    if value is None:
        raise SystemExit(
            "Program timed out; use Program FPGA if the hardware was changed."
        )
    if value != 1:
        raise SystemExit(f"Program returned failure (HTIF code {value >> 1}).")
    print("Program: PASS")


def read_stdout(root: Path, project: dict[str, Any]) -> None:
    doctor(root, project, require_hardware=True)
    config = write_config(root, project)
    cfg = load_config(config)
    platform = platform_dir(project) / "platform.yaml"
    platform_cfg = yaml.safe_load(platform.read_text(encoding="utf-8"))
    stdout_cfg = platform_cfg["reserved"]["stdout"]
    stdout_base = int(stdout_cfg["base"])
    # platform.yaml's region size includes the two 32-bit header words.
    stdout_bytes = evaluate(stdout_cfg["size"]) - 8
    ram_base = int(cfg["memory"]["ram_base"])
    word_offset = (stdout_base - ram_base) // 4
    link = JtagLink(
        hardware_name=detect_jtag_hardware(
            cfg["quartus"]["jtag_device"], project.get("jtag_hardware")
        ),
        device_name=cfg["quartus"]["jtag_device"],
    )
    target = ram_target.target_from_config(cfg, link)
    words = ram_target.read_words(link, target, word_offset, 2)
    length = min(words[0], stdout_bytes)
    data = (
        ram_target.read_words(link, target, word_offset + 2, (length + 3) // 4)
        if length
        else []
    )
    payload = b"".join(word.to_bytes(4, "little") for word in data)[:length]
    if not payload and not words[1]:
        return
    emit_program_output(payload)
    if words[1]:
        raise SystemExit(
            f"Program stdout exceeded its {stdout_bytes}-byte RAM buffer; output is incomplete."
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--debug",
        action="store_true",
        help="Show tool commands, warnings and diagnostics",
    )
    result.add_argument("--project", help="project directory; defaults to cwd")
    sub = result.add_subparsers(dest="command", required=True)
    for command in (
        "doctor",
        "setup",
        "build",
        "simulate",
        "stdout",
        "drivers",
    ):
        command_parser = sub.add_parser(command)
        command_parser.add_argument(
            "--debug", action="store_true", default=argparse.SUPPRESS
        )
    fpga_parser = sub.add_parser("fpga")
    fpga_parser.add_argument(
        "--debug", action="store_true", default=argparse.SUPPRESS
    )
    fpga_parser.add_argument(
        "--mode", choices=["full", "fast", "reprogram"], required=True
    )
    return result


def execute(
    args: argparse.Namespace, root: Path, project: dict[str, Any]
) -> None:
    if args.command == "doctor":
        doctor(root, project)
    elif args.command == "setup":
        setup(root, project)
    elif args.command == "build":
        build(root, project, "mif")
    elif args.command == "simulate":
        simulate(root, project)
    elif args.command == "drivers":
        drivers.generate(
            SDK, root, project, platform_dir(project) / "platform.yaml"
        )
    elif args.command == "stdout":
        read_stdout(root, project)
    else:
        fpga(root, project, args.mode)


def main() -> None:
    global PROGRAM_OUTPUT
    args = parser().parse_args()
    root = project_root(args.project)
    project = read_project(root)
    debug = args.debug or args.command == "doctor"
    log = root / "logs" / "rv32" / f"{args.command}-latest.log"
    output = None
    if not debug:
        output = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8")
        PROGRAM_OUTPUT = output
    try:
        with diagnostic_log(log, debug):
            execute(args, root, project)
    except (Exception, SystemExit) as error:
        if debug:
            raise
        code = (
            error.code
            if isinstance(error, SystemExit)
            else (
                error.returncode
                if isinstance(error, subprocess.CalledProcessError)
                else 1
            )
        )
        if code == 0:
            return
        with log.open("a", encoding="utf-8") as details:
            traceback.print_exc(file=details)
        message = (
            error.code
            if isinstance(error, SystemExit) and isinstance(error.code, str)
            else f"{args.command} failed"
        )
        print(
            f"RV32: {message}. Details: {log} (enable RV32 Debug Output).",
            file=sys.stderr,
        )
        raise SystemExit(code if isinstance(code, int) else 1) from None
    finally:
        PROGRAM_OUTPUT = None
        if output is not None:
            output.close()


if __name__ == "__main__":
    main()
