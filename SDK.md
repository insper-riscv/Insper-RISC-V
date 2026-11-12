# Live SDK 0.7.1 (review candidate)

This SDK adds external C/Rust application projects and the Live VS Code
extension to the current processor tree. It does not replace upstream RTL or
normal platform runtime files. See the [Live installation guide](https://github.com/insper-riscv/Live/tree/sdk-profiles-drivers)
for VS Code, Dev Containers and Remote - SSH setup.

## Source baseline

- Processor: `dfdf585e87355a739916cd3140adc40e21982aa3` (main 0.5.0).
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

Initialize the processor submodules before registering a Git checkout:

```bash
git clone --recurse-submodules --branch live-vscode https://github.com/insper-riscv/Insper-RISC-V.git
cd Insper-RISC-V
git submodule update --init --recursive
```

Run the last command again after pulling a branch that changes module pointers. A plain clone/pull leaves uninitialized module folders empty. The SDK checks their source files before container setup and reports the recovery command. A complete source ZIP already includes these sources and needs no Git initialization.

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

The processor package release is 0.5.1; the isolated SDK and bundled extension
are 0.7.1. SDK CI runs on pushes to main and both review branches, as well
as pull requests. Processor RTL and ordinary platform runtimes are unchanged
by these SDK additions.

## CPU profiles in application TOML

```toml
[project]
name = "app"
language = "c"
platform = "internal-mem"
cpu_profile = "rv32im_zicsr"
source = "src/main.c"
include_dirs = ["include"]
```

`cpu_profile` accepts the eleven named `Core/profiles/rv32*.yaml` profiles. Omission or `"auto"` preserves the existing platform CPU/compiler behavior. Explicit overrides target `internal-mem` and simulation-only `modular`; CPU profiles do not change a platform's peripheral or memory map. ISA constants and HPM parameters are applied in private `.rv32/cpu` files; tracked processor sources remain untouched. C receives the selected ISA; a source's `RV32_EXT` request outside that profile is rejected. Rust selects the compatible built-in RV32I or RV32IM target and links the platform C runtime with the selected GCC ISA (no unsupported extension is required by the Rust target). Run Prepare Project to install a newly selected Rust target.

Changing a profile invalidates the SOF cache. C-only changes do not. For an explicit profile, Fast Update requires a matching previous successful Program FPGA on that cable. After another tool programs the board, run Program FPGA again; this software record cannot detect arbitrary external reprogramming. Cache schema changed once in this release, so existing projects may need their first bitstream regenerated.

The development toolchain needs library variants for the selected ISA. A toolchain with only RV32IM libraries cannot safely run RV32I-only applications. See the profile integration checks before installing on another machine.

## Automatic C peripheral drivers

```toml
[project]
language = "c"
platform = "modular"
cpu_profile = "rv32im"
generate_drivers = true
source = "src/main.c"
include_dirs = ["include"]
```

Prepare Project, Simulate and Program FPGA regenerate drivers before compiling when `generate_drivers` is enabled. New C templates enable it. Existing projects without that field retain their prior behavior. Use **RV32: Refresh Peripheral Drivers** or `scripts/rv32-drivers --project /path/to/app` to inspect/regenerate files separately. Keep `generate_drivers = true` to include generated C sources automatically in the application build.

The generator reads the selected platform's canonical YAML, resolves and validates its addresses with Tools, reads the named CPU profile, and discovers descriptors under `Peripherals/src/<peripheral>/<implementation>/driver/c/driver.yaml`. A descriptor lists its C sources, headers, mapped instance names and required register-window size. It does not duplicate memory addresses. The descriptors now cover GPIO, TIMER, CLINT, PLIC, UART serial/JTAG, DISPLAY and FLASH_CTRL. Optional `requires_cpu_flags` lists hardware elaboration requirements: CLINT/PLIC are not vendored when the selected CPU profile removes the interrupt fabric.

`vendor/rv32_platform.h` describes the declared MMIO map and CPU feature flags. `vendor/GPIO` contains the reusable driver and generated per-instance configuration. The SDK adds its include paths and C sources; applications include `rv32_drivers.h`. One GPIO implementation serves both SWITCHES and KEYS. The platform declares addresses; CPU interrupt capability and the platform's actual I/O instantiation still determine which operations hardware implements.

A managed-file manifest protects hand edits and unrelated vendor files. Regeneration refuses to overwrite edited/unmanaged files, removes only unchanged files it previously generated, and rejects symlink/traversal paths. Customize driver sources in Peripherals, or preserve local changes elsewhere before regeneration. The copied Apache license accompanies vendored sources. Generated driver changes do not invalidate hardware bitstreams; platform/RTL changes still do.

All device structs have `rv32_<device>_new(...)` constructors. They are non-owning values: no malloc and no MMIO writes during construction. Use the constructor and public operations; applications do not change a handle's base address or calculate register offsets. Invalid pin/digit/source indices are rejected before MMIO. GPIO accepts `size_t` pin numbers, DISPLAY accepts digit numbers, and PLIC accepts source numbers. Whole-mask GPIO operations remain available for compatibility.

The base address comes from the canonical platform map (`base`, or peripheral window plus `offset`). Internal register offsets come from the peripheral RTL and are private C constants. Pin numbers become bit masks inside the driver, not hexadecimal addresses. Pin counts, display digit counts, UART backend/FIFO capacity, PLIC source/priority widths and FLASH page size must match the actual RTL instance; they are not inferred from the slot size. The C driver neither installs CPU trap handlers nor enables machine interrupts.

GPIO/TIMER IRQ status is read-to-clear; FLASH IRQ status is W1C. PLIC claim consumes one pending source. JTAG UART status reads acknowledge dropped TX bytes, unlike serial UART status. UART writes are nonblocking or use an explicit total poll budget, not an unlimited wait. CLINT reads its 64-bit counter high/low/high and writes deadlines low=all-ones/high/low. Flash commands are asynchronous; true means submitted, and callers still check busy/refused/completion. Execute erase/program routines outside the FLASH being modified.

See `examples/gpio` for constructor/pin operations and bounded synchronization/IRQ polling with no arbitrary settle delay. `examples/peripherals` additionally exercises TIMER, serial/JTAG UART and DISPLAY, plus CLINT and PLIC/GPIO when `HAS_INTERRUPTS` is enabled. The private modular SDK view enables its mapped display; the normal processor configuration is unchanged. All C code uses the Peripherals `.clang-format`, one statement per line and blank lines between logical blocks.

`platform = "modular"` is a simulation-only SDK view of the stock modular platform with internal memories. It uses compact storage models and the public RAM observation ports to stay within the container's 8 GiB limit. Its runtime/testbench/stdout adjustments are private; main's source files are unchanged. FPGA actions reject this selection before accessing a board. Explicit CPU profiles now also work on this simulation platform.

The default internal-mem and de0-cv maps, and the fpga-uart-jtag example map, do not declare GPIO. They must not acquire invented GPIO addresses or a GPIO driver. Only mapped instances with a supported descriptor and satisfied elaboration requirements acquire drivers. A FLASH memory region is not a FLASH_CTRL peripheral and must never be treated as one.
