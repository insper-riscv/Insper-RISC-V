# Installing DOOM on the DE0-CV

🌐 [Português](../../pt-br/platform/doom-instalacao.md) · [English](doom-instalacao.md)

This guide takes the DE0-CV, with the microSD card prepared, to running DOOM from a Linux computer with Docker. It covers the side of the `doom` platform whose FLASH is a window of the SDRAM: compiling the `.sof`, programming the FPGA and writing the game. Building `doom.bin` and preparing the card are in the `docs/en/INSTALL.md` guide of the [DOOM](https://github.com/insper-riscv/DOOM) repository, and section 2 sums up what is needed from it here.

## 1. How the game reaches the board

The `doom` platform executes code from the SDRAM. The FLASH is the instruction window, 4 MiB at the top of the SDRAM chip, with base `0x1000` in the core map and offset `0x3C01000` inside the chip. The BOOT_MEMORY jumps straight to `0x1000`, so there is no loader.

| Step | What happens |
| :--- | :--- |
| 1 | The `.sof` configures the FPGA; the core comes up, the SDRAM initializes and `0x1000` is empty |
| 2 | A program on the computer writes `doom.bin` to the FLASH window, through the SDRAM debug port (Virtual JTAG instance 3), and reads everything back to check it |
| 3 | The `.sof` is programmed again; the core restarts, the BOOT jumps to `0x1000` and the game comes up |

The FPGA configuration and the SDRAM are lost at every power-off, so the three steps repeat every time the board is turned on.

## 2. Files needed

| File | How to get it |
| :--- | :--- |
| `doom_de0_cv.sof` | Section 4 |
| `doom.bin` (FatFs version) | `PLATFORM_DIR=platform_doom SDFS=fatfs MENU=1 VIDEO=1 INTERACTIVE=1 SD=demand ONDEMAND=1 sh scripts/image.sh`, at the root of the DOOM repository |
| `load_flash.py` | Section 6, in the same repository as `scripts/load_flash.py` |
| microSD card | FAT32 with `DOOM.WAD`, `DOOM2.WAD`, `PLUTONIA.WAD`, `TNT.WAD` and the `MASTER/` folder, 8.3 names |

The `.sof` and the `doom.bin` form a pair and are not mixed with files of another platform version. An exFAT card shows no game in the menu, because the game reads only FAT12, FAT16 and FAT32.

## 3. Preparing the computer

| Item | Requirement |
| :--- | :--- |
| Docker | Working, with the `default` context |
| Image | `ghcr.io/insper-riscv/dev_tools:latest`, which brings `uv` and Python 3.14 |
| Quartus Prime Lite 25.1 | Installed in `/opt/altera_lite`, with `quartus_pgm` and `jtagconfig` on the `PATH` |
| USB-Blaster | udev rule installed and the cable reconnected after it |
| Network | Access to `github.com`, because the write downloads the Tools at commit `f7ea593` |

```bash
sudo udevadm control --reload-rules && sudo udevadm trigger
```

The computer's Python is not used. Every Python command runs inside the container.

## 4. Compiling the `.sof`

At the root of this repository, with the `doom` platform in `src/cyclone-v/doom/`:

```bash
docker -c default run --rm --network host \
  -v /opt/altera_lite:/opt/altera_lite:ro -v "$PWD":/w -w /w \
  -e HOME=/tmp -u "$(id -u):$(id -g)" ghcr.io/insper-riscv/dev_tools:latest sh -c \
  'export PATH="$PATH:/opt/altera_lite/25.1std/quartus/bin"; \
   riscv-tools --root . --config src/cyclone-v/doom/config.yaml program --compile-only --seed 6'
```

The `.sof` comes out as `build/doom-de0-cv/output_files/doom_de0_cv.sof`, after 7 to 10 minutes. `doom_de0_cv.sta.summary`, in the same folder, lists the setup slack of each clock, and all of them must be positive. The core and the fetch run at 100 MHz and the SDRAM at 125 MHz.

## 5. Finding the cable

1. Connect the power supply, the USB-Blaster cable, the VGA monitor, the PS/2 keyboard and the microSD card, and turn the board on.
2. List the cables.

```bash
jtagconfig
```

The DE0-CV shows up with IDCODE `02B050DD` (`5CE(BA4|FA4)`). Keep the cable name from that line, for example `USB-Blaster [3-6]`, because the number changes between computers and after a restart. The DE2-115 has IDCODE `020F70DD` and never receives this `.sof`.

## 6. Writing the game

The three steps use the same cable name. Only one computer programs the board at a time.

1. Program the FPGA.

```bash
quartus_pgm -c "USB-Blaster [3-6]" -m jtag -o "p;build/doom-de0-cv/output_files/doom_de0_cv.sof@1"
```

2. Write `doom.bin`. The program below, saved as `load_flash.py` (it already exists in the DOOM repository as `scripts/load_flash.py`), writes the image starting at `0x1000` and reads everything back.

```python
import sys
from pathlib import Path
from riscv_tools import ram_load
from riscv_tools.jtag import JtagLink

link = JtagLink(hardware_name=sys.argv[2], device_name="@1: 5CE(BA4|FA4) (0x02B050DD)", sdram_instance=3)
FLASH_BASE, CHIP_BYTE = 0x1000, 0x3C01000
seg = ram_load.segment_from_file("flash", Path(sys.argv[1]), FLASH_BASE)
ram_load.load_ram(link, [seg], FLASH_BASE, None,
                  ram_load.LoadOptions(verify=True, chip_words=CHIP_BYTE // 4, report=print))
```

With `doom.bin` and `load_flash.py` in the current folder, the write takes about 5 minutes and ends with `flash: conferido`.

```bash
docker -c default run --rm --network host \
  -v /opt/altera_lite:/opt/altera_lite:ro -v "$PWD":/g:ro -w /tmp \
  -e HOME=/tmp -e UV_CACHE_DIR=/tmp/uvc -e RV32_SDRAM_DEBUG_INSTANCE=3 \
  -u "$(id -u):$(id -g)" ghcr.io/insper-riscv/dev_tools:latest sh -c \
  'export PATH="$PATH:/opt/altera_lite/25.1std/quartus/bin"; \
   uv run --no-project --python 3.14 \
     --with "git+https://github.com/insper-riscv/Tools.git@f7ea593" \
     python /g/load_flash.py /g/doom.bin "USB-Blaster [3-6]"'
```

| Part of the command | Effect |
| :--- | :--- |
| `--network host` | The container reaches the computer's `jtagd` |
| `-v /opt/altera_lite:...:ro` | Gives the container the `quartus_stp` that the write uses |
| `RV32_SDRAM_DEBUG_INSTANCE=3` | Points to the SDRAM debug port; without it the write does not find the port |
| `--python 3.14` | Without it `uv` picks Python 3.15 and the cocotb build fails |
| `@f7ea593` | Tools version whose debug port matches this `.sof` |

3. Program the `.sof` again, with the same command as step 1. The second programming resets the core, and the BOOT jumps to `0x1000`, where the game is already written.

The DOOM menu shows on the monitor. Pick the game with the arrows or with `W` and `S`, and confirm with `Enter`, `E` or space.

## 7. Checking that the board is alive

Reading one SDRAM word only answers if the FPGA is configured.

```bash
docker -c default run --rm --network host -v /opt/altera_lite:/opt/altera_lite:ro \
  -e HOME=/tmp -e RV32_SDRAM_DEBUG_INSTANCE=3 -u "$(id -u):$(id -g)" \
  ghcr.io/insper-riscv/dev_tools:latest sh -c \
  'export PATH="$PATH:/opt/altera_lite/25.1std/quartus/bin"; \
   quartus_stp -t /opt/riscv-tools/riscv-tools/lib/python3.14/site-packages/riscv_tools/jtag/tcl/sdram_dbg.tcl \
   "USB-Blaster [3-6]" "@1: 5CE(BA4|FA4) (0x02B050DD)" read 15860736 1'
```

If the command fails, the FPGA lost its configuration and the three steps of section 6 are repeated.

## 8. If something does not work

| Symptom | Likely cause | What to do |
| :--- | :--- | :--- |
| `jtagconfig` does not list the board | udev rule missing or loose cable | Section 3 and reconnect the cable |
| `load-flash: this bitstream has no hold and CRC` | The write was made with `riscv-tools load-flash`, which asks for an `INFO` word that the debug port of this `.sof` does not have | Write with `load_flash.py`, as in section 6 |
| Error `cocotb ... maximum Python version of 3.14` | `uv` picked Python 3.15 | Keep `--python 3.14` |
| `the SDRAM is not initialized` | Wrong Virtual JTAG instance | Export `RV32_SDRAM_DEBUG_INSTANCE=3` |
| Black screen after step 3 | Image not written or a check error | Repeat step 2 and read the check message |
| Menu with no game | The card is not FAT32 or was not detected | Section 2 |
| Game hangs right after the menu | `.sof` and `doom.bin` from different versions | Redo section 4 and the `doom.bin` from the same commit |

## 9. Precautions

1. Before using the board, take its lock, so that no other process programs it in the middle of the steps. The lock is one file per board, such as `/tmp/de0cv-<machine>.lock`.

```bash
exec 9>/tmp/de0cv-laptop.lock && flock -w 60 9
```

2. Do not run someone else's `quartus_pgm` or `quartus_stp` at the same time.
3. A service that reprograms the FPGA by itself must be stopped, or have the cable disconnected from it, before the cable is used on another computer.
