# Supported boards

## 1. Table

Each board has its package in `boards/<board>/` and a research sheet in `Plans/Multi-FPGA/placas/<board>.md` of the Capstone repository, with the source and seal of each fact. The package format is in [formato.md](formato.md).

| Board | Device | Family | IDCODE | Cable | Memory outside the FPGA | Target level |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| `de0-cv` | 5CEBA4F23C7 | `cyclone-v` | `02B050DD` | USB-Blaster | SDRAM 64 MB, 16 bits | N4 |
| `de2-115` | EP4CE115F29C7 | `cyclone-iv-e` | `020F70DD` | USB-Blaster | SDRAM 128 MB (2 x 16 bits), SRAM 2 MB, NOR FLASH 8 MB | N4 |
| `de0-nano` | EP4CE22F17C6 | `cyclone-iv-e` | `020F30DD` | USB-Blaster | SDRAM 32 MB, EPCS64 | N3 |
| `de10-lite` | 10M50DAF484C7G | `max-10` | `031050DD` | USB-Blaster | SDRAM 64 MB, internal FLASH (UFM) | N3 |
| `de10-nano` | 5CSEBA6U23I7 | `cyclone-v-soc` | `4BA00477` (HPS) and `02D020DD` | USB-Blaster II | none on the fabric (DDR3 belongs to the HPS) | N2 |
| `mkr-vidor-4000` | 10CL016YU256C8G | `cyclone-10-lp` | `020F10DD` (inferred) | SAMD21 with USBBlaster sketch | SDRAM 8 MB, QSPI 2 MB | N1 |

## 2. Differences in handling

| Board | What changes |
| :--- | :--- |
| `de2-115` | The IDCODE is shared with the 10CL120 and the EP3C120; KEY, SW and some HEX follow jumper JP7 (factory 2.5 V), and the only UART on pins (RS-232) is in `console.uart` |
| `de0-nano`, `de10-lite` | No UART and no dedicated reset; the reset is `KEY[0]` |
| `de10-nano` | The chain has two devices (HPS and FPGA); the cable is identified by the name `DE-SoC` and the USB IDs `09fb:6010` and `09fb:6810` |
| `mkr-vidor-4000` | USB reaches only the SAMD21 (`2341:8056`); the emulated cable needs the `USBBlaster` sketch on the SAMD21, and the JTAG pads for an external cable are not soldered. Seven pins are assigned to two signals in the official `.qsf` and are listed in `conflicts` |

## 3. Console

Every board declares `console.default: jtag`: the console is the JTAG UART over the programming cable. A UART on pins exists only on the `de2-115`.
