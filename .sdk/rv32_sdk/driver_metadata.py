"""Resolve driver variants and parameters from canonical peripheral entries."""

from pathlib import Path
from typing import Any

from riscv_tools.memory_map.expressions import evaluate

from rv32_sdk.driver_examples import generic


def matches(spec: dict[str, Any], instance: dict[str, Any]) -> bool:
    """Match hardware kind and variant, retaining legacy named instances."""
    kind = instance.get("kind")
    if kind is not None and spec.get("kinds"):
        if kind not in spec["kinds"]:
            return False
        devices = spec.get("devices")
        return not devices or instance.get("device", "keyboard") in devices
    return instance["name"] in spec["instances"]


def fields(
    sdk: Path, spec: dict[str, Any], instance: dict[str, Any]
) -> dict[str, int]:
    """Resolve constructor state without guessing it from address-slot IDs."""
    values = dict(spec.get("platform_fields", {}))
    name = spec["name"]
    source = sdk / "Peripherals/src"
    if name == "ADC":
        chip = instance.get("chip", "adc128s022")
        if chip not in {"adc128s022", "ltc2308", "max10"}:
            raise SystemExit(f"Unsupported ADC backend: {chip}")
        values.update(
            BACKEND=int(chip == "max10"), CHANNELS=18 if chip == "max10" else 8
        )
        required = 104 if chip == "max10" else 44
        if evaluate(instance["size"]) < required:
            raise SystemExit(f"MMIO window too small for {chip}")
    elif name == "SPI":
        values["SELECT_COUNT"] = int(instance.get("cs_count", 1))
        values["WORD_BITS"] = int(
            instance.get(
                "word_width",
                generic(source / "SPI/master/spi.vhd", "word_width"),
            )
        )
    elif name in {"VIDEO", "HDMI"}:
        rtl = (
            "video/soc/video.vhd"
            if name == "VIDEO"
            else "HDMI/soc/hdmi_tx.vhd"
        )
        width = int(
            instance.get("addr_width", generic(source / rtl, "addr_width"))
        )
        if not 11 <= width <= 29:
            raise SystemExit("Framebuffer word-address width must be 11..29")
        values["FRAMEBUFFER_OFFSET"] = 1 << (width + 1)
        values["WINDOW_BYTES"] = min(
            evaluate(instance["size"]), 1 << (width + 2)
        )
        if values["WINDOW_BYTES"] <= values["FRAMEBUFFER_OFFSET"]:
            raise SystemExit("Framebuffer does not fit its mapped window")
    elif name == "ETH":
        rtl = source / "ETH/mac/eth.vhd"
        for direction in ("tx", "rx"):
            key = direction + "_buffer_addr_bits"
            bits = int(instance.get(key, generic(rtl, key)))
            if not 1 <= bits <= 20:
                raise SystemExit("Unsupported Ethernet buffer address width")
            values[direction.upper() + "_WORDS"] = 1 << bits
    for key, value in values.items():
        if type(value) is not int or not 0 <= value <= 0xFFFFFFFF:
            raise SystemExit(f"Invalid driver parameter {name}/{key}")
    return values


def platform_definitions(
    sdk: Path, spec: dict[str, Any], instances: list[dict[str, Any]]
) -> list[str]:
    """Generate complete constructor tables, including all same-kind instances."""
    name = spec["name"]
    bases = ", ".join(
        f"((uintptr_t)RV32_PERIPH_{item['name']}_BASE)" for item in instances
    )
    lines = [
        '#include "../rv32_platform.h"',
        f"#define RV32_{name}_INSTANCE_COUNT {len(instances)}",
        f"#define RV32_{name}_BASES {{{bases}}}",
    ]
    configured = [fields(sdk, spec, item) for item in instances]
    for index, item in enumerate(instances):
        lines.append(f"#define RV32_{name}_{item['name']}_INSTANCE {index}")
    for key in spec.get("platform_fields", {}):
        values = ", ".join(str(item[key]) for item in configured)
        lines.append(f"#define RV32_{name}_{key} {{{values}}}")
    if name == "USB":
        lines.extend(
            [
                f"#define RV32_USB_DEFAULT_BASE ((uintptr_t)RV32_PERIPH_{instances[0]['name']}_BASE)",
                f"#define RV32_USB_DEFAULT_POLL_BUDGET {configured[0]['POLL_BUDGET']}",
            ]
        )
    return lines
