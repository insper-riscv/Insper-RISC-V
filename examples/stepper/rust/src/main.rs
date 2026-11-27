#![no_std]
#![no_main]

use insper_riscv_clint::Clint;
use insper_riscv_gpio::{Direction, GPIO, Pin};
use rv32_runtime::{entry, prelude::*};

entry!(main);

// Enable only after matching IN1..IN4 to the physical wiring.
const RUN_MOTOR: bool = false;
const MOTOR_PINS: [usize; 4] = [0, 1, 2, 3];
const PHASES: [u8; 8] = [1, 3, 2, 6, 4, 12, 8, 9];
const STEP_COUNT: usize = 1024;
// periph-de0-cv: the CLINT ticks at 1 MHz. 2000 ticks = 2 ms.
const STEP_TICKS: u64 = 2_000;

struct Stepper<'a> {
    pins: [Pin<'a>; 4],
    timer: Clint,
    phase: usize,
}

impl<'a> Stepper<'a> {
    fn new(gpio: &'a GPIO, timer: Clint, indices: [usize; 4]) -> Result<Self, &'static str> {
        for i in 0..indices.len() {
            if indices[..i].contains(&indices[i]) {
                return Err("duplicate motor pin");
            }
        }

        let mut pins = [
            gpio.get(indices[0]).map_err(|_| "invalid motor pin")?,
            gpio.get(indices[1]).map_err(|_| "invalid motor pin")?,
            gpio.get(indices[2]).map_err(|_| "invalid motor pin")?,
            gpio.get(indices[3]).map_err(|_| "invalid motor pin")?,
        ];

        // The FPGA reset preloads the output register with zero.
        for pin in &mut pins {
            pin.set_direction(Direction::Output);
            pin.set_low().map_err(|_| "cannot initialize motor output")?;
        }

        Ok(Self {
            pins,
            timer,
            phase: 0,
        })
    }

    fn release(&mut self) {
        for pin in &mut self.pins {
            let _ = pin.set_low();
        }
    }

    fn move_steps(&mut self, forward: bool, steps: usize) -> Result<(), &'static str> {
        for _ in 0..steps {
            let pattern = PHASES[self.phase];

            for (coil, pin) in self.pins.iter_mut().enumerate() {
                pin.write(pattern & (1 << coil) != 0)
                    .map_err(|_| "motor output changed direction")?;
            }

            wait_ticks(&mut self.timer, STEP_TICKS);
            self.phase = (self.phase + if forward { 1 } else { 7 }) % PHASES.len();
        }

        self.release();

        Ok(())
    }
}

impl Drop for Stepper<'_> {
    fn drop(&mut self) {
        self.release();
    }
}

fn wait_ticks(timer: &mut Clint, ticks: u64) {
    let start = timer.time();

    while timer.time().wrapping_sub(start) < ticks {
        core::hint::spin_loop();
    }
}

fn run() -> Result<(), &'static str> {
    let gpio = GPIO::group(0).map_err(|_| "GPIO unavailable")?;
    let mut timer = Clint::new().map_err(|_| "CLINT unavailable")?;
    let before = timer.time();

    wait_ticks(&mut timer, 1_000);

    if timer.time() <= before || gpio.pin_count() < 4 {
        return Err("timer or GPIO width check failed");
    }

    if !RUN_MOTOR {
        println!("Rust: GPIO and CLINT available; timer PASS; motor outputs not enabled");

        return Ok(());
    }

    let mut motor = Stepper::new(&gpio, timer, MOTOR_PINS)?;

    println!("Rust: 1024 half-steps forward");
    motor.move_steps(true, STEP_COUNT)?;
    wait_ticks(&mut motor.timer, 250_000);
    println!("Rust: 1024 half-steps backward");
    motor.move_steps(false, STEP_COUNT)?;
    println!("Rust: stepper sequence PASS; coils released");

    Ok(())
}

fn main() {
    if let Err(error) = run() {
        println!("Rust: {}", error);
        rv32_runtime::exit(1);
    }
}
