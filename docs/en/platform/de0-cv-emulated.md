# Platform `de0-cv-emulated`: the emulated FLASH with its controller, simulation only

## 1. What it is

It is the memory model of the DE0-CV from before the split of the SDRAM, kept as a simulation top. The FLASH is emulated in blocks of the FPGA with the latency of a serial chip (24 edges for the first word of a burst and 4 for each following one), and the RAM is the SDRAM of the board. Both sit behind the instruction and data caches.

The platform exists to test the program update in the field. The FLASH controller and the command chip (erase a sector, program a page, protect) only make sense with a FLASH that the core can program, and [`de0-cv`](de0-cv.md) has none, because its FLASH lives inside the SDRAM chip and only the debug port writes it.

## 2. Differences from `de0-cv`

| Item | `de0-cv` | `de0-cv-emulated` |
| :--- | :--- | :--- |
| FLASH | 32 MiB window of the SDRAM chip | `emulated`, 256 KiB in FPGA blocks |
| Who writes the FLASH | The debug port of the chip | The FLASH controller, from the program |
| RAM | 32 MiB window, 32 MiB into the chip | 64 MB SDRAM, from byte 0 of the chip |
| Update banks | A and B of 16 MiB each | A of 124 KiB and B of 128 KiB |
| Board | Yes | No, simulation only |

## 3. Use

The top is `rv32im_sdram_flash_emulated_sim_test`, with `has_flash_controller` on. The parameters `FLASH_ERASE_LATENCY` and `FLASH_PROGRAM_LATENCY` give the wait of the chip in edges. The project that runs the tests uses the headers of this platform, because banks A and B of `de0-cv` fall outside the emulated FLASH.
