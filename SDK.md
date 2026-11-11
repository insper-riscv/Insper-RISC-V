# Live SDK 0.5.0 (review candidate)

This SDK adds external C/Rust application projects and the Live VS Code
extension to the current processor tree. It does not replace upstream RTL or
normal platform runtime files. See the [Live installation guide](https://github.com/insper-riscv/Live)
for VS Code, Dev Containers and Remote - SSH setup.

## Source baseline

- Processor: `c954c77120af6865c7ccc34f16e94a41fb7c5fbb` (main 0.5.0).
- Tools: `0340eefe0e95c674d68f7516c392b5c8f17cf7f3` (1.13.0).
- Processor submodules follow this checkout's gitlinks; clone with `--recurse-submodules`.
- `.sdk/dependencies.json` pins Tools. `.sdk/patches/tools-sdk.patch` adds
  application include directories, packed JTAG memory decoding and bounded STP calls.

The managed dependency is downloaded into ignored `.sdk/tools`, with its own
`.sdk/.venv`. It does not modify a sibling Tools checkout. Setup refuses to
replace an existing mismatched dependency. Move that dependency aside to allow
recreation after an intentional SDK update. The lockfile pins Python packages.

## Installation and project creation

On the Docker/FPGA host:

```bash
bash scripts/install-user.sh --quartus /path/to/altera/std25.1
~/.local/bin/rv32-new c /path/to/new-c-app
~/.local/bin/rv32-new rust /path/to/new-rust-app
```

Install `share/rv32-development.vsix` into VS Code (and into its SSH extension
host when using Remote - SSH). Open the application and reopen in Dev Container.
Bootstrap installs the bundled extension in the container. The first bootstrap
needs network access for Tools/Python/Rust. Docker access must already work.

CLI equivalents inside the development environment:

```bash
scripts/rv32-project --project /path/to/app simulate
scripts/rv32-project --project /path/to/app fpga --mode full
scripts/rv32-project --project /path/to/app fpga --mode fast
scripts/rv32-project --debug --project /path/to/app simulate
```

The TOML accepts `project.source`, additional `project.sources` and
`project.include_dirs`; paths are relative to the application. The C template
uses `include/`. Rust is `no_std`, with no built-in heap allocator.

## Compatibility and output

The validated SDK platform is `internal-mem` on Cyclone V. Other upstream
platforms remain available for their normal processor workflows; SDK integration
for them is not validated. The SDK verifies its upstream platform inputs against
`.sdk/platform-inputs.json` and fails if those files drift unexpectedly.

An ignored `.sdk/platforms/internal-mem` view is derived from upstream runtime
and testbench files. It reserves 64 KiB stdout while upstream's ordinary platform
keeps its original map. About 96 KiB remains for program data, heap and stack.
Buffer overflow reports failure. Output is read through JTAG RAM; the physical
UART remains upstream's hardware output too. No serial adapter is required for
the VS Code stdout path. Simulation disables wire-time UART stdio by default;
`project.simulation_uart_stdio = true` opts in. Rust runtime changes trigger a
relink when switching execution mode.

This revision uses upstream's boot_memory and HTIF loader. Old SDK bitstreams
are incompatible. Run Program FPGA after upgrading, then use Fast Update.
The SOF cache hashes hardware, platform/runtime configuration, Quartus and build
flow inputs, and verifies the SOF checksum. C/Rust application changes reuse it.

An exact target chip match is mandatory; several matches require
`project.jtag_hardware`. This avoids accidentally programming another board.
Coordinate shared boards and JTAG service usage with other lab users.

Quiet execution preserves stdout bytes, including an absent final newline.
Diagnostics go to `logs/rv32/`; `--debug` or VS Code `rv32.debug` shows them live.
Simulation cycle limits and FPGA wall-clock limits are independent TOML settings.

## Validation

Inside the development image:

```bash
python3 .sdk/prepare_tools.py
uv sync --project .sdk --locked
uv run --project .sdk ruff check .sdk
uv run --project .sdk ruff format --check .sdk
(cd .sdk && uv run deptry .)
uv run --project .sdk python -m unittest discover -s .sdk/tests
source scripts/env.sh
uv run --project .sdk python .sdk/tests/integration.py
make check
```

SDK CI covers its separate Python project and actual C/GHDL execution. The
processor CI retains its own checks. Hardware acceptance additionally requires
Program FPGA, Fast Update, long stdout, and C/Rust mode switching on an available
board; simulation is not a substitute for those tests.

## Local KPI benchmark development

The initial counter harness and pinned Embench workload runner are documented in
[the benchmark guide](.sdk/benchmarks/README.md). It exports raw measurements and
provenance; it does not yet produce an official Embench suite score.

Controlled historical RTL comparisons, correctness regressions and raw physical
measurements are collected in the [evidence dossier](.sdk/benchmarks/results/evidence-2026-11-10/README.md).
It reports targeted arithmetic reuse gains and a load-use regression; it does
not establish a general application speedup.

The processor package release is 0.5.2; the isolated SDK and bundled extension
remain 0.5.0. SDK CI runs on pushes to main and both review branches, as well
as pull requests. Processor RTL and ordinary platform runtimes are unchanged
by these SDK additions.
