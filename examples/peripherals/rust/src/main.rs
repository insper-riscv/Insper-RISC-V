#![no_std]
#![no_main]

use rv32_runtime::{entry, prelude::*};
use insper_riscv_gpio::{GPIO, Instance, Direction};
use insper_riscv_timer::Timer;
use insper_riscv_display::Display;
use insper_riscv_clint::Clint;
use insper_riscv_plic::Plic;
use insper_riscv_uart::{Uart, Instance as UartInstance};

entry!(main);

fn main() {
    let mut values = vec![1_u32, 2, 3];
    values.push(4);
    let message = String::from("Rust heap");
    assert_eq!(values.iter().sum::<u32>(), 10);
    println!("{}: {:?}", message, values);

    let gpio = GPIO::from_platform(Instance::Switches).expect("switches");
    let keys = GPIO::from_platform(Instance::Keys).expect("keys");
    assert_eq!(keys.pin_count(), 4);
    let mut pin = gpio.get(0).expect("pin 0");
    pin.set_direction(Direction::Output).expect("direction");
    pin.set_high().expect("high");
    pin.set_low().expect("low");
    pin.set_direction(Direction::Input).expect("input");

    let mut timer = Timer::new().expect("timer");
    timer.stop();
    timer.set_divider(1).expect("divider");
    timer.set_top(100);
    timer.one_shot(true);
    timer.load(0);
    timer.start();
    timer.stop();

    let mut display = Display::new().expect("display");
    let saved = display.read();
    display.write_digit(0, 10).expect("digit");
    let digit = display.read_digit(0).expect("read digit");
    display.write(saved);
    assert_eq!(digit, 10);

    let mut clint = Clint::new().expect("clint");
    clint.set_deadline(u64::MAX);
    clint.set_software_interrupt(true);
    assert!(clint.software_interrupt_pending());
    clint.set_software_interrupt(false);

    let mut plic = Plic::new().expect("plic");
    plic.set_priority(1, 1).expect("priority");
    plic.set_threshold(0).expect("threshold");
    plic.enable(1, false).expect("disable source");

    let mut serial = Uart::new_for(UartInstance::Serial).expect("serial UART");
    let mut jtag = Uart::new_for(UartInstance::Jtag).expect("JTAG UART");
    let _status = serial.status();
    let _idle = jtag.tx_idle();

    println!("Rust peripherals: PASS");
}
