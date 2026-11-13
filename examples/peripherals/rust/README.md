# Rust peripherals project

Open this folder in VS Code and reopen in its Dev Container. Prepare the project,
then simulate. This project selects modular + rv32im_zicsr_irq so GPIO, TIMER,
DISPLAY, both UARTs, CLINT and PLIC are present. It demonstrates Vec/String,
ordinary Rust main(), formatting and address-free driver constructors.

The SDK generates vendor sources and Cargo path dependencies. Each driver has
Rust documentation examples for its operations; `cargo doc --no-deps --open`
opens them. Independent per-driver projects appear in vendor/NAME/example.

FLASH is absent on modular; its generated physical-platform example reads status
only. See that driver's documentation for explicit storage-changing operations.
The default panic handler prints once and loops, so a failed assertion leads to a
simulation timeout with diagnostics in the debug log. It does not silently succeed.
