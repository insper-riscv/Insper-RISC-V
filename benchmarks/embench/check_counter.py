"""Check the RTL observer against eight known instructions."""

import json
import resource
from pathlib import Path

from benchmarks.embench.provenance import metadata
from benchmarks.embench.run import (
    GCC,
    HERE,
    NM_FIELDS,
    Experiment,
    build_boot,
    build_simulator,
    command,
    hex_image,
    path_parser,
    read_yaml,
)


def run_kernel(exp: Experiment, folder: Path, boot: Path, code: int) -> None:
    """Run eight instructions, then check the original exit protocol."""
    platform = read_yaml(exp.platform / "platform.yaml")
    regions = {r["name"]: r for r in platform["regions"]}
    elf = folder / "counter.elf"
    runtime = exp.platform / "runtime"
    log = folder / f"counter-{code}.log"
    command(
        [
            GCC + "gcc",
            "-march=rv32im",
            "-mabi=ilp32",
            "-std=gnu23",
            "--specs=" + str(runtime / "rv32im-fpga.specs"),
            "-I",
            str(exp.upstream / "support"),
            "-DTEST_RAM_BASE=" + str(regions["RAM"]["base"]),
            "-DRETURN_CODE=" + str(code),
            str(HERE / "counter.S"),
            str(HERE / "board.c"),
            str(runtime / "_exit.c"),
            "-o",
            str(elf),
        ],
        exp.root,
        log,
    )
    symbols = command([GCC + "nm", str(elf)], folder, log)
    addresses = {
        line.split()[2]: int(line.split()[0], 16)
        for line in symbols.splitlines()
        if len(line.split()) == NM_FIELDS
    }
    (folder / "markers.txt").write_text(
        f"{addresses['start_trigger']}\n{addresses['stop_trigger']}\n"
    )
    image = hex_image(
        elf, folder / "counter.hex", log, int(regions["ROM"]["base"])
    )
    command(
        [
            "ghdl",
            "-r",
            "--std=08",
            "embench_top",
            "-grom_file=" + str(image),
            "-gboot_file=" + str(boot),
            "-gmax_cycles=10000",
        ],
        folder,
        log,
    )
    counts = list(map(int, (folder / "metrics.txt").read_text().split()))
    if counts[1:] != [8, 3, 2, 3, 0]:
        raise ValueError(f"Incorrect retire/mix counts: {counts}")


def main() -> None:
    """Require exact counts and rejection of a failing program exit."""
    parser = path_parser(__doc__)
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    _, hard = resource.getrlimit(resource.RLIMIT_STACK)
    resource.setrlimit(resource.RLIMIT_STACK, (64 * 1024 * 1024, hard))
    exp = Experiment(
        args.root.resolve(),
        args.upstream.resolve(),
        args.output,
        read_yaml(HERE / "suite.yaml"),
        metadata(args.root.resolve()),
    )
    folder, _ = build_simulator(exp, "rv32im")
    boot = build_boot(exp)
    run_kernel(exp, folder, boot, 0)
    try:
        run_kernel(exp, folder, boot, 1)
    except RuntimeError:
        failure = (folder / "counter-1.log").read_text()
        if "original verifier failed" not in failure:
            raise
    else:
        raise ValueError("A failing program exit was accepted")
    (args.output / "counter-check.json").write_text(
        json.dumps(
            {
                "status": "pass",
                "instructions": 8,
                "branching": 3,
                "memory": 2,
                "compute": 3,
                "other": 0,
                "failing_exit_rejected": True,
            },
            indent=2,
        )
        + "\n"
    )
    print("RTL counter PASS: 8 instructions, 3 branches, 2 memory, 3 compute")


if __name__ == "__main__":
    main()
