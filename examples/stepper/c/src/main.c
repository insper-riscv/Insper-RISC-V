#include "rv32_drivers.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/* Enable only after matching IN1..IN4 to the physical wiring. */
static const bool RUN_MOTOR = false;
static const size_t MOTOR_PINS[4] = {0, 1, 2, 3};
static const uint8_t PHASES[8] = {1, 3, 2, 6, 4, 12, 8, 9};
static const size_t STEP_COUNT = 1024;
/* periph-de0-cv: CLINT runs at 1 MHz, so 2000 ticks = 2 ms. */
static const uint64_t STEP_TICKS = 2000;

typedef struct {
    rv32_gpio_t gpio;
    rv32_clint_t timer;
    size_t pins[4];
    size_t phase;
    bool valid;
} stepper_t;

static stepper_t stepper_new(rv32_gpio_t gpio, rv32_clint_t timer,
                             const size_t pins[4])
{
    stepper_t motor = {.gpio = gpio, .timer = timer, .phase = 0, .valid = false};

    if (!rv32_gpio_valid(gpio) || !rv32_clint_valid(timer)) {
        return motor;
    }

    for (size_t i = 0; i < 4; ++i) {
        if (pins[i] >= gpio.pin_count) {
            return motor;
        }

        for (size_t j = 0; j < i; ++j) {
            if (pins[i] == pins[j]) {
                return motor;
            }
        }

        motor.pins[i] = pins[i];
    }

    /* This demo owns its GPIO group. Preload zero before enabling outputs. */
    rv32_gpio_write(gpio, 0);

    for (size_t i = 0; i < 4; ++i) {
        if (!rv32_gpio_pin_direction(gpio, pins[i], RV32_GPIO_OUTPUT_PIN)) {
            return motor;
        }
    }

    motor.valid = true;

    return motor;
}

static bool stepper_release(stepper_t *motor)
{
    bool ok = true;

    for (size_t i = 0; i < 4; ++i) {
        ok = rv32_gpio_pin_write(motor->gpio, motor->pins[i], false) && ok;
    }

    return ok;
}

static void wait_ticks(rv32_clint_t timer, uint64_t ticks)
{
    uint64_t start = rv32_clint_time(timer);

    while (rv32_clint_time(timer) - start < ticks) {
        /* Wait on the CLINT, independently of compiler optimization. */
    }
}

static bool stepper_move(stepper_t *motor, bool forward, size_t steps)
{
    if (!motor->valid) {
        return false;
    }

    for (size_t step = 0; step < steps; ++step) {
        uint8_t pattern = PHASES[motor->phase];

        for (size_t coil = 0; coil < 4; ++coil) {
            if (!rv32_gpio_pin_write(motor->gpio, motor->pins[coil],
                                     (pattern & (1u << coil)) != 0)) {
                (void)stepper_release(motor);

                return false;
            }
        }

        wait_ticks(motor->timer, STEP_TICKS);
        motor->phase = (motor->phase + (forward ? 1u : 7u)) % 8u;
    }

    return stepper_release(motor);
}

int main(void)
{
    rv32_gpio_t gpio = rv32_gpio_platform_group_new(0);
    rv32_clint_t timer = rv32_clint_platform_new();

    if (!rv32_gpio_valid(gpio) || !rv32_clint_valid(timer)) {
        puts("C: GPIO/CLINT unavailable on this platform");

        return 1;
    }

    uint64_t before = rv32_clint_time(timer);

    wait_ticks(timer, 1000);

    if (rv32_clint_time(timer) <= before || gpio.pin_count < 4) {
        return 2;
    }

    if (!RUN_MOTOR) {
        puts("C: GPIO and CLINT available; timer PASS; motor outputs not enabled");

        return 0;
    }

    stepper_t motor = stepper_new(gpio, timer, MOTOR_PINS);

    puts("C: 1024 half-steps forward");

    if (!stepper_move(&motor, true, STEP_COUNT)) {
        return 3;
    }

    wait_ticks(timer, 250000);
    puts("C: 1024 half-steps backward");

    if (!stepper_move(&motor, false, STEP_COUNT)) {
        return 4;
    }

    puts("C: stepper sequence PASS; coils released");

    return 0;
}
