# DE2-115 results

This report records what the two DE2-115 platforms did on the board, with Quartus 25.1 Lite and the board of the lab PC1. The description of the platforms is in [de2-115.md](de2-115.md).

## 1. Synthesis

| Platform | Logic elements | Memory bits | Setup slack |
| :--- | ---: | ---: | :--- |
| `de2-115-n2` | 18.961 of 114.480 | 3.254.528 of 3.981.312 | positive in every domain, minimum 0.084 ns |
| `de2-115` | 20.111 of 114.480 | 108.800 of 3.981.312 | positive in every domain, minimum 0.780 ns (`DRAM_CLK`) |

The RAM of the map has 128 MiB (`cache_window_bits` 27), and the setup slack was measured with three Quartus seeds.

| Seed | `clk[3]` | `DRAM_CLK` (pin) |
| :--- | ---: | ---: |
| 5 | +1.250 ns | +0.810 ns |
| 1 | +1.471 ns | +0.780 ns |
| 9 | +1.208 ns | +0.810 ns |

The core runs at 50 MHz with a phase of 8250 ps against the fetch clock. With the phase at zero the core skips instructions, because the instruction memories read on the fetch clock one cycle ahead of the core.

## 2. Level N2 (`de2-115-n2`)

| Program | Result |
| :--- | :--- |
| `hello`, `display`, `code-sweep`, `conformance-fencei` | pass |
| `clint-mtip` | fails with code 2: the write to `msip` does not light the MSIP bit of `mip` |
| programs of the 16 MB SDRAM window | out of the level, the emulated RAM has 128 KiB |

## 3. 32-bit SDRAM and `DRAM_CLK` phase

The test uses the debug port: it fills the two halves of $2^{24}$ words with different values, checks words at the ends and the middle of each half, and writes and reads back 32 addresses (24 drawn and the two extremes of each bank). Bit 24 of the address travels in bit 3 of the operation code.

| `DRAM_CLK` phase (ps, at 100 MHz) | Result |
| ---: | :--- |
| 0 | passes |
| 2000 | fails |
| 4000 | passes |
| 6000 | passes |
| 8000 | passes |

The value in `board.yaml` is 6000 ps, in the middle of the window that passes. The `tohost` and `fromhost` addresses change by themselves because the core writes them, and the test does not count them.

## 4. NOR FLASH and level N4 (`de2-115`)

Each program is written to bank A of the NOR by a program the host leaves in the SDRAM, and the BOOT_MEMORY starts it through the RAM entry (magic `RAMB` and entry in the last 8 bytes of the RAM). The chip has eight 8 KiB boot sectors in the first 64 KiB, and the controller erases with that granularity.

| Program | Result |
| :--- | :--- |
| `cache-sweep`, `code-sweep`, `conformance-fencei`, `cpi-kernels`, `display`, `hello` | pass |
| `misaligned-cache-lines`, `misaligned-crossing`, `sdram-bytes`, `sdram-copy`, `sdram-exec-copy` | pass |
| `sdram-loop`, `sdram-memtest`, `sdram-muldiv`, `sdram-refresh`, `selfmod-repeat` | pass |
| `clint-mtip` | fails with code 2, as in N2 |
| `flash-const` | fails with code 6: reading the FLASH word after a store to it does not return the earlier value |

That is 16 of the 18 programs built for the board. `monitor` and `hex-id` need a person and are not included.

## 5. Limitations

| Item | Limitation |
| :--- | :--- |
| FLASH of the map | 1024 KiB of the chip, the window of the region router |
| Cache invalidation | the invalidation pulse of the controller covers an 8 KiB sector, even when the chip erases a 64 KiB sector |
| Program update | banks A and B by the firmware (`c-sdram-update`) did not run on this board, because the `uart_input.txt` of the tests is the DE0-CV bank B image |
| ACT4 | the ELFs of the full profile did not run on this board |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
