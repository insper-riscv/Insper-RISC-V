"""Render standalone, map-selected C driver example projects."""

import json
import re
from pathlib import Path
from typing import Any

from riscv_tools.settings import load_config

TOKEN = re.compile(r"@([A-Z_]+)@")


def generic(source: Path, name: str) -> int:
    """Read a literal generic default rather than guessing from MMIO sizes."""
    pattern = (
        rf"^\s*{re.escape(name)}\s*:\s*(?:natural|positive|integer)"
        r"(?:\s+range\s+\d+\s+to\s+\d+)?\s*:=\s*(\d+)"
    )
    match = re.search(
        pattern, source.read_text(), re.MULTILINE | re.IGNORECASE
    )
    if not match:
        raise SystemExit(
            f"Cannot resolve example hardware parameter {name}: {source}"
        )
    return int(match[1])


def parameters(platform_file: Path) -> dict[str, Any]:
    """Read explicit simulation generic overrides when the platform has them."""
    config = platform_file.with_name("config.yaml")
    return (
        load_config(config).get("sim", {}).get("parameters", {})
        if config.exists()
        else {}
    )


def direct_uart(sdk: Path, platform_file: Path) -> str | None:
    """Detect legacy tops that instantiate a UART directly, regardless of slot."""
    config = platform_file.with_name("config.yaml")
    if not config.exists():
        return None
    sim = load_config(config).get("sim", {})
    for value in sim.get("vhdl_sources", []):
        source = sdk / value
        if source.stem == sim.get("toplevel") and source.is_file():
            kinds = set(
                re.findall(
                    r"entity\s+work\.(uart|jtag_uart)\b",
                    source.read_text(),
                    re.IGNORECASE,
                )
            )
            if len(kinds) == 1:
                return kinds.pop().lower()
    return None


def context(
    sdk: Path,
    platform_file: Path,
    platform: dict[str, Any],
    name: str,
    instance: dict[str, Any],
) -> dict[str, str]:
    """Resolve constructor arguments from the platform and instantiated RTL."""
    overrides = parameters(platform_file)
    soc = sdk / "src/soc/soc.vhd"
    periph = sdk / "Peripherals/src"
    alias = instance["name"]
    values = {"BASE": f"RV32_{name}_{alias}_BASE"}

    def number(key: str, source: Path = soc, io: str | None = None) -> int:
        if key.upper() in overrides:
            value = int(overrides[key.upper()])
        elif io and io in platform.get("io", {}):
            value = int(platform["io"][io]["count"])
        else:
            value = generic(source, key)
        if value <= 0:
            raise SystemExit(
                f"Cannot generate an example for a zero-width {alias}"
            )
        return value

    if name == "GPIO":
        role = {"SWITCHES": "switches", "KEYS": "keys"}.get(alias)
        width = (
            number(role + "_width", io=role)
            if role
            else number("data_width", periph / "GPIO/soc/gpio.vhd")
        )
        values["PIN_COUNT"] = str(width)
    elif name == "DISPLAY":
        values["DIGIT_COUNT"] = str(number("display_digits", io="display"))
    elif name == "PLIC":
        plic = platform.get("interrupts", {}).get("plic", {})
        values["SOURCE_COUNT"] = str(number("plic_n_sources"))
        values["PRIORITY_BITS"] = str(
            overrides.get(
                "PLIC_PRIORITY_BITS",
                plic.get("priority_bits", generic(soc, "plic_priority_bits")),
            )
        )
        sources = platform.get("interrupts", {}).get("sources", [])
        values["SOURCE"] = str(sources[0]["id"] if sources else 1)
    elif name == "FLASH":
        values["PAGE_BYTES"] = str(
            number(
                "page_bytes",
                periph / "flash-controller/soc/flash_controller.vhd",
            )
        )
    elif name == "UART":
        console = periph / "UART/console/console.vhd"
        direct = direct_uart(sdk, platform_file)
        if alias == "UART_JTAG" or platform.get("console") == "jtag":
            jtag = True
        elif alias == "UART_PINS" or platform.get("console") == "pins":
            jtag = False
        elif direct is not None:
            jtag = direct == "jtag_uart"
            console = periph / (
                "UART/jtag/jtag_uart.vhd" if jtag else "UART/serial/uart.vhd"
            )
        else:
            jtag = instance.get("id") == number("uart_jtag_id")
        values["BACKEND"] = "RV32_UART_JTAG" if jtag else "RV32_UART_SERIAL"
        values["TX_CAPACITY"] = str(
            1 << generic(console, "log2_depth")
            if jtag
            else generic(console, "tx_fifo_depth")
        )
    return values


def project_files(
    sdk: Path,
    project: dict[str, Any],
    platform_file: Path,
    platform: dict[str, Any],
    descriptor: Path,
    spec: dict[str, Any],
    instance: dict[str, Any],
) -> dict[str, bytes]:
    """Create an independent child project with recursion explicitly disabled."""
    name = spec["name"]
    selected_platform = project.get("platform", str(platform["platform"]))
    if selected_platform not in {"internal-mem", "modular", "de0-cv"}:
        return {}
    values = context(sdk, platform_file, platform, name, instance)
    source = (descriptor.parent / spec["example"]).read_text()
    missing = set(TOKEN.findall(source)) - values.keys()
    if missing:
        raise SystemExit(
            f"Unknown example placeholders for {name}: {sorted(missing)}"
        )
    source = TOKEN.sub(lambda match: values[match[1]], source)
    files: dict[str, bytes] = {}
    for folder in (sdk / "templates/common", sdk / "templates/c"):
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                files[str(path.relative_to(folder))] = path.read_bytes()
    config = {
        "name": name.lower() + "-example",
        "language": "c",
        "platform": selected_platform,
        "cpu_profile": project.get("cpu_profile", "auto"),
        "generate_drivers": True,
        "generate_driver_examples": False,
        "source": "src/main.c",
        "include_dirs": ["include"],
        "simulation_timeout_cycles": project.get(
            "simulation_timeout_cycles", 2_000_000
        ),
    }
    files["rv32.toml"] = (
        "[project]\n"
        + "\n".join(
            f"{key} = {json.dumps(value)}" for key, value in config.items()
        )
        + "\n"
    ).encode()
    files["src/main.c"] = source.encode()
    files["README.md"] = (
        f"# {name} C driver example\n\n"
        f"Instance: `{instance['name']}`; platform: `{config['platform']}`; "
        f"CPU: `{config['cpu_profile']}`.\n\n"
        "Open this directory in VS Code, reopen in its Dev Container, then run "
        "RV32: Prepare Project and RV32: Simulate. FPGA actions require a physical "
        "platform; modular is simulation-only. The host must have the SDK registered.\n\n"
        "This managed example has its own TOML, editor tasks and container. "
        "Copy the complete folder elsewhere before customizing it. Parent driver "
        "refresh refuses to overwrite edited managed files. Child projects disable "
        "example generation to prevent recursive project trees.\n\n"
        "Constructor arguments reflect platform/generic defaults; review them if "
        "you customize the instantiated RTL. FLASH only reads status. GPIO drives "
        "pin 0 high/low and returns it to input; TIMER runs a bounded one-shot; "
        "DISPLAY restores its previous value; UART transmission has a poll limit.\n"
    ).encode()
    return {f"{name}/example/{key}": value for key, value in files.items()}
