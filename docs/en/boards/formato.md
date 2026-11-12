# Board package: board.yaml and pins.yaml

## 1. The package

Each supported board has a folder `boards/<board>/` at the repository root, with two files.

| File | Content | Read by |
| :--- | :--- | :--- |
| `board.yaml` | What the board offers: device, clocks, I/O roles, memories, JTAG chain, capacities | Resource validator, PLL and top generators, JTAG identification |
| `pins.yaml` | Pin, I/O standard, direction and certainty seal of each signal | Pin generator |

`board.yaml` names signals only. Pin numbers and I/O standards exist only in `pins.yaml`, and the organization and timings of a memory chip exist only in the chip catalog. Neither file repeats what the other holds. The timing of each video mode lives in a single catalog, `boards/video-modes.yaml`, shared by all boards (section 4.3).

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
| `io.<role>` | Roles `leds`, `switches`, `keys` and `display`, each with `signals` and `active` (`high` or `low`), and the `video` role, described in section 4 |
| `memories` | `sdram`, `sram`, `nor`, `onchip_flash` and `serial_flash`, each with the catalog chip and the signals |
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

## 4. The video role

The `io.video` role declares the board's video output. Boards without a video output do not have it.

### 4.1. Fields

| Field | Meaning |
| :--- | :--- |
| `kind` | `vga` (analog DAC, with or without a chip) or `hdmi` (digital transmitter fed with parallel RGB) |
| `channel_bits` | Bits per color channel delivered to the board, `4` or `8` |
| `signals` | Prefix of the video signals in `pins.yaml`, without the trailing underscore |
| `default_mode` | Mode used when the platform asks for none; it must be listed in `modes` |
| `modes` | Modes the board manual specifies or the output chip supports; each name exists in `boards/video-modes.yaml` |

### 4.2. Signals by output kind

The `signals` prefix matches every signal of `pins.yaml` that starts with it.

| `kind` | Prefix | Expected signals |
| :--- | :--- | :--- |
| `vga` with a resistor DAC | `VGA` | `VGA_R[n]`, `VGA_G[n]`, `VGA_B[n]`, `VGA_HS`, `VGA_VS` |
| `vga` with an integrated DAC (ADV7123) | `VGA` | The above plus `VGA_CLK`, `VGA_BLANK_N` and `VGA_SYNC_N` |
| `hdmi` (ADV7513) | `HDMI_TX` | `HDMI_TX_D[n]` (24 bits), `HDMI_TX_DE`, `HDMI_TX_HS`, `HDMI_TX_VS`, `HDMI_TX_CLK` and `HDMI_TX_INT` |

Each color bus has `channel_bits` wires in the `vga` kinds. In `hdmi`, the transmitter takes 24 bits and `channel_bits` says how many bits of each channel the content uses. The HDMI transmitter is configured through an I2C bus that sits outside the prefix (`I2C_SCL` and `I2C_SDA` on the DE10-Nano) and appears in `pins.yaml` like any other signal.

### 4.3. Mode catalog

The file `boards/video-modes.yaml` holds the timing of each mode, and a mode name has the form `<width>x<height>@<refresh in Hz>`.

| Field | Meaning |
| :--- | :--- |
| `width`, `height`, `refresh_hz` | Visible area in pixels and refresh rate |
| `aspect` | Reduced aspect ratio of the visible area (`4:3`, `16:9` or `5:4`) |
| `pixel_clock_mhz` | Pixel clock in MHz |
| `horizontal`, `vertical` | Per axis, `sync`, `back_porch`, `visible`, `front_porch`, `total` and `polarity` |
| `source` | Manual table or standard the values come from |

On each axis the total is the sum of the four intervals, and `polarity` is `neg` (active-low pulse) or `pos` (active-high pulse). The horizontal axis counts pixels and the vertical axis counts lines.

$$
\text{total} = \text{sync} + \text{back\_porch} + \text{visible} + \text{front\_porch}
$$

$$
\text{refresh\_hz} \approx \frac{\text{pixel\_clock\_mhz} \cdot 10^{6}}{\text{total}_{h} \cdot \text{total}_{v}}
$$

```yaml
modes:
  640x480@60:
    width: 640
    height: 480
    refresh_hz: 60
    aspect: "4:3"
    pixel_clock_mhz: 25.0
    horizontal: {total: 800, sync: 96, back_porch: 48, visible: 640, front_porch: 16, polarity: neg}
    vertical:   {total: 525, sync: 2, back_porch: 33, visible: 480, front_porch: 10, polarity: neg}
```

### 4.4. Default mode and platform override

`platform.yaml` can ask for another mode in `io.video`, and all three fields are optional.

| Field | Meaning |
| :--- | :--- |
| `width`, `height` | Requested resolution; the mode is looked up in the catalog |
| `aspect` | Requested aspect ratio, `4:3` or `16:9` |

| Platform request | Chosen mode |
| :--- | :--- |
| No `io.video` | The board's `default_mode` |
| Only `aspect` | The largest mode in `modes` with that aspect ratio |
| `width` and `height` | The catalog mode with that resolution |

```yaml
io:
  video:
    width: 1280
    height: 720
    aspect: 16:9
```

The chosen mode must be listed in the board's `modes`, and the requested aspect ratio must match `width` and `height`. A mode outside `modes` is accepted only when the platform marks it explicitly as outside the manual. The pixel clock must be reachable by the board's PLL, the framebuffer must fit in the free memory, and the board's `channel_bits` caps the requested bits per channel.

### 4.5. Examples

```yaml
# DE2-115: 8-bit ADV7123 DAC, five modes
io:
  video: {kind: vga, channel_bits: 8, signals: VGA, default_mode: 640x480@60,
          modes: [640x480@60, 640x480@85, 800x600@60, 1024x768@60, 1280x1024@60]}
```

```yaml
# DE10-Nano: ADV7513 HDMI transmitter, configured through I2C
io:
  video: {kind: hdmi, channel_bits: 8, signals: HDMI_TX, default_mode: 640x480@60,
          modes: [640x480@60, 1024x768@60, 1280x1024@60, 1920x1080@60]}
```

## 5. Example

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
