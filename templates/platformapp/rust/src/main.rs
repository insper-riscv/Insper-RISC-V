#![no_std]
#![no_main]

use rv32_runtime::{entry, prelude::*};

entry!(main);

fn main() {
    // alloc, Vec and String are available through the prelude when needed.
    println!("Hello from a PlatformApp Rust project.");
}
