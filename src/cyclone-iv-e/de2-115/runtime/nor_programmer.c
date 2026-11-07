// RV32_EXT: M,Zifencei
// RV32_TEST_KIND: unit
#include <stdint.h>

#include "rv32_test.h"
#include "rv32_platform.h"
#include "rv32_flash_update.h"

// The NOR programmer: the program the host leaves in the SDRAM (through the debug port) to write a bank of the NOR chip when
// the chip holds nothing that can run. The boot memory starts it through its RAM entry (magic and entry in the last 8 bytes of
// the RAM), it reads the job the host left (magic, destination bank, size in bytes, flags) and the image after it, erases and
// programs the bank by the commands of the FLASH controller, reads it back and stops in rv32_wait_restart with tohost set.
// NOR_JOB_ADDR and NOR_IMAGE_ADDR come from the build of riscv-tools (nor_program), the same numbers it loads the host data at.

#define NOR_JOB_MAGIC 0x504F524Eu  // 'NROP'
#define ROUTINE_WORDS 256u

static uint32_t ram_code[ROUTINE_WORDS];

int main(void) {
    volatile uint32_t *job = (volatile uint32_t *)NOR_JOB_ADDR;
    if (job[0] != NOR_JOB_MAGIC) RV32_FAIL(1);
    int status = rv32_update_bank(job[1], (uint8_t *)NOR_IMAGE_ADDR, job[2], job[3], ram_code, ROUTINE_WORDS);
    if (status != RV32_UPDATE_OK) RV32_FAIL(10 + status);
    RV32_PASS();
}
