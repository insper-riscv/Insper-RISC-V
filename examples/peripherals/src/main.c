#include "rv32_drivers.h"

#include <stdio.h>

static bool test_timer(void)
{
    rv32_timer_t timer = rv32_timer_platform_new();

    if (!rv32_timer_valid(timer) || !rv32_timer_set_divider(timer, 1)) {
        return false;
    }

    rv32_timer_stop(timer);
    rv32_timer_set_top(timer, 100);
    rv32_timer_one_shot(timer, true);
    rv32_timer_load(timer, 0);
    (void)rv32_timer_overflow_read_clear(timer);
    rv32_timer_start(timer);

    for (size_t attempt = 0; attempt < 4096; ++attempt) {
        if (rv32_timer_overflow_read_clear(timer)) {
            rv32_timer_stop(timer);

            return rv32_timer_count(timer) == 100 &&
                   !rv32_timer_overflow_read_clear(timer);
        }
    }

    rv32_timer_stop(timer);

    return false;
}

#if RV32_CPU_HAS_INTERRUPTS

static bool test_clint(void)
{
    rv32_clint_t clint = rv32_clint_platform_new();
    uint64_t before = rv32_clint_time(clint);

    rv32_clint_set_deadline(clint, UINT64_MAX);
    rv32_clint_software_irq(clint, true);

    if (!rv32_clint_software_irq_pending(clint)) {
        return false;
    }

    rv32_clint_software_irq(clint, false);

    return !rv32_clint_software_irq_pending(clint) && rv32_clint_time(clint) > before;
}

static bool test_plic_gpio(void)
{
    /* Six source lines and three priority bits in modular_sim_top. */
    rv32_plic_t plic = rv32_plic_platform_new();
    rv32_gpio_t gpio = rv32_gpio_platform_new(RV32_GPIO_SWITCHES_INSTANCE);
    size_t source = RV32_GPIO_SWITCHES_IRQ;

    if (!rv32_plic_set_priority(plic, source, 7) || !rv32_plic_set_threshold(plic, 0) ||
        !rv32_plic_enable(plic, source, true) ||
        !rv32_gpio_pin_direction(gpio, 0, RV32_GPIO_OUTPUT_PIN) ||
        !rv32_gpio_pin_write(gpio, 0, true) ||
        !rv32_gpio_pin_irq_configure(gpio, 0, RV32_GPIO_IRQ_HIGH_LEVEL)) {
        return false;
    }

    bool pending = false;

    for (size_t attempt = 0; attempt < 4096; ++attempt) {
        if (rv32_plic_pending(plic, source)) {
            pending = true;
            break;
        }
    }

    if (!pending || rv32_plic_claim(plic) != source) {
        return false;
    }

    (void)rv32_gpio_pin_irq_configure(gpio, 0, RV32_GPIO_IRQ_DISABLED);
    (void)rv32_gpio_irq_read_clear(gpio);

    if (!rv32_plic_complete(plic, source) || !rv32_plic_enable(plic, source, false)) {
        return false;
    }

    return rv32_plic_claim(plic) == 0;
}

#endif

static bool test_uart_display(void)
{
    rv32_uart_t serial = rv32_uart_platform_new(RV32_UART_SERIAL_INSTANCE);
    rv32_uart_t jtag = rv32_uart_platform_new(RV32_UART_JTAG_INSTANCE);
    rv32_display_t display = rv32_display_platform_new();
    uint8_t digit = 0;
    uint8_t byte = 0;

    rv32_uart_irq_configure(serial, false, false, false);
    rv32_uart_irq_configure(jtag, false, false, false);

    if (!rv32_uart_tx_idle(serial) || !rv32_uart_tx_idle(jtag) ||
        rv32_uart_try_read(serial, &byte) || rv32_uart_try_read(jtag, &byte) ||
        !rv32_uart_try_write(serial, 'S') || !rv32_uart_try_write(jtag, 'J')) {
        return false;
    }

    rv32_display_write(display, 0);

    if (!rv32_display_write_digit(display, 0, 3) ||
        !rv32_display_write_digit(display, 5, 10) ||
        !rv32_display_read_digit(display, 5, &digit)) {
        return false;
    }

    return digit == 10 && rv32_display_read(display) == 0x00a00003;
}

int main(void)
{
    if (!test_timer()) {
        return 1;
    }

#if RV32_CPU_HAS_INTERRUPTS
    if (!test_clint()) {
        return 2;
    }

    if (!test_plic_gpio()) {
        return 3;
    }

#endif

    if (!test_uart_display()) {
        return 4;
    }

    puts("TIMER, serial/JTAG UART and DISPLAY: PASS");

#if RV32_CPU_HAS_INTERRUPTS
    puts("CLINT and PLIC/GPIO: PASS");
#endif

    return 0;
}
