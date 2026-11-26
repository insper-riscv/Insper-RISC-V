# RV32 application

This project is independent from the processor repository. The SDK only needs
to be registered once per workstation, from inside the RV32 checkout:

```bash
bash scripts/install-user.sh --quartus /path/to/altera/std25.1
```

After that, external C and Rust projects can be opened directly with `code .`;
they require no path exports or project-specific `.env` file. Reopen the
project in the Dev Container and run one of the `RV32:` tasks. See
`$RV32_SDK_ROOT/docs/EXTERNAL_PROJECTS.md` for host, Docker, simulation and
FPGA instructions.

## Additional C sources and headers

List source files and header search directories in `rv32.toml`:

```toml
[project]
name = "app"
language = "c"
source = "src/main.c"
sources = ["src/math_utils.c"]
include_dirs = ["include", "vendor/include"]
```

Paths are relative to the project folder. Create each listed directory. Use
`#include "math_utils.h"` in your C files; do not list headers under `sources`.
The same paths apply to all C translation units in simulation and FPGA builds.
Projects that omit `include_dirs` keep their previous behavior.
