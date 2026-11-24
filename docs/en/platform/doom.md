# Platform `doom`: the DE0-CV with the code in the SDRAM and 4:3 video

## 1. What it is

The `doom` platform is the `de0-cv` tuned to run DOOM (the `doomgeneric` port, about 540 KiB with the code, the constants and the initial data). The core keeps only the BOOT_MEMORY. The SDRAM chip of the board (64 MB, one controller) is split in two windows, the FLASH (the instructions and the constants, 4 MiB at the top of the chip, read only for the core) and the RAM (the data, 60 MiB from the start of the chip), both behind the instruction cache and the data cache. There is no FLASH emulated in M10K blocks, no FLASH controller and no loader: the host writes the image into the FLASH window through the debug port of the SDRAM (`riscv-tools load-flash`) and releases the core, and the BOOT_MEMORY jumps to `0x1000`.

The organization of the two windows is that of the [de0-cv](de0-cv.md) platform. This page describes what the `doom` changes: the map, the clocks, the video, the SD card and the tests.

## 2. Memory map

| Region | Base | Size | Access |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | 4 KiB | Fetch and read, direct, no cache |
| FLASH (`type: sdram`) | `0x00001000` | `0x3FF000` (4 MiB minus 4 KiB) | Fetch and read through the caches, read only for the core |
| RAM (`type: sdram`) | `0x40000000` | 60 MiB | Read and write through the caches |
| Internal memory of the data cache | `0x43BE8000` | 32 KiB | Read and write in two cycles, inside the RAM, without going through the SDRAM |
| Peripherals | `0x80000000` | windows of 256 MB | Read and write, no cache |

Inside the 64 MiB chip, the RAM starts at byte 0 (`offset: 0`), which keeps the chip addresses that the WAD and the measurement block have always had, and the FLASH starts at byte `0x3C01000` (`offset`), that is, 60 MiB plus the base `0x1000`. The 4 KiB at the top of the RAM (`0x43BFF000` to `0x43BFFFFF`), which the data cache ignores, hold the words shared with the host.

| Word | Address | Use |
| :--- | :--- | :--- |
| `stdout` | `0x43BFFBE0` | Header and buffer of the program output (1 KiB plus 8 bytes) |
| `tohost` | `0x43BFFFE8` | End of the program (HTIF protocol) |
| `fromhost` | `0x43BFFFF0` | Restart by the host |

The BOOT_MEMORY clears `stdout`, `tohost` and `fromhost` on every reset.

## 3. How the code runs

The BOOT_MEMORY is the common one (`base/src/boot/boot_core.S`) and, since the platform has no FLASH banks, it jumps straight to `boot.entry`, `0x1000`, where the `_start` of DOOM is. The binary is linked with two regions: the ROM at `0x1000` (`.init`, `.text`, `.rodata` and the initial values of `.data`) and the RAM at `0x40000000` (`.data`, `.bss`, the stack and the heap), and the `crt0` of picolibc copies the initial values from one to the other.

| Step | Operation |
| :--- | :--- |
| 1 | Build the flat image, starting at `0x1000` (`doom.bin`) |
| 2 | `riscv-tools --root . load-flash --platform src/cyclone-v/doom/platform.yaml --image doom.bin --address 0x1000` |
| 3 | The command holds the core, writes the FLASH window, checks the CRC-32 computed on the board and releases the core |

The command is described in `flash_load` and `sdram_windows` of the Tools repository. A reconfiguration of the FPGA erases the SDRAM, and the image is written again after it; the reset button of the board restarts only the core and keeps the FLASH. The WADs of the game are not in the SDRAM at start: the port reads them from the microSD card (section 7.7).

## 4. Clocks and timing closure

The `platform.yaml` declares the clocks of the generated PLL.

| Clock | Frequency | Phase | PLL output |
| :--- | ---: | ---: | :--- |
| `core` | 100 MHz | 0 | a single one, shared with `fetch` |
| `fetch` | 100 MHz | 0 | that of `core` |
| `mem` | 125 MHz | 0 | its own, not merged with `core` |

With `fetch` equal to `core` in frequency and phase, the generator turns on the `early_fetch_addr` generic of the SoC. The instruction memories (the BOOT_MEMORY and the instruction cache) read, on the edge of the core clock, the address the PC will have in the next cycle, and the loop from the PC to the cache is made of whole cycles, with no dependence on the phase of a clock ahead. The target of a taken branch, a jump or an exception arrives one cycle later, and `fast_icache_select` is a prerequisite. `mem` sits on its own PLL output because Quartus merges outputs of the same frequency and phase, and the generated `.sdc` would treat the crossing between `mem` and `core` as asynchronous, hiding the real path from the instruction cache to the core.

Measured on the DE0-CV with the final `.sof` (Quartus Prime Lite 25.1, seed 6):

| Item | Value |
| :--- | ---: |
| Setup slack of the core domain (100 MHz) | +0.090 ns |
| Setup slack of the memory domain (125 MHz) | +0.806 ns |
| Hold slack | positive in every corner |

The multiplier uses DSP blocks in three cycles (Core, `dsp_multiplier_rv32`), which takes the Booth multiplier in logic off the critical path.

## 5. Game clock

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

## 6. Simulation top test

The catalog `tests/python/tests.json` has the entries `DoomSimTop` and `DoomSimTopStaggered`, which run the `doom_sim_test` top with the real BOOT_MEMORY (`boot_memory.S`), the same one the board uses. The top has the FLASH and RAM windows in the same SDRAM chip model, at the offsets given by the generics `flash_chip_offset_bytes` and `ram_chip_offset_bytes` (those of the `platform.yaml` by default). The `DoomSimTop` entry turns `early_fetch` on, which is what the generated top of the board does, and `DoomSimTopStaggered` runs the fetch clock ahead.

| Entry | Chip image at time zero | Result checked |
| :--- | :--- | :--- |
| `DoomSimTop` | Test program at the base of the FLASH | The BOOT_MEMORY jumps to it, it stores the mark `0xD00D` in the RAM and writes `tohost` |
| `DoomSimTopStaggered` | The same, with the fetch clock ahead | The same result |

To keep the image small, the test puts the FLASH at byte `0x1000` of the chip and the RAM at byte `0x10000`, and uses only the start of the two windows; the SDRAM clock of the test has the period of `clocks.mem` (8 ns), which the top uses in the refresh times of the chip. The images come from `tests/python/gen_doom_images.py`, and `--check` verifies they are up to date. The `DoomSimVideo` and `DoomSimKeyboard` entries run the same top with the programs of sections 7.4 and 7.5.

## 7. Video and keyboard

### 7.1. Peripherals and addresses

The `platform.yaml` lists three external peripherals, which the generated top of the board instantiates next to the SoC and the `doom_sim_test` simulation top instantiates in the same windows.

| Peripheral | `kind` | Base | Window | Interrupt | DE0-CV pins |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `VIDEO` | `video` | `0x80100000` | 256 KiB | none | `VGA_R[3:0]`, `VGA_G[3:0]`, `VGA_B[3:0]`, `VGA_HS`, `VGA_VS` |
| `KBD` | `ps2` (`device: keyboard`) | `0x80007000` | 16 bytes | PLIC line 5 (`IRQ_KBD`) | `PS2_CLK` (D3), `PS2_DAT` (G2) |
| `SD` | `sd_native` | `0x80008000` | 4 KiB | PLIC line 7 (`IRQ_SD`), unused | `SD_CLK`, `SD_CMD`, `SD_DATA[3:0]` |

The second channel of the Y cable (`PS2_CLK2` on E2 and `PS2_DAT2` on G1) belongs to a mouse, which enters as one more entry of `peripherals` (`MOUSE: {kind: ps2, device: mouse, base: 0x80007100}`). The generated map (`memory_map.h` and `doom_map_pkg.vhd`) has `RV32_VIDEO_BASE`, `RV32_KBD_BASE`, `RV32_SD_BASE`, `RV32_IRQ_KBD` and `RV32_IRQ_SD`.

### 7.2. Indexed video in 4:3

The `io.video` of the `platform.yaml` asks for an indexed 320x200 framebuffer (8 bits per pixel and a palette of 256 entries of 12 bits, the width of the DE0-CV converter), magnified twice horizontally (`scale: 2`) and by 12/5 vertically (`scale_y: 12/5`). The mode is the default of the board, 640x480 at 60 Hz with a 25 MHz pixel clock, and the 640x480 image fills the whole screen in 4:3, without the 40-line black bands that the 2x2 magnification left.

The source line of displayed line $n$ is

$$\mathrm{src}(n)=\left\lfloor \frac{n \cdot 5}{12} \right\rfloor$$

computed with no division by an error accumulator. Each group of 5 source lines takes 12 screen lines, repeated 3, 2, 3, 2 and 2 times (average 2.4), so each source pixel takes 2 columns by 2.4 lines, the 1.2 ratio of the non-square DOOM pixel. The game keeps drawing 320x200 at the same addresses. With `v_scale_num` other than zero, register 4 of the video holds the numerator in bits 28:25 and the denominator in bits 31:29.

| Region of the video window | Offset | Content |
| :--- | :--- | :--- |
| Registers | `0x00000` to `0x00010` | Control, status, frame counter, geometry and format |
| Palette | `0x00400` | 256 words, the color in the low 12 bits (red in bits 11:8) |
| Framebuffer | `0x20000` | 16000 words, four pixels per word, the lowest column in the low bits |

The framebuffer and the palette accept only writes, and the core updates them with `sw`, `sh` or `sb`. The display turns on with bit 0 of the control register. The `Peripherals` package documents the peripheral in `docs/en/video/video.md`.

The pixel clock is one more output of the PLL of the generated top, and the generated `.sdc` declares the paths between the core domain and the pixel domain false, because the video crosses them only through two-flip-flop synchronizers and memories with one clock on each port.

#### 7.2.1. Video borders

The catalog `boards/video-modes.yaml` has a single 640x480 at 60 Hz timing (front porch 16, sync 96 and back porch 48 horizontally), the one in the DE0-CV manual, and the `io.video` of the `platform.yaml` has no field to change the porches. A monitor that cuts the first 16 pixels of each line on the left (the case of the monitor used in the validation on the board) needs `h_front_porch => 0` and `h_back_porch => 64`, with the same total of 800 pixels, in the `generic map` of the `video` in the generated top (`doom_de0_cv_top.vhd`). This adjustment is made by hand in the generated top, before the Quartus compilation, because the Tools generator has no field for the porches.

### 7.3. Resources

The video alone, with these generics, compiled in Quartus Prime Lite 25.1 for the DE0-CV, takes 137 ALMs, 65 M10K blocks (21 %) and 527,360 memory bits (17 %). Tools estimates 51 blocks for the same framebuffer and palette, because it counts bits and not the organization in blocks 32 bits wide.

### 7.4. Video test in simulation

The program of `sdram_video.hex`, in the FLASH, reads the geometry and the format, writes the palette and a 16x8 pixel frame of a four-color diagonal, turns the display on and writes `tohost`. The testbench (`doom_video.py`) uses a small 40x20 mode with the structure of 640x480, captures a whole frame of the `VGA_*` output from the edge of the vertical synchronism and compares every pixel and both synchronisms with the model of `tests/python/utils/doom_frame.py`. It also checks what the core read from the registers.

### 7.5. Keyboard test in simulation

The program of `sdram_kbd.hex`, in the FLASH, enables PLIC line 5 and the receive interrupt of the keyboard, says it is ready, waits for each byte in the queue, reads the PLIC claim with the first one and stores the 20 bytes. The testbench (`doom_keyboard.py`) is the keyboard: through the open drain lines of the connector it injects the make and the break of the four arrows in set 2 scancodes (`E0 75`, `E0 F0 75`, `E0 6B`, `E0 74` and `E0 72` with the `E0 F0`), and checks the bytes the core stored and the claim.

### 7.6. C tests for the first run on the board

The programs `tests/c/doom_video/src.c` and `tests/c/doom_keyboard/src.c` are linked at the base of the FLASH and compiled with the other C tests of the platform (section 5).

| Program | What it does | Return code |
| :--- | :--- | :--- |
| `doom_video` | Reads the geometry and the format, writes the palette and the bars (eight color bars and a ramp of 16 grays), turns the display on and waits for three frames | 1 geometry, 2 format, 3 the frame counter did not advance |
| `doom_keyboard` | Enables the keyboard interrupt and waits for an arrow pressed and released, printing the bytes in hexadecimal | 1 transmitter, 2 state error, 3 timeout (30 s), 4 no line in the PLIC, 5 bytes that are not an arrow |

In Spike both return zero without touching the devices. On the board, `doom_video` leaves the bars on the monitor after it ends, and `doom_keyboard` needs a person to press and release an arrow.

### 7.7. microSD card

The `SD` peripheral (`kind: sd_native`, `0x80008000`) wires the microSD socket of the board in the native 4-bit mode (`SD_CLK`, `SD_CMD`, `SD_DATA[3:0]`). The controller clock is `clocks.core`, so `SD_CLK` is $100\,\mathrm{MHz} / (2 (\mathtt{DIVIDER} + 1))$: 399 kHz after the reset and 25 MHz with `DIVIDER = 1`. The game port reads the WADs from the card by polling, and the interrupt bits of `CONTROL` stay off, so PLIC line 7, assigned by the map, stays inert. The output of the controller to the pins is registered (`sd_native` of Peripherals).

## 8. Caches, write queue and internal memory

The `platform.yaml` sizes the parts that cut the memory time of the game, and none is fixed in the code.

| Part | Key | Value | Effect |
| :--- | :--- | :--- | :--- |
| Instruction cache | `memory.instructions[].cache.size_bits` | 262144 (32 KiB) | The rendering loop and the hot code fit in the cache |
| Data cache | `memory.data[].cache.size_bits` | 262144 (32 KiB) | More data of the game and of the WAD stay in the cache |
| Write queue | `memory.data[].cache.write_buffer` | 4 words | A store completes without waiting for the SDRAM; a read leaves only with the queue empty, so program order holds |
| Internal memory | `memory.data[].cache.scratch_kib` and `scratch_base` | 32 KiB at `0x43BE8000` | The data cache serves the window in two cycles, without the SDRAM |

The internal memory sits inside the RAM and holds only what the program writes after the reset. DOOM puts the stack and the bss of the drawing loop in it (`SCRATCH=1` in the build of the DOOM repository), and the RAM of the linker ends where it starts (`0x43BE8000`).

## 9. What the platform does not have

| Item | State |
| :--- | :--- |
| Mouse | Outside the `platform.yaml`, because it depends on the Y cable |
| Emulated FLASH, FLASH controller and banks | They do not exist; the in-field program update is that of [`de0-cv-emulated`](de0-cv-emulated.md) |
| Video porch adjustment in the `platform.yaml` | It does not exist (section 7.2.1) |
| DOOM linker script and `crt0` | They belong to the game port, which links the binary at `0x1000` (ROM) and `0x40000000` (RAM) |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
