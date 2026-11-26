#include "rv32_drivers.h"

#include <stdio.h>

/* Poll budgets bound attempts; they are not calibrated time delays. */
static bool wait_pin(rv32_gpio_t gpio, size_t pin, bool expected)
{
    for (size_t attempt = 0; attempt < 2048; ++attempt) {
        bool value = false;

        if (!rv32_gpio_pin_read(gpio, pin, &value)) {
            return false;
        }

        if (value == expected) {
            return true;
        }
    }

    return false;
}

static bool wait_irq(rv32_gpio_t gpio, size_t pin)
{
    for (size_t attempt = 0; attempt < 2048; ++attempt) {
        uint32_t events = rv32_gpio_irq_read_clear(gpio);

        if (rv32_gpio_irq_contains(events, pin)) {
            return true;
        }
    }

    return false;
}

int main(void)
{
    /* These widths match the modular simulation top, not its MMIO slot size. */
    rv32_gpio_t gpio = rv32_gpio_platform_new(RV32_GPIO_SWITCHES_INSTANCE);
    rv32_gpio_t keys = rv32_gpio_platform_new(RV32_GPIO_KEYS_INSTANCE);

    if (!rv32_gpio_valid(gpio) || !rv32_gpio_valid(keys)) {
        return 1;
    }

    if (!rv32_gpio_pin_direction(gpio, 0, RV32_GPIO_OUTPUT_PIN) ||
        !rv32_gpio_pin_write(gpio, 0, false) || !wait_pin(gpio, 0, false)) {
        return 2;
    }

    if (!rv32_gpio_pin_write(gpio, 0, true) || !wait_pin(gpio, 0, true)) {
        return 3;
    }

    if (!rv32_gpio_pin_write(gpio, 0, false) || !wait_pin(gpio, 0, false)) {
        return 4;
    }

    if (!rv32_gpio_pin_toggle(gpio, 0) || !wait_pin(gpio, 0, true)) {
        return 5;
    }

    if (!rv32_gpio_pin_irq_configure(gpio, 0, RV32_GPIO_IRQ_BOTH_EDGES)) {
        return 6;
    }

    (void)rv32_gpio_irq_read_clear(gpio);

    if (!rv32_gpio_pin_write(gpio, 0, false) || !wait_irq(gpio, 0)) {
        return 7;
    }

    if (rv32_gpio_irq_contains(rv32_gpio_irq_read_clear(gpio), 0)) {
        return 8;
    }

    if (!rv32_gpio_pin_write(gpio, 0, true) || !wait_irq(gpio, 0)) {
        return 9;
    }

    if (!rv32_gpio_pin_direction(keys, 1, RV32_GPIO_OUTPUT_PIN) ||
        !rv32_gpio_pin_write(keys, 1, true) || !wait_pin(keys, 1, true)) {
        return 10;
    }

    (void)rv32_gpio_pin_irq_configure(gpio, 0, RV32_GPIO_IRQ_DISABLED);
    (void)rv32_gpio_pin_direction(gpio, 0, RV32_GPIO_INPUT);
    (void)rv32_gpio_pin_direction(keys, 1, RV32_GPIO_INPUT);

    puts("GPIO constructors, pin indices, read-clear IRQ and two instances: PASS");

    return 0;
}
