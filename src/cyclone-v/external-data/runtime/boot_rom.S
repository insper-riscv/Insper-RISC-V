/* boot_rom.S -- the fixed, generic bootloader. Programmed into BOOT_ROM
 * once (initial full Quartus compile), never JTAG-rewritten again: only
 * FLASH gets reprogrammed per test (see config.yaml quartus:). It plays
 * the role a real SOC's boot ROM plays: it does not know what firmware
 * (FLASH content) it is booting.
 *
 * It does two things:
 *
 *  - _reset (address 0): clears the words the host and the test share
 *    (see below) and executes fence.i and jumps to FLASH_BASE (0x800), where the toolchain's
 *    crt0 (_start, from rv32im-fpga.specs) is. The crt0 sets sp and gp,
 *    copies .data from FLASH to RAM, clears .bss, sets up TLS, runs the
 *    constructors and calls main; main returning lands in _exit
 *    (platform/_exit.c).
 *
 *  - rv32_wait_restart (fixed at 0x100, see boot_rom.ld): where every test
 *    ends. It parks the core until the host has written a new FLASH image
 *    and written fromhost, then starts over at _reset. It lives here, and
 *    not in FLASH, because FLASH is rewritten while the core waits.
 *
 * The words it clears, all at the top of RAM: the stdout header (length and
 * truncated), tohost and fromhost, at the addresses of memory_map.h, which
 * `riscv-tools generate-memory-map` writes from platform.yaml.
 *
 * They must be clean on every entry, cold boot or restart: a stale nonzero
 * tohost reads as "already done", and the previous test's output must not
 * leak into the next one.
 */

#include "memory_map.h"

    .section .text.reset
    .global _reset
_reset:
    li   t0, RV32_RAM_END
    sw   x0, RV32_FROMHOST_ADDR - RV32_RAM_END(t0)
    sw   x0, RV32_FROMHOST_ADDR - RV32_RAM_END + 4(t0)
    sw   x0, RV32_TOHOST_ADDR - RV32_RAM_END(t0)
    sw   x0, RV32_TOHOST_ADDR - RV32_RAM_END + 4(t0)
    li   t0, RV32_STDOUT_BASE    // stdout header
    sw   x0, 0(t0)               // length
    sw   x0, 4(t0)               // truncated
    .word 0x0000100F             // fence.i (the boot ROM is assembled for rv32i): drop the lines of the previous program
    li   t0, RV32_BOOT_ENTRY     // the crt0's _start
    li   a0, 0                   // the hart (entry contract: a0 = 0, a1 = 0)
    li   a1, 0
    jr   t0

    /* The test has already written tohost (1 = pass, (code << 1) | 1 = fail,
     * see rv32_test.h). The core parks here until the host has written a new
     * FLASH image and a nonzero value to fromhost, then starts over at
     * _reset, which clears both words. */
    .section .text.wait_restart
    .global rv32_wait_restart
rv32_wait_restart:
    li   t0, RV32_RAM_END

rv32_wait_restart_poll:
    lw   t1, RV32_FROMHOST_ADDR - RV32_RAM_END(t0)
    beqz t1, rv32_wait_restart_poll
    j    _reset
