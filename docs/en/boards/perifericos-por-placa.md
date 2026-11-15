# External peripherals by board

## 1. Declared roles

Each board describes in `board.yaml` the pins the FPGA reaches, by I/O role (`io`) and by external peripheral role (`buses`, see [formato.md](formato.md)). The table shows what each package declares.

| Board | `io` roles | `buses` roles |
| :--- | :--- | :--- |
| `de0-cv` | `leds`, `switches`, `keys`, `display`, `gpio`, `clock_extra`, `video` (4-bit VGA) | `ps2` (2), `sd` |
| `de2-115` | `leds`, `leds_green`, `switches`, `keys`, `display`, `gpio`, `ex_io`, `hsmc`, `clock_extra`, `video` (8-bit ADV7123) | `ps2` (2), `sd`, `lcd`, `i2c` (2), `audio`, `eth` (2), `tv`, `usb`, `ir`, `serial` |
| `de0-nano` | `leds`, `switches`, `keys`, `gpio` | `adc` (ADC128S022), `adxl345`, `i2c` |
| `de10-lite` | `leds`, `switches`, `keys`, `display`, `gpio`, `clock_extra`, `video` (4-bit VGA) | `adxl345`, `adc` (internal to the MAX 10) |
| `de10-nano` | `leds`, `switches`, `keys`, `gpio`, `clock_extra`, `video` (HDMI ADV7513) | `hdmi`, `hdmi_audio`, `adc` (LTC2308) |
| `de0-nano-soc` | `leds`, `switches`, `keys`, `gpio`, `clock_extra` | `adc` (LTC2308) |
| `mkr-vidor-4000` | `gpio` | `i2c`, `spi`, `serial` |

## 2. New roles in this version

| Board | Role | Signals | Source |
| :--- | :--- | :--- | :--- |
| `de2-115` | `serial` | `UART_RXD`, `UART_TXD`, `UART_CTS`, `UART_RTS` | Manual, section 4.12, table 4-18 |
| `de10-nano` | `hdmi_audio` | `HDMI_MCLK`, `HDMI_SCLK`, `HDMI_LRCLK`, `HDMI_I2S0` | Manual, section 3.6.5, table 3-13 |
| `mkr-vidor-4000` | `gpio` | `bMKR_D[14:0]`, `bMKR_A[6:0]` and the 25 `PEX` nets of the FPGA | ABX00022 datasheet (section 1.2), pinout and schematic |
| `mkr-vidor-4000` | `i2c` | SDA on `bMKR_D[11]`, SCL on `bMKR_D[12]` | ABX00022-pinout.pdf (SERCOM 2 of the SAMD21) |
| `mkr-vidor-4000` | `spi` | COPI on `bMKR_D[8]`, SCK on `bMKR_D[9]`, CIPO on `bMKR_D[10]`, select on `bMKR_D[7]` | ABX00022-pinout.pdf (SERCOM 1 of the SAMD21); the select is a project choice |
| `mkr-vidor-4000` | `serial` | RX on `bMKR_D[13]`, TX on `bMKR_D[14]` | ABX00022-pinout.pdf (SERCOM 5 of the SAMD21) |

The Vidor `gpio` role numbers `bMKR_D[14:0]` from 0 to 14, `bMKR_A[6:0]` from 15 to 21 and the `PEX` nets from 22 to 46, in the order of the connector pin number. The analog reference `bMKR_AREF` is left out because it belongs to the SAMD21, and the nets `PEX_PIN1`, `PEX_PIN3`, `PEX_PIN5` and `PEX_PIN7` are left out because the Wi-Fi module uses them as `bWM_PIO2`, `bWM_PIO3`, `bWM_PIO4` and `bWM_PIO34`.

## 3. Pins without a role

The pins below are in `pins.yaml` with a seal and a source, and have no role in `board.yaml`, because the role registry of the Tools has no role that describes them.

| Board | Pins | Role the Tools lack |
| :--- | :--- | :--- |
| `de10-lite` | `HEX0[7]` to `HEX5[7]` (decimal point, section 3.4, table 3-6) | Display with eight segments per digit; the `display` role has seven |
| `de0-nano` | `GPIO_0_IN[1:0]`, `GPIO_1_IN[1:0]` and `GPIO_2_IN[2:0]` | Input-only GPIO; the `gpio` block uses a bidirectional cell |
| `de2-115` | `OTG_DREQ` and `OTG_DACK`, which the manual does not list | None, because the board has no such signals |
| `mkr-vidor-4000` | `oHDMI_TX[2:0]` and `oHDMI_CLK` (direct TMDS), `iMIPI_*`, `bMIPI_*` and `bWM_*` | Direct-TMDS `hdmi`, MIPI camera and Wi-Fi bridge |

The USB of the DE2-115 is the HPI interface of the CY7C67200, so DMA access to the internal memory of the chip goes through the data bus of table 4-25 itself, and the board carries no DMA request or acknowledge pins.

## 4. Seals of the new pins

| Seal | When it holds | New pins |
| :--- | :--- | :--- |
| `manual` | The pin number was read in a manual table or in the board document | The Vidor `bMKR_*` pins (ball checked on the pinout) and `bPEX_*` and `iPEX_*` (ball checked on the schematic) |
| `repo` | The pin was read in the `.qsf` of the repository | No new pin |
| `inferred` | The pin came from a third-party source | No new pin |
| `measured` | The pin was read from a real board | No new pin |

The I/O standard of the Vidor pins follows the 3.3 V of the datasheet, and the choice of `3.3-V LVTTL` among the 3.3 V standards of Quartus is the project's. The direction of `iPEX_*` comes from the `.qsf`, and the schematic does not confirm it.

## 5. Example platforms

Each board has in `src/periph-examples/<board>/` a platform that requests the external peripherals of its package, with absolute `base` and no overlap. All of them start from the calibration platform of the board (full profile, FLASH and RAM emulated in blocks) and add the `gpio` block and the external peripherals.

| Platform | External peripherals (name, `kind`, `base`) |
| :--- | :--- |
| `de0-cv-periph` | `KBD` and `MOUSE` (`ps2`, `0x80007000` and `0x80007100`), `SD` (`sd_native`, `0x80008000`) |
| `de2-115-periph` | `KBD`, `MOUSE`, `SD`, `IR` (`0x80009000`), `LCD` (`0x8000A000`), `USB` (`0x8000B000`), `I2C0` and `I2C1` (`0x8000C000` and `0x8000C100`), `AUDIO` (`0x8000D000`), `ETH0` and `ETH1` (`0x8000E000` and `0x8000E100`), `TV` (`0x8000F000`), `SERIAL` (`uart`, `0x80220000`) |
| `de0-nano-periph` | `ADC0` (`adc` ADC128S022, `0x80010000`), `ACCEL` (`adxl345` on three-wire SPI, `0x80012000`) |
| `de10-lite-periph` | `ADC0` (internal `adc`, `0x80010000`), `ACCEL` (`adxl345` on four-wire SPI, `0x80012000`) |
| `de10-nano-periph` | `ADC0` (`adc` LTC2308, `0x80010000`), `HDMI` (`hdmi`, `0x80200000`), `HDMI_AUDIO` (`hdmi_audio`, `0x80240000`) |
| `de0-nano-soc-periph` | `ADC0` (`adc` LTC2308, `0x80010000`) |
| `mkr-vidor-4000-periph` | `I2C0` (`0x8000C000`), `SPI0` (`spi`, `0x80011000`), `SERIAL` (`uart`, `0x80220000`) |

Every platform also has the `GPIO` block (`gpio` of the `gpio` role, `0x80001000`). On the Vidor it gathers `D0` to `D6`, `A0` to `A6` and the Mini PCI Express in three groups. The window of `hdmi` is 256 KiB, and the `base` of each peripheral is a multiple of its window size.

## 6. Shared pins

A pair of pins that two roles use at once has one owner per platform, because two masters on the same wire corrupt the bus.

### 6.1. DE0-Nano, EEPROM and ADXL345

`I2C_SCLK` (`F2`) and `I2C_SDAT` (`F1`) connect the EEPROM (section 3.4, write and read addresses `0xA0` and `0xA1`) and the ADXL345 (section 3.7, table 3-10). The level of `G_SENSOR_CS_N` selects the accelerometer mode.

| `G_SENSOR_CS_N` | ADXL345 mode | Package role | Use of `I2C_SCLK` and `I2C_SDAT` |
| :--- | :--- | :--- | :--- |
| Low | Three-wire SPI | `adxl345` | SPI SCLK and MOSI |
| High | I2C | `i2c` | SCL and SDA of the bus |

In a platform, the `adxl345` peripheral and the `i2c` peripheral do not coexist. With the `adxl345` on three-wire SPI, the accelerometer is the only master of the pins and the EEPROM is not accessed. To use the EEPROM, the platform requests only the `i2c` peripheral and keeps `G_SENSOR_CS_N` high, and the accelerometer is read by that master only if the platform addresses it with the value the ADXL345 datasheet defines, which the board manual does not give.

### 6.2. DE2-115, codec and TV decoder

`I2C_SCLK` and `I2C_SDAT` configure the WM8731 (section 4.11) and the ADV7180 (section 4.15), and sit on the second copy of the `i2c` role. The platform uses a single `i2c` peripheral on that copy, and the EEPROM has the first copy (`EEP_I2C_SCLK` and `EEP_I2C_SDAT`, section 4.19).

### 6.3. DE10-Nano, HDMI

`I2C_SCL` and `I2C_SDA` configure the ADV7513 and belong to the `hdmi` role. The `hdmi_audio` role carries only the output I2S audio and does not use that bus, and the `hdmi` peripheral also loads the audio register table (`audio_init_table`).

### 6.4. Vidor, header and gpio block

The `i2c`, `spi` and `serial` pins of the Vidor are also pins of the `gpio` role. The `mkr-vidor-4000-periph` platform uses each pin in one role only, and its `gpio` block leaves out indexes 7 to 14 (`D7` to `D14`), which `spi`, `i2c` and `serial` occupy.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
