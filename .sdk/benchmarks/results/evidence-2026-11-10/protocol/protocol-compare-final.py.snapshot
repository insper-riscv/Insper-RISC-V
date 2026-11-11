"""Run identical assembler kernels on pinned old and current unmodified RTL."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from riscv_tools.settings import load_config
from riscv_tools.sim_runner import run_test

from rv32_sdk.cli import write_config

SDK = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASELINE_REV = "2115e4c8f49f75f9ef045bb59cf375c36f02b3ca"


def kernels():
    """Include independent known answers and an unsupported-feature negative control."""
    value = 0x7FFFFFFF
    for _ in range(32):
        value = value // 3 + 1000001
    return {
        "alu-chain": ("li a0,0\n", "addi a0,a0,1\n" * 128, 128),
        "branch-loop": ("li a0,100\n", "1: addi a0,a0,-1\nbnez a0,1b\n", 0),
        "mul-chain": (
            "li a0,1\nli t1,64\nli t2,3\n",
            "1: mul a0,a0,t2\naddi t1,t1,-1\nbnez t1,1b\n",
            pow(3, 64, 2**32),
        ),
        "div-chain": (
            "li a0,0x7fffffff\nli t1,32\nli t2,3\nli t3,1000001\n",
            "1: divu a0,a0,t2\nadd a0,a0,t3\naddi t1,t1,-1\nbnez t1,1b\n",
            value,
        ),
        "mul-pair": (
            "li a0,0\nli a1,0x12345678\nli t1,64\nli t2,0x01020304\n",
            "1: mulhu t3,a1,t2\nmul t4,a1,t2\nxor t3,t3,t4\nadd a0,a0,t3\naddi t1,t1,-1\nbnez t1,1b\n",
            (
                (
                    ((0x12345678 * 0x01020304) >> 32)
                    ^ ((0x12345678 * 0x01020304) & 0xFFFFFFFF)
                )
                * 64
            )
            & 0xFFFFFFFF,
        ),
        "div-rem-pair": (
            "li a0,0\nli a1,0x7ffffff9\nli t1,64\nli t2,17\n",
            "1: divu t3,a1,t2\nremu t4,a1,t2\nxor t3,t3,t4\nadd a0,a0,t3\naddi t1,t1,-1\nbnez t1,1b\n",
            (((0x7FFFFFF9 // 17) ^ (0x7FFFFFF9 % 17)) * 64) & 0xFFFFFFFF,
        ),
        "mul-pair-separated": (
            "li a1,0x12345678\nli t2,0x01020304\n",
            "mulhu t3,a1,t2\n"
            + "nop\n" * 8
            + "mul t4,a1,t2\n"
            + "nop\n" * 8
            + "xor a0,t3,t4\n"
            + "nop\n" * 8,
            (
                ((0x12345678 * 0x01020304) >> 32)
                ^ ((0x12345678 * 0x01020304) & 0xFFFFFFFF)
            ),
        ),
        "div-rem-separated": (
            "li a1,0x7ffffff9\nli t2,17\n",
            "divu t3,a1,t2\n"
            + "nop\n" * 8
            + "remu t4,a1,t2\n"
            + "nop\n" * 8
            + "xor a0,t3,t4\n"
            + "nop\n" * 8,
            ((0x7FFFFFF9 // 17) ^ (0x7FFFFFF9 % 17)),
        ),
        "mul-pair-different": (
            "li a1,0x12345678\nli t2,0x01020304\nli t5,0x01020305\n",
            "mulhu t3,a1,t2\n"
            + "nop\n" * 8
            + "mul t4,a1,t5\n"
            + "nop\n" * 8
            + "xor a0,t3,t4\n"
            + "nop\n" * 8,
            (
                ((0x12345678 * 0x01020304) >> 32)
                ^ ((0x12345678 * 0x01020305) & 0xFFFFFFFF)
            ),
        ),
        "div-rem-different": (
            "li a1,0x7ffffff9\nli t2,17\nli t5,19\n",
            "divu t3,a1,t2\n"
            + "nop\n" * 8
            + "remu t4,a1,t5\n"
            + "nop\n" * 8
            + "xor a0,t3,t4\n"
            + "nop\n" * 8,
            ((0x7FFFFFF9 // 17) ^ (0x7FFFFFF9 % 19)),
        ),
        "load-use": (
            "li s1,0x8200\nsw zero,0(s1)\nli t1,64\n",
            "1: lw a0,0(s1)\naddi a0,a0,1\nsw a0,0(s1)\naddi t1,t1,-1\nbnez t1,1b\n",
            64,
        ),
        "misaligned-cross-word": (
            "li s1,0x8200\nli t1,0x01020304\nsw t1,0(s1)\nli t1,0x05060708\nsw t1,4(s1)\n",
            "lw a0,1(s1)\n",
            0x08010203,
        ),
    }


def main():
    """Compare observed cycles only when both designs compute the correct answer."""
    baseline = Path(sys.argv[1]).resolve()
    root = Path(sys.argv[2]).resolve()
    root.mkdir(parents=True, exist_ok=False)
    old_config = json.loads(
        (baseline / "tests/python/tests.json").read_text()
    )["one"]
    baseline_manifest = {}
    for relative in ["tests/python/tests.json", *old_config["sources"]]:
        expected = subprocess.check_output(
            ["git", "-C", str(SDK), "show", f"{BASELINE_REV}:{relative}"]
        )
        actual = (baseline / relative).read_bytes()
        if actual != expected:
            raise ValueError(
                f"Frozen baseline source differs from pinned commit: {relative}"
            )
        baseline_manifest[relative] = hashlib.sha256(actual).hexdigest()
    project = root / "configuration"
    project.mkdir()
    current_config = load_config(write_config(project, {"language": "c"}))
    results = {
        "baseline_commit": BASELINE_REV,
        "current_commit": subprocess.check_output(
            ["git", "-C", str(SDK), "rev-parse", "HEAD"], text=True
        ).strip(),
        "scope": "Controlled RTL simulation, identical instruction bytes, synchronous memory; not delivered-system FPGA speedup",
        "runs": [],
        "baseline_source_hashes": baseline_manifest,
        "current_source_hashes": {
            str(Path(path).relative_to(SDK)): hashlib.sha256(
                Path(path).read_bytes()
            ).hexdigest()
            for path in current_config["sim"]["vhdl_sources"]
        },
        "runner_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
        "monitor_sha256": hashlib.sha256(
            (HERE / "marker_monitor.py").read_bytes()
        ).hexdigest(),
    }
    for name, (initial, body, expected) in kernels().items():
        if sys.argv[3:] and name not in sys.argv[3:]:
            continue
        case = root / name
        case.mkdir()
        source = case / "kernel.S"
        source.write_text(
            ".global _start\n.text\n_start:\nli s0,0x8100\n"
            + initial
            + "li t0,1\nsw t0,0(s0)\n"
            + body
            + "sw a0,4(s0)\nli t0,1\nsw t0,8(s0)\n2: j 2b\n"
        )
        elf = case / "kernel.elf"
        binary = case / "kernel.bin"
        obj = case / "kernel.o"
        linker = case / "kernel.ld"
        linker.write_text(
            "ENTRY(_start)\nSECTIONS { . = 0x1000; .text : { *(.text*) } }\n"
        )
        subprocess.run(
            [
                "riscv32-unknown-elf-gcc",
                "-march=rv32im",
                "-mabi=ilp32",
                "-c",
                str(source),
                "-o",
                str(obj),
            ],
            check=True,
        )
        subprocess.run(
            [
                "riscv32-unknown-elf-ld",
                "-m",
                "elf32lriscv",
                "--no-relax",
                "-T",
                str(linker),
                str(obj),
                "-o",
                str(elf),
            ],
            check=True,
        )
        subprocess.run(
            [
                "riscv32-unknown-elf-objcopy",
                "-O",
                "binary",
                str(elf),
                str(binary),
            ],
            check=True,
        )
        blob = binary.read_bytes()
        assert len(blob) <= 2048, "Exceeds the original simulation ROM"
        words = [
            f"{int.from_bytes(blob[i : i + 4], 'little'):08x}"
            for i in range(0, len(blob), 4)
        ]
        boot = case / "boot.hex"
        boot.write_text("000012b7\n00028067\n")
        for variant in ["baseline", "current"]:
            image = case / f"{variant}.hex"
            image.write_text(
                "\n".join(
                    (["00000000"] * 1024 if variant == "current" else [])
                    + words
                )
                + "\n"
            )
            result_file = case / f"{variant}.json"
            if variant == "baseline":
                sources = [str(baseline / p) for p in old_config["sources"]]
                parameters = {"ROM_FILE": str(image)}
            else:
                sources = current_config["sim"]["vhdl_sources"]
                parameters = {
                    **current_config["sim"]["parameters"],
                    "BOOT_MEMORY_FILE": str(boot),
                    "ROM_FILE": str(image),
                }
            os.environ["PYTHONPATH"] = (
                str(HERE) + os.pathsep + os.environ.get("PYTHONPATH", "")
            )
            passed = run_test(
                "rv32i3stage_core_sim_test",
                sources,
                "08",
                "marker_monitor",
                image,
                build_dir=case / variant,
                parameters=parameters,
                test_name=f"{variant}/{name}",
                extra_env={
                    "PYTHONPATH": os.environ["PYTHONPATH"],
                    "VARIANT": variant,
                    "KERNEL": name,
                    "EXPECTED": str(expected),
                    "RESULT": str(result_file),
                },
            )
            result = (
                json.loads(result_file.read_text())
                if result_file.exists()
                else {
                    "variant": variant,
                    "kernel": name,
                    "verified": False,
                    "error": "No completed measurement",
                }
            )
            result.update(
                simulation_passed=passed,
                binary_sha256=hashlib.sha256(blob).hexdigest(),
            )
            results["runs"].append(result)
            (root / "results.json").write_text(
                json.dumps(results, indent=2) + "\n"
            )
            print("EVIDENCE", name, variant, result, flush=True)
    print(
        "Completed controlled comparison; inspect failures and scope before drawing conclusions.",
        flush=True,
    )
    if any(
        row["variant"] == "current" and not row["verified"]
        for row in results["runs"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
