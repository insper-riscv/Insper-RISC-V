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

The safe driver crates now use the 0.2 interfaces. GPIO direction changes and
reads are infallible after constructing a valid pin. Timer dividers use
`NonZeroU32`. Display operations use a validated `Digit` and `HexDigit`, and PLIC
operations use a validated source handle. A claimed interrupt is completed by
consuming its claim token. Constructors and newly supplied numeric inputs still
report validation errors; UART readiness and flash busy remain runtime outcomes.

See `Peripherals/RUST-DRIVER-INVARIANTS.md` in the SDK repository for migration
examples and the GPIO aliasing constraints. Regenerate vendor files through the
SDK before compiling an existing project against the revised APIs.
