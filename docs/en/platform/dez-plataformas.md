# The ten platforms: four for tests, four on the FPGA and two for the UART

## 1. What they are

Each combination of memory and peripherals is a platform with its own `platform.yaml`, `config.yaml` and `runtime/`. All ten run the same simulation top, `modular_sim_top` (`src/simulation/modular/`), and differ by the map, by the memory combination and by the peripherals wired in. The `platform:` field of each `platform.yaml` is the name of the folder.

| Group | How many | Where it runs | Peripherals |
| :--- | ---: | :--- | :--- |
| Test | 4 | Simulation | None |
| FPGA | 4 | DE0-CV | Switches, seven-segment displays and buttons |
| UART | 2 | DE0-CV | UART over JTAG or UART on the pins |

## 2. The memory combinations

The four combinations come from `rom_external` and `ram_external`, derived from the `memory` section of the `platform.yaml`, and the caches exist only on the bus side.

| Combination | ROM | RAM | Caches | `modular` architecture |
| :--- | :--- | :--- | :--- | :--- |
| `integrated` | internal | internal | none | A |
| `external-data` | internal | external | data | B |
| `external-instruction` | external | internal | instruction | C |
| `external` | external | external | instruction and data | D |

## 3. The platforms

| # | Platform | Folder | Combination | Profile | Peripherals |
| ---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `test-integrated` | `src/simulation/` | `integrated` | `rv32im_zicclsm` | none |
| 2 | `test-external-data` | `src/simulation/` | `external-data` | `rv32im_zicclsm` | none |
| 3 | `test-external-instruction` | `src/simulation/` | `external-instruction` | `rv32im_zicclsm_zifencei` | none |
| 4 | `test-external` | `src/simulation/` | `external` | `rv32im_zicclsm_zifencei` | none |
| 5 | `fpga-integrated` | `src/cyclone-v/` | `integrated` | `rv32im_zicclsm_zicntr_zihpm` | switches, buttons, displays |
| 6 | `fpga-external-data` | `src/cyclone-v/` | `external-data` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | switches, buttons, displays |
| 7 | `fpga-external-instruction` | `src/cyclone-v/` | `external-instruction` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | switches, buttons, displays |
| 8 | `fpga-external` | `src/cyclone-v/` | `external` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | switches, buttons, displays |
| 9 | `fpga-uart-jtag` | `src/cyclone-v/` | `external` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | UART over JTAG |
| 10 | `fpga-uart-pins` | `src/cyclone-v/` | `external` | `rv32im_zicclsm_zicntr_zihpm_zifencei` | UART on the pins |

All of them turn on the `Zimop` and `Zicond` extensions through the `extras` field. The platforms with an instruction cache use the profile with `Zifencei`.

## 4. Memory maps

The 4 KiB BOOT_MEMORY starts at `0x00000000` in all ten, and the ROM (or the FLASH) starts right after it.

| Platforms | ROM | RAM |
| :--- | :--- | :--- |
| 1 to 4 | `0x00001000` to `0x00100000` | `0x00100000`, 1 MiB |
| 5 | `0x00001000`, 28 KiB | `0x00008000`, 160 KiB |
| 7 | `0x00001000`, 252 KiB | `0x00040000`, 160 KiB |
| 6, 8, 9 and 10 | `0x00001000`, 252 KiB | `0x40000000`, 32 MiB |

The words that the host and the program share (`stdout`, `tohost` and `fromhost`) sit at the top of the RAM of each platform. The board SDRAM has 64 MiB and the map uses 32 MiB of it, the largest size of the RAM chip model of the simulation (`ram_chip`).

## 5. Peripherals and windows

Each peripheral takes a window of the region from `0x80000000`, whose base and size come from `platform.yaml`. The interconnect hits it through the table of the map package, and the index of each peripheral is its position in the `peripherals` list.

| Peripheral | Block | Board pin | Index | Base | Platforms |
| :--- | :--- | :--- | ---: | :--- | :--- |
| `SWITCHES` | 10-pin GPIO | `SW` | 1 | `0x90000000` | 5 to 8 |
| `KEYS` | 4-pin GPIO | `KEY` | 2 | `0xA0000000` | 5 to 8 |
| `UART` on the pins | `UART/serial` | two pins, TX and RX | 3 | `0xB0000000` | 10 |
| `UART` over JTAG | `UART/jtag` | JTAG cable | 4 | `0xC0000000` | 9 |
| `DISPLAY` | display | `HEX0` to `HEX5` | 5 | `0xD0000000` | 5 to 8 |

On the test platforms the peripheral window has no device: a read answers zero and a write has no effect. The GPIO blocks read the synchronized pins at word 9 of the window (offset `0x24`), with the pins as inputs after the reset.

## 6. How they are built

1. `riscv-tools generate-memory-map` writes, from each `platform.yaml`, the `modular_map_pkg.vhd` package in the folder of the platform, the `runtime/memory_map.h` header, the linker specs file and the linker script of the BOOT_MEMORY (`make generate`, and `make generate-check` verifies).
2. The package of each platform is called `modular_map_pkg`, the name the top uses, and the source list of the platform carries the package of its own folder. The `<name>_sim_top` component of the `provides` (with the platform name in snake_case) lists the sources in the right order.
3. The memory combination and the `HAS_*` of the profile reach the top through the package. The peripherals enter through the `has_switches`, `has_keys`, `has_display`, `has_uart_jtag` and `has_uart_pins` generics of the top, which the `sim.parameters` of each platform `config.yaml` turns on, and the table indices of the peripherals are the `switches_index`, `keys_index`, `display_index`, `uart_jtag_index` and `uart_pins_index` generics. Both UARTs enter through the same `console` entity of the Peripherals (see `Peripherals/docs/en/UART/console.md`): `has_uart_jtag` instantiates the `jtag` backend and `has_uart_pins` the `pinos` backend, and each stays wired to its PLIC source (`UART` at id 1 and `UART_JTAG` at id 2).
4. The peripheral ports of the top are `io_sw` and `io_key` (the GPIO blocks), `o_display_hex` and `o_display_value`, the `i_uart_*` and `o_uart_tdo` ports of the Virtual JTAG and the `i_uart_rx` and `o_uart_tx` pins. The I/O roles take their width and polarity from generics (`switches_width`, `keys_width`, `display_digits`, `*_active_low`), with the DE0-CV values as default; width zero omits the role (see the [SoC](../soc/soc.md) document).

## 7. How to use

```bash
ulimit -s unlimited
riscv-tools --root . generate-memory-map --platform src/cyclone-v/fpga-external/platform.yaml
riscv-tools --profile rv32im_zicclsm_zicntr_zihpm_zifencei \
  --config src/cyclone-v/fpga-external/config.yaml compile --emit hex ...
```

`--memory` of `riscv-tools` replaces the memory combination for one run, and `--profile` replaces the profile.

## 8. Verification

`make unit-tests` runs the minimal program on the ten (`PlatformTestIntegrated` to `PlatformFpgaUartPins` of `tests.json`), which stores `0x5A` at the RAM base, reads it back, adds 1 and stores the result in the next word. The test reads the base and the side of the RAM from the generics of the top, so the same check holds for all of them.

| `tests.json` entry | What it checks |
| :--- | :--- |
| `Platform<Name>` (ten) | The two words of the minimal program, in the RAM of the core or in the external chip |
| `Platform<Name>Board` (5 to 8) | The program reads the switches and buttons that the test drives, writes the display value and reads it back; `o_display_value` and the `HEX0` digit match |
| `PlatformFpgaUartPinsUart` | The program sends `0x55` on TX, the test closes the line back to RX and the program receives the byte with `RX_VALID` |
| `PlatformFpgaUartJtagUart` | The host reads the `H` that the program sends over the Virtual JTAG, delivers a byte and reads the echo plus 1 |

`make check-tops` elaborates the top of each one, `make check-generics` checks that the top declares every `HAS_*` of the package and `make sources-check` checks the generated source lists.
