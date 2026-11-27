# PlatformApp software workspaces

PlatformApp can export C or Rust applications alongside its generated hardware.
The `project` platform reads the actual hardware `platform.yaml`; it does not
silently replace it with a standard SDK platform.

## Configuration

```toml
[project]
name = "my-app"
language = "rust" # or "c"
platform = "project"
platform_file = "src/periph-examples/my-platform/platform.yaml"
cpu_profile = "auto"
sdk_relative_root = "Insper-RISC-V"
```

Paths above are relative to the embedded hardware checkout, except
`sdk_relative_root`, which is relative to the application. The core's YAML
selects the ISA. C compile flags, runtime objects, Rust target, memory regions,
reserved mailboxes and generated driver addresses all follow that platform.
The current ABI requires RV32I (optional extensions supported), one instruction
region and one data region, with `stdout`, `tohost`, and `fromhost` in data RAM.
Reserved RAM limits the heap/stack; stdout capacity follows the reserved size.

The standalone exporter uses Python 3.14's standard library. PlatformApp embeds
a deterministic SDK archive with a revision and file hashes. It overlays only
SDK/runtime/driver files, preserving hardware RTL, and saves replaced files in
`.rv32/sdk-backup-*`. Failed application exports restore those replacements.
Existing application files and edited generated drivers are never overwritten.

The application includes Dev Container settings, the RV32 VS Code extension,
Cargo dependencies or C build settings, and examples per enabled driver. Child
examples inherit the platform and use relative SDK mounts. Moving the complete
project preserves its build; generated private paths are recreated.

## Reproduce the validation

Use the SDK's tooling environment with GCC for RISC-V, the installed Rust
`riscv32i-unknown-none-elf` and `riscv32im-unknown-none-elf` targets, libclang,
Python 3.14 and uv. Prepare dependencies using `.sdk/prepare_tools.py` and uv.
From the repository root:

```bash
PYTHONPATH=.sdk uv run --project .sdk python -m unittest discover -s .sdk/tests -v
uv run --project .sdk ruff check .sdk
uv run --project .sdk ruff format --check .sdk
uv run --project .sdk python .sdk/tests/integration_platformapp.py \
  --output /tmp/platformapp-evidence-new
```

The opt-in integration test accepts `--hardware-source /path/to/clean/main`
to validate the SDK overlay against a separate hardware revision. It requires
a new output directory. It creates real
DE2-115 hardware projects with two GPIO instances (and CLINT/PLIC entries,
selected only when the CPU enables their interrupt fabric), exports C and
Rust projects, cross-compiles each, moves each directory and rebuilds, then
compiles its generated GPIO example. It leaves the projects and `result.json`
for inspection. The test launches no FPGA operation and no simulation. Run it
inside an isolated container capped at 8 GiB RAM, no additional swap, 2 CPUs.

Validation on 23 November 2026 passed all 85 SDK unit tests, Ruff checks and
both languages' export/build/relocation/GPIO-example integration checks. The
Flutter side passed 150 tests and static analysis. These results cover software
generation and compilation, not physical board programming.

## Current limits

Custom physical maps do not yet have a complete SoC/peripheral simulation in
the SDK. `simulate` reports that limitation instead of selecting a different
platform. Quartus build/programming still needs the correct board and local or
remote Quartus/JTAG access. The compact Rust starter fits the default small
physical instruction banks; additional application code may require increasing
the generated hardware's memory allocation.
