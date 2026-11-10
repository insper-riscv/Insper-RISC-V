#include <stdint.h>
#include <stdio.h>

static volatile uint32_t results[4];

int main(void)
{
    for (uint32_t i = 0; i < 4; ++i) {
        results[i] = i * i;
    }

    puts("Hello from an RV32 C project.");
    return 0;
}
