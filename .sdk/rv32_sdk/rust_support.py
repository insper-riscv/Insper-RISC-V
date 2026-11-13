"""Vendor standalone Rust runtime/FFI crates and manage only owned Cargo entries."""

import json
import os
import tomllib
from pathlib import Path
from typing import Any


def tree(files: dict[str, bytes], source: Path, prefix: str) -> None:
    """Copy source files, excluding compiler outputs and generated lockfiles."""
    for folder, directories, names in os.walk(source, followlinks=False):
        directories[:] = sorted(
            name for name in directories if name not in {"target", ".git"}
        )
        for name in sorted(names):
            path = Path(folder) / name
            relative = path.relative_to(source)
            if path.is_symlink():
                raise SystemExit(f"Symlink in Rust driver source: {path}")
            if (
                path.suffix in {".rs", ".toml", ".h", ".md"}
                or path.name == ".gitignore"
            ):
                files[f"{prefix}/{relative.as_posix()}"] = path.read_bytes()


def vendor_driver(
    files: dict[str, bytes], descriptor: Path, name: str
) -> None:
    """Keep each safe crate, sys crate and C implementation together."""
    source = descriptor.parent.parent / "rust"
    if not (source / f"insper-riscv-{name.lower()}/Cargo.toml").is_file():
        raise SystemExit(f"Rust driver missing: {source}")
    tree(files, source, f"{name}/rust")


def vendor_runtime(sdk: Path, files: dict[str, bytes]) -> None:
    """Every generated Rust project gets the same platform-neutral runtime."""
    tree(files, sdk / ".sdk/rust/rv32-runtime", "rv32-runtime")


def dependencies(files: dict[str, bytes]) -> dict[str, str]:
    """Find safe crates, never expose the low-level FFI crates as direct deps."""
    result = {}
    for name, content in files.items():
        if not name.endswith("Cargo.toml"):
            continue
        package = tomllib.loads(content.decode()).get("package", {})
        crate = package.get("name", "")
        if (
            crate == "rv32-runtime" or crate.startswith("insper-riscv-")
        ) and not crate.endswith("-sys"):
            result[crate] = "vendor/" + str(Path(name).parent)
    return dict(sorted(result.items()))


def dependency_update(
    root: Path, project: dict[str, Any], wanted: dict[str, str]
) -> tuple[Path, str, dict[str, str]]:
    """Preserve custom dependencies/comments; refuse edited managed entries."""
    manifest = root / project.get("manifest", "Cargo.toml")
    if any(part.is_symlink() for part in (manifest, *manifest.parents)):
        raise SystemExit("Refusing symlink in Rust manifest path")
    manifest = manifest.resolve()
    if root.resolve() not in manifest.parents:
        raise SystemExit(
            "Rust manifest must be a regular file within the project"
        )
    text = manifest.read_text()
    record = root / ".rv32/rust-dependencies.json"
    if record.is_symlink():
        raise SystemExit("Refusing symlink in Rust dependency record")
    previous = json.loads(record.read_text()) if record.exists() else {}
    for crate, line in previous.items():
        if line + "\n" not in text:
            raise SystemExit(
                f"Managed Cargo dependency was edited: {crate}; files preserved"
            )
        text = text.replace(line + "\n", "", 1)
    parsed = tomllib.loads(text)
    existing = parsed.get("dependencies", {})
    managed = {}
    for crate, path in wanted.items():
        value = existing.get(crate)
        if value is not None:
            # Template declarations become managed. Custom dependencies stay owned
            # by the user; they can intentionally point at an external driver tree.
            if isinstance(value, dict) and value == {"path": path}:
                line = f"{crate} = {{ path = {json.dumps(path)} }}"
                if line + "\n" in text:
                    text = text.replace(line + "\n", "", 1)
                else:
                    continue
            else:
                continue
        managed[crate] = f"{crate} = {{ path = {json.dumps(path)} }}"
    lines = text.splitlines(keepends=True)
    position = next(
        (
            i + 1
            for i, line in enumerate(lines)
            if line.strip() == "[dependencies]"
        ),
        None,
    )
    if position is None:
        lines.extend(["\n[dependencies]\n"])
        position = len(lines)
    lines[position:position] = [line + "\n" for line in managed.values()]
    updated = "".join(lines)
    tomllib.loads(updated)
    return manifest, updated, managed


def check_dependencies(
    root: Path, project: dict[str, Any], wanted: dict[str, str]
) -> None:
    """Preflight Cargo changes before writing any vendored files."""
    dependency_update(root, project, wanted)


def install_dependencies(
    root: Path, project: dict[str, Any], wanted: dict[str, str]
) -> None:
    """Atomically update the manifest and remember exactly the inserted lines."""
    manifest, text, managed = dependency_update(root, project, wanted)
    temporary = manifest.with_name(manifest.name + ".rv32-tmp")
    if temporary.exists() or temporary.is_symlink():
        raise SystemExit(f"Temporary Cargo file already exists: {temporary}")
    temporary.write_text(text)
    os.replace(temporary, manifest)
    record = root / ".rv32/rust-dependencies.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(managed, indent=2, sort_keys=True) + "\n")


EXAMPLES = {
    "GPIO": (
        "use insper_riscv_gpio::{GPIO, GPIOError as Error, Direction};",
        """let gpio = GPIO::new(4)?;
    let mut pin = gpio.get(0)?;
    pin.set_direction(Direction::Output)?;
    pin.set_high()?;
    pin.set_low()?;
    pin.set_direction(Direction::Input)?;""",
    ),
    "TIMER": (
        "use insper_riscv_timer::{Timer, Error};",
        """let mut timer = Timer::new()?;
    timer.stop();
    timer.one_shot(true);
    timer.set_top(100);
    timer.set_divider(1)?;
    timer.load(0);
    timer.start();
    timer.stop();""",
    ),
    "CLINT": (
        "use insper_riscv_clint::{Clint, Error};",
        """let mut clint = Clint::new()?;
    let _ticks = clint.time();
    clint.set_deadline(u64::MAX);
    clint.set_software_interrupt(true);
    assert!(clint.software_interrupt_pending());
    clint.set_software_interrupt(false);""",
    ),
    "PLIC": (
        "use insper_riscv_plic::{Plic, Error};",
        """let mut plic = Plic::new()?;
    plic.set_priority(1, 1)?;
    plic.set_threshold(0)?;
    plic.enable(1, false)?;
    assert_eq!(plic.pending(0), Err(Error::Rejected));""",
    ),
    "UART": (
        "use insper_riscv_uart::{Uart, Error};",
        """let mut uart = Uart::new()?;
    assert_eq!(uart.write(b"UART driver transmission\\n", 4096), 25);""",
    ),
    "DISPLAY": (
        "use insper_riscv_display::{Display, Error};",
        """let mut display = Display::new()?;
    let saved = display.read();
    display.write_digit(0, 10)?;
    let readback = display.read_digit(0)?;
    display.write(saved);
    assert_eq!(readback, 10);""",
    ),
    "FLASH": (
        "use insper_riscv_flash::{Flash, Error};",
        """let mut flash = Flash::new()?;
    // Read-only demonstration: do not erase or program attached hardware.
    let _busy = flash.busy();
    let _refused = flash.refused();""",
    ),
}


def example_files(
    sdk: Path, project: dict[str, Any], name: str
) -> dict[str, bytes]:
    """Generate independent Rust projects without recursively generating examples."""
    files = {}
    for folder in (sdk / "templates/common", sdk / "templates/rust"):
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                files[str(path.relative_to(folder))] = path.read_bytes()
    config = {
        "name": name.lower() + "-rust-example",
        "language": "rust",
        "platform": project.get("platform", "internal-mem"),
        "cpu_profile": project.get("cpu_profile", "auto"),
        "manifest": "Cargo.toml",
        "generate_drivers": True,
        "generate_driver_examples": False,
    }
    files["rv32.toml"] = (
        "[project]\n"
        + "\n".join(
            f"{key} = {json.dumps(value)}" for key, value in config.items()
        )
        + "\n"
    ).encode()
    imports, body = EXAMPLES[name]
    files["src/main.rs"] = (
        "#![no_std]\n#![no_main]\n\nuse rv32_runtime::{entry, println};\n"
        + imports
        + "\n\nentry!(main);\n\nfn main() -> Result<(), Error> {\n    "
        + body
        + f'\n    println!("{name} Rust example: PASS");\n    Ok(())\n}}\n'
    ).encode()
    files["README.md"] = (
        f"# {name} Rust driver project\n\nOpen in its Dev Container, prepare, and simulate.\n"
        "Drivers/runtime and path dependencies are generated from rv32.toml.\n"
        "Copy this managed project elsewhere before editing. FLASH is read-only.\n"
    ).encode()
    return {f"{name}/example/{key}": value for key, value in files.items()}
