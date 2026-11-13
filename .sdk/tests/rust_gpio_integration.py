"""Run the address-free Rust GPIO wrapper through bindgen, C and actual CPU RTL."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

SDK = Path(__file__).resolve().parents[2]
SOURCE = r"""
#![no_std]
#![no_main]

use insper_riscv_gpio::{Direction, GPIO, GPIOError, Instance};

unsafe extern "C" {
    fn puts(message: *const u8) -> i32;
    fn _exit(code: i32) -> !;
}

fn exercise() -> Result<(), GPIOError> {
    let gpio = GPIO::from_platform(Instance::Switches)?;
    let keys = GPIO::from_platform(Instance::Keys)?;
    if gpio.pin_count() != 10 || keys.pin_count() != 4 {
        return Err(GPIOError::InvalidBuilder);
    }
    if GPIO::new(11).is_ok() || gpio.get(10).is_ok() || keys.get(4).is_ok() {
        return Err(GPIOError::InvalidPinIndex);
    }
    let mut pin = gpio.get(0)?;
    pin.set_direction(Direction::Output);
    pin.set_high()?;
    let mut observed = false;
    for _ in 0..2048 {
        if pin.is_high() {
            observed = true;
            break;
        }
    }
    if !observed {
        panic!("GPIO loopback did not settle");
    }
    pin.toggle()?;
    observed = false;
    for _ in 0..2048 {
        if pin.is_low() {
            observed = true;
            break;
        }
    }
    if !observed {
        panic!("GPIO loopback did not settle");
    }
    pin.set_low()?;
    pin.set_direction(Direction::Input);
    Ok(())
}

#[unsafe(no_mangle)]
pub extern "C" fn main() -> i32 {
    match exercise() {
        Ok(()) => {
            unsafe { puts(c"Rust GPIO platform bindings: PASS".as_ptr().cast()) };
            0
        }
        Err(_) => 1,
    }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    unsafe { _exit(2) }
}
"""


def main() -> None:
    """Test both ISA targets and reconfigure the same Cargo build directory."""
    with tempfile.TemporaryDirectory(prefix="rust-gpio-", dir=SDK) as temp:
        root = Path(temp)
        shutil.copytree(SDK / "templates/common", root, dirs_exist_ok=True)
        shutil.copytree(SDK / "templates/rust", root, dirs_exist_ok=True)
        (root / "src/main.rs").write_text(SOURCE)
        manifest = root / "Cargo.toml"
        dependency = (
            SDK / "Peripherals/src/GPIO/soc/driver/rust/insper-riscv-gpio"
        )
        manifest.write_text(
            manifest.read_text()
            + f'\ninsper-riscv-gpio = {{ path = "{dependency}" }}\n'
        )
        for profile in ("rv32i", "rv32im"):
            (root / "rv32.toml").write_text(
                '[project]\nname="rust-gpio"\nlanguage="rust"\n'
                f'platform="modular"\ncpu_profile="{profile}"\n'
                "generate_drivers=true\ngenerate_driver_examples=false\n"
            )
            result = subprocess.run(
                [
                    str(SDK / "scripts/rv32-project"),
                    "--project",
                    str(root),
                    "simulate",
                ],
                env=dict(
                    os.environ,
                    RV32_SDK_ROOT=str(SDK),
                    CARGO_NET_OFFLINE="true",
                    CARGO_BUILD_JOBS="2",
                ),
                capture_output=True,
                timeout=300,
            )
            if (
                result.returncode
                or result.stderr
                or result.stdout != b"Rust GPIO platform bindings: PASS\n"
            ):
                print(profile, result.returncode, result.stdout, result.stderr)
                log = root / "logs/rv32/simulate-latest.log"
                if log.exists():
                    print(log.read_text()[-12000:])
                raise SystemExit(1)
            print(
                "PASS Rust/C GPIO platform integration on", profile, flush=True
            )


if __name__ == "__main__":
    main()
