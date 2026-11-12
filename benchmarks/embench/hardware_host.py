"""Serialize bounded containers and lock the DE0-CV."""

import argparse
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import uuid
from contextlib import ExitStack
from pathlib import Path

IMAGE = (
    "ghcr.io/insper-riscv/ci-elf@sha256:"
    "69a94e0e42869be2dc14a5174c49eed7cead20afe3282e3ce6c629179ef8aeb8"
)
PYTHON = "/opt/riscv-tools/riscv-tools/bin/python"
QUARTUS = "/opt/altera_lite/25.1std/quartus/bin"
HERE = Path(__file__).resolve().parent


def execute(arguments: list[str], timeout: int) -> str:
    """Bound a command group and clean up its container."""
    try:
        return wait_command(arguments, timeout)
    finally:
        if arguments[:2] == ["docker", "run"]:
            name = arguments[arguments.index("--name") + 1]
            subprocess.run(  # noqa: S603
                ["/usr/bin/docker", "rm", "-f", name],
                check=False,
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def wait_command(arguments: list[str], timeout: int) -> str:
    """Capture a bounded process and kill its group on expiry."""
    with subprocess.Popen(  # noqa: S603
        arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    ) as process:
        try:
            output, _ = process.communicate(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
    if process.returncode:
        raise RuntimeError(output[-8000:])
    return output


def jtag_execute(arguments: list[str], timeout: int) -> str:
    """Recover the daemon only after a JTAG timeout, per lab policy."""
    try:
        return execute(arguments, timeout)
    except (subprocess.TimeoutExpired, RuntimeError) as error:
        timed_out = isinstance(error, subprocess.TimeoutExpired) or any(
            marker in str(error)
            for marker in ("TimeoutExpired", "exit status 124")
        )
        if timed_out:
            subprocess.run(
                ["/usr/bin/sudo", "-n", "killall", "jtagd"],
                check=False,
                timeout=15,
            )
        raise


def docker(arguments: list[str], network: str) -> list[str]:
    """Isolate the compiler from host credentials, USB and Docker."""
    driver = HERE.parents[1]
    return [
        "docker",
        "run",
        "--name",
        "rv32-embench-" + uuid.uuid4().hex,
        "--rm",
        "--init",
        "--read-only",
        "--workdir",
        "/",
        "--memory=8g",
        "--memory-swap=8g",
        "--cpus=2",
        "--pids-limit=512",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--security-opt=label=disable",
        "--network=" + network,
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--tmpfs",
        "/tmp:rw,exec,size=512m",  # noqa: S108 - isolated container tmpfs
        "--env",
        "PYTHONPATH=/driver",
        "--env",
        "PYTHONDONTWRITEBYTECODE=1",
        "--env",
        "EMBENCH_IMAGE=" + IMAGE,
        "--env",
        "GIT_CONFIG_COUNT=1",
        "--env",
        "GIT_CONFIG_KEY_0=safe.directory",
        "--env",
        "GIT_CONFIG_VALUE_0=*",
        "--env",
        "PATH=" + QUARTUS + ":/opt/riscv-tools/riscv-tools/bin"
        ":/opt/riscv-foundation/riscv32-elf/bin:/opt/ghdl/bin"
        ":/usr/local/bin:/usr/bin:/bin",
        "--mount",
        f"type=bind,src={driver},dst=/driver,readonly",
        "--mount",
        "type=bind,src=/opt/altera_lite,dst=/opt/altera_lite,readonly",
        *arguments,
    ]


def lock_board(stack: ExitStack) -> None:
    """Respect canonical and legacy board locks."""
    names = (
        "de0cv-D-20003267-LINUX.lock",
        "de0cv-ws.lock",
        "de0-cv-ws.lock",
        "de0-cv-ws-2.lock",
    )
    for name in names:
        path = Path("/tmp") / name  # noqa: S108 - shared lab lock paths
        stream = stack.enter_context(path.open("r" if path.exists() else "a+"))
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)


def build(
    root: Path,
    upstream: Path,
    folder: Path,
    args: argparse.Namespace,
    previous: Path | None = None,
) -> None:
    """Compile PR sources inside an offline container."""
    reuse = (
        []
        if previous is None
        else ["--mount", f"type=bind,src={previous},dst=/previous,readonly"]
    )
    command = docker(
        [
            *reuse,
            "--mount",
            f"type=bind,src={root},dst=/input,readonly",
            "--mount",
            f"type=bind,src={upstream},dst=/upstream,readonly",
            "--mount",
            f"type=bind,src={folder},dst=/work",
            IMAGE,
            PYTHON,
            "-m",
            "benchmarks.embench.hardware_container",
            "--profile",
            args.profile,
            "--workload",
            args.workload,
        ],
        "none",
    )
    (folder / "container-build.log").write_text(execute(command, 2400))


def program_and_measure(folder: Path, args: argparse.Namespace) -> None:
    """Check device identity before programming the selected cable."""
    mount = ["--mount", f"type=bind,src={folder},dst=/work"]
    scan = jtag_execute(
        docker(
            [
                *mount,
                IMAGE,
                "quartus_pgm",
                "-l",
            ],
            "host",
        ),
        60,
    )
    # Check device identity per cable, not just the USB port.
    chain = jtag_execute(
        docker(
            [
                *mount,
                IMAGE,
                "jtagconfig",
            ],
            "host",
        ),
        60,
    )
    sections = re.split(r"(?m)^\d+\) ", chain)
    matching = [
        section
        for section in sections
        if section.strip() and section.splitlines()[0].strip() == args.cable
    ]
    if (
        len(matching) != 1
        or "02B050DD" not in matching[0]
        or "020F70DD" in matching[0]
    ):
        raise ValueError("Selected cable is not the approved DE0-CV")
    (folder / "jtag-chain.log").write_text(scan + chain)
    execute(
        docker(
            [
                *mount,
                IMAGE,
                PYTHON,
                "-m",
                "benchmarks.embench.hardware_measure",
                "--input",
                "/work/build",
                "--cable",
                args.cable,
                "--check-only",
            ],
            "none",
        ),
        60,
    )
    sof = "/work/build/board/de0-cv-de0-cv/output_files/de0_cv_de0_cv.sof"
    programming = jtag_execute(
        docker(
            [
                *mount,
                IMAGE,
                "quartus_pgm",
                "-m",
                "jtag",
                "-c",
                args.cable,
                "-o",
                "p;" + sof + "@1",
            ],
            "host",
        ),
        120,
    )
    (folder / "program.log").write_text(programming)
    output = jtag_execute(
        docker(
            [
                *mount,
                IMAGE,
                PYTHON,
                "-m",
                "benchmarks.embench.hardware_measure",
                "--input",
                "/work/build",
                "--cable",
                args.cable,
            ],
            "host",
        ),
        1800,
    )
    (folder / "measure.log").write_text(output)


def main() -> None:
    """Measure an explicit profile on both PR sides."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("candidate", "upstream", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--base", type=Path)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--cable", default="USB-Blaster [1-6]")
    parser.add_argument("--workload", choices=("ci", "full"), default="ci")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, cancelled)
    if not re.fullmatch(r"rv32i[a-z0-9_]*", args.profile):
        raise ValueError("Only explicit RV32I-family profiles are supported")
    args.output.mkdir(parents=True, exist_ok=False)
    previous = None
    for side in ("candidate", "base"):
        root = getattr(args, side)
        if root is None:
            continue
        folder = args.output / side
        folder.mkdir()
        build(root.resolve(), args.upstream.resolve(), folder, args, previous)
        with ExitStack() as stack:
            lock_board(stack)
            program_and_measure(folder, args)
        target = args.output / "results" / side / args.profile
        target.mkdir(parents=True)
        shutil.copyfile(folder / "build/results.json", target / "results.json")
        previous = folder / "build"
    (args.output / "status.json").write_text(json.dumps({"status": "pass"}))


def cancelled(_signal: int, _frame: object) -> None:
    """Release locks and containers when Actions cancels a job."""
    raise KeyboardInterrupt


if __name__ == "__main__":
    main()
