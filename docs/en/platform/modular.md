# `modular` platform: memories and caches in any combination

## 1. What it is

A single simulation top, `modular_sim_top` (`src/simulation/modular/`), instantiates the [SoC](../soc/soc.md) and adds the three-phase clock and the chip models to it. The SoC builds the core with four independent choices: the FLASH and the RAM direct or on the bus, and the instruction cache and the data cache present or not. A memory on the bus sits in a simulated chip model of configurable size. It serves any variation of the core (the `has_*` generics pick the extensions), runs the programs of the test repositories (section 7) and is the base of the ACT4 simulation of the 60 profiles.

The top also wires, through generics, optional board peripherals (switches, buttons, displays and the two UARTs) that the [ten platforms](dez-plataformas.md) use; without them the peripheral window table has only the CLINT and the external controller, when the interrupts are on.

Every combination has the BOOT_MEMORY, the boot memory that leaves the CPU in a known state, and the ROM always starts right after it.

## 2. The choices and the architectures

| Choice | Generic | Values |
| :--- | :--- | :--- |
| FLASH | `rom_external` | direct (false) or on the bus (true) |
| RAM | `ram_external` | direct (false) or on the bus (true) |
| Instruction cache | `has_icache` | without or with |
| Data cache | `has_dcache` | without or with |

The caches speak the bus protocol, so a cache exists only on the bus side: the instruction cache requires `rom_external` and the data cache requires `ram_external`, the strict rule of the `check_isa` of the `config_pkg`. Of the 16 combinations of `rom_external`, `ram_external`, `has_icache` and `has_dcache`, 9 are valid and 7 are refused.

| `rom_external` | `ram_external` | Valid cache combinations |
| :---: | :---: | :--- |
| false | false | no cache |
| false | true | no cache or only the data cache |
| true | false | no cache or only the instruction cache |
| true | true | all four: no cache, only instruction, only data or both |

Each memory is in the core or on the bus, and the simulated chip plays it when it is on the bus. The 9 valid combinations give distinct structures, one per pair of sides.

| FLASH side | Instruction fetch | FLASH data |
| :--- | :--- | :--- |
| Direct | Two-port internal FLASH | Second port of the internal FLASH |
| On the bus, no cache | Fetch bridge, which keeps only the current line | Data router, arbiter and FLASH chip |
| On the bus, with cache | Instruction cache | Data router, arbiter and FLASH chip |

| RAM side | Data access |
| :--- | :--- |
| Direct | Internal RAM of the core |
| On the bus, no cache | Interconnect, word by word, straight to the RAM chip |
| On the bus, with cache | Interconnect, data cache and RAM chip |

The four architectures that the test repositories and ACT4 use are the following.

| Architecture | `--memory` | ROM | RAM | Caches |
| :--- | :--- | :--- | :--- | :--- |
| A | `rom=int,ram=int,icache=off,dcache=off` | internal | internal | none |
| B | `rom=int,ram=ext,icache=off,dcache=on` | internal | external | data |
| C | `rom=ext,ram=int,icache=on,dcache=off` | external | internal | instruction |
| D | `rom=ext,ram=ext,icache=on,dcache=on` | external | external | both |

When not given, the `has_icache` and `has_dcache` generics are `rom_external` or `HAS_ICACHE` of the package, and `ram_external` or `HAS_DCACHE` of the package. The four original models (`integrated`, `external-data`, `external-instruction` and `external`) remain the architectures A, B, C and D, chosen by `rom_external` and `ram_external` alone.

## 3. Data paths

### 3.1. Data via port

When the FLASH or the RAM is on the bus, the core has the external data port. The interconnect splits off the peripherals of the window table, ends in an error what has no slave and hands the request to the data cache or, without one, straight to the memory side, with the addresses of the map and one word at a time.

| FLASH on the bus | RAM on the bus | Destination of the data requests |
| :--- | :--- | :--- |
| no | yes | RAM chip |
| yes | no | Data router: the ROM goes to the FLASH chip and what falls outside it answers zero |
| yes | yes | Data router: the ROM goes to the FLASH chip and the rest to the RAM chip |

With the ROM via port, the data router and the FLASH arbiter sit between the core and the chip, and the instruction fetch is the other input of the arbiter. With both via port, a second router sends the fetch to the FLASH or to the RAM chip.

### 3.2. Data read without a data cache

The write-back stage (WB) reads the data of a load after the request ends, and by then the address of the core has changed. The data cache keeps the data, but without it the data router would choose the region by the new address and return the wrong data. The data router then uses `hold_rdata`, which makes the data read follow the region of the last completed request (documented in the `mem_region_router` of Memory).

### 3.3. Memory on the bus with and without a cache

| Combination | How the simulation builds it |
| :--- | :--- |
| Memory on the bus with a cache | The cache sits over the chip model, with the latency of the chip generics; the cache only adds latency on a miss |
| FLASH on the bus without an instruction cache | The fetch bridge reads the FLASH chip, which serves word and line requests |
| RAM on the bus without a data cache | The interconnect talks to the RAM chip with word requests |

Both simulated chips serve word requests without a cache. The FLASH and the SDRAM of the DE0-CV board stay behind the caches in the board top, which does not change with the choice.

## 4. Memory map

The map comes from generics and holds for the core and for the top. The default value of each one is in `src/simulation/modular/platform.yaml`, which is the source of the map, and `riscv-tools generate-memory-map` carries it to the `modular_map_pkg.vhd` package that the top uses, to the `memory_map.h` header of the runtime, to the linker specs file and to the linker script of the BOOT_MEMORY (`make generate`, and `make generate-check` verifies it in CI). The values are those of the ACT4 simulation. The package also carries the `HAS_*` of the platform (`HAS_E` among them), which the top does not pass on as generics: the core and the SoC read the base and the extensions from the `config_pkg`. It also carries `BOOT_MEMORY_BITS` (12) and `FLASH_STORAGE_BYTES` (1048576). The default choice is the `memory` section of `platform.yaml` (both memories in the core, no cache), which yields `FLASH_ON_BUS`, `RAM_ON_BUS`, `HAS_ICACHE` and `HAS_DCACHE`; `--memory` of `riscv-tools` replaces it for one run, and each test overrides it through the parameters of `tests.json`. The checks of `riscv-tools check-memory-map` (`checks` of `platform.yaml`) cover the hand-written copy of the RAM base in the tests and the platform header of the test repository. `HAS_ZIMOP`, `HAS_ZICOND` and `HAS_SSCOFPMF` come from the package, turned on by `core.extensions` of `platform.yaml`; the last one needs `Zihpm` and `Interrupts` in `core.extensions`.

| Region | Start | End | Generics |
| :--- | :--- | :--- | :--- |
| BOOT_MEMORY | `0x00000000` | `0x00001000` | `boot_memory_size_bytes` |
| FLASH | right after the BOOT_MEMORY, `0x00001000` | `0x00100000` | `rom_end_kib` |
| RAM | `0x00100000` | `0x00200000` | `ram_base_kib`, `ram_end_kib` |
| Peripherals | the windows of the table of the map package, from `0x80000000` | | `periph_count`, `periph_bases`, `periph_masks` |

The limits are in KiB. The words that the host and the program share (the standard output, `tohost` and `fromhost`) sit at the top of the RAM, in the last 4 KiB page, which the caches bypass. The BOOT_MEMORY clears those words and jumps to the start of the ROM.

## 5. Sizes

Every size is a power of two, checked at elaboration time by the `log2_exact` of `utils_pkg`, and a value outside the rule fails the elaboration.

| Generic | Unit | Default |
| :--- | :--- | :--- |
| `boot_memory_size_bytes` | bytes | 4096, multiple of 1 KiB |
| `rom_size_bytes` | bytes | 1048576 (1 MB) |
| `ram_size_bytes` | bytes | 1048576 (1 MB) |
| `icache_size_bits` | bits | 4096 (4 kbit) |
| `dcache_size_bits` | bits | 4096 (4 kbit) |

The `flash_first_latency`, `flash_next_latency` and `ext_ram_latency` generics give the latency of the chips in clock edges.

## 6. How to use

The images enter through the `boot_memory_file`, `rom_file` and `ram_file` generics, one 32-bit word per line in hexadecimal.

| Port | Use |
| :--- | :--- |
| `i_clk`, `i_rst` | Base clock and reset |
| `i_dbg_word_addr`, `o_dbg_word_data` | Reads a word of the RAM chip by index, without going through the caches. It is how the testbench sees `tohost` when it is in the chip |
| `o_ram_en`, `o_ram_wren`, `o_ram_addr`, `o_ram_wdata`, `o_ram_byteena` | The bus of the internal RAM of the core, which the testbench watches when the RAM is in the core |

GHDL allocates the memory arrays on the stack, so simulating 1 MB memories needs the stack limit raised (`ulimit -s unlimited` or `--max-stack-alloc=0`).

## 7. Programs of the test repositories

`src/simulation/modular/config.yaml` takes the platform to `riscv-tools`: the runtime (`boot_memory.S`, `_exit.c`, `stdio.c`, `spike_exit.S`), the linker script and the specs file generated from the map, the cocotb testbench and the list of VHDL sources. Nothing of the map is written in it. The profile and the memories of a run come from the command line, without changing any versioned file.

```bash
ulimit -s unlimited
riscv-tools --profile rv32im_zicclsm_zicntr_zihpm_zifencei \
  --memory rom=ext,ram=int,icache=on,dcache=off \
  platform sync --prefix Insper-RISC-V \
  --source Insper-RISC-V/src/simulation/modular/config.yaml \
  --output tools/riscv_build/config.generated.yaml
```

The command writes, in the test repository, `config.generated.yaml` with the `FLASH_ON_BUS`, `RAM_ON_BUS`, `HAS_ICACHE` and `HAS_DCACHE` generics and the text of the `config_pkg` of the profile in `sim.config_pkg`, which the simulation compiles in place of the `config_pkg.vhd` of the platform (the base and the extensions of the profile are not generics of the top). A file that extends it and points `paths.include_dir` to the header directory of the modular platform (`tools/riscv_build/include-modular` of the test repository, with the map of section 4) compiles and simulates the programs of `c/` and `asm/` with `compile --emit hex` and `sim`.

| Item | Behavior on the modular platform |
| :--- | :--- |
| BOOT_MEMORY | Clears the standard-output header, `tohost` and `fromhost` and jumps to the ROM; it does not run `fence.i`, because the simulation starts from empty caches |
| Standard output | Linear 1 KiB buffer at the top of the RAM |
| UART and display | No peripheral wired: the `uart-echo`, `uart-tx` and `uart-errors` programs do not apply |
| Testbench | Watches the bus of the RAM of the core and the external bus at the same time, detects the `tohost` write and, in tests with a `golden.json`, checks the RAM rebuilt from the writes |
| Time limit | 2000000 core cycles |

## 8. Verification

`tests/python/runner.py` runs a minimal program on the structures of section 2. The program stores `0x5A` at the RAM base, reads it back, adds 1 and stores the result in the next word, and the test checks the two words in the RAM of the core or in the external chip. Every entry uses the same two images, `boot_to_rom.hex` and `rom_program.hex`, generated by `tests/python/gen_modular_images.py`.

| `tests.json` entry | ROM | RAM |
| :--- | :--- | :--- |
| `ModularIntegrated` (A) | in the core | in the core |
| `ModularExternalData` (B) | in the core | via port, data cache |
| `ModularExternalInstruction` (C) | via port, instruction cache | in the core |
| `ModularExternal` (D) | via port, instruction cache | via port, data cache |
| `ModularRomBridge` | via port, fetch bridge | in the core |
| `ModularRamDirect` | in the core | via port, direct |
| `ModularBridgeDirect` | via port, fetch bridge | via port, direct |
| `ModularBridgeDcache` | via port, fetch bridge | via port, data cache |
| `ModularIcacheDirect` | via port, instruction cache | via port, direct |
| `ModularBridgeCaches` | via port, instruction cache | via port, data cache |
| `ModularInterrupts` | in the core, with `HAS_ZICSR` of the `config_pkg` and the CLINT in the peripheral window | in the core |

The entries that extend `ModularIntegrated` (`extends` in `tests.json`) inherit the list of sources and change only the parameters. `make check-tops` elaborates the top and `make check-generics` checks that the top declares every `HAS_*` of the generated package.

`ModularInterrupts` runs the `integrated` model with `HAS_ZICSR` on in the `config_pkg` and the `rom_irq_program.hex` image: the program writes the largest value to `mtimecmp`, reads `mip` (MTIP low), arms `mtimecmp` a few ticks ahead of `mtime` and waits for the MTIP bit of `mip`. The `mtimecmp` of the CLINT is cleared synchronously and the clock generator stops the clocks in reset, so the program writes it before reading `mip`.
