#include <stdint.h>
#include <stdio.h>
#include "rv32_test.h"

static volatile uint32_t results[4];

int main(void)
{
    results[0] = 0;
    results[1] = 1;
    results[2] = 2;
    results[3] = 3;

    for (int i = 0; i < 4; i++)
        if (results[i] != i)
            RV32_FAIL();

    puts("Test from FPGA.");

    RV32_PASS();
}