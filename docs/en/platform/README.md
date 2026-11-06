# Platforms

A platform wires the core, the memories and the peripherals into something that runs. This repository has five.

| Platform | Path | Description |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `src/cyclone-v/de0-cv/` | The DE0-CV board (Cyclone V), with the BOOT_ROM in the core and the FLASH and the SDRAM behind the caches |
| [external-data](external-data.md) | `src/cyclone-v/external-data/` | The DE0-CV board, with the BOOT_ROM and the two-port FLASH inside the FPGA and the SDRAM behind the data cache |
| [internal-mem](internal-mem.md) | `src/simulation/internal-mem/` | Simulation-only platform, with BOOT_ROM, FLASH and RAM inside the FPGA |
| [modular](modular.md) | `src/simulation/modular/` | Configurable simulation top that covers the 16 combinations of internal or external ROM and RAM with and without instruction and data caches, with memories and caches sized in powers of two, and runs the programs of the Tests repository |
| [template](template.md) | `src/simulation/template/` | Minimal model platform (internal RAM and ROM, optional UART over JTAG, `rv32i` profile) that the new architecture guide copies |

The documents common to both describe what the program sees.

| Document | Content |
| :--- | :--- |
| [memoria.md](memoria.md) | BOOT_ROM, FLASH and RAM memory architecture |
| [boot.md](boot.md) | Boot state, the picolibc `crt0` and `boot_rom.S` |
| [contrato-de-entrada.md](contrato-de-entrada.md) | Entry contract between the BOOT_ROM and the firmware |
| [runtime.md](runtime.md) | C runtime, platform file, `stdout` and Spike |
| [atualizacao-de-programa.md](atualizacao-de-programa.md) | Replacing one program with another and the boot handoff between tests |
| [timing/README.md](timing/README.md) | Timing baseline (Fmax, critical paths), cycles per instruction and clock domain crossings of the `de0-cv` |
