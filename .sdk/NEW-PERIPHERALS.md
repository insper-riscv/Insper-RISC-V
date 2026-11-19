# New peripheral driver integration (SDK 0.10.0)

Use this SDK branch with its pinned Peripherals commit and the matching
Live 0.10.0 extension. Clone recursively, or run
`git submodule update --init --recursive` before installing/registering the SDK.
No upstream main platform RTL is rewritten by driver generation.

Existing SDK installations update the managed Tools dependency automatically.
The replacement is fetched and patched before the old directory is moved to
`.sdk/.tools-backup-*/tools`. Local edits and untracked files remain in that
backup. A fetch/patch failure leaves the current checkout untouched; an
activation failure restores it. Details are kept in `.sdk/.tools-bootstrap.log`
without adding setup messages to program output.

After pulling SDK changes, align processor dependencies with
`git submodule update --init --recursive` from the SDK root. The SDK requires
the recorded revisions, including the Core boot fragments; independently
updating each submodule to its main branch can produce incompatible layouts.

Create a C or Rust project using the extension and select a platform, or use:

```sh
/path/to/Insper-RISC-V/scripts/rv32-new rust ./my-app --platform periph-de10-lite
```

The project TOML selects the authoritative map:

```toml
[project]
name = "app"
language = "rust"
manifest = "Cargo.toml"
platform = "periph-de10-lite"
cpu_profile = "auto"
generate_drivers = true
generate_driver_examples = true
```

For C use `language = "c"`, `source = "src/main.c"`, `sources = []`, and
`include_dirs = ["include"]`. The creation command supplies all editor/container
files and the include directory. The seven current `periph-<board>` choices
correspond exactly to `src/periph-examples/*/platform.yaml`. `auto` retains the
physical platform's compiled CPU configuration; explicit profile overrides
continue to target the existing internal-memory/modular simulation platforms.

Run **RV32: Refresh Peripheral Drivers** or **RV32: Prepare Project**. The SDK
matches peripheral `kind` and PS/2 device variants, resolves base addresses,
GPIO groups, ADC backend/channel count, SPI widths/selects, Ethernet buffer
sizes, and framebuffer windows. It writes `vendor/`, adds only safe Rust crates
to Cargo dependencies, and generates complete independent examples under
`vendor/<DRIVER>/example/`. Edited managed files are never silently overwritten.
Drivers absent from the map are not invented. Multiple instances use logical
indices (`Ethernet::instance(1)`, for example); platform tables hide addresses.
Serial UART entries remain serial even when the standard-output console is JTAG.

GPIO logical group indices flatten the map declaration order. On MKR Vidor the
three groups have 7, 7 and 25 pins. Group/pin indices are logical, not raw pin
numbers. Existing named GPIO instances remain backward compatible.

New C/Rust families: ADC (ADC128S022/LTC2308/MAX10), ADXL345, Ethernet, HDMI
(including TMDS), I2C, infrared, LCD, MIPI, PS/2 keyboard/mouse, native SD, SD-SPI,
SPI, TV capture, Wi-Fi/NINA, audio (including HDMI audio), and video. USB gains
a safe Rust/sys pair and generated instance selection. These expose controller
register interfaces; protocol stacks, card/PHY initialization and attached-device
configuration are separate responsibilities. See each driver's README/docs.

Physical peripheral platforms have build/FPGA actions but no complete SoC model
for every attached device. **Simulate reports this limitation explicitly**.
Existing `internal-mem`, `modular` and legacy `de0-cv` behavior remains available.
A generated read-only smoke example is not a physical device acceptance test.

## Reproduce SDK checks

```sh
python3 .sdk/prepare_tools.py
uv sync --project .sdk --frozen
PYTHONPATH=.sdk uv run --project .sdk python -m unittest discover -s .sdk/tests -p 'test_*.py'
PYTHONPATH=.sdk uv run --project .sdk python .sdk/tests/new_peripherals_integration.py
```

The integration suite cross-checks all 18 new Rust example families and C
examples against generated tables, and builds complete C/Rust projects for all
seven physical board maps. No FPGA is programmed. Use the pinned multilib CI
image with Rust 1.85.1, both RV32 targets, Clang/libclang, two compiler jobs and an
8 GiB/no-swap container limit. RTL and C/Rust API checks are in Peripherals.
