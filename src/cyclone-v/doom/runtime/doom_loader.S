/* doom_loader.S -- the program of bank A of the doom platform.
 *
 * The DOOM image (code, constants and initial data, about 400 KiB) does not fit the 8 KiB FLASH, so the code runs from
 * the SDRAM. The BOOT_MEMORY only starts a bank with a valid header, and this program is that bank: a payload of a few
 * instructions, linked at the entry of bank A (0x1100), that waits for the host to finish loading the SDRAM and then
 * jumps to its base.
 *
 * The protocol is one word, `launch`, in the last 4 KiB page of the RAM (platform.yaml, `reserved`). That page is the
 * one the data cache ignores, so every poll reads the SDRAM. The host loads the image at the base of the RAM through
 * the debug port, then writes DOOM_LAUNCH_MAGIC to `launch`. The loader clears the word before the jump, so the next
 * reset waits again instead of running the old image, and executes fence.i so that no line of an earlier run, in
 * either cache, hides the image the host has just written.
 *
 * Only t0, t1 and t2 are used: the program that starts at the base of the RAM sets sp, gp and tp itself, like the
 * program of any other bank.
 */

#include "memory_map.h"

/* The doorbell: platform.yaml `reserved.launch` (checked by check-memory-map). A test overrides it with -D. */
#ifndef DOOM_LAUNCH_ADDR
#define DOOM_LAUNCH_ADDR 0x43FFFFF8
#endif

/* ASCII "DOOM": what the host writes to `launch` when the image is complete. */
#define DOOM_LAUNCH_MAGIC 0x4D4F4F44

/* The first address of the image: the base of the RAM. */
#define DOOM_IMAGE_BASE 0x40000000

    .section .text.loader
    .global _start
_start:
    li   t0, DOOM_LAUNCH_ADDR
    li   t2, DOOM_LAUNCH_MAGIC
loader_poll:
    lw   t1, 0(t0)
    bne  t1, t2, loader_poll
    sw   x0, 0(t0)              // consumed: the next reset waits for a new image
    fence.i                     // drop the lines of an earlier run in both caches
    li   t0, DOOM_IMAGE_BASE
    jr   t0
