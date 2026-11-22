# base

🌐 [Português](README.md) · [English](README.en.md)

The `base/` folder gathers what every project generated from Insper-RISC-V shares, regardless of board: the SoC, the external interconnect and the boot code. It sits at the root, outside `src/` (which holds the platforms) and `templates/` (which holds the software skeletons), and it is the only source of these files. No platform keeps a copy of them; all of them read the files by relative path.

## 1. Contents

| Path | Responsibility |
| :--- | :--- |
| `src/soc/soc.vhd` | The system on chip with no board pin, family name or chip model, which connects the core, the caches, the interconnect, the CLINT, the PLIC and the I/O peripherals |
| `src/interconnect/` | The external interconnect (native and AXI4), which decodes the platform window table between the bus memory and the peripherals, and the package with the decode types and functions |
| `src/boot/boot_core.S` | The common BOOT_MEMORY, included by the `boot_memory.S` of each platform |

## 2. Users

The `soc`, `ext_interconnect`, `interconnect_pkg` and `axi_interconnect` components are declared in the `provides` of the root `paths.yaml`, with the files pointing to this folder. The platforms in `src/` require these components by name and include `boot_core.S` by relative path. The simulation tops and the testbenches of each platform stay in `src/` and are not part of this folder.

The documentation of each part is in [docs/en/soc/soc.md](../docs/en/soc/soc.md), [docs/en/interconnect/ext_interconnect.md](../docs/en/interconnect/ext_interconnect.md) and [docs/en/platform/boot.md](../docs/en/platform/boot.md).

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../LICENSE).
