# Platform `doom`: the code runs from the SDRAM

## 1. What it is

The `doom` platform is the `de0-cv` with the FLASH cut to the minimum and the SDRAM executable. The DOOM binary (the `doomgeneric` port, 363 to 412 KiB with the code, the constants and the initial data) does not fit the FLASH emulated in M10K blocks, because the whole chip has 308 blocks (about 385 KiB). The game code therefore runs from the SDRAM, and the FLASH holds only a loader of a few instructions.

The project comes from `riscv-tools new-project doom --board de0-cv --profile rv32im_zicclsm_zicntr_zihpm_zifencei --rom 8K --ram 64M --icache 32768 --dcache 32768`. The `de0-cv`, its BOOT_MEMORY and its tests do not change.

## 2. Memory map

| Region | Base | Size | Access |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Fetch and read, direct, no cache |
| FLASH, bank A | `0x00001000` | 4 KiB | Fetch and read through the caches, read-only |
| FLASH, bank B | `0x00002000` | 4 KiB | Fetch and read through the caches, read-only |
| SDRAM (`RAM`, `exec: true`) | `0x40000000` | 64 MB | Fetch, read and write through the caches |
| Peripherals | `0x80000000` | 256 MB windows | Read and write, no cache |

The top 4 KiB of the SDRAM (`0x43FFF000` to `0x43FFFFFF`), which the data cache ignores, hold the words shared with the host.

| Word | Address | Use |
| :--- | :--- | :--- |
| `stdout` | `0x43FFFBE0` | Header and buffer of the program output (1 KiB plus 8 bytes) |
| `tohost` | `0x43FFFFE8` | End of the program (HTIF protocol) |
| `fromhost` | `0x43FFFFF0` | Restart by the host |
| `launch` | `0x43FFFFF8` | Doorbell of the FLASH loader |

The BOOT_MEMORY clears `stdout`, `tohost` and `fromhost` at every reset. Only the loader clears `launch`, after it consumes it.

## 3. How the code comes to run from the SDRAM

The BOOT_MEMORY only jumps to a bank whose header and CRC-32 check out, and it does not know an executable SDRAM exists. Bank A therefore holds the program `runtime/doom_loader.S`, 44 bytes long, linked at `0x1100`, which does the following.

1. It polls the `launch` word in a loop. The word is in the last page of the SDRAM, which the data cache ignores, so every read goes to memory.
2. When the word equals `0x4D4F4F44` (the bytes `DOOM`), it writes zero to it, so the next reset waits for a new image instead of running the old one.
3. It executes `fence.i`, which drops the lines that an earlier run left in both caches.
4. It jumps to `0x40000000`, the base of the SDRAM, where the `_start` of DOOM is.

The program enters with `sp`, `gp` and `tp` undefined, like any bank, and the `_start` of the image sets them.

The memory map generator (`riscv-tools generate-memory-map` and `check-memory-map`) accepts the `RAM` region with `exec: true` unchanged, and checks its two conditions, which are the external RAM with the fetch through the core port and the Zifencei extension in the profile, because the instruction cache sits over the SDRAM. The `exec` flag does not change the generated VHDL, which already executes code from the SDRAM in the `de0-cv` tests. `boot.entry` stays in the FLASH, at `0x1000`.

## 4. How to load the binary into the SDRAM

The binary is linked at `0x40000000` with the code, the constants and the initial data in sequence. The WAD (`doom1.wad`) goes to another SDRAM address, above the end of the binary, which the game port defines. The load uses the SDRAM debug port (instance 3 of the Virtual JTAG) while the core runs in the loader.

| Step | Operation |
| :--- | :--- |
| 1 | Write the FLASH with the loader (section 4.1) |
| 2 | Clear the `launch` doorbell, so the loader does not jump over a half-written image |
| 3 | Write the binary image from word 0 of the SDRAM, and the WAD at its address |
| 4 | Write the magic `0x4D4F4F44` to `launch` |

### 4.1. Write the loader into bank A

```bash
riscv32-unknown-elf-gcc -march=rv32i_zifencei -mabi=ilp32 -nostdlib -nostartfiles \
  -Isrc/cyclone-v/doom/runtime -T loader.ld src/cyclone-v/doom/runtime/doom_loader.S -o doom_loader.elf
riscv32-unknown-elf-objcopy -O binary doom_loader.elf doom_loader.bin
riscv-tools --root . flash-image pack doom_loader.bin --output doom_loader.img --version 1 \
  --platform src/cyclone-v/doom/platform.yaml --bank A
```

The linker script `loader.ld`, written by the user, puts the `.text` section at `0x1100` (`ENTRY(_start)` and `SECTIONS { . = 0x1100; .text : { *(.text.loader) *(.text*) } }`). The `doom_loader.img` image enters the FLASH through `flash-image send` or through the JTAG FLASH loader, like the image of any other bank (see [program update](atualizacao-de-programa.md)).

### 4.2. Write the SDRAM and ring the doorbell

`riscv-tools` has no subcommand yet that loads an image into the SDRAM. The `sdram_debug` module has the function, which `certify-board` already uses, and the script below runs in the Python of the `dev_tools` image, with Quartus visible and the JTAG cable of the board.

```python
from pathlib import Path
import struct

from riscv_tools import sdram_debug
from riscv_tools.jtag import JtagLink

LAUNCH_WORD = (0x43FFFFF8 - 0x40000000) // 4
MAGIC = 0x4D4F4F44

link = JtagLink(
    hardware_name="<cable>", device_name="<chip>", sdram_instance=3
)
data = Path("doom.bin").read_bytes()
words = [
    w
    for (w,) in struct.iter_unpack(
        "<I", data.ljust(-(-len(data) // 4) * 4, b"\0")
    )
]

sdram_debug.write_word(link, LAUNCH_WORD, 0, 0xF)
sdram_debug.load_words(link, 0, words)
sdram_debug.write_word(link, LAUNCH_WORD, MAGIC, 0xF)
```

A core reset without a new load leaves the loader waiting, because the doorbell was consumed.

## 5. M10K block budget

The Quartus Prime Lite 25.1 compilation of the generated project (`build/doom-de0-cv`, default seed, DE0-CV) fits and closes timing in the slow 85 C model.

| Resource | Used | Available |
| :--- | ---: | ---: |
| RAM blocks (M10K) | 31 | 308 (10 %) |
| Block memory bits | 239,872 | 3,153,920 (8 %) |
| Logic (ALMs) | 9,503 | 18,480 (51 %) |
| Worst setup slack, slow 85 C model | 0.515 ns | |

The FLASH storage is $2^{14}$ bytes (the smallest power of two that covers the end of the FLASH, 12 KiB). The remaining M10K blocks are free for the framebuffer of the video controller.

## 6. Simulation top test

The `tests/python/tests.json` catalog has the entries `DoomSimTop` and `DoomSimWait`, which run the `doom_sim_test` top with the real BOOT_MEMORY (`boot_memory.S`) and the real `doom_loader.S`, packed as bank A by `flash_image.pack`.

| Entry | SDRAM at time zero | Checked result |
| :--- | :--- | :--- |
| `DoomSimTop` | Test program at the base and the magic in the doorbell | The program runs, stores the mark `0xD00D`, writes `tohost`, and the doorbell goes back to zero |
| `DoomSimWait` | Test program at the base, without the magic | After 400 thousand cycles nothing of the program ran |

The simulator loads the SDRAM linearly from the base, and the last page is 64 MiB above it, so the test puts the doorbell at `0x40000800` (`-DDOOM_LAUNCH_ADDR`). That address is the only difference from the board, and the `check-memory-map` check compares the default value in `doom_loader.S` with the `platform.yaml`. The images come from `tests/python/gen_doom_images.py`, and `--check` verifies they are up to date.

## 7. What the platform does not have

| Item | State |
| :--- | :--- |
| PS/2 and VGA | Not wired in the top; the `platform.yaml` has only the peripherals of the `de0-cv` |
| SDRAM load from the command line | Only through the `sdram_debug.load_words` function (section 4.2) |
| Bank B | Free; a new loader enters it with a higher version |
| DOOM linker script and `crt0` | Belong to the game port, which links the binary at `0x40000000` |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
