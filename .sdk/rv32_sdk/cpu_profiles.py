"""Apply named Core profiles to private SDK builds, never to tracked RTL."""

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

import yaml
from riscv_tools.memory_map.config_pkg import render_variant
from riscv_tools.memory_map.core import load_platform
from riscv_tools.memory_map.profile import SWITCHES


def selected(sdk: Path, project: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve only canonical named profiles; absence preserves the legacy flow."""
    name = project.get("cpu_profile", "auto")
    if name == "auto":
        return None
    if not isinstance(name, str) or not re.fullmatch(r"rv32i[a-z0-9_]*", name):
        raise SystemExit(
            "project.cpu_profile must be auto or a named Core RV32I profile"
        )
    path = sdk / "Core/profiles" / (name + ".yaml")
    if not path.is_file():
        raise SystemExit(
            f"Unknown CPU profile: {name}; see Core/profiles/*.yaml"
        )
    spec = yaml.safe_load(path.read_text())
    if spec.get("profile") != name or "I" not in spec.get("extensions", []):
        raise SystemExit(f"Unsupported Core profile specification: {path}")
    defaults = dict(
        re.findall(
            r"constant (HAS_\w+|IS_BASE_E|IS_64)\s*:\s*boolean\s*:=\s*(true|false)",
            (sdk / "Common-Components/src/config_pkg.vhd").read_text(),
        )
    )
    names = {key.upper() for key in SWITCHES} | {"IS_BASE_E", "IS_64"}
    flags = {
        key: value == "true" for key, value in defaults.items() if key in names
    }
    flags.update(spec.get("config", {}))
    extensions = {str(e).lower() for e in spec["extensions"]}
    march = "rv32i" + ("m" if "m" in extensions else "")
    march += "".join(
        "_" + e for e in sorted(extensions - {"i", "m", "zicclsm"})
    )
    return {
        "name": name,
        "flags": flags,
        "generics": spec.get("generics", {}),
        "extensions": sorted(extensions),
        "march": march,
        "rust_target": "riscv32im-unknown-none-elf"
        if "m" in extensions
        else "riscv32i-unknown-none-elf",
    }


def write_if_changed(path: Path, text: str) -> None:
    """Keep runtime object timestamps stable between unchanged builds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def apply(
    sdk: Path,
    root: Path,
    platform: Path,
    cfg: dict[str, Any],
    spec: dict[str, Any],
) -> None:
    """Replace just CPU constants and HPM generics in an isolated build."""
    if platform.name != "internal-mem":
        raise SystemExit(
            "Explicit CPU profiles currently require project.platform = internal-mem"
        )
    state = root / ".rv32/cpu"
    state.mkdir(parents=True, exist_ok=True)
    platform_file = platform / "platform.yaml"
    data = load_platform(platform_file)
    config_text = render_variant(data, platform_file, sdk, spec["flags"])
    config_path = state / "config_pkg.vhd"
    write_if_changed(config_path, config_text)
    cfg["sim"]["vhdl_sources"] = [
        str(config_path) if Path(p).name == "config_pkg.vhd" else p
        for p in cfg["sim"]["vhdl_sources"]
    ]
    parameters = cfg["sim"]["parameters"]
    for key, value in spec["flags"].items():
        if key.startswith("HAS_"):
            parameters[key] = value
    parameters["HAS_E"] = False
    parameters.update(
        {key.upper(): value for key, value in spec["generics"].items()}
    )
    cfg["isa"]["base"] = "i"
    cfg["sdk_cpu_profile"] = spec
    cfg["sdk_hardware_inputs"] = {
        "config_pkg": hashlib.sha256(config_text.encode()).hexdigest()
    }
    # Clone the hardware project once per project/profile. External source and IP
    # assignments keep their original absolute paths; tracked files stay intact.
    original = Path(cfg["quartus"]["project_dir"])
    target = state / "quartus"
    target.mkdir(exist_ok=True)
    for path in original.iterdir():
        if path.is_file() and path.suffix in {".qpf", ".sdc", ".qdf"}:
            shutil.copyfile(path, target / path.name)
    qsf = original / (cfg["quartus"]["project_name"] + ".qsf")
    if not qsf.is_file():
        raise SystemExit(f"Missing Quartus project: {qsf}")
    pattern = re.compile(
        r"(?m)^(set_global_assignment -name (?:\w+_FILE|SEARCH_PATH)) (.+)$"
    )

    def assignment(match):
        value = match[2].strip().strip('"')
        source = (original / value).resolve()
        if source.name == "config_pkg.vhd":
            source = config_path
        elif source.name == "core_fpga_test.vhd":
            text = source.read_text()
            for key, number in spec["generics"].items():
                text, count = re.subn(
                    rf"(?im)^(\s*{key}\s*:[^;\n]*?:=\s*)\d+",
                    rf"\g<1>{int(number)}",
                    text,
                )
                if count != 1:
                    raise SystemExit(f"Hardware top does not support {key}")
            source = state / "core_fpga_test.vhd"
            write_if_changed(source, text)
            cfg["sdk_hardware_inputs"]["top"] = hashlib.sha256(
                text.encode()
            ).hexdigest()
        # QSF requires double-quoted paths; its reader retains literal braces.
        if any(c in str(source) for c in "{}\n"):
            raise SystemExit(
                "SDK/project paths contain unsupported Tcl metacharacters"
            )
        return match[1] + ' "' + str(source) + '"'

    text = pattern.sub(assignment, qsf.read_text()).replace(
        "NUM_PARALLEL_PROCESSORS ALL", "NUM_PARALLEL_PROCESSORS 2"
    )
    write_if_changed(target / qsf.name, text)
    cfg["quartus"]["project_dir"] = str(target)


def prepare_source(text: str, spec: dict[str, Any]) -> str:
    """Make TOML authoritative, rejecting source requests absent from hardware."""
    pattern = r"(?m)^\s*//\s*RV32_EXT:\s*(.*?)$"
    for match in re.finditer(pattern, text):
        requested = {
            s.strip().lower() for s in match[1].split(",") if s.strip()
        }
        if requested - set(spec["extensions"]):
            raise SystemExit(
                "RV32_EXT requests extensions outside project.cpu_profile"
            )
    text = re.sub(pattern, "", text)
    extensions = [e for e in spec["extensions"] if e not in {"i", "zicclsm"}]
    return (
        ("// RV32_EXT: " + ",".join(extensions) + "\n") if extensions else ""
    ) + text


def hardware_stamp(cable: str, key: str) -> tuple[str, str]:
    """Name a shared per-cable programming record for explicit profile updates."""
    return hashlib.sha256(cable.encode()).hexdigest(), key
