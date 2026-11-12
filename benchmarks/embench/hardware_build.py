"""Build an isolated DE0-CV observer for an exact Core profile."""

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

from riscv_tools.bin_to_image.core import bin_to_mif, mif_text
from riscv_tools.boot_memory import build_boot_memory
from riscv_tools.flash_image import pack
from riscv_tools.settings import load_config

from benchmarks.embench import run
from benchmarks.embench.provenance import capture, hash_files, metadata

PLATFORM = Path("src/cyclone-v/de0-cv")
PROJECT = "de0_cv_de0_cv"


def identity(root: Path) -> dict[str, Any]:
    """Fingerprint the independent hardware measurement driver."""
    document = metadata(root)
    names = [
        "hardware_build.py",
        "hardware_container.py",
        "hardware_measure.py",
        "hardware_monitor.vhd.in",
        "hardware_scan.tcl",
        "retirement_counter.vhd.in",
        "counter.S",
    ]
    document["contract"]["hardware_adapter_sha256"] = hash_files(
        run.HERE, [run.HERE / name for name in names]
    )
    return document


def observed_core(root: Path, folder: Path) -> Path:
    """Append an observer to a build-directory source copy."""
    original = (root / "Core/src/core/core.vhd").read_text()
    ending = "end architecture rtl;"
    if original.count(ending) != 1:
        raise ValueError("Core observer insertion point changed")
    target = folder / "core_observed.vhd"
    target.write_text(
        original.replace(
            ending,
            (run.HERE / "hardware_monitor.vhd.in").read_text() + ending,
        )
    )
    return target


def prepare_board(exp: run.Experiment, settings: dict[str, Any]) -> Path:
    """Generate board sources, boot image and profile configuration."""
    folder = exp.output / "board/de0-cv-de0-cv"
    exp.tool(
        [
            "--board",
            "de0-cv",
            "board",
            "generate",
            "--platform",
            str(PLATFORM / "platform.yaml"),
            "--boards-dir",
            str(exp.root / "boards"),
            "--out",
            str(exp.output / "board"),
        ],
        exp.output / "build.log",
    )
    config = run.build_config(exp, folder, settings)
    text = restore_platform(config)
    for key, value in settings["generics"].items():
        pattern = rf"(constant {key.upper()}\s*:[^;]*?:=\s*)\d+"
        text, count = re.subn(pattern, rf"\g<1>{int(value)}", text)
        if count != 1:
            raise ValueError(f"Missing generated profile generic: {key}")
    config.write_text(text)
    patch_project(exp, folder, config)
    prepare_boot(exp, folder, settings)
    for name in ("flash_init.mif", "init.mif"):
        (folder / name).write_text(
            mif_text(65536, ["[0000..FFFF] : 00000000;"])
        )
    return folder


def patch_project(exp: run.Experiment, folder: Path, config: Path) -> None:
    """Substitute build sources in the generated Quartus project."""
    observed = observed_core(exp.root, folder)
    observer = folder / "retirement_counter.vhd"
    shutil.copyfile(run.HERE / (observer.name + ".in"), observer)
    qsf = folder / f"{PROJECT}.qsf"
    text = qsf.read_text().replace(
        "NUM_PARALLEL_PROCESSORS ALL", "NUM_PARALLEL_PROCESSORS 2"
    )
    for source, target in (
        (exp.root / PLATFORM / "config_pkg.vhd", config),
        (exp.root / "Core/src/core/core.vhd", observed),
    ):
        relative = str(source.relative_to(exp.root))
        pattern = (
            r"(?m)^set_global_assignment -name VHDL_FILE .*"
            + re.escape(relative)
            + "$"
        )
        text, count = re.subn(
            pattern, f"set_global_assignment -name VHDL_FILE {target}", text
        )
        if count != 1:
            raise ValueError(f"Missing generated Quartus source: {relative}")
    text += f"\nset_global_assignment -name VHDL_FILE {observer}\n"
    qsf.write_text(text)


def prepare_boot(
    exp: run.Experiment, folder: Path, settings: dict[str, Any]
) -> None:
    """Omit unsupported FENCE.I after a full SoC/cache reset."""
    cfg = load_config(exp.root / PLATFORM / "config.yaml")
    runtime = folder / "boot-runtime"
    shutil.copytree(exp.platform / "runtime", runtime)
    source = runtime / "boot_memory.S"
    if "Zifencei" not in settings["extensions"]:
        text = source.read_text()
        instruction = ".word 0x0000100F"
        if text.count(instruction) != 1:
            raise ValueError("Boot FENCE.I insertion point changed")
        source.write_text(text.replace(instruction, ".word 0x00000013"))
    cfg["paths"]["boot_memory"] = str(source)
    boot = build_boot_memory(cfg["toolchain"], cfg["paths"], exp.root, folder)
    bin_to_mif(boot.with_suffix(".bin"), folder / "boot_memory_init.mif", 1024)


def restore_platform(config: Path) -> str:
    """Preserve hardware memory and peripherals with Core defaults."""
    text = config.read_text()
    pattern = r"constant (HAS_\w+)\s*:\s*boolean\s*:=\s*(true|false)"
    platform = (config.parent / "platform_config.vhd").read_text()
    isa = {"HAS_M", "HAS_INTERRUPTS", "HAS_SSCOFPMF", "HAS_ACCESS_FAULTS"}
    for key, value in re.findall(pattern, platform):
        if key.startswith("HAS_Z") or key in isa:
            continue
        text = re.sub(
            rf"(constant {key}\s*:\s*boolean\s*:=\s*)(true|false)",
            rf"\g<1>{value}",
            text,
        )
    return text


def firmware(exp: run.Experiment, settings: dict[str, Any]) -> dict[str, Any]:
    """Build workloads with the same CSR-free marker port as RTL."""
    folder = exp.output / "firmware"
    folder.mkdir()
    runtime = folder / "runtime"
    shutil.copytree(exp.platform / "runtime", runtime)
    shutil.copyfile(
        runtime / "rv32im-fpga-bank-a.specs", runtime / "rv32im-fpga.specs"
    )
    suite = dict(exp.suite, platform=str(folder))
    fw = run.Experiment(
        exp.root, exp.upstream, exp.output, suite, exp.provenance
    )
    obj = run.build_runtime(fw, folder, settings)
    options = {"folder": folder, "settings": settings, "runtime": obj}
    names = exp.suite["programs"]
    for code in (0, 1):
        build_counter(exp, settings, obj, code)
    records: dict[str, Any] = {}
    for name in ["_counter", "_counter_fail", *names]:
        elf = (
            folder / (name + ".elf")
            if name.startswith("_counter")
            else run.build_program(fw, name, options)
        )
        records[name] = image_record(elf)
        if not name.startswith("_counter"):
            records[name]["scale"] = json.loads(
                (folder / f"{name}-scale.json").read_text()
            )
            reference = json.loads(
                (exp.upstream / "baseline-data/speed.json").read_text()
            )
            records[name]["reference_ms"] = reference[name]
    return records


def build_counter(
    exp: run.Experiment,
    settings: dict[str, Any],
    obj: Path,
    code: int,
) -> None:
    """Build identical count oracles with passing and failing exits."""
    folder = obj.parent
    runtime = folder / "runtime"
    name = "_counter" if code == 0 else "_counter_fail"
    counter = folder / (name + ".elf")
    run.command(
        [
            *run.compile_arguments(exp, settings),
            "-DTEST_RAM_BASE=0x40000000",
            f"-DRETURN_CODE={code}",
            "-I",
            str(exp.upstream / "support"),
            "--specs=" + str(runtime / "rv32im-fpga.specs"),
            str(run.HERE / "counter.S"),
            str(run.HERE / "board.c"),
            str(obj),
            "-o",
            str(counter),
        ],
        folder,
        folder / "build.log",
    )


def image_record(elf: Path) -> dict[str, Any]:
    """Pack firmware and identify retirement marker addresses."""
    folder = elf.parent
    binary = elf.with_suffix(".bin")
    run.command(
        [run.GCC + "objcopy", "-O", "binary", str(elf), str(binary)],
        folder,
        folder / "build.log",
    )
    image = elf.with_suffix(".image.bin")
    image.write_bytes(pack(binary.read_bytes(), 1, 124 * 1024))
    symbols = run.command(
        [run.GCC + "nm", str(elf)], folder, folder / "build.log"
    )
    markers = {
        words[2]: int(words[0], 16)
        for line in symbols.splitlines()
        if len(words := line.split()) == run.NM_FIELDS
        and words[2] in {"start_trigger", "stop_trigger"}
    }
    return {
        "elf_sha256": run.digest(elf),
        "image_sha256": run.digest(image),
        "markers": markers,
    }


def build(args: argparse.Namespace) -> None:
    """Compile one isolated profile without programming a board."""
    args.output.mkdir(parents=True, exist_ok=False)
    suite = run.read_yaml(run.HERE / "suite.yaml")
    if capture(["git", "rev-parse", "HEAD"], args.upstream) != suite["commit"]:
        raise ValueError("Upstream Embench revision mismatch")
    if capture(["git", "status", "--porcelain"], args.upstream):
        raise ValueError("Upstream Embench checkout is dirty")
    suite.update(platform=str(PLATFORM), workload=args.workload)
    if args.programs:
        names = json.loads(args.programs)
        if not names or not set(names) <= set(suite["programs"]):
            raise ValueError("Unknown hardware benchmark program")
        suite["programs"] = names
    provenance = identity(args.root)
    exp = run.Experiment(
        args.root, args.upstream, args.output, suite, provenance
    )
    settings = run.profile_settings(args.root, args.profile)
    if "E" in settings["extensions"]:
        raise ValueError("DE0-CV firmware currently requires the ilp32 ABI")
    folder = prepare_board(exp, settings)
    records = firmware(exp, settings)
    run.command(
        ["quartus_sh", "--flow", "compile", PROJECT],
        folder,
        args.output / "quartus.log",
        timeout=1800,
    )
    platform = run.read_yaml(exp.platform / "platform.yaml")
    document = {
        "schema": 1,
        "backend": "fpga",
        "profile": args.profile,
        "settings": settings,
        "suite": suite,
        "provenance": provenance,
        "configured_mhz": platform["clocks"]["core"]["mhz"],
        "quartus": capture(["quartus_sh", "--version"], args.root),
        "sof_sha256": run.digest(folder / "output_files" / f"{PROJECT}.sof"),
        "firmware": records,
    }
    run.write_json(args.output / "hardware-manifest.json", document)


def main() -> None:
    """Parse explicit paths for the offline builder container."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--programs")
    parser.add_argument("--workload", choices=("ci", "full"), default="ci")
    build(parser.parse_args())


if __name__ == "__main__":
    main()
