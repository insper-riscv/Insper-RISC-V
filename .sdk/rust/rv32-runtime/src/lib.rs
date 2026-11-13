//! Minimal bare-metal conveniences using the platform's C runtime.
//! Allocation and printing are for foreground code: libc/stdout are not IRQ locks.
#![no_std]

extern crate alloc;

pub mod allocator;

use core::fmt::{self, Write};

unsafe extern "C" {
    fn putchar(byte: i32) -> i32;
    fn _exit(code: i32) -> !;
}

#[cfg(all(feature = "allocator", target_os = "none"))]
#[global_allocator]
static ALLOCATOR: allocator::LibcAllocator = allocator::LibcAllocator::new();

/// Common owned containers and output macros.
pub mod prelude {
    pub use crate::{print, println};
    pub use alloc::{boxed::Box, format, string::String, vec, vec::Vec};
}

struct Console;

impl Console {
    const fn new() -> Self {
        Self
    }
}

impl Write for Console {
    fn write_str(&mut self, text: &str) -> fmt::Result {
        for byte in text.bytes() {
            if unsafe { putchar(i32::from(byte)) } < 0 {
                return Err(fmt::Error);
            }
        }
        Ok(())
    }
}

#[doc(hidden)]
pub fn _print(arguments: fmt::Arguments<'_>) {
    let _ = Console::new().write_fmt(arguments);
}

/// Print formatted UTF-8 through the same output channel as C stdio.
/// ```no_run
/// rv32_runtime::print!("value={}", 42);
/// ```
#[macro_export]
macro_rules! print {
    ($($arg:tt)*) => { $crate::_print(core::format_args!($($arg)*)) };
}

/// Print a line, including an empty line, without allocating a String.
/// ```no_run
/// rv32_runtime::println!("value={}", 42);
/// rv32_runtime::println!();
/// ```
#[macro_export]
macro_rules! println {
    () => { $crate::print!("\n") };
    ($($arg:tt)*) => { $crate::print!("{}\n", core::format_args!($($arg)*)) };
}

/// Terminate through the platform runtime (including the simulator's tohost).
/// ```no_run
/// rv32_runtime::exit(0);
/// ```
pub fn exit(code: i32) -> ! {
    unsafe { _exit(code) }
}

/// Return types accepted by `entry!`: `()`, `i32`, and `Result<(), E>`.
pub trait Termination {
    /// ```
    /// assert_eq!(rv32_runtime::Termination::exit_code(()), 0);
    /// ```
    fn exit_code(self) -> i32;
}

impl Termination for () {
    fn exit_code(self) -> i32 {
        0
    }
}

impl Termination for i32 {
    fn exit_code(self) -> i32 {
        self
    }
}

impl<E: fmt::Debug> Termination for Result<(), E> {
    fn exit_code(self) -> i32 {
        match self {
            Ok(()) => 0,
            Err(error) => {
                println!("Error: {:?}", error);
                1
            }
        }
    }
}

/// Connect an ordinary Rust function to the C startup's `main` symbol.
/// ```ignore
/// #![no_std]
/// #![no_main]
/// rv32_runtime::entry!(main);
/// fn main() { rv32_runtime::println!("Hello"); }
/// ```
#[macro_export]
macro_rules! entry {
    ($main:path) => {
        #[unsafe(export_name = "main")]
        pub extern "C" fn __rv32_rust_entry() -> i32 {
            $crate::Termination::exit_code($main())
        }
    };
}

/// Print the panic once, then remain available for debugging. No unwinding.
#[cfg(all(feature = "panic-handler", target_os = "none"))]
#[panic_handler]
fn panic(info: &core::panic::PanicInfo<'_>) -> ! {
    println!("panic: {}", info);
    loop {
        core::hint::spin_loop();
    }
}
