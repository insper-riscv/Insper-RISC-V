#![no_std]
#![no_main]

use core::panic::PanicInfo;

unsafe extern "C" {
    fn puts(message: *const u8) -> i32;
    fn _exit(code: i32) -> !;
}

#[unsafe(no_mangle)]
pub extern "C" fn main() -> i32 {
    static MESSAGE: &[u8] = b"Hello from an external RV32 Rust project.\0";

    unsafe {
        puts(MESSAGE.as_ptr());
    }

    0
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    unsafe { _exit(1) }
}
