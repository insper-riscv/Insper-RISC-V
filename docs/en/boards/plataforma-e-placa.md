# Board fields of the platform.yaml, chips and validation rules

## 1. The platform.yaml fields that link the board

The `platform.yaml` describes the memory map, the Core profile, the peripheral windows and the interrupts, and carries the fields below to link the platform to a board. Their reader is the same as for the board files, so an unknown field or one of the wrong type is an error pointed out by the dotted path of the field.

| Field | Type | Meaning |
| :--- | :--- | :--- |
| `board` | text | `auto` (default) asks for identification by JTAG ([identificacao-jtag.md](identificacao-jtag.md)); a name fixes the board |
| `boards` | list of text | Boards the platform is built on, and the list `auto` considers |
| `top` | text or list | Component(s) of `paths.yaml` whose closure of `requires` is the source list of the generated project and gathers the resources the board must offer |
| `memory.<rom or ram>.backend` | `emulado` or `dispositivo` | Realization of the external region; required with `external: true` |
| `memory.<rom or ram>.device` | `nor`, `flash-interna`, `serial`, `sdram`, `sram` | Only with `dispositivo`, and of the type of the region (`nor`, `flash-interna` and `serial` for the ROM; `sdram` and `sram` for the RAM) |
| `memory.<rom or ram>.latency` | `{first, next}` | `clocks.core` cycles of the first word of a burst and of the following ones; only with `emulado` |
| `memory.rom.sector_bytes` | power of 2 | Sector of the `emulado` FLASH; with `dispositivo` the sector comes from the chip |
| `memory.icache`, `memory.dcache` | `{enabled, size_bits}` | Caches |
| `clocks.core` | `{mhz, phase_ps}` | Core clock; also the source of `interrupts.clock_hz` |
| `clocks.fetch` | `{mhz, phase_ps}` | Clock of the instruction memories, with phase relative to `core`; without it the core clock applies |
| `clocks.mem` | `{mhz}` | Ceiling of the device controller clock; the effective one is the smaller of it and the chip limit |
| `console` | `jtag` or `pinos` | `jtag` is the default; `pinos` requires a UART on pins on the board |
| `io.<role>` | `{count, need}` | Roles `leds`, `switches`, `keys` and `display`; `need` is `required` or `optional` |

Each clock is written once. The PLL, the `.sdc` and `interrupts.clock_hz` derive from `clocks`, and the phase of the clock that leaves through the SDRAM pin belongs to the board (`memories.sdram.clk_phase_ps`).

### 1.1. Example

Excerpts of the `platform.yaml` of the `de2-115`, with the NOR FLASH and the SDRAM of the board.

```yaml
platform: de2-115
board: auto
boards: [de2-115]
top: Insper-RISC-V/de2_115_board
core:
  type: 32
  base: I
  extensions:
    - M
    - Zicclsm
    - Zicntr
    - Zihpm
    - Zifencei
regions:
  - {name: BOOT_MEMORY, base: 0x00000000, size: 4K,    kind: rom, exec: true}
  - {name: FLASH,       base: 0x00001000, size: 1024K, kind: rom, exec: true}
  - {name: RAM,         base: 0x40000000, size: 64M,   kind: ram}
flash:
  region: FLASH
  banks:
    - {name: A, base: 0x00001000, size: 512K}
    - {name: B, base: 0x00081000, size: 512K}
memory:
  rom:    {external: true, backend: dispositivo, device: nor}
  ram:    {external: true, backend: dispositivo, device: sdram}
  icache: {enabled: true, size_bits: 32768}
  dcache: {enabled: true, size_bits: 32768}
clocks:
  core:  {mhz: 50, phase_ps: 8250}
  fetch: {mhz: 50, phase_ps: 0}
  mem:   {mhz: 100}
console: jtag
io:
  leds:    {count: 18, need: required}
  display: {count: 8,  need: optional}
```

The FLASH starts at `0x00001000`, offset 0 of the chip. With the 64 KiB sector, each bank starts at a multiple of 64 KiB from the start of the chip, which is why bank B is at `0x00081000`, offset `0x80000`.

## 2. Derivation of requires and provides

Two sets are computed and never written. The `requires` of the platform gathers what it asks for (`regions`, `memory`, `clocks`, `io`, `console`) and the union of the `needs` keys of the components in the closure of the top. The `provides` of the board comes from the `board.yaml`, the catalog chip and the `pins.yaml`. The inclusion of the first in the second is the check.

| Required resource | Origin in `requires` | Origin in `provides` |
| :--- | :--- | :--- |
| Device type (`sdram`, `sram`, `nor`, `onchip_flash`, `serial_flash`, `vjtag`, `block_ram`) | Union of the `needs` in the closure of the top | Key present in `memories` and `jtag.chain` |
| Capacity and width | `regions` and `memory.<region>` | Catalog chip and `chips` or `bus_width` |
| RAM blocks | `emulado` memories, caches and register file | `resources.block_ram` |
| Logic and multipliers | Estimate of [cabimento.md](cabimento.md) | `resources.logic` and `resources.multipliers` |
| PLLs | Distinct clocks of `clocks` | `resources.plls` |
| I/O roles and console | `io` and `console` | `io` and `console.uart` |
| Frequency | `clocks.*` | PLL range of the family and `max_mhz` of the chip |

The `needs` key lives beside `sources` and `requires` in the `paths.yaml` of the repository that owns the component, with the types `block_ram`, `sdram`, `sram`, `nor`, `onchip_flash`, `serial_flash` and `vjtag`.

## 3. Chip catalog

Each memory chip is a file `Memory/chips/<chip>.yaml`, and the file name is the chip name.

| Field | Meaning |
| :--- | :--- |
| `chip` | Name |
| `extends` | Optional; name of another chip whose fields this one inherits and overrides |
| `kind` | `sdram`, `sram`, `nor` or `serial_flash` |
| `organization` | `{words, width, banks, row_bits, col_bits}` for SDRAM; `{words, width}` for the others |
| `cas_latency` | Column latency of the SDRAM |
| `timing` | Timings with datasheet names; picoseconds on SDRAM (`trcd_ps`), nanoseconds on SRAM and NOR (`access_ns`) |
| `io_timing` | Setup, hold and access of the pins, used in the `.sdc` |
| `sector_bytes`, `boot_sector_bytes` | FLASH sector |
| `max_mhz` | Clock ceiling of the chip |
| `source` | `datasheet` or `inferido` |

```yaml
chip: IS42S16320B-7
extends: IS42S16320D-7
source: inferido
```

The chip of the `de2-115` belongs to the same series as the one of the `de0-cv` and repeats no value. The chip timings become a generated VHDL package, read by the controller and the simulation model, and the I/O delays of the `.sdc`.

## 4. Validation rules

The rules run in `check-memory-map`, in `board generate` and before compiling. Each is an error (E) or a warning (W), and the messages are in English.

| Rule | Level | What it checks |
| :--- | :--- | :--- |
| V1 | E | The board, the family and the chips exist and the files follow the schema |
| V2 | E | Every `needs` type is on the board, and the sum of the regions of a device fits in it |
| V3 | E | The device of a `dispositivo` backend exists on the board |
| V4 | E | The `pinos` console requires `console.uart` |
| V5 | E | `required` role missing or with fewer units |
| V6 | W | `optional` role missing or with fewer units; the peripheral is omitted |
| V7 | E | Clock above the PLL range of the family or the chip ceiling |
| V8 | W | Core clock above the measured Fmax of the family and grade |
| V9 | E | FLASH bank not a multiple of the sector, counted from the start of the region |
| V10 | E | Region larger than the capacity of the device |
| V11 | E or W | RAM blocks above the capacity (E) or above 85 % of it (W) |
| V12 | E | Estimated logic above the capacity, in a family with maximum validation error up to 10 % |
| V13 | W | Estimated logic between 85 % and 100 % of the capacity |
| V14 | E or W | The fit report exceeds a resource (E) or passes 85 % of it (W) |
| V15 | E | More PLL outputs than the board offers |
| V16 | E | `inferred` pin in use without `--accept-inferred-pins` |
| V17 | E | The JTAG chain read from the cable is not the board's |
| V18 | W | Family without calibration, `null` capacity or `null` coefficient of a profile term |
| V19 | E | Bus width the backend cannot slice (8 and 16 on NOR, 16 and 32 on SRAM and SDRAM) |

Message examples.

```text
E platform 'de0-cv' requires sdram (64M) but board 'de0-nano' provides sdram of 32M
E memory.rom.device nor is not provided by board 'de0-cv' (provides: none); use backend emulado
E flash bank B base 0x7F000 is not a multiple of the NOR sector 0x10000 of chip S29GL064N90
E pin M16 for SPI_FLASH_CS is inferred, not confirmed; pass --accept-inferred-pins
```

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
