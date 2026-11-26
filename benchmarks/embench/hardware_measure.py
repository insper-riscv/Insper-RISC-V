"""Measure verified firmware with the retirement observer."""

import argparse
import json
import re
import statistics
import time
from pathlib import Path
from typing import Any

from riscv_tools import flash_loader, htif, ram_target
from riscv_tools.bin_to_image.core import read_words
from riscv_tools.jtag import JtagLink

from benchmarks.embench import run

RAM_BASE = 0x40000000
TOHOST = 0x43FFFFE8
MAGIC = 0x454D4248
ORACLE_INSTRUCTIONS = 8
REPEATS = 3


def decode_frame(text: str) -> dict[str, Any] | None:
    """Reject incomplete scans, traps and unbalanced counters."""
    match = re.search(r"(?m)^METRICS=([0-9a-fA-F]{112})$", text)
    if not match:
        raise ValueError("Missing observer response")
    frame = int(match[1], 16)
    if frame == 0:
        return None
    if frame & 0xFFFFFFFF != MAGIC or (frame >> 32) & 0xFFFFFFFF != 1:
        raise ValueError("Observer failed, trapped or produced stale data")
    values = [(frame >> (64 + 64 * i)) & ((1 << 64) - 1) for i in range(6)]
    cycles, instructions, *mix = values
    if min(cycles, instructions) <= 0 or sum(mix) != instructions:
        raise ValueError("Invalid hardware accounting")
    return {
        "cycles": cycles,
        "instructions": instructions,
        "operations": dict(zip(run.BUCKETS, mix, strict=True)),
    }


def scan(link: JtagLink, operation: str, markers: str, log: Path) -> str:
    """Execute the fixed JTAG script with a bounded process group."""
    return run.command(
        [
            "quartus_stp",
            "-t",
            str(run.HERE / "hardware_scan.tcl"),
            link.hardware_name,
            link.device_name,
            operation,
            markers,
        ],
        log.parent,
        log,
        timeout=60,
    )


def one_program(
    folder: Path, name: str, record: dict[str, Any], link: JtagLink
) -> dict[str, Any]:
    """Load firmware, wait without SDRAM polling, then check exit."""
    firmware = folder / "firmware"
    image = firmware / f"{name}.image.bin"
    if run.digest(image) != record["image_sha256"]:
        raise ValueError("Firmware image checksum mismatch")
    flash_loader.halt(link)
    ram = ram_target.SdramDebugRam()
    ram_target.write_word(link, ram, (TOHOST - RAM_BASE) // 4, 0)
    markers = record["markers"]
    packed = f"{markers['stop_trigger']:08x}{markers['start_trigger']:08x}"
    scan(link, "configure", packed, folder / "observer.log")
    flash_loader.load_image(link, read_words(image), word_address=1024)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        measured = decode_frame(
            scan(link, "read", "0" * 16, folder / "observer.log")
        )
        if measured is not None:
            break
        time.sleep(0.05)
    else:
        raise TimeoutError(f"{name}: observer did not finish within 180s")
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        status = htif.read_tohost(link, ram, RAM_BASE, TOHOST)
        if htif.is_done(status):
            if status != 1:
                raise ValueError(f"{name}: original verifier failed: {status}")
            return measured
        time.sleep(0.05)
    raise TimeoutError(f"{name}: original verifier did not finish")


def summarize(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Use median cycles and require deterministic instructions."""
    first = samples[0]
    if any(
        (sample["instructions"], sample["operations"])
        != (first["instructions"], first["operations"])
        for sample in samples
    ):
        raise ValueError("Hardware repetitions retired different instructions")
    cycles = [sample["cycles"] for sample in samples]
    median = int(statistics.median(cycles))
    return dict(
        first,
        cycles=median,
        samples=samples,
        cycle_range_percent=100 * (max(cycles) - min(cycles)) / median,
        cpi=median / first["instructions"],
        ipc=first["instructions"] / median,
    )


def timing(folder: Path) -> dict[str, Any]:
    """Require passing multicorner timing and domain-specific Fmax."""
    base = folder / "board/de0-cv-de0-cv/output_files/de0_cv_de0_cv"
    summary = base.with_suffix(".sta.summary").read_text()
    values = re.findall(r"(?m)^Slack\s*:\s*(-?\d+\.\d+)$", summary)
    if not values or min(map(float, values)) < 0:
        raise ValueError("Hardware timing missing or failing")
    report = base.with_suffix(".sta.rpt").read_text()
    frequencies = re.findall(
        r";\s*[\d.]+ MHz\s*;\s*([\d.]+) MHz\s*;\s*"
        r"pll_inst\|altera_pll_i\|general\[3\][^;]+;",
        report,
    )
    if not frequencies:
        raise ValueError("Missing restricted core-domain Fmax")
    return {
        "status": "pass",
        "minimum_slack_ns": min(map(float, values)),
        "core_domain_fmax_mhz": min(map(float, frequencies)),
        "scope": "Instrumented build; intra-core paths, not system Fmax",
    }


def validate(folder: Path) -> dict[str, Any]:
    """Check firmware hashes and timing before programming the board."""
    manifest = json.loads((folder / "hardware-manifest.json").read_text())
    sof = folder / "board/de0-cv-de0-cv/output_files/de0_cv_de0_cv.sof"
    if run.digest(sof) != manifest["sof_sha256"]:
        raise ValueError("Bitstream checksum mismatch")
    for name, record in manifest["firmware"].items():
        image = folder / "firmware" / f"{name}.image.bin"
        if run.digest(image) != record["image_sha256"]:
            raise ValueError("Firmware image checksum mismatch")
    manifest["timing"] = timing(folder)
    return manifest


def counter_checks(
    folder: Path,
    manifest: dict[str, Any],
    link: JtagLink,
) -> dict[str, Any]:
    """Validate exact retirement and reject a failing exit."""
    check = one_program(
        folder, "_counter", manifest["firmware"]["_counter"], link
    )
    if check["instructions"] != ORACLE_INSTRUCTIONS or check["operations"] != {
        "branching": 3,
        "memory": 2,
        "compute": 3,
        "other": 0,
    }:
        raise ValueError("Hardware retirement oracle failed")
    try:
        one_program(
            folder,
            "_counter_fail",
            manifest["firmware"]["_counter_fail"],
            link,
        )
    except ValueError as error:
        if "original verifier failed: 3" not in str(error):
            raise
    else:
        raise ValueError("Negative hardware exit oracle unexpectedly passed")
    check["negative_exit_rejected"] = True
    return check


def measure(args: argparse.Namespace) -> None:
    """Require the counter oracle and every repetition to pass."""
    folder = args.input
    manifest = validate(folder)
    link = JtagLink(
        args.cable, "@1: 5CE(BA4|FA4) (0x02B050DD)", sdram_instance=3
    )
    check = counter_checks(folder, manifest, link)
    identity = manifest["provenance"]
    identity["contract"].update(
        memory="DE0-CV/emulated-FLASH/SDRAM/4KiB-I-D-caches",
        measurement="retire-PC-markers/independent-FPGA-observer/v1",
        quartus=manifest["quartus"],
        workload=manifest["suite"]["workload"],
    )
    document: dict[str, Any] = {
        "schema": 1,
        "backend": "fpga",
        "profile": manifest["profile"],
        "suite": manifest["suite"],
        "provenance": identity,
        "results": [],
        "configured_mhz": manifest["configured_mhz"],
        "timing": manifest["timing"],
        "sof_sha256": manifest["sof_sha256"],
        "counter_check": check,
    }
    for name in manifest["suite"]["programs"]:
        record = manifest["firmware"][name]
        row = summarize(
            [one_program(folder, name, record, link) for _ in range(REPEATS)]
        )
        scale = record["scale"]
        normalization = scale["original"] / scale["executed"]
        row.update(
            program=name,
            status="pass",
            scale=scale,
            score_kind="CI estimate"
            if manifest["suite"]["workload"] == "ci"
            else "Embench",
            score_per_mhz=float(record["reference_ms"])
            * 1000
            / (row["cycles"] * normalization),
            elf_sha256=record["elf_sha256"],
            mips_nominal=row["ipc"] * manifest["configured_mhz"],
            elapsed_seconds_nominal=row["cycles"]
            / (manifest["configured_mhz"] * 1e6),
        )
        document["results"].append(row)
        run.write_json(folder / "results.json", document)


def main() -> None:
    """Parse paths and an explicitly selected DE0-CV cable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--cable", required=True)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        validate(args.input)
    else:
        measure(args)


if __name__ == "__main__":
    main()
