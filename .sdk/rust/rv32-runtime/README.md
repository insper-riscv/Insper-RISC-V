# Bare-metal Rust conveniences

```rust
use rv32_runtime::prelude::*;

let current_val: usize = 42;
let text: String = current_val.to_string();
let mut message = "value=".to_owned();
write!(&mut message, "{}", current_val).unwrap();
assert_eq!(message, "value=42");
```

`ToString` is the standard trait from `alloc::string`, implemented for types
that implement `core::fmt::Display`. It was previously missing from our
prelude; it does not need a new implementation or an operating system.
`ToOwned` is also included, allowing borrowed strings/slices to become owned
values. `String` and `Vec` keep their normal Rust methods, including parsing,
iteration and collection.

The prelude provides:

| API | Purpose |
| --- | --- |
| `String`, `Vec`, `Box` | Owned text, vectors and heap storage |
| `ToString`, `ToOwned` | Standard owned-value conversions |
| `format!`, `vec!` | Allocate formatted strings and vectors |
| `write!`, `writeln!`, `FmtWrite` | Format into a String or another `core::fmt::Write` sink |
| `Cow`, `Rc` | Borrow-or-own values and single-threaded shared ownership |
| `BTreeMap`, `BTreeSet`, `VecDeque` | Ordered maps/sets and double-ended queues |
| `print!`, `println!` | Existing C-runtime-backed program output |
| `alloc` | Standard allocation namespace for explicit imports |

With the prelude imported, `use alloc::string::ToString;` is supported too.
Without it, use `rv32_runtime::alloc::string::ToString` or Rust's usual
`extern crate alloc; use alloc::string::ToString;`.

These APIs reuse Rust's `core`/`alloc` implementations and the existing C-backed
global allocator. They add no crate dependencies and require no atomic
instructions on RV32I/RV32IM. Imports of unused APIs do not allocate storage.
The SDK refreshes the vendored runtime using its managed-file protection; it
refuses to overwrite an edited generated file.

Native no_std consumer tests cover imports and helper behavior. The SDK's
`rust_addons_integration.py` additionally checks them on RV32I and RV32IM CPU
RTL using `.sdk/tests/fixtures/rust_prelude.rs`.
