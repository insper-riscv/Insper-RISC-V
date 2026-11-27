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

- 117 SDK unit tests.
- All 11 named Core profiles: real C compiler and GHDL execution.
- Seven C CLI acceptance cases, including headers, multiple sources, allocation,
  exact/no/long stdout, compiler errors, nonzero exit and bounded infinite loops.
- Rust runtime, Vec/String and normal main in RV32I and RV32IM; the combined
  peripheral application also passed actual CPU/peripheral simulation.
- GPIO register and physical-pin mapping regressions, including ascending
  generics, forward/reverse half-steps and undriven unused pins.
- Fresh remote Tools bootstrap and clean application of the SDK patch.
- VSCode extension tests and exact rebuilt/installation VSIX equality.

The remaining generated-example matrix, current-image C acceptance, Quartus
synthesis and physical C/Rust revalidation were still running when this note was
created. Final results must be checked in the PR checks and the follow-up
validation update before treating the branch as ready to merge.

The motor examples default to a non-driving self-check. Motor wiring was not
identified, so no claim of mechanical movement was made. Only the connected
DE0-CV was available for physical validation; other boards require their own
hardware checks. No main merge was performed.
