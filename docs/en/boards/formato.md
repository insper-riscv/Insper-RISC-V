# Board package: board.yaml and pins.yaml

## 1. The package

Each supported board has a folder `boards/<board>/` at the repository root, with two files.

| File | Content | Read by |
| :--- | :--- | :--- |
| `board.yaml` | What the board offers: device, clocks, I/O roles, memories, JTAG chain, capacities | Resource validator, PLL and top generators, JTAG identification |
| `pins.yaml` | Pin, I/O standard, direction and certainty seal of each signal | Pin generator |

`board.yaml` names signals only. Pin numbers and I/O standards exist only in `pins.yaml`, and the organization and timings of a memory chip exist only in the chip catalog. Neither file repeats what the other holds.

## 2. board.yaml fields

| Field | Meaning |
| :--- | :--- |
| `board`, `name` | Identifier (equal to the folder name) and commercial name |
| `family` | `cyclone-v`, `cyclone-v-soc`, `cyclone-iv-e`, `max-10` or `cyclone-10-lp` |
| `device`, `speed_grade` | Full device and the grade contained in it (`C7`) |
| `target_level` | Target support level, from `N0` (project synthesized) to `N4` (ACT4 conformance on the board) |
| `jtag.cable` | `usb-blaster`, `usb-blaster-ii`, `samd21-usbblaster` or `external` |
| `jtag.cable_name` | Name `jtagconfig` gives the cable, without the port suffix, when it is not the default |
| `jtag.usb` | USB IDs (`vid:pid`) used to recognize the cable before a chain exists |
| `jtag.chain` | Chain devices, in order. Each has `name`, `idcode` (8 hexadecimal digits), `confirmed` and `fpga: true` (exactly one) or `hps: true` |
| `jtag.samd21`, `jtag.external_pads` | Only for `samd21-usbblaster`: the sketch that exposes the emulated cable and the JTAG pads for an external cable |
| `resources` | `logic`, `block_ram`, `multipliers`, `plls`, `user_pins` (`null` when the capacity is unknown) |
| `clocks.inputs`, `clocks.reference`, `clocks.reset` | Input clocks (`name`, `signal`, `mhz`), the one that feeds the PLL, and the user reset with polarity |
| `io.<role>` | Roles `leds`, `switches`, `keys`, `display` and `leds_green`, each with `signals` and `active` (`high` or `low`), and the general-use roles `gpio`, `ex_io`, `hsmc` and `clock_extra`, with no polarity, with `signals` (one group or a list of groups, numbered in list order) and `bidirectional: true` when the pins are I/O |
| `memories` | `sdram`, `sram`, `nor`, `onchip_flash` and `serial_flash`, each with the catalog chip and the signals |
| `buses` | Pin roles of the external peripherals (section 2.3), one per role, with the signal of each role pin |
| `console` | `default: jtag` (JTAG UART) and `uart: {rx, tx}` only when the board has a UART on pins |
| `pins` | Path of `pins.yaml` |
| `notes` | Board pitfalls, in short prose |

The `confirmed` field of the chain and of the USB IDs uses the seals of `pins.yaml` plus `measured`, for what was read from a real cable.

### 2.1. Signal references

The `signals` fields of the I/O roles, clocks and UART use names from `pins.yaml`.

| Form | Expands to |
| :--- | :--- |
| `CLOCK_50` | The signal of that name |
| `LEDR[9:0]` | `LEDR[9]` to `LEDR[0]` |
| `HEX[5:0][6:0]` | `HEX5[6]` to `HEX0[0]`: the first range is the index in the name, the second is the bit |

In `memories.<type>.signals` the value is a prefix (or a list of prefixes) without the trailing underscore. `DRAM` matches `DRAM_ADDR[0]`, `DRAM_CLK` and every name that starts with `DRAM_`; on the Vidor, `[oSDRAM, bSDRAM]` matches the `oSDRAM_*` and `bSDRAM_*` signals.

### 2.2. Resource units

| Family | Logic | Multipliers |
| :--- | :--- | :--- |
| `cyclone-v`, `cyclone-v-soc` | `alm` | `dsp_block` (the DSP block, as the Quartus counts it) |
| `cyclone-iv-e`, `max-10`, `cyclone-10-lp` | `le` | `dsp9x9` (9-bit elements) |

No unit converts into another by a fixed factor.

### 2.3. Pin roles of the external peripherals

The `buses` key ties each external peripheral of the platform (a `kind` of `Peripherals`) to the signals of `pins.yaml`. Each key is a role, and the value is a mapping from role pin to signal, or a list of mappings when the board has more than one copy (the two PS/2 channels, the two Ethernet PHYs). The signal accepts the bus form of section 2.1 (`"SD_DAT[3:0]"`).

| Role | Role pins | `chip` key |
| :--- | :--- | :--- |
| `ps2` | `clk`, `dat` | No |
| `sd` | `clk`, `cmd`, `dat` | No |
| `lcd` | `data`, `rs`, `rw`, `en`, `power`, `blon` (optional) | No |
| `i2c` | `scl`, `sda` | No |
| `audio` | `xck`, `bclk`, `adclrck`, `adcdat`, `daclrck`, `dacdat` | No |
| `eth` | `rx_clk`, `rxd`, `rx_dv`, `rx_er`, `tx_clk`, `txd`, `tx_en`, `tx_er`, `mdc`, `mdio`, `int_n` (optional), `rst_n` | No |
| `hdmi` | `d`, `clk`, `de`, `hs`, `vs`, `int`, `scl`, `sda` | No |
| `tv` | `data`, `clk27`, `reset_n` | No |
| `usb` | `addr`, `data`, `cs_n`, `rd_n`, `wr_n`, `rst_n`, `int` | No |
| `ir` | `rxd` | No |
| `adc` | Depends on the chip: `adc128s022` (`cs_n`, `sclk`, `saddr`, `sdat`), `ltc2308` (`convst`, `sck`, `sdi`, `sdo`), `max10` (none) | Yes, required |
| `adxl345` | `cs_n`, `sclk`, `mosi`, `miso` (optional), `int1` (optional) | No |

Video is not in `buses`; it is the `io.video` role. A board that declares in `buses` a role with FPGA-side pins only leaves out what sits on the HPS, and the `adxl345` role of the DE0-Nano uses `I2C_SCLK` and `I2C_SDAT` as `sclk` and `mosi`, because `G_SENSOR_CS_N` low selects the three-wire SPI mode on the same pins as the I2C.

### 2.4. Seal of the pins read only from the manual

The `manual` seal of a pin means the pin number was read from a manual table. The DE2-115 pins of PS/2, audio, Ethernet, TV, USB and IR carry in `note` that the bank and the voltage were not checked against the schematic, and none was measured on the board.

## 3. pins.yaml fields

| Field | Meaning |
| :--- | :--- |
| `board`, `device` | Equal to those of `board.yaml` |
| `signals[].name` | Signal name; buses carry the index in brackets (`LEDR[3]`) |
| `signals[].pin` | Device pin, without prefix (`M9`) |
| `signals[].io_standard` | Quartus I/O standard |
| `signals[].direction` | `in`, `out` or `inout` |
| `signals[].source` | Where the pin was read (manual table, `.qsf` line, third-party source) |
| `signals[].confirmed` | `manual` (read in the manual), `repo` (read in the repository `.qsf`) or `inferred` (third-party source) |
| `signals[].note` | Polarity, jumper or other caveat |
| `conflicts` | Pins assigned to more than one signal: `{pin, signals, note?}` |
| `notes` | Board remarks |

A pin may appear in two signals only if it is listed in `conflicts`. The Tools refuse to build with an `inferred` pin unless `--accept-inferred-pins` is given.

## 4. Example

```yaml
board: de0-cv
family: cyclone-v
device: 5CEBA4F23C7
jtag:
  cable: usb-blaster
  chain: [{name: "5CE(BA4|FA4)", idcode: "02B050DD", fpga: true, confirmed: measured}]
clocks:
  inputs: [{name: clock_50, signal: CLOCK_50, mhz: 50}]
  reference: clock_50
  reset: {signal: FPGA_RESET_N, active: low}
io:
  leds: {signals: "LEDR[9:0]", active: high}
memories:
  sdram: {chip: IS42S16320D-7, chips: 1, signals: DRAM, clk_phase_ps: 4000}
```

The board table and the target level of each one are in [placas.md](placas.md).
