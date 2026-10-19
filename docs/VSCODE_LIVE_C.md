# Reproducible live C development

This workflow provides a short edit--compile--run cycle for one C program. It
uses paths relative to the `RV32` checkout by default; machine-specific paths
are supplied through environment variables and are never committed.

## Repository layout

- `Live/c/live/src.c`: program edited by the user.
- `scripts/rv32.sh`: portable entry point used by every VS Code task.
- `scripts/env.sh`: path defaults and environment-variable setup.
- `scripts/live_c.py`: compilation, simulation, Spike and FPGA orchestration.
- `Tests`: test compiler and runner, included as a Git submodule.
- `TopLevel/platforms/internal-mem`: simulation and FPGA platform.

Clone with submodules:

```bash
git clone --recurse-submodules https://github.com/insper-riscv/RV32.git
cd RV32
```

For an existing clone, run `git submodule update --init --recursive`.
The complete source ZIP already bundles the submodule contents, so its
bootstrap automatically skips this Git-only step.

## Option A: Dev Container (recommended)

The container image supplies the RISC-V compiler, Python environment, GHDL,
Spike and the other simulation dependencies.

1. Install Docker, VS Code and the **Dev Containers** extension.
2. Open the `RV32` directory in VS Code.
3. Run `Dev Containers: Reopen in Container`.
4. Wait for `scripts/bootstrap.sh` to initialize the submodules and Python
   environment.
5. Run `Terminal > Run Task > RV32: Check environment`.
6. Edit `Live/c/live/src.c` and run `RV32: Simulate C program`.

Simulation does not require Quartus or an FPGA.

### Add local Quartus and the FPGA to the container

Create the local configuration file:

```bash
cp .devcontainer/.env.example .devcontainer/.env
```

Edit `.devcontainer/.env` and set the directory that contains `quartus/`:

```dotenv
RV32_QUARTUS_HOST_ROOT=/home/your-user/altera/std25.1
```

Rebuild the Dev Container after changing the file. The host directory is
mounted read-only at `/opt/altera_lite/25.1std`, while the commands locate it
through `QUARTUS_ROOTDIR`. The `.env` file is ignored by Git.

The host must already have working USB-Blaster permissions and `jtagd`. Verify
inside the container:

```bash
bash scripts/rv32.sh doctor
jtagconfig
```

If Docker cannot access the USB-Blaster reliably, use Option B. Do not run two
JTAG clients at the same time.

## Option B: host or Remote SSH

Install `uv`, the RISC-V toolchain, GHDL and Quartus on the FPGA workstation.
Export only the installation-specific roots; repository paths are derived
automatically:

```bash
export RV32_TOOLCHAIN_ROOT=/absolute/path/to/riscv32-toolchain
export QUARTUS_ROOTDIR=/home/your-user/altera/std25.1/quartus
source scripts/env.sh
bash scripts/bootstrap.sh
code .
```

The same commands work through VS Code Remote SSH. This is the preferred way
to operate a remote board: VS Code and all JTAG commands run on the workstation
to which the FPGA is physically connected.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `RV32_ROOT` | repository containing `scripts/` | Parent repository |
| `RV32_TESTS_ROOT` | `$RV32_ROOT/Tests` | Tests/tooling submodule |
| `RV32_LIVE_ROOT` | `$RV32_ROOT/Live` | Editable program and outputs |
| `RV32_CONFIG` | `$RV32_LIVE_ROOT/config.yaml` | `riscv-tools` configuration |
| `RV32_PLATFORM` | internal-memory `platform.yaml` | Memory and JTAG metadata |
| `RV32_TOOLCHAIN_ROOT` | image/host dependent | Directory containing the RISC-V `bin/` |
| `RV32_GCC` | toolchain compiler | VS Code C compiler |
| `QUARTUS_ROOTDIR` | image/host dependent | Quartus directory containing `bin/` |
| `RV32_DEV_IMAGE` | `ghcr.io/insper-riscv/dev_tools:latest` | Dev Container image |
| `RV32_QUARTUS_HOST_ROOT` | empty placeholder | Host directory mounted into the container |

Only tool installation roots normally need to be configured. Avoid adding a
personal absolute path to a tracked JSON, YAML or shell file.

## Development cycle

Run tasks from `Terminal > Run Task` or invoke the portable wrapper directly:

```bash
bash scripts/rv32.sh simulate
bash scripts/rv32.sh spike
bash scripts/rv32.sh assembly
```

For a physical FPGA:

```bash
# First run, or after an RTL/platform change: synthesize and configure.
bash scripts/rv32.sh fpga --mode full

# Normal C edit cycle: update only application memory over JTAG.
bash scripts/rv32.sh fpga --mode fast

# Reprogram an existing SOF without compiling Quartus again.
bash scripts/rv32.sh fpga --mode reprogram
```

`main` reports PASS/FAIL through the mailbox. `puts`, `printf` and `putchar`
write to a RAM buffer that the tool reads over JTAG after a successful run.
The fast mode still compiles the C program, but does not resynthesize the FPGA.

## What should be committed

Commit source and configuration files such as `Live/c/live/src.c`, scripts,
documentation, `.vscode`, `.devcontainer`, VHDL, QSF and platform YAML files.
Do not commit any of the following:

- `.devcontainer/.env` or other machine-specific paths;
- `.venv`, Python caches or coverage output;
- `Live/build`, generated headers and logs;
- Quartus `db`, `incremental_db`, `output_files`, simulation output or reports;
- a generated modification to a tracked memory initialization file unless that
  image is intentionally part of the change.

Before committing, inspect every repository independently because this project
uses nested Git submodules:

```bash
git status --short
git -C Tests status --short
git -C Tests/tools/Tools status --short
git -C TopLevel status --short
```

A change inside `Tools` or `TopLevel` must first be committed in that
repository. The updated submodule pointer is then committed in `Tests` and/or
the parent `RV32` repository. Never stage generated outputs just to make the
parent repository appear clean.

## Current limitations

- This is a short edit--compile--load cycle, not GDB step debugging; the CPU
  has no compatible RISC-V Debug Module.
- FPGA execution requires a bitstream compatible with the current memory map.
- Standard input is not interactive. Standard output is a bounded RAM buffer
  read only when execution finishes.
- Some JTAG/PLL failure states can require a physical reset or power cycle.
