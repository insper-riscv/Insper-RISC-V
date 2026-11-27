# Main integration and presentation validation

This branch integrates Insper-RISC-V main `2e98cb7e`, current Core `ff14dc7`,
Memory main `fae441f5`, and the reviewed Tools/Peripherals branches. It retains
the SoC/interconnect/boot relocation to `base/`, upstream peripheral fixes,
and the C/Rust SDK, PlatformApp exports, language servers and DE0-CV support.
Memory's earlier loading repairs were already present in main; no separate
Memory feature diff was needed.

The latest Core references its DSP multiplier even in manually listed simulation
sources. The root configuration lists now include that entity before `multdiv`;
the SDK's guarded input hashes were updated with the corresponding files.
PlatformApp exports also include `scripts/editor-deps.sh`, required by container
startup. New projects pin the current official ci-elf image by immutable digest.

Validated locally with at most 8 GiB RAM, no additional swap, and two CPUs:

- 118 SDK unit tests.
- All 11 named Core profiles: real C compiler and GHDL execution.
- Seven C CLI acceptance cases, including headers, multiple sources, allocation,
  exact/no/long stdout, compiler errors, nonzero exit and bounded infinite loops.
- Rust runtime, Vec/String and normal main in RV32I and RV32IM; the combined
  peripheral application, six generated simulated examples and four physical-map
  builds also passed. The complete Rust CI job passed on the published SDK.
- GPIO register and physical-pin mapping regressions, including ascending
  generics, forward/reverse half-steps and undriven unused pins.
- Fresh remote Tools bootstrap and clean application of the SDK patch.
- VSCode extension tests and exact rebuilt/installation VSIX equality.

A clean main hardware checkout also passed C/Rust export, relocation/rebuild and
GPIO child-example builds. All maps, config variants and source lists passed
`make memory-map` with the reviewed Tools revision. Tools CI passed completely.

CI found an example-refresh ownership conflict: child setup legitimately merged
editor and Cargo configuration, then a parent refresh mistook those changes for
edited driver source. Example project configuration is now seeded and preserved
when modified; driver/library and example source protections remain unchanged.
Twenty C/Rust child setups across RV32I and RV32IM/IRQ passed repeated parent
refresh. A dedicated unit regression covers preserved configuration on refresh
and peripheral removal. Rust RTL acceptance also repeats parent regeneration.

Root CI now installs the reviewed, unpatched Tools revision for source/map checks
instead of depending on whichever generator happened to ship in the image. In a
tooling container, the same local validation is:

```sh
python3 .sdk/prepare_tools.py
uv sync --project .sdk --locked
PATH="$PWD/.sdk/.venv/bin:$PATH" make memory-map
```

Final hardware synthesis/cache and physical C/Rust revalidation remain pending.
Check the final PR checks and follow-up validation before recommending merge.

The motor examples default to a non-driving self-check. Motor wiring was not
identified, so no claim of mechanical movement was made. Only the connected
DE0-CV was available for physical validation; other boards require their own
hardware checks. No main merge was performed.
