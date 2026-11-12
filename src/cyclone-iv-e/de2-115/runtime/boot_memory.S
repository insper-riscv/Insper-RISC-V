/* boot_memory.S -- the fixed bootloader of the de2-115. Programmed into BOOT_MEMORY
 * once (initial full Quartus compile), never JTAG-rewritten again: only
 * FLASH gets reprogrammed (see config.yaml quartus:). It plays the role a
 * real SOC's boot memory plays: it does not know what firmware (FLASH content)
 * it is booting, it only knows how an image in a FLASH bank is laid out.
 *
 * The FLASH holds two banks (flash.banks of platform.yaml, flash_banks.h).
 * Each starts with a 256-byte header page, written last by the update
 * routine, so a bank whose header is valid is a bank whose update finished:
 *
 *   +0 magic (RV32_IMAGE_MAGIC)  +4 size of the payload in bytes
 *   +8 CRC-32 of the payload     +12 version (larger is newer)
 *   +16 CRC-32 of the first 16 bytes of the header
 *
 * (the format of riscv-tools flash-image, src/riscv_tools/flash_image/header.py).
 *
 * What it does:
 *
 *  - _reset (address 0): clears the words the host and the program share
 *    (stdout header, tohost and fromhost, at the addresses of memory_map.h),
 *    executes fence.i (no line of the previous program, in either cache, can
 *    hide the FLASH the host has just written) and goes to bank_select.
 *
 *  - RAM entry: if the word at RV32_RAM_END - 8 holds 'RAMB' (0x52414D42), the
 *    host has left a program in the SDRAM through the debug port and the word at
 *    RV32_RAM_END - 4 is its entry. The magic is cleared and the program runs
 *    (once); this is how the NOR programmer reaches a board whose FLASH is empty.
 *
 *  - bank_select: checks the magic, the header CRC, the size and the payload
 *    CRC-32 of each bank. It jumps to the entry (base + header size) of the
 *    valid bank with the larger version, A on a tie; a bank that does not
 *    validate is skipped, so a failed update falls back to the other bank.
 *    The program enters with a0 = 0 (the hart) and a1 = 0, and every other
 *    register undefined (sp, gp and tp included: the firmware's _start sets
 *    them). With no valid bank it parks in rv32_wait_restart.
 *
 *  - rv32_wait_restart (fixed at 0x100, see boot_memory.ld): where a test ends
 *    and where the boot memory parks when no bank is valid. It waits until the
 *    host has written a new FLASH image and written fromhost, then starts
 *    over at _reset. It lives here, and not in FLASH, because FLASH is
 *    rewritten while the core waits.
 *
 * There is no stack and no libc, so sp, gp and tp are free scratch (the
 * program sets them in its _start) and only the registers of RV32E are
 * used: the routines are leaves that return through
 * ra, or through tp for the CRC loop. The CRC-32 is the bitwise one (IEEE
 * 802.3, reflected polynomial 0xEDB88320), one 32-bit word at a time, so the
 * ROM keeps no table (it is instruction-only memory): 5 instructions for
 * each of the 32 bits of a word, unrolled so that a word costs no taken
 * branch but the one of the loop (the rolled loop, with its counter and
 * its branch, was 7 instructions and 1 taken branch for each bit, and
 * took about 4x more cycles for the same CRC).
 *
 * The words it clears must be clean on every entry, cold boot or restart: a
 * stale nonzero tohost reads as "already done", and the previous test's
 * output must not leak into the next one.
 */

#include "memory_map.h"
#include "flash_banks.h"

#define CRC_POLY 0xEDB88320
#define RV32_RAM_BOOT_MAGIC 0x52414D42   // 'RAMB'

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
    .word 0x0000100F             // fence.i (the boot memory is assembled for rv32i): drop the lines of the previous program
    li   t0, RV32_RAM_END        // RAM entry: the host left a program in the SDRAM (magic and entry in the last 8 bytes)
    lw   t1, -8(t0)
    li   t2, RV32_RAM_BOOT_MAGIC
    bne  t1, t2, bank_select
    lw   t3, -4(t0)
    sw   x0, -8(t0)              // once: the next restart goes back to the FLASH
    jr   t3

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

    /* s0/s1: A valid (1) or not (0) and its version; gp/tp: the same for B. */
bank_select:
    li   a2, RV32_BANK_A_BASE
    li   a3, RV32_BANK_A_SIZE
    jal  ra, bank_check
    mv   s0, a0
    mv   s1, a1
    li   a2, RV32_BANK_B_BASE
    li   a3, RV32_BANK_B_SIZE
    jal  ra, bank_check
    mv   gp, a0
    mv   tp, a1
    beqz s0, bank_a_invalid
    beqz gp, boot_a             // only A is valid
    bltu s1, tp, boot_b         // both: B only when strictly newer
boot_a:
    li   t0, RV32_BANK_A_ENTRY
    j    boot_go
bank_a_invalid:
    beqz gp, rv32_wait_restart  // no valid bank: park, safe
boot_b:
    li   t0, RV32_BANK_B_ENTRY
boot_go:
    li   a0, 0                  // hart id
    li   a1, 0
    jr   t0

    /* bank_check: a2 = base of the bank, a3 = size of the bank.
     * Returns a0 = 1 and a1 = version when the image is valid, a0 = 0 else.
     * Clobbers t0-t2, sp, gp, tp, a4, a5. */
bank_check:
    lw   t0, 0(a2)
    li   t1, RV32_IMAGE_MAGIC
    bne  t0, t1, bank_bad
    mv   sp, a2                 // the header CRC covers the first 4 words
    li   gp, 4
    li   a4, -1
    jal  tp, crc_words
    not  a4, a4
    lw   t0, 16(a2)
    bne  a4, t0, bank_bad
    lw   a5, 4(a2)              // size of the payload: nonzero, whole words, inside the bank
    beqz a5, bank_bad
    andi t0, a5, 3
    bnez t0, bank_bad
    addi t0, a3, -RV32_IMAGE_HEADER_SIZE
    bltu t0, a5, bank_bad
    addi sp, a2, RV32_IMAGE_HEADER_SIZE
    srli gp, a5, 2
    li   a4, -1
    jal  tp, crc_words
    not  a4, a4
    lw   t0, 8(a2)
    bne  a4, t0, bank_bad
    lw   a1, 12(a2)
    li   a0, 1
    ret
bank_bad:
    li   a0, 0
    ret

    /* crc_words: sp = address, gp = number of words, a4 = CRC register.
     * Returns the register in a4 (not yet inverted) and jumps back through tp.
     * Clobbers t0-t2, sp, gp. */
crc_words:
    li   t2, CRC_POLY
crc_next_word:
    beqz gp, crc_done
    lw   t0, 0(sp)
    xor  a4, a4, t0
    .rept 32                    // one bit per step, straight-line: no branch inside a word
    andi t0, a4, 1
    neg  t0, t0                 // all ones when the low bit is set
    and  t0, t0, t2
    srli a4, a4, 1
    xor  a4, a4, t0
    .endr
    addi sp, sp, 4
    addi gp, gp, -1
    j    crc_next_word
crc_done:
    jr   tp
