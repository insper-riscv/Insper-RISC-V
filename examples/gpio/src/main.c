#include <stdio.h>
#include "rv32_drivers.h"
static void settle(void) {for(volatile unsigned i=0;i<100;i=i+1) {}}
int main(void) {
 rv32_gpio_t gpio={RV32_GPIO_SWITCHES_BASE};
 rv32_gpio_t keys={RV32_GPIO_KEYS_BASE};
 rv32_gpio_direction(gpio,1u);rv32_gpio_write(gpio,0u);settle();
 rv32_gpio_set(gpio,1u);settle();
 if (rv32_gpio_read_output(gpio)!=1u || !(rv32_gpio_read(gpio)&1u)) return 1;
 rv32_gpio_clear(gpio,1u);settle();if (rv32_gpio_read_output(gpio)!=0u) return 2;
 rv32_gpio_toggle(gpio,1u);settle();if (rv32_gpio_read_output(gpio)!=1u) return 3;
 rv32_gpio_irq_configure(gpio,1u,1u,1u,0u);
 (void)rv32_gpio_irq_read_clear(gpio);
 rv32_gpio_write(gpio,0u);settle();
 if (!(rv32_gpio_irq_read_clear(gpio)&1u)) return 4;
 settle(); if (rv32_gpio_irq_read_clear(gpio)&1u) return 5;
 rv32_gpio_write(gpio,1u);settle();
 if (!(rv32_gpio_irq_read_clear(gpio)&1u)) return 6;
 rv32_gpio_direction(keys,2u);rv32_gpio_write(keys,2u);settle();
 if(rv32_gpio_read_output(keys)!=2u || !(rv32_gpio_read(keys)&2u)) return 7;
 rv32_gpio_direction(gpio,0u);rv32_gpio_direction(keys,0u);
 puts("GPIO set/clear/toggle, pins, IRQ read-clear and two instances: PASS");return 0;
}
