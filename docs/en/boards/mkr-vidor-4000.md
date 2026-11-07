# Arduino MKR Vidor 4000

## 1. Reference

The package of the board is in `boards/mkr-vidor-4000/` and the research sheet in `Plans/Multi-FPGA/placas/mkr-vidor-4000.md` of the Capstone repository. The hardware sources are the schematic `ABX00022-schematics.pdf`, the datasheet and the official `.qsf` of VidorBitstream, all cited in the sheet. The package format is in [formato.md](formato.md).

| Item | Value |
| :--- | :--- |
| FPGA | Cyclone 10 LP `10CL016YU256C8G` |
| IDCODE | `020F20DD`, the same as the EP3C16, read from the Quartus device database |
| External memory | 8 MB AS4C4M16SA-7BCN SDRAM and 2 MB W25Q16DV QSPI FLASH |
| Clock and reset | `iCLK` (48 MHz, pin E2) and `iRESETn` (pin E1) |

The SDRAM has 12 address bits (`A0` to `A11`), 4 banks (`BS0` and `BS1`) and 16 data bits, and the FLASH holds the bitstream of the board, of which 1 MB belongs to the user.

## 2. Pins of the official `.qsf` resolved by the schematic

The official `.qsf` assigned each of seven pins to two signals. The net that the schematic wires to each pin decides, and the signal with no net on that pin leaves `pins.yaml` (`conflicts` stays empty).

| Pin | Schematic net | Signal kept | Signal removed |
| :--- | :--- | :--- | :--- |
| L4 | `PANEL_SDA` | `bHDMI_SDA` | `panel_en` |
| R4 | `WM_PIO35` | `bWM_PIO35` | `bWM_PIO17` (goes to a resistor) |
| T4 | `WM_PIO31` | `bWM_PIO31` | `bWM_PIO16` (goes to a resistor) |
| R5 | `WM_PIO20` | `bWM_PIO20` | `iWM_RTS` |
| R6 | `WM_PIO21` | `bWM_PIO21` | `iWM_CTS` |
| R7 | `CFG_HOLD` | `oFLASH_HOLD` | `bWM_PIO25` |
| T7 | `CFG_WP` | `oFLASH_WP` | `bWM_PIO24` |

Four pins keep the `.qsf` name with a net of another name in the schematic: `bWM_PIO2`, `bWM_PIO3`, `bWM_PIO4` and `bWM_PIO34` are on R10, P11, R11 and M6, which the schematic wires to `PEX_PIN1`, `PEX_PIN3`, `PEX_PIN5` and `PEX_PIN7`. The pin is the same and stays `inferred`.

## 3. JTAG chain and cable

The USB of the board connects only to the SAMD21 (`2341:8056`, CDC serial port). The JTAG of the FPGA sits behind it, and there are two ways.

| Way | Cable | `jtagconfig` |
| :--- | :--- | :--- |
| Emulated | The `USBBlaster` sketch on the SAMD21 makes the USB look like a USB-Blaster | `USB-Blaster [bus-port]` with `020F20DD` |
| External | A 10-pin USB-Blaster on the `J11` connector | The same |

### 3.1. Connector J11

`J11` is a 2x5 Samtec FTSH-105-01-F-D-K with 1.27 mm pitch, and the pads come unsoldered.

| Pin | Signal | Pin | Signal |
| :---: | :--- | :---: | :--- |
| 1 | `+3V3` | 2 | `TMS` |
| 3 | `GND` | 4 | `TCK` |
| 5 | `GND` | 6 | `TDO` |
| 7 | not connected | 8 | `TDI` |
| 9 | `GND` | 10 | not connected |

The four `JTAG.CPORT_*` nets join the connector, the SAMD21 (`TMS` on PA14, `TDI` on PA12, `TCK` on PA13 and `TDO` on PA15) and the JTAG pins of the FPGA (`TMS` on J5, `TCK` on H3, `TDO` on J4 and `TDI` on H4). With an external cable, the SAMD21 stays in bootloader mode (double tap on reset) so that it does not fight for the lines.

## 4. Board detection

Tools recognizes the board by the USB of the SAMD21 before any JTAG chain exists, because `2341:8056` is in `jtag.usb` of the package.

| Command | What it shows |
| :--- | :--- |
| `riscv-tools board scan` | A block `usb 2341:8056 board: mkr-vidor-4000` with the state "no chain" |
| `riscv-tools board doctor` | The `MKR Vidor 4000` warning with the instructions of section 5 |

With the sketch running the SAMD21 reappears as a USB-Blaster, the ID `2341:8056` disappears, and the board is identified by the chain IDCODE like the others.

## 5. Instructions for the USBBlaster sketch

The tools do not write the sketch to the SAMD21, because a wrong write can ruin the USB path. The user loads the sketch with the Arduino IDE.

1. Install the `Arduino SAMD Boards` core at version 1.6.25 or later.
2. Choose the `Arduino MKR Vidor 4000` board and the serial port of the SAMD21.
3. Open the `USBBlaster` example of the library of the same name and upload it.
4. Check with `jtagconfig`, which must list a `USB-Blaster` with IDCODE `020F20DD`.
5. To use the SAMD21 as an Arduino again, upload another sketch with the IDE.

The exact name of the example in the IDE comes from the board sheet and must be checked on the first upload. The `.sof` loaded over JTAG is volatile and disappears when the board is powered off.

## 6. Support levels

| Level | Criterion | What holds for the board |
| :--- | :--- | :--- |
| N0 | `board generate` and `quartus_map` without error | The device is accepted by Quartus in the M.0 measurements |
| N1 | Fit and timing analysis | Target of the package |
| N2 | Live board | Needs the emulated or external cable working |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
