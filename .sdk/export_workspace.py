"""Package the reviewed SDK and create a portable C/Rust hardware workspace.

This bootstrap intentionally uses only Python's standard library. The embedded
SDK remains responsible for platform validation, driver selection and Cargo.
"""

import argparse
import fcntl
import gzip
import hashlib
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid
from pathlib import Path

DIRECTORIES = (".sdk/rv32_sdk", ".sdk/rust", ".sdk/patches", "templates")
FILES = (
    "LICENSE",
    "Peripherals/LICENSE",
    ".sdk/export_workspace.py",
    ".sdk/prepare_tools.py",
    ".sdk/dependencies.json",
    ".sdk/platform-inputs.json",
    ".sdk/pyproject.toml",
    ".sdk/uv.lock",
    "share/rv32-development.vsix",
    "scripts/env.sh",
    "scripts/rv32-project",
    "scripts/rv32-new",
    "scripts/rv32-drivers",
    "scripts/rv32-rust-linker",
    "scripts/rust-build-deps.sh",
    "scripts/editor-deps.sh",
    "scripts/bootstrap-external.sh",
    "scripts/container-start.sh",
    "scripts/install-vscode-extension.sh",
)
SKIP = {".git", "target", "build", "__pycache__", ".venv", "node_modules"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def walk(root: Path):
    for folder, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(
            name for name in directories if name not in SKIP
        )
        for name in sorted(names):
            path = Path(folder) / name
            if path.is_symlink():
                raise ValueError(
                    f"Symlink refused in SDK distribution: {path}"
                )
            if path.suffix != ".pyc":
                yield path


def package_files(sdk: Path) -> list[Path]:
    paths = {sdk / name for name in FILES}
    for folder in DIRECTORIES:
        paths.update(walk(sdk / folder))
    for folder in (sdk / "Peripherals/src").glob("*/**/driver"):
        if "common" not in folder.relative_to(sdk / "Peripherals/src").parts:
            paths.update(walk(folder))
    return sorted(paths)


def bundle(sdk: Path, output: Path) -> None:
    entries = {}
    for path in package_files(sdk):
        if not path.is_file():
            raise ValueError(f"Incomplete SDK distribution: {path}")
        entries[path.relative_to(sdk).as_posix()] = {
            "sha256": digest(path.read_bytes()),
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=sdk, text=True
    ).strip()
    manifest = {"schema": 1, "sdk_revision": revision, "files": entries}
    output.parent.mkdir(parents=True, exist_ok=True)
    with (
        output.open("wb") as raw,
        gzip.GzipFile(
            fileobj=raw, mode="wb", filename="", mtime=0
        ) as compressed,
        tarfile.open(fileobj=compressed, mode="w|") as archive,
    ):
        for name in [*entries, "SDK-MANIFEST.json"]:
            data = (
                (
                    json.dumps(manifest, sort_keys=True, indent=2) + "\n"
                ).encode()
                if name == "SDK-MANIFEST.json"
                else (sdk / name).read_bytes()
            )
            entry = tarfile.TarInfo("sdk/" + name)
            entry.size = len(data)
            entry.mode = entries.get(name, {}).get("mode", 0o644)
            archive.addfile(entry, io.BytesIO(data))


def safe_target(root: Path, relative: str) -> Path:
    name = Path(relative)
    if name.is_absolute() or ".." in name.parts or not name.parts:
        raise ValueError(f"Unsafe SDK path: {relative}")
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes its workspace: {relative}")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Refusing to replace a symlink: {part}")
        if part == root:
            break
    return path


def copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".export-" + uuid.uuid4().hex)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def install_overlay(
    source: Path, hardware: Path, backup: Path
) -> tuple[dict, list[tuple[Path, Path | None]]]:
    manifest = json.loads((source / "SDK-MANIFEST.json").read_text())
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported SDK bundle manifest")
    entries = []
    for name, spec in manifest["files"].items():
        original = safe_target(source, name)
        target = safe_target(hardware, name)
        if (
            not original.is_file()
            or digest(original.read_bytes()) != spec["sha256"]
        ):
            raise ValueError(f"Corrupt SDK bundle member: {name}")
        if target.exists() and not target.is_file():
            raise ValueError(f"Not a file: {target}")
        entries.append((name, original, target))
    changed = []
    try:
        for name, original, target in entries:
            if (
                target.exists()
                and target.read_bytes() == original.read_bytes()
                and stat.S_IMODE(target.stat().st_mode)
                == stat.S_IMODE(original.stat().st_mode)
            ):
                continue
            saved = backup / name if target.exists() else None
            if saved is not None:
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            changed.append((target, saved))
            copy_atomic(original, target)
    except OSError:
        restore(changed)
        raise
    return manifest, changed


def restore(changed: list[tuple[Path, Path | None]]) -> None:
    for target, saved in reversed(changed):
        if saved is None:
            target.unlink(missing_ok=True)
        else:
            copy_atomic(saved, target)


def run_drivers(hardware: Path, application: Path, environment: Path) -> None:
    env = dict(
        os.environ,
        UV_PROJECT_ENVIRONMENT=str(environment),
        UV_CACHE_DIR=str(environment.parent / "uv-cache"),
    )
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            "bash",
            str(hardware / "scripts/rv32-project"),
            "--project",
            str(application),
            "drivers",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=480,
    )
    if result.returncode:
        details = result.stdout + result.stderr
        log = application / "logs/rv32/drivers-latest.log"
        if log.exists():
            details += "\n" + log.read_text()
        raise RuntimeError(
            "Could not generate application drivers:\n" + details[-16000:]
        )


def create(
    source: Path, project: Path, hardware: Path, platform: str, language: str
) -> dict:
    if language not in {"c", "rust"}:
        raise ValueError("Language must be c or rust")
    project, hardware = project.resolve(), hardware.resolve()
    if (
        not project.is_dir()
        or not hardware.is_dir()
        or not hardware.is_relative_to(project)
        or hardware == project
    ):
        raise ValueError(
            "Hardware checkout must be inside the existing project folder"
        )
    if not (project / "project.yaml").is_file():
        raise ValueError("The hardware project must have project.yaml")
    relative_sdk = hardware.relative_to(project).as_posix()
    if any(
        char
        not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_. /-"
        for char in relative_sdk
    ):
        raise ValueError("Unsupported hardware checkout folder name")
    safe_target(hardware, platform)
    if (
        Path(platform).name != "platform.yaml"
        or not (hardware / platform).is_file()
    ):
        raise ValueError("Select the hardware project's platform.yaml")
    if (project / "rv32.toml").exists():
        raise ValueError(
            "Application already exists; refresh its drivers instead of overwriting it"
        )
    state = project / ".rv32"
    state.mkdir(exist_ok=True)
    with (state / ".software-export.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(
            prefix=".software-create-", dir=state
        ) as temporary:
            work = Path(temporary)
            application = work / "application"
            application.mkdir()
            for directory in ("common", language):
                shutil.copytree(
                    source / "templates" / directory,
                    application,
                    dirs_exist_ok=True,
                )
            compact = source / "templates/platformapp" / language
            if compact.is_dir():
                # Physical templates can have two small flash banks; start small.
                shutil.copytree(compact, application, dirs_exist_ok=True)
            (application / "SOFTWARE.md").write_text(
                (application / "README.md").read_text()
                + "\n\nThe SDK is embedded in "
                + relative_sdk
                + ". Open this project in VS Code and reopen in its Dev Container. Hardware choices come from "
                + platform
                + "; change them in PlatformApp and refresh the drivers.\n"
            )
            (application / "README.md").unlink()
            manifest = application / "rv32.toml"
            options = {
                "platform": "project",
                "platform_file": platform,
                "cpu_profile": "auto",
                "sdk_relative_root": relative_sdk,
            }
            text = manifest.read_text()
            # Templates may omit platform; remove the default profile before inserting choices.
            text = (
                "\n".join(
                    line
                    for line in text.splitlines()
                    if not line.startswith("cpu_profile =")
                )
                + "\n"
            )
            text = text.replace(
                "[project]",
                "[project]\n"
                + "\n".join(
                    f"{key} = {json.dumps(value)}"
                    for key, value in options.items()
                ),
                1,
            )
            manifest.write_text(text)
            compose = application / ".devcontainer/compose.yaml"
            compose.write_text(
                compose.read_text().replace(
                    '"${HOME}/.local/share/rv32-sdk:/opt/rv32-sdk:cached"',
                    json.dumps("../" + relative_sdk + ":/opt/rv32-sdk:cached"),
                    1,
                )
            )
            initial = [
                path.relative_to(application).as_posix()
                for path in walk(application)
            ]
            for name in initial:
                if name == ".gitignore" and (project / name).exists():
                    continue
                if safe_target(project, name).exists():
                    raise ValueError(
                        f"Refusing to overwrite application file: {name}"
                    )
            backup = state / ("sdk-backup-" + uuid.uuid4().hex)
            backup.mkdir()
            provenance, changed = install_overlay(source, hardware, backup)
            committed = []
            try:
                run_drivers(hardware, application, work / "python-env")
                metadata = json.loads(
                    (application / "vendor/.rv32-drivers.json").read_text()
                )
                export = {
                    "schema": 1,
                    "language": language,
                    "platform_file": platform,
                    "sdk_relative_root": relative_sdk,
                    "sdk_revision": provenance["sdk_revision"],
                }
                (application / ".rv32/platformapp.json").write_text(
                    json.dumps(export, indent=2) + "\n"
                )
                files = list(walk(application))
                # Preflight every generated destination before publishing any application file.
                for path in files:
                    name = path.relative_to(application).as_posix()
                    if name == ".gitignore" and (project / name).exists():
                        continue
                    if safe_target(project, name).exists():
                        raise ValueError(
                            f"Refusing to overwrite application file: {name}"
                        )
                for path in files:
                    name = path.relative_to(application).as_posix()
                    if name == ".gitignore" and (project / name).exists():
                        continue
                    target = safe_target(project, name)
                    copy_atomic(path, target)
                    committed.append(target)
                return {
                    "language": language,
                    "project": str(project),
                    "drivers": sorted(
                        {
                            Path(name).parent.name
                            for name in metadata["sources"]
                        }
                    ),
                }
            except (
                OSError,
                ValueError,
                RuntimeError,
                subprocess.SubprocessError,
            ):
                for path in reversed(committed):
                    path.unlink(missing_ok=True)
                restore(changed)
                raise


def hardware(
    source: Path, project: Path, checkout: Path, arguments: list[str]
) -> None:
    """Create hardware with the same pinned Tools used by the exported SDK."""
    project, checkout = project.resolve(), checkout.resolve()
    if checkout.parent != project or not checkout.is_dir():
        raise ValueError(
            "Use the hardware checkout inside the new project folder"
        )
    if (project / "project.yaml").exists():
        raise ValueError("Hardware project already exists")
    state = project / ".rv32"
    state.mkdir(exist_ok=True)
    _, changed = install_overlay(
        source, checkout, state / ("sdk-backup-" + uuid.uuid4().hex)
    )
    try:
        with tempfile.TemporaryDirectory(
            prefix="platformapp-hardware-"
        ) as temporary:
            env = dict(
                os.environ,
                UV_PROJECT_ENVIRONMENT=temporary + "/venv",
                UV_CACHE_DIR=temporary + "/cache",
            )
            env.pop("PYTHONPATH", None)
            subprocess.run(
                [sys.executable, str(checkout / ".sdk/prepare_tools.py")],
                env=env,
                check=True,
                timeout=240,
            )
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--project",
                    str(checkout / ".sdk"),
                    "python",
                    "-m",
                    "riscv_tools.cli",
                    *arguments,
                ],
                cwd=checkout,
                env=env,
                check=True,
                timeout=240,
            )
    except OSError, subprocess.SubprocessError:
        restore(changed)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("bundle")
    pack.add_argument("--sdk-root", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    export = commands.add_parser("create")
    export.add_argument("--sdk-source", type=Path, required=True)
    export.add_argument("--project-root", type=Path, required=True)
    export.add_argument("--hardware-root", type=Path, required=True)
    export.add_argument("--platform", required=True)
    export.add_argument("--language", choices=["c", "rust"], required=True)
    hardware_parser = commands.add_parser("hardware")
    hardware_parser.add_argument("--sdk-source", type=Path, required=True)
    hardware_parser.add_argument("--project-root", type=Path, required=True)
    hardware_parser.add_argument("--hardware-root", type=Path, required=True)
    hardware_parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.command == "bundle":
            bundle(args.sdk_root.resolve(), args.output)
        elif args.command == "hardware":
            hardware(
                args.sdk_source.resolve(),
                args.project_root,
                args.hardware_root,
                args.arguments[1:]
                if args.arguments[:1] == ["--"]
                else args.arguments,
            )
        else:
            print(
                json.dumps(
                    create(
                        args.sdk_source.resolve(),
                        args.project_root,
                        args.hardware_root,
                        args.platform,
                        args.language,
                    )
                )
            )
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
