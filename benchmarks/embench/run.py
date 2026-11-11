"""Compile and execute unmodified Embench kernels on the modular RTL."""

import argparse
import hashlib
import json
import os
import re
import resource
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

from benchmarks.embench.provenance import cache_key, capture, metadata
from benchmarks.embench.records import checksum, intact

HERE = Path(__file__).resolve().parent
GCC = "riscv32-unknown-elf-"
SCHEMA = 1
NM_FIELDS = 3
BUCKETS = ("branching", "memory", "compute", "other")


def command(args: list[str], cwd: Path, log: Path, timeout: int = 900) -> str:
    """Run an argument vector, saving combined output for diagnosis."""
    with log.open("a+", encoding="utf-8") as stream:
        stream.write("\n$ " + " ".join(args) + "\n")
        stream.flush()
        position = stream.tell()
        with subprocess.Popen(  # noqa: S603
            args,
            cwd=cwd,
            stdout=stream,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        ) as process:
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired, KeyboardInterrupt:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                stream.write(
                    f"\nTerminated command group after {timeout}s limit\n"
                )
                raise
        stream.seek(position)
        output = stream.read()
    if returncode:
        raise RuntimeError(f"Command failed ({returncode}): {log}")
    return output


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a repository-owned YAML mapping."""
    return cast("dict[str, Any]", yaml.safe_load(path.read_text()))


def digest(path: Path) -> str:
    """Hash the complete bytes of an input or executable."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    """Write a stable machine-readable artifact."""
    if isinstance(value, dict) and "results" in value:
        document = cast("dict[str, Any]", value)
        document["record_sha256"] = checksum(document)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


@dataclass
class Experiment:
    """Paths and immutable suite settings for one execution."""

    root: Path
    upstream: Path
    output: Path
    suite: dict[str, Any]
    provenance: dict[str, Any]

    def tool(self, arguments: list[str], log: Path) -> str:
        """Invoke the infrastructure CLI from the target checkout."""
        return command(
            ["riscv-tools", "--root", str(self.root), *arguments],
            self.root,
            log,
        )

    @property
    def platform(self) -> Path:
        """Locate the existing modular platform."""
        return self.root / str(self.suite["platform"])


def profile_settings(root: Path, profile: str) -> dict[str, Any]:
    """Read profile switches, preserving Core defaults."""
    path = root / "Core/profiles" / f"{profile}.yaml"
    if not re.fullmatch(r"rv32[ie][a-z0-9_]*", profile):
        raise ValueError("Invalid profile name")
    if not path.is_file():
        return expanded_settings(root, profile)
    profile_data = read_yaml(path)
    if profile_data["profile"] != profile:
        raise ValueError(f"Profile name mismatch: {path}")
    return profile_data


def expanded_settings(root: Path, profile: str) -> dict[str, Any]:
    """Resolve a generated profile from the Core matrix."""
    expanded = json.loads(
        capture(
            [
                "riscv-tools",
                "profiles",
                "--spec",
                str(root / "Core/profiles/matrix.yaml"),
                "--format",
                "json",
            ],
            root,
        )
    )
    selected = next((p for p in expanded if p["name"] == profile), None)
    if selected is None:
        raise ValueError(f"Unknown CPU profile: {profile}")
    switches = {"IS_BASE_E": selected["generics"]["has_e"]}
    switches.update(
        {k.upper(): v for k, v in selected["generics"].items() if k != "has_e"}
    )
    base = "E" if switches["IS_BASE_E"] else "I"
    return {
        "profile": profile,
        "extensions": [base, *selected["extensions"]],
        "config": switches,
        "generics": {},
    }


def compiler_isa(settings: dict[str, Any]) -> str:
    """Select the compiler ISA from enabled extensions."""
    extensions = {str(e).lower() for e in settings["extensions"]}
    base = "rv32e" if "e" in extensions else "rv32i"
    if "m" in extensions:
        base += "m"
    # Zicclsm changes memory semantics, not the compiler ISA.
    supported = (
        "zmmul",
        "zicsr",
        "zicntr",
        "zihpm",
        "zifencei",
        "zicond",
        "zimop",
    )
    return base + "".join("_" + e for e in supported if e in extensions)


def build_config(
    exp: Experiment, folder: Path, settings: dict[str, Any]
) -> Path:
    """Combine platform memory constants with the exact Core profile."""
    log = folder / "build.log"
    base = folder / "platform_config.vhd"
    exp.tool(
        [
            "generate-config-pkg",
            "--platform",
            str(exp.platform / "platform.yaml"),
            "--output",
            str(base),
        ],
        log,
    )
    # Follow Core/formal/build_profile.sh defaults and overrides.
    defaults = (exp.root / "Core/src/common/src/config_pkg.vhd").read_text()
    switches = dict(
        re.findall(
            r"constant (HAS_\w+|IS_BASE_E|IS_64)\s*:\s*boolean"
            r"\s*:=\s*(true|false)",
            defaults,
        )
    )
    switches.update(
        {str(k): str(v).lower() for k, v in settings["config"].items()}
    )
    target = folder / "config_pkg.vhd"
    overrides = " ".join(f"{key}={value}" for key, value in switches.items())
    command(
        [
            "env",
            "CONFIG_BASE=" + str(base),
            "bash",
            str(exp.root / "Core/formal/config_variant.sh"),
            "--set",
            overrides,
            str(target),
        ],
        exp.root,
        log,
    )
    return target


def instrument_sources(exp: Experiment, folder: Path) -> list[str]:
    """Prepare instrumented copies in the build directory."""
    sources = read_yaml(exp.platform / "config.yaml")["sim"]["vhdl_sources"]
    original = exp.root / "Core/src/core/core.vhd"
    text = original.read_text()
    ending = "end architecture rtl;"
    if text.count(ending) != 1:
        raise ValueError("Core observer insertion point changed")
    observed = folder / "core_observed.vhd"
    observed.write_text(
        text.replace(
            ending, (HERE / "monitor.vhd.in").read_text() + "\n" + ending
        )
    )
    files = [str(exp.root / p) for p in sources]
    files[files.index(str(original))] = str(observed)
    for kind in ("RAM", "ROM"):
        path = (
            exp.root / f"Memory/src/{kind}/SoC/{kind.lower()}_simulation.vhd"
        )
        entity = path.read_text().split("architecture rtl of ", 1)[0]
        fast = folder / f"{kind.lower()}_storage.vhd"
        fast.write_text(entity + (HERE / f"{kind.lower()}.vhd.in").read_text())
        files[files.index(str(path))] = str(fast)

    return files


def build_simulator(
    exp: Experiment, profile: str
) -> tuple[Path, dict[str, Any]]:
    """Elaborate one profile with a retirement observer."""
    folder = exp.output / profile
    folder.mkdir(parents=True, exist_ok=True)
    settings = profile_settings(exp.root, profile)
    config = build_config(exp, folder, settings)
    files = instrument_sources(exp, folder)
    files[files.index(str(exp.platform / "config_pkg.vhd"))] = str(config)
    platform_data = read_yaml(exp.platform / "platform.yaml")
    tohost = int(platform_data["reserved"]["tohost"]["base"])
    top = folder / "embench_top.vhd"
    top.write_text(
        (HERE / "top.vhd.in").read_text().replace("@TOHOST@", str(tohost))
    )
    log = folder / "build.log"
    command(["ghdl", "-a", "--std=08", "-O2", *files, str(top)], folder, log)
    command(["ghdl", "-e", "--std=08", "embench_top"], folder, log)
    return folder, settings


def build_boot(exp: Experiment) -> Path:
    """Build the platform's unchanged restart loader once."""
    elf = exp.output / "boot.elf"
    command(
        [
            GCC + "gcc",
            "-march=rv32i",
            "-mabi=ilp32",
            "-nostdlib",
            "-T",
            str(exp.platform / "runtime/boot_memory.ld"),
            str(exp.platform / "runtime/boot_memory.S"),
            "-o",
            str(elf),
        ],
        exp.root,
        exp.output / "build.log",
    )
    return hex_image(elf, exp.output / "boot.hex", exp.output / "build.log")


def hex_image(elf: Path, target: Path, log: Path, origin: int = 0) -> Path:
    """Convert an ELF into the platform word image."""
    binary = target.with_suffix(".bin")
    command(
        [GCC + "objcopy", "-O", "binary", str(elf), str(binary)],
        target.parent,
        log,
    )
    data = bytes(origin) + binary.read_bytes()
    data += b"\0" * (-len(data) % 4)
    target.write_text(
        "".join(
            f"{int.from_bytes(data[slice(i, i + 4)], 'little'):08X}\n"
            for i in range(0, len(data), 4)
        )
    )
    return target


def compile_arguments(exp: Experiment, settings: dict[str, Any]) -> list[str]:
    """Use the profile's ISA and ABI with fixed optimization flags."""
    abi = "ilp32e" if "E" in settings["extensions"] else "ilp32"
    return [
        GCC + "gcc",
        "-march=" + compiler_isa(settings),
        "-mabi=" + abi,
        *exp.suite["cflags"],
    ]


def build_runtime(
    exp: Experiment, folder: Path, settings: dict[str, Any]
) -> Path:
    """Compile the platform runtime separately as C23."""
    target = folder / "runtime.o"
    command(
        [
            *compile_arguments(exp, settings),
            "-std=gnu23",
            "-c",
            str(exp.platform / "runtime/_exit.c"),
            "-o",
            str(target),
        ],
        exp.root,
        folder / "build.log",
    )
    return target


def build_program(
    exp: Experiment, program: str, options: dict[str, Any]
) -> Path:
    """Link original benchmark sources and local board triggers."""
    folder = Path(options["folder"])
    elf = folder / f"{program}.elf"
    sources = sorted((exp.upstream / "src" / program).glob("*.c"))
    if not sources:
        raise ValueError(f"No sources for {program}")
    scale = 1
    prepared: list[Path] = []
    for source in sources:
        text = source.read_text()
        match = re.search(r"^#define LOCAL_SCALE_FACTOR (\d+)$", text, re.M)
        if match:
            scale = int(match[1])
            if exp.suite["workload"] == "ci":
                text = (
                    text[slice(None, match.start())]
                    + "#define LOCAL_SCALE_FACTOR 1"
                    + text[slice(match.end(), None)]
                )
        target = folder / f"{program}-{source.name}"
        target.write_text(text)
        prepared.append(target)
    write_json(
        folder / f"{program}-scale.json",
        {
            "original": scale,
            "executed": 1 if exp.suite["workload"] == "ci" else scale,
        },
    )
    support = exp.upstream / "support"
    runtime = exp.platform / "runtime"
    arguments = [
        *compile_arguments(exp, options["settings"]),
        "-std=" + str(exp.suite["c_standard"]),
        "-DCPU_MHZ=1",
        "-DGLOBAL_SCALE_FACTOR=1",
        "-DWARMUP_HEAT=" + str(exp.suite["warmup"]),
        "-I",
        str(support),
        "-I",
        str(exp.upstream / "src" / program),
        "--specs=" + str(runtime / "rv32im-fpga.specs"),
        "-Wl,--gc-sections",
        *map(str, prepared),
        str(support / "main.c"),
        str(support / "beebsc.c"),
        str(HERE / "board.c"),
        str(options["runtime"]),
        "-lm",
        "-o",
        str(elf),
    ]
    command(arguments, exp.root, folder / "build.log")
    return elf


def measure(
    exp: Experiment, elf: Path, options: dict[str, Any]
) -> dict[str, Any]:
    """Collect metrics after a verified program exit."""
    folder = elf.parent
    log = folder / f"{elf.stem}.log"
    symbols = command([GCC + "nm", str(elf)], folder, log)
    addresses = {
        line.split()[2]: int(line.split()[0], 16)
        for line in symbols.splitlines()
        if len(line.split()) == NM_FIELDS
    }
    (folder / "markers.txt").write_text(
        f"{addresses['start_trigger']}\n{addresses['stop_trigger']}\n"
    )
    for name in ("metrics.txt", "verdict.txt"):
        (folder / name).unlink(missing_ok=True)
    image_origin = next(
        int(region["base"])
        for region in read_yaml(exp.platform / "platform.yaml")["regions"]
        if region["name"] == "ROM"
    )
    image = hex_image(elf, elf.with_suffix(".hex"), log, image_origin)
    arguments = [
        "ghdl",
        "-r",
        "--std=08",
        "embench_top",
        "-grom_file=" + str(image),
        "-gboot_file=" + str(options["boot"]),
        "-gmax_cycles=" + str(exp.suite["max_cycles"]),
    ]
    for key, value in options["settings"]["generics"].items():
        arguments.append(f"-g{key}={value}")
    started = time.monotonic()
    command(
        arguments,
        folder,
        log,
        int(exp.suite["wall_timeout_seconds"]),
    )
    return collect_metrics(exp, elf, time.monotonic() - started)


def collect_metrics(
    exp: Experiment, elf: Path, elapsed: float
) -> dict[str, Any]:
    """Accept metrics only after the benchmark's verified exit."""
    folder = elf.parent
    if (folder / "verdict.txt").read_text().strip() != "PASS":
        raise ValueError(
            f"Missing original benchmark verification: {elf.stem}"
        )
    counts = list(map(int, (folder / "metrics.txt").read_text().split()))
    cycles, retired, *mix = counts
    if len(mix) != len(BUCKETS) or sum(mix) != retired or min(counts) < 0:
        raise ValueError("Invalid instruction accounting")
    if cycles <= 0 or retired <= 0:
        raise ValueError("Empty measurement")
    reference = json.loads(
        (exp.upstream / "baseline-data/speed.json").read_text()
    )
    scaling = json.loads((folder / f"{elf.stem}-scale.json").read_text())
    normalization = scaling["original"] / scaling["executed"]
    return {
        "scale": scaling,
        "score_kind": "CI estimate" if normalization != 1 else "Embench",
        "program": elf.stem,
        "status": "pass",
        "cycles": cycles,
        "instructions": retired,
        "cpi": cycles / retired,
        "operations": dict(zip(BUCKETS, mix, strict=True)),
        "mix_percent": {
            k: 100 * v / retired for k, v in zip(BUCKETS, mix, strict=True)
        },
        "score_per_mhz": float(reference[elf.stem])
        * 1000
        / (cycles * normalization),
        "elf_sha256": digest(elf),
        "wall_seconds": elapsed,
    }


def execute(
    exp: Experiment, profile: str, programs: list[str]
) -> dict[str, Any]:
    """Keep a row and diagnostics for every attempted program."""
    folder, settings = build_simulator(exp, profile)
    boot = build_boot(exp)
    runtime = build_runtime(exp, folder, settings)
    rows: list[dict[str, Any]] = []
    for program in programs:
        print(f"{profile}: {program}", flush=True)
        try:
            options = {
                "folder": folder,
                "settings": settings,
                "boot": boot,
                "runtime": runtime,
            }
            elf = build_program(exp, program, options)
            row = measure(exp, elf, options)
        except (
            RuntimeError,
            ValueError,
            OSError,
            subprocess.TimeoutExpired,
        ) as error:
            row = {"program": program, "status": "failed", "error": str(error)}
        rows.append(row)
        write_json(
            exp.output / "results.json",
            {
                "schema": SCHEMA,
                "profile": profile,
                "settings": settings,
                "provenance": exp.provenance,
                "suite": exp.suite,
                "results": rows,
            },
        )
    return {
        "schema": SCHEMA,
        "profile": profile,
        "settings": settings,
        "provenance": exp.provenance,
        "suite": exp.suite,
        "results": rows,
    }


def reusable(
    path: Path, exp: Experiment, profile: str, programs: list[str]
) -> dict[str, Any] | None:
    """Reuse only intact, complete records of identical inputs."""
    try:
        saved: dict[str, Any] = json.loads(path.read_text())
        valid = (
            intact(saved)
            and saved.get("profile") == profile
            and saved.get("schema") == SCHEMA
            and (
                cache_key(saved["provenance"], profile)
                == cache_key(exp.provenance, profile)
            )
        )
        rows = saved.get("results", [])
        if (
            valid
            and {r["program"] for r in rows} == set(programs)
            and all(r["status"] == "pass" for r in rows)
        ):
            return saved
    except ValueError, TypeError, KeyError, OSError:
        return None
    return None


def path_parser(description: str | None) -> argparse.ArgumentParser:
    """Build the shared source, upstream and output path arguments."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def validate_upstream(exp: Experiment) -> None:
    """Require a clean checkout of the exact pinned Embench sources."""
    revision = command(
        ["git", "rev-parse", "HEAD"], exp.upstream, exp.output / "build.log"
    ).strip()
    if revision != exp.suite["commit"]:
        raise ValueError("Embench source must match the pinned commit")
    dirty = capture(
        ["git", "status", "--porcelain", "--untracked-files=all"], exp.upstream
    )
    if dirty:
        raise ValueError("Embench checkout must be clean")


def main() -> None:
    """Run a profile without changing tracked CPU files."""
    parser = path_parser(__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--program", action="append")
    parser.add_argument("--reuse", action="store_true")
    parser.add_argument("--workload", choices=("ci", "full"), default="ci")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    exp = Experiment(
        args.root.resolve(),
        args.upstream.resolve(),
        args.output,
        read_yaml(HERE / "suite.yaml"),
        metadata(args.root.resolve()),
    )
    exp.suite["workload"] = args.workload
    exp.provenance["contract"]["workload"] = args.workload
    try:
        validate_upstream(exp)
    except ValueError as error:
        parser.error(str(error))
    programs = args.program or exp.suite["programs"]
    if set(programs) - set(exp.suite["programs"]):
        parser.error("Unknown Embench program")
    previous = exp.output / "results.json"
    saved = (
        reusable(previous, exp, args.profile, programs) if args.reuse else None
    )
    if saved is not None:
        saved["provenance"] = exp.provenance
        saved["reused"] = True
        write_json(previous, saved)
        print("Reusing identical verified benchmark inputs", flush=True)
        return
    # GHDL's large memory models need more than the Linux 8 MiB default.
    # This is stack space, not an increase to the container RAM limit.
    _, hard = resource.getrlimit(resource.RLIMIT_STACK)
    resource.setrlimit(resource.RLIMIT_STACK, (64 * 1024 * 1024, hard))
    result: dict[str, Any]
    try:
        result = execute(exp, args.profile, programs)
    except (
        RuntimeError,
        ValueError,
        OSError,
        subprocess.TimeoutExpired,
    ) as error:
        result = {
            "schema": SCHEMA,
            "profile": args.profile,
            "provenance": exp.provenance,
            "suite": exp.suite,
            "results": [
                {"program": p, "status": "failed", "error": str(error)}
                for p in programs
            ],
        }
        write_json(previous, result)
    if any(row["status"] != "pass" for row in result["results"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
