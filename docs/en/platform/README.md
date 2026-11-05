# Platforms

A platform wires the core, the memories and the peripherals into something that runs. This repository has three.

| Platform | Path | Description |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `src/cyclone-v/de0-cv/` | The DE0-CV board (Cyclone V), with the BOOT_ROM in the core and the FLASH and the SDRAM behind the caches |
| [internal-mem](internal-mem.md) | `src/simulation/internal-mem/` | Simulation-only platform, with BOOT_ROM, FLASH and RAM inside the FPGA |
| [modular](modular.md) | `src/simulation/modular/` | Configurable simulation top that covers the `integrated`, `external-data`, `external-instruction` and `external` models, with memories and caches sized in powers of two |

The documents common to both describe what the program sees.

| Document | Content |
| :--- | :--- |
| [memoria.md](memoria.md) | BOOT_ROM, FLASH and RAM memory architecture |
| [boot.md](boot.md) | Boot state, the picolibc `crt0` and `boot_rom.S` |
| [contrato-de-entrada.md](contrato-de-entrada.md) | Entry contract between the BOOT_ROM and the firmware |
| [runtime.md](runtime.md) | C runtime, platform file, `stdout` and Spike |
| [atualizacao-de-programa.md](atualizacao-de-programa.md) | Replacing one program with another and the boot handoff between tests |
