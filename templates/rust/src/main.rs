#![no_std]
#![no_main]

use rv32_runtime::{entry, prelude::*};

entry!(main);

fn main() {
    let mut values = vec![1_u32, 2, 3];
    values.push(4);

    let message = String::from("Hello from an RV32 Rust project.");
    println!("{}", message);
    println!("values = {:?}", values);
}
