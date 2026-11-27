"""Generate editor analysis settings from the same project as the firmware."""

import json
import re
import shutil
from pathlib import Path

from riscv_tools.compiler.build import optimize_flags
from riscv_tools.compiler.headers import parse_header


def read_settings(path: Path) -> dict:
    """Accept VS Code JSON comments/trailing commas without losing values."""
    if not path.exists():
        return {}
    text = re.sub(
        r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*[\s\S]*?\*/',
        lambda m: m[0] if m[0].startswith('"') else "",
        path.read_text(),
    )
    text = re.sub(
        r'"(?:\\.|[^"\\])*"|,\s*([}\]])',
        lambda m: m[1] if m[1] else m[0],
        text,
    )
    return json.loads(text)


def configure(root: Path, project: dict, cfg: dict, target: str) -> None:
    """Refresh owned language-server keys, preserving unrelated user settings."""
    state = root / ".rv32"
    state.mkdir(exist_ok=True)
    settings_path = root / ".vscode/settings.json"
    settings = read_settings(settings_path)
    compiler = str(cfg["toolchain"]["gcc"])
    compiler = shutil.which(compiler) or compiler
    settings.update(
        {
            "C_Cpp.intelliSenseEngine": "disabled",
            "clangd.arguments": [
                f"--compile-commands-dir={state}",
                f"--query-driver={compiler}",
                "--background-index",
                "-j=2",
            ],
        }
    )
    if project["language"] == "rust":
        settings.update(
            {
                "rust-analyzer.server.path": shutil.which("rust-analyzer")
                or str(Path.home() / ".cargo/bin/rust-analyzer"),
                "rust-analyzer.linkedProjects": [
                    str(project.get("manifest", "Cargo.toml"))
                ],
                "rust-analyzer.cargo.target": target,
                "rust-analyzer.cargo.allTargets": False,
                "rust-analyzer.check.allTargets": False,
                "rust-analyzer.cfg.setTest": False,
                "rust-analyzer.cargo.buildScripts.enable": True,
                "rust-analyzer.procMacro.enable": True,
                "rust-analyzer.cargo.targetDir": True,
                "rust-analyzer.cargo.extraEnv": {
                    **settings.get("rust-analyzer.cargo.extraEnv", {}),
                    "CARGO_BUILD_JOBS": "1",
                },
                "rust-analyzer.check.command": "check",
                "rust-analyzer.check.extraArgs": ["--release", "--bins"],
                "rust-analyzer.numThreads": 2,
            }
        )
    text = json.dumps(settings, indent=2) + "\n"
    settings_path.parent.mkdir(exist_ok=True)
    if settings_path.exists() and settings_path.read_text() != text:
        backup = state / "editor-settings.before.jsonc"
        if not backup.exists():
            backup.write_text(settings_path.read_text())
    if not settings_path.exists() or settings_path.read_text() != text:
        settings_path.write_text(text)

    required = ["llvm-vs-code-extensions.vscode-clangd"]
    if project["language"] == "rust":
        required.append("rust-lang.rust-analyzer")
    recommendations = root / ".vscode/extensions.json"
    extension_settings = read_settings(recommendations)
    entries = extension_settings.setdefault("recommendations", [])
    entries.extend(name for name in required if name not in entries)
    _write_json(recommendations, extension_settings)
    container = root / ".devcontainer/devcontainer.json"
    if container.exists():
        metadata = read_settings(container)
        entries = (
            metadata.setdefault("customizations", {})
            .setdefault("vscode", {})
            .setdefault("extensions", [])
        )
        entries.extend(name for name in required if name not in entries)
        _write_json(container, metadata)

    sources = [
        Path(p) for p in cfg["paths"]["sources"] if Path(p).suffix == ".c"
    ]
    if project["language"] == "c":
        main = root / str(project.get("source", "src/main.c"))
        sources.insert(0, main)
        source_text = main.read_text() if main.is_file() else ""
        march = (
            cfg.get("sdk_cpu_profile", {}).get("march")
            or parse_header(
                cfg["isa"], cfg["quartus"]["default_timeout_s"], source_text
            )[0]
        )
    else:
        march = "rv32i" if target == "riscv32i-unknown-none-elf" else "rv32im"
        # These are the same generated C implementations bound by the sys crates.
        sources.extend(sorted((root / "vendor").glob("*/*.c")))
    includes = [
        cfg["paths"]["include_dir"],
        *cfg["paths"].get("include_dirs", []),
    ]
    flags = [
        *optimize_flags(march),
        "-ffreestanding",
        *[f"-I{p}" for p in includes],
    ]
    records = [
        {
            "directory": str(root),
            "file": str(p.resolve()),
            "arguments": [compiler, *flags, "-c", str(p.resolve())],
        }
        for p in dict.fromkeys(sources)
        if p.is_file()
    ]
    database = state / "compile_commands.json"
    text = json.dumps(records, indent=2) + "\n"
    if not database.exists() or database.read_text() != text:
        database.write_text(text)


def _write_json(path: Path, data: dict) -> None:
    text = json.dumps(data, indent=2) + "\n"
    if not path.exists() or path.read_text() != text:
        if path.exists():
            backup = (
                path.parent.parent
                / ".rv32/editor-metadata.before"
                / path.parent.name
                / path.name
            )
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_text(path.read_text())
        path.write_text(text)
