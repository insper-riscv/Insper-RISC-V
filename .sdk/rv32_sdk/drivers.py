"""Vendor C peripheral drivers against the selected platform's canonical map."""

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import yaml
from riscv_tools.memory_map.core import load_platform, peripheral_list, symbols
from riscv_tools.memory_map.expressions import evaluate
from riscv_tools.memory_map.interrupts import sources_of
from riscv_tools.memory_map.problems import platform_problems
from riscv_tools.memory_map.profile import resolve

from rv32_sdk import cpu_profiles, driver_examples, rust_support

IDENTIFIER = re.compile(r"[A-Z][A-Z0-9_]*")


def digest(data: bytes) -> str:
    """Track generated files so regeneration cannot destroy hand edits."""
    return hashlib.sha256(data).hexdigest()


def safe_name(value: str) -> str:
    """Reject invalid C identifiers from descriptors and platform maps."""
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise SystemExit(f"Invalid driver/peripheral identifier: {value!r}")
    return value


def relative_file(value: str) -> Path:
    """Constrain driver and ownership paths to the managed tree."""
    if not isinstance(value, str):
        raise SystemExit("Driver paths must be strings")
    path = Path(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(p in {".", ".."} for p in path.parts)
    ):
        raise SystemExit(f"Unsafe driver path: {value}")
    return path


def descriptors(sdk: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Discover reusable drivers in the peripheral repositories."""
    result = []
    for path in sorted(
        (sdk / "Peripherals/src").glob("*/**/driver/c/driver.yaml")
    ):
        if path.relative_to(sdk / "Peripherals/src").parts[0] == "common":
            continue
        spec = yaml.safe_load(path.read_text())
        if not isinstance(spec, dict) or spec.get("schema") != 1:
            raise SystemExit(f"Unsupported driver descriptor: {path}")
        safe_name(spec.get("name"))
        aliases = spec.get("instances")
        if not isinstance(aliases, list) or not aliases:
            raise SystemExit(f"Driver descriptor needs instance names: {path}")
        for alias in aliases:
            safe_name(alias)
        requirements = spec.get("requires_cpu_flags", [])
        if not isinstance(requirements, list):
            raise SystemExit(f"Invalid CPU requirements: {path}")
        for flag in requirements:
            safe_name(flag)
        size = spec.get("register_bytes")
        if type(size) is not int or size <= 0 or size % 4:
            raise SystemExit(f"Invalid register window: {path}")
        for kind, suffix in (("headers", ".h"), ("sources", ".c")):
            files = spec.get(kind, [])
            if not isinstance(files, list) or (
                kind == "headers" and not files
            ):
                raise SystemExit(f"Invalid {kind}: {path}")
            for value in files:
                source = path.parent / relative_file(value)
                if (
                    source.suffix != suffix
                    or not source.resolve().is_relative_to(
                        path.parent.resolve()
                    )
                    or not source.is_file()
                ):
                    raise SystemExit(f"Invalid driver source: {source}")
        if "example" in spec:
            example = path.parent / relative_file(spec["example"])
            if not example.is_file() or not example.resolve().is_relative_to(
                path.parent.resolve()
            ):
                raise SystemExit(f"Invalid driver example: {example}")
        result.append((path, spec))
    return result


def header(lines: list[str], guard: str) -> bytes:
    """Render a deterministic C23 configuration header."""
    return (
        "/* Generated from platform.yaml; regenerate with RV32: Refresh Peripheral Drivers. */\n"
        f"#ifndef {guard}\n#define {guard}\n\n#include <stdint.h>\n\n"
        + "\n".join(lines)
        + "\n\n#endif\n"
    ).encode()


def instance_irqs(platform: dict[str, Any]) -> dict[str, int]:
    """Match platform instance names to canonical interrupt source names."""
    sources = dict(sources_of(platform))
    irq = dict(sources)
    if "FLASH" in sources:
        irq["FLASH_CTRL"] = sources["FLASH"]
    if "UART" in {p["name"] for p in peripheral_list(platform)}:
        if platform.get("console") == "jtag" or (
            "UART" not in sources and "UART_JTAG" in sources
        ):
            if "UART_JTAG" in sources:
                irq["UART"] = sources["UART_JTAG"]
            else:
                irq.pop("UART", None)
        if platform.get("console") == "pins" and "UART" not in sources:
            irq.pop("UART", None)
    return irq


def plan(
    sdk: Path, project: dict[str, Any], platform_file: Path
) -> tuple[dict[str, bytes], dict[str, Any]]:
    """Resolve addresses with Tools instead of deriving them from slot IDs."""
    platform = load_platform(platform_file)
    problems = platform_problems(platform)
    if problems:
        raise SystemExit(
            "Invalid peripheral map: " + "; ".join(str(p) for p in problems)
        )
    selected = cpu_profiles.selected(sdk, project)
    profile = (
        selected["name"] if selected else str(platform.get("profile", "rv32i"))
    )
    table = symbols(platform)
    peripherals = peripheral_list(platform)
    irq = instance_irqs(platform)
    examples_enabled = project.get("generate_driver_examples", True)
    if not isinstance(examples_enabled, bool):
        raise SystemExit(
            "project.generate_driver_examples must be true or false"
        )
    examples = []
    files: dict[str, bytes] = {}
    flags = (
        selected["flags"]
        if selected
        else {
            key.upper(): value
            for key, value in resolve(platform, platform_file)[1].items()
            if key.startswith("has_")
        }
    )
    definitions = ["#define RV32_DRIVERS_CPU_PROFILE " + json.dumps(profile)]
    definitions.extend(
        f"#define RV32_CPU_{key} {int(bool(value))}"
        for key, value in sorted(flags.items())
    )
    for peripheral in peripherals:
        name = safe_name(peripheral["name"])
        base = table[f"{name}.base"]
        if base < 0 or base > 0xFFFFFFFF or base % 4:
            raise SystemExit(
                f"Driver requires a 32-bit aligned MMIO base: {name}"
            )
        definitions += [
            f"#define RV32_PERIPH_{name}_BASE UINT32_C(0x{base:08X})",
            f"#define RV32_PERIPH_{name}_SIZE UINT32_C({evaluate(peripheral['size'])})",
        ]
        if name in irq:
            definitions.append(
                f"#define RV32_PERIPH_{name}_IRQ UINT32_C({irq[name]})"
            )
    files["rv32_platform.h"] = header(definitions, "RV32_VENDOR_PLATFORM_H")
    sources, includes, umbrella, claimed = [], ["vendor"], [], set()
    for descriptor, spec in descriptors(sdk):
        name = spec["name"]
        if any(
            not flags.get(flag, False)
            for flag in spec.get("requires_cpu_flags", [])
        ):
            continue
        instances = [p for p in peripherals if p["name"] in spec["instances"]]
        if not instances:
            continue
        definitions = ['#include "../rv32_platform.h"']
        for instance in instances:
            alias = instance["name"]
            if alias in claimed:
                raise SystemExit(f"Ambiguous C driver for {alias}")
            claimed.add(alias)
            if evaluate(instance["size"]) < spec["register_bytes"]:
                raise SystemExit(f"MMIO window too small for {name}/{alias}")
            definitions.append(
                f"#define RV32_{name}_{alias}_BASE ((uintptr_t)RV32_PERIPH_{alias}_BASE)"
            )
            if alias in irq:
                definitions.append(
                    f"#define RV32_{name}_{alias}_IRQ RV32_PERIPH_{alias}_IRQ"
                )
        config = f"{name}/rv32_{name.lower()}_config.h"
        files[config] = header(definitions, f"RV32_VENDOR_{name}_CONFIG_H")
        includes.append("vendor/" + name)
        umbrella.append(config)
        for kind in ("headers", "sources"):
            for value in spec.get(kind, []):
                target = f"{name}/{value}"
                if target in files:
                    raise SystemExit(f"Driver filename collision: {target}")
                files[target] = (descriptor.parent / value).read_bytes()
                if kind == "headers":
                    umbrella.append(target)
                else:
                    sources.append("vendor/" + target)
        if name == "GPIO":
            gpio_definitions = []
            for alias in ("DEFAULT", "SWITCHES", "KEYS"):
                selected = (
                    instances[0]
                    if alias == "DEFAULT"
                    else next(
                        (item for item in instances if item["name"] == alias),
                        None,
                    )
                )
                base, width = "0", "0"
                if selected is not None:
                    base = f"((uintptr_t)RV32_PERIPH_{selected['name']}_BASE)"
                    width = driver_examples.context(
                        sdk, platform_file, platform, name, selected
                    )["PIN_COUNT"]
                gpio_definitions.extend(
                    [
                        f"#define RV32_GPIO_{alias}_BASE {base}",
                        f"#define RV32_GPIO_{alias}_PIN_COUNT {width}",
                    ]
                )
            files["GPIO/rv32_gpio_platform.h"] = header(
                ['#include "../rv32_platform.h"', *gpio_definitions],
                "RV32_GPIO_PLATFORM_H",
            )
        if name != "GPIO":
            fields = {
                "TIMER": {},
                "CLINT": {},
                "PLIC": {"SOURCE_COUNT": "0", "PRIORITY_BITS": "0"},
                "UART": {"BACKEND": "RV32_UART_SERIAL", "TX_CAPACITY": "0"},
                "DISPLAY": {"DIGIT_COUNT": "0"},
                "FLASH": {"PAGE_BYTES": "0"},
            }[name]
            configured = [
                (
                    item,
                    driver_examples.context(
                        sdk, platform_file, platform, name, item
                    ),
                )
                for item in instances
            ]
            definitions = ['#include "../rv32_platform.h"']
            aliases = (
                ["DEFAULT", "SERIAL", "JTAG"]
                if name == "UART"
                else ["DEFAULT"]
            )
            for alias in aliases:
                chosen = (
                    configured[0]
                    if alias == "DEFAULT"
                    else next(
                        (
                            item
                            for item in configured
                            if item[1]["BACKEND"] == f"RV32_UART_{alias}"
                        ),
                        None,
                    )
                )
                values = {"BASE": "0", **fields}
                if chosen is not None:
                    instance, context = chosen
                    values = {
                        "BASE": f"((uintptr_t)RV32_PERIPH_{instance['name']}_BASE)",
                        **{key: context[key] for key in fields},
                    }
                definitions.extend(
                    f"#define RV32_{name}_{alias}_{key} {value}"
                    for key, value in values.items()
                )
            files[f"{name}/rv32_{name.lower()}_platform.h"] = header(
                definitions, f"RV32_{name}_PLATFORM_H"
            )
        if project.get("language") == "rust":
            rust_support.vendor_driver(files, descriptor, name)
        if examples_enabled and "example" in spec:
            rendered = (
                rust_support.example_files(sdk, project, name)
                if project.get("language") == "rust"
                else driver_examples.project_files(
                    sdk,
                    project,
                    platform_file,
                    platform,
                    descriptor,
                    spec,
                    instances[0],
                )
            )
            files.update(rendered)
            if rendered:
                examples.append(f"vendor/{name}/example")
    if claimed:
        files["LICENSE.peripherals"] = (
            sdk / "Peripherals/LICENSE"
        ).read_bytes()
    if project.get("language") == "rust":
        rust_support.vendor_runtime(sdk, files)
    metadata = {
        "schema": 1,
        "profile": profile,
        "cpu_flags": flags,
        "platform": str(platform["platform"]),
        "platform_sha256": digest(platform_file.read_bytes()),
        "sources": sources,
        "rust_dependencies": rust_support.dependencies(files),
        "example_projects": examples,
        "include_dirs": includes,
        "umbrella": ["rv32_platform.h", *umbrella],
    }
    return files, metadata


def destination(vendor: Path, name: str) -> Path:
    """Reject symlinks before reading or writing managed project files."""
    path = vendor / relative_file(name)
    for part in (path, *path.parents):
        if part.is_symlink():
            raise SystemExit(
                f"Refusing symlink in managed driver path: {part}"
            )
        if part == vendor.parent:
            break
    return path


def install(
    root: Path, files: dict[str, bytes], metadata: dict[str, Any]
) -> None:
    """Validate ownership of every affected file before changing any of them."""
    vendor = root / "vendor"
    manifest = destination(vendor, ".rv32-drivers.json")
    previous = {}
    if manifest.exists():
        try:
            saved = json.loads(manifest.read_text())
            if saved.get("schema") != 1 or not isinstance(
                saved.get("files"), dict
            ):
                raise ValueError("invalid schema")
            previous = saved["files"]
        except (ValueError, OSError) as error:
            raise SystemExit(
                "Invalid managed driver manifest; files were preserved"
            ) from error
    for name in set(previous) | files.keys():
        path = destination(vendor, name)
        if path.exists():
            current = path.read_bytes()
            expected = previous.get(name)
            if expected is None and current != files.get(name):
                raise SystemExit(
                    f"Unmanaged driver file would be overwritten: {path}"
                )
            if expected is not None and digest(current) != expected:
                raise SystemExit(
                    f"Generated driver was edited; preserve your changes before regenerating: {path}"
                )
    for name, content in files.items():
        path = destination(vendor, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".rv32-tmp")
        if temporary.exists() or temporary.is_symlink():
            raise SystemExit(
                f"Temporary driver path already exists: {temporary}"
            )
        temporary.write_bytes(content)
        os.replace(temporary, path)
    for name in previous.keys() - files.keys():
        destination(vendor, name).unlink(missing_ok=True)
    record = dict(
        metadata,
        files={
            name: digest(content) for name, content in sorted(files.items())
        },
    )
    manifest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    umbrella = root / ".rv32/include/rv32_drivers.h"
    umbrella.parent.mkdir(parents=True, exist_ok=True)
    umbrella.write_bytes(
        header(
            [
                f'#include "../../vendor/{name}"'
                for name in metadata["umbrella"]
            ],
            "RV32_GENERATED_DRIVERS_H",
        )
    )


def generate(
    sdk: Path, root: Path, project: dict[str, Any], platform_file: Path
) -> dict[str, Any]:
    """Regenerate and return C compiler inputs without terminal noise."""
    files, metadata = plan(sdk, project, platform_file)
    if project.get("language") == "rust":
        rust_support.check_dependencies(
            root, project, metadata["rust_dependencies"]
        )
    install(root, files, metadata)
    if project.get("language") == "rust":
        rust_support.install_dependencies(
            root, project, metadata["rust_dependencies"]
        )
    return metadata
