# DE0-CV stepper demonstration (C and Rust)

Open either `c/` or `rust/` as the VS Code project, then reopen in its Dev
Container. Both projects select `project.platform = "periph-de0-cv"` and generate
their drivers from that platform. Do not open a nested `vendor/*/example` when
you intend to run the motor application.

## Wiring and enabling movement

The example targets a four-input motor driver, such as a ULN2003 with a
compatible unipolar stepper. It does not drive motor windings directly.
Use the motor driver's rated supply and connect its logic ground to board
ground. The FPGA GPIO uses 3.3 V logic.

The proposed IN1, IN2, IN3 and IN4 mapping is GPIO group 0, logical pins
`0, 1, 2, 3`, respectively. On this platform those are `GPIO_0[0..3]`, not
physical header positions 0 through 3. Check the board header diagram and the
actual wiring, or change `MOTOR_PINS` in the source accordingly.

`RUN_MOTOR` initially equals `false`. This runs a non-driving check of the GPIO
handle and CLINT timer. Set it to `true` only after confirming the mapping.
The program then produces 1,024 half-steps forward, pauses, produces 1,024
half-steps backward and releases all four coils. The exact mechanical angle
depends on the motor and gearbox. The pattern is `1, 3, 2, 6, 4, 12, 8, 9`.

The platform's CLINT increments at 1 MHz. Each phase lasts at least 2,000 ticks
(2 ms); software overhead adds slightly to this interval. This is independent
of the 50 MHz processor clock. Change `STEP_TICKS` if the platform or motor
timing changes.

## Running

1. Open `src/main.c` or `src/main.rs`.
2. Use **RV32: Program FPGA** for the first load. A valid hardware cache avoids
   repeated Quartus builds.
3. Use **RV32: Fast Update FPGA** after source-only changes.
4. Check the program output for the completion message. The non-driving check
   does not prove movement or correct motor wiring.

The `periph-de0-cv` platform has no complete SoC/external-device simulation
model. Its Simulate command reports this limitation. RTL GPIO regression and
runtime tests on the modular simulation platform are separate checks; neither
replaces observing the motor on the physical board.

## Abstractions

C constructs `stepper_t` using `stepper_new`, which validates its numbered pins
and peripheral handles before configuring outputs. Rust constructs `Stepper`
from validated `GPIO` and `Clint` handles and numbered `Pin` values. Its lifetime
keeps the GPIO owner alive, and `Drop` releases coils on normal scope exit or a
returned error. It cannot guarantee cleanup after power loss or an aborting
panic. Neither application contains a peripheral base address.
