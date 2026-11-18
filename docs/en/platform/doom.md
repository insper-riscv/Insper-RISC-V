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
| Internal memory of the data cache | `0x43FE8000` | 32 KiB | Read and write in two cycles, inside the SDRAM range, without going through the SDRAM |
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

The `load-ram` subcommand does steps 2 to 4 in one call: it clears `launch`, writes the binary and the WAD through the debug port, reads each back to verify it and only then writes the magic to `launch`. A difference in the read-back aborts the load without touching the doorbell.

```bash
riscv-tools --root . --config src/cyclone-v/doom/config.yaml load-ram doom.bin \
  --wad doom1.wad --wad-address 0x40100000
```

The binary address is the SDRAM base, and the WAD address is the one the game port defines. `launch` comes from the `reserved` section of the `platform.yaml` (`memory.launch_addr`). A core reset without a new load leaves the loader waiting, because the doorbell was consumed. The full description of the subcommand is in the documentation of the `ram_load` module of the Tools repository.

## 5. M10K block budget

The Quartus Prime Lite 25.1 compilation of the generated project (`build/doom-de0-cv`, default seed, DE0-CV) fits and closes timing in the slow 85 C model.

| Resource | Used | Available |
| :--- | ---: | ---: |
| RAM blocks (M10K) | 31 | 308 (10 %) |
| Block memory bits | 239,872 | 3,153,920 (8 %) |
| Logic (ALMs) | 9,503 | 18,480 (51 %) |
| Worst setup slack, slow 85 C model | 0.515 ns | |

The FLASH storage is $2^{14}$ bytes (the smallest power of two that covers the end of the FLASH, 12 KiB). The remaining M10K blocks are free for the framebuffer of the video controller.

## 6. Game clock

The `doomgeneric` port asks for the time in milliseconds through `DG_GetTicksMs`, which the platform runtime (`runtime/doom_clock.c`) provides from the `time` CSR of Zicntr.

| Item | Value |
| :--- | :--- |
| Source of `time` | `mtime` of the CLINT, mirrored by the core |
| Core cycles per tick | 100 (`CLINT_TICK_CYCLES`) |
| Core clock | 100 MHz |
| Real ticks per second | $100 \cdot 10^{6} / 100 = 1{,}000{,}000$ |
| Nominal ticks per second (`mtime_hz`) | 1,000,000 |

The clock converts with the nominal value, which matches the real rate of the counter.

The conversion avoids the `div` instruction (CPI of about 11) and 64-bit division. On each read, the clock adds to the total the advance of the low 32 bits of `time`, computed by unsigned subtraction (correct even when the counter goes from $2^{32}$ to 0), and divides by 1000 with a multiplication:

$$\left\lfloor \frac{x}{1000} \right\rfloor = \left\lfloor \frac{x \cdot \mathtt{0x10624DD3}}{2^{38}} \right\rfloor \quad \forall\, x < 2^{32}$$

The compiler does it with one `mulhu`, and the generated object has no `div`, `rem` or call. The remainder of fewer than 1000 ticks carries from one read to the next, so no tick is lost. The clock returns the milliseconds since the first call, which returns zero. It loses time only if two calls are more than $2^{32}$ ticks (71.6 minutes) apart, which a game that reads the time every tic does not do. If the `mtime_hz` of the platform changes, the inverse no longer holds and the build fails on a static assertion.

The `tests/c/doom_clock/src.c` test checks the conversion against the 64-bit computation in 4000 advances of varied size (including the counter passing through 0 and the maximum 32-bit advance) and that the real `time` never goes backwards.

```bash
riscv-tools --root . --config tests/c/config.yaml compile --emit mif
riscv-tools --root . --config tests/c/config.yaml spike-run
riscv-tools --root . --config tests/c/config.yaml compile --emit hex
riscv-tools --root . --config tests/c/config.yaml sim
```

The Spike of `spike-run` runs without a CLINT, and in it `time` stays at zero; the advance of the real `time` is checked in the platform simulation (`sim`), where `time` mirrors the `mtime` of the CLINT.

## 7. Simulation top test

The `tests/python/tests.json` catalog has the entries `DoomSimTop` and `DoomSimWait`, which run the `doom_sim_test` top with the real BOOT_MEMORY (`boot_memory.S`) and the real `doom_loader.S`, packed as bank A by `flash_image.pack`.

| Entry | SDRAM at time zero | Checked result |
| :--- | :--- | :--- |
| `DoomSimTop` | Test program at the base and the magic in the doorbell | The program runs, stores the mark `0xD00D`, writes `tohost`, and the doorbell goes back to zero |
| `DoomSimWait` | Test program at the base, without the magic | After 400 thousand cycles nothing of the program ran |

The simulator loads the SDRAM linearly from the base, and the last page is 64 MiB above it, so the test puts the doorbell at `0x40000800` (`-DDOOM_LAUNCH_ADDR`). That address is the only difference from the board, and the `check-memory-map` check compares the default value in `doom_loader.S` with the `platform.yaml`. The images come from `tests/python/gen_doom_images.py`, and `--check` verifies they are up to date.

The entries `DoomSimVideo` and `DoomSimKeyboard` run the same top with the programs of sections 8.4 and 8.5.

## 8. Video and keyboard

### 8.1. Peripherals and addresses

The `platform.yaml` lists two external peripherals, which the generated top of the board instantiates next to the SoC and the `doom_sim_test` simulation top instantiates in the same windows.

| Peripheral | `kind` | Base | Window | Interrupt | DE0-CV pins |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `VIDEO` | `video` | `0x80100000` | 256 KiB | none | `VGA_R[3:0]`, `VGA_G[3:0]`, `VGA_B[3:0]`, `VGA_HS`, `VGA_VS` |
| `KBD` | `ps2` (`device: keyboard`) | `0x80007000` | 16 bytes | PLIC line 5 (`IRQ_KBD`) | `PS2_CLK` (D3), `PS2_DAT` (G2) |

The second channel of the Y cable (`PS2_CLK2` on E2 and `PS2_DAT2` on G1) belongs to a mouse, which enters as one more entry of `peripherals` (`MOUSE: {kind: ps2, device: mouse, base: 0x80007100}`). The generated map (`memory_map.h` and `doom_map_pkg.vhd`) has `RV32_VIDEO_BASE`, `RV32_KBD_BASE` and `RV32_IRQ_KBD`.

### 8.2. Indexed video

The `io.video` of the `platform.yaml` asks for a 320x200 indexed framebuffer (8 bits per pixel and a palette of 256 entries of 12 bits, the width of the DE0-CV converter). The mode is the default of the board, 640x480 at 60 Hz with a 25 MHz pixel clock, and the image comes out enlarged twice and centered, with black bands of 40 lines at the top and at the bottom.

| Region of the video window | Offset | Content |
| :--- | :--- | :--- |
| Registers | `0x00000` to `0x00010` | Control, state, frame counter, geometry and format |
| Palette | `0x00400` | 256 words, the color in the low 12 bits (red in bits 11:8) |
| Framebuffer | `0x20000` | 16000 words, four pixels per word, the lowest column in the low bits |

The framebuffer and the palette are write only, and the core updates them with `sw`, `sh` or `sb`. The display turns on with bit 0 of the control register. The `Peripherals` package documents the peripheral in `docs/en/video/video.md`.

The pixel clock is one more output of the PLL of the generated top, and the generated `.sdc` declares the paths between the core domain and the pixel domain false, because the video crosses them only through two-flip-flop synchronizers and through memories with one clock on each port.

### 8.3. Resources

The video alone, with these generics, compiled in Quartus Prime Lite 25.1 for the DE0-CV, takes 137 ALMs, 65 M10K blocks (21 %) and 527,360 memory bits (17 %). Tools estimates 51 blocks for the same framebuffer and palette, because it counts bits and not the organization in blocks 32 bits wide.

### 8.4. Video test in simulation

The program `sdram_video.hex` reads the geometry and the format, writes the palette and a 16x8 pixel frame of a four-color diagonal, turns the display on and writes `tohost`. The testbench (`doom_video.py`) uses a small 40x20 mode with the structure of 640x480, captures a whole frame of the `VGA_*` output from the edge of the vertical synchronism and compares every pixel and both synchronisms with the model of `tests/python/utils/doom_frame.py`. It also checks what the core read from the registers.

### 8.5. Keyboard test in simulation

The program `sdram_kbd.hex` enables PLIC line 5 and the receive interrupt of the keyboard, says it is ready, waits for each byte in the queue, reads the PLIC claim with the first one and stores the 20 bytes. The testbench (`doom_keyboard.py`) is the keyboard: through the open drain lines of the connector it injects the make and the break of the four arrows in set 2 scancodes (`E0 75`, `E0 F0 75`, `E0 6B`, `E0 74` and `E0 72` with the `E0 F0`), and checks the bytes the core stored and the claim.

### 8.6. C tests for the first run on the board

The programs `tests/c/doom_video/src.c` and `tests/c/doom_keyboard/src.c` are linked in bank A and compiled with the other C tests of the platform (section 6).

| Program | What it does | Return code |
| :--- | :--- | :--- |
| `doom_video` | Reads the geometry and the format, writes the palette and the bars (eight color bars and a ramp of 16 grays), turns the display on and waits for three frames | 1 geometry, 2 format, 3 the frame counter did not advance |
| `doom_keyboard` | Enables the keyboard interrupt and waits for an arrow pressed and released, printing the bytes in hexadecimal | 1 transmitter, 2 state error, 3 timeout (30 s), 4 no line in the PLIC, 5 bytes that are not an arrow |

In Spike both return zero without touching the devices. On the board, `doom_video` leaves the bars on the monitor after it ends, and `doom_keyboard` needs a person to press and release an arrow.

## 9. Caches, write queue and internal memory

The `platform.yaml` sizes the three parts that cut the memory time of the game, and none is fixed in the code.

| Part | Key | Value | Effect |
| :--- | :--- | :--- | :--- |
| Instruction cache | `memory.instructions[].cache.size_bits` | 262144 (32 KiB) | The rendering loop and the hot code fit in the cache |
| Data cache | `memory.data[].cache.size_bits` | 32768 (4 KiB) | No change |
| Write queue | `memory.data[].cache.write_buffer` | 4 words | A store completes without waiting for the SDRAM; a read leaves only with the queue empty, so program order holds |
| Internal memory | `memory.data[].cache.scratch_kib` and `scratch_base` | 32 KiB at `0x43FE8000` | The data cache serves the window in two cycles, without the SDRAM |

The internal memory sits inside the SDRAM range and holds only what the program writes after the reset, because the host loads the SDRAM behind the cache. DOOM puts the stack and the bss of the drawing loop in it (`SCRATCH=1` in the build of the DOOM repository), and the RAM of the linker ends where it starts (`0x43FE8000`).

## 9. What the platform does not have

| Item | State |
| :--- | :--- |
| Mouse | Outside the `platform.yaml`, because it depends on the Y cable |
| Bank B | Free; a new loader enters it with a higher version |
| DOOM linker script and `crt0` | Belong to the game port, which links the binary at `0x40000000` |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
