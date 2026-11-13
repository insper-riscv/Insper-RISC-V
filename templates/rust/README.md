# RV32 Rust application

Requires matching SDK/extension 0.9.1. Reopen in the Dev Container, prepare, then
simulate or run on FPGA. Edit src/main.rs and select platform/cpu_profile in
rv32.toml. Setup generates the runtime and enabled drivers in vendor/ and adds
Cargo path dependencies without replacing user source or custom dependencies.

This is no_std firmware, with an ordinary fn main() connected by entry!(main).
rv32_runtime::prelude::* provides Vec, String, Box, vec!, format!, print! and
println!. The global allocator uses the C heap, preserving arbitrary alignment.
No OS, threading, filesystem, networking or full Rust std is provided.

Main can return (), i32, or Result<(), E: Debug>. Returning ends through the C
startup; runtime::exit(code) terminates explicitly. Panics print once and loop
for debugging; there is no unwinding. Allocation failure uses the same panic
policy. A panic in simulation times out; it is never reported as success.

Allocation/output/configuration are foreground operations; serialize access
with interrupts. The runtime has allocator and panic-handler default features;
disable those features if supplying your own global allocator/panic handler.

Driver APIs use numbered pins/digits/sources and typed modes. They contain
compiling no_run documentation examples; cargo doc --no-deps generates the API.
Generated vendor/NAME/example folders are independent Rust projects. Copy them
before editing; refresh protects edited managed files. Set
 generate_driver_examples = false
under [project] to omit those projects. FLASH examples are read-only.

The SDK installs host Clang/libclang in Rust Dev Containers with driver generation
enabled. This is a build dependency, not software running on the processor.
Use -j 2 for standalone Cargo builds; the container is limited to 8 GiB/no swap.
