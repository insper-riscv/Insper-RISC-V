"""Detect empty or incomplete processor submodules before SDK generation."""

import sys
from pathlib import Path

REQUIRED_SOURCES = (
    "Core/profiles/matrix.yaml",
    "Core/src/core/core.vhd",
    "Core/src/common/src/config_pkg.vhd",
    "Memory/src/RAM/SoC/ram_simulation.vhd",
    "Memory/src/common/src/utils_pkg.vhd",
    "Peripherals/src/GPIO/soc/driver/c/driver.yaml",
    "Peripherals/src/common/src/utils_pkg.vhd",
    "Common-Components/src/utils_pkg.vhd",
)


def check(sdk: Path) -> None:
    """Check real source files, not the empty folders a plain clone creates."""
    missing = [name for name in REQUIRED_SOURCES if not (sdk / name).is_file()]
    if missing:
        command = "git submodule update --init --recursive"
        raise SystemExit(
            f"RV32 SDK processor sources are missing or incomplete ({sdk}):\n  "
            + "\n  ".join(missing)
            + "\nRun on the host, from the processor repository folder:\n  "
            + command
            + "\nThen rerun Prepare Project or reopen the Dev Container."
        )


if __name__ == "__main__":
    check(Path(sys.argv[1]).expanduser().resolve())
