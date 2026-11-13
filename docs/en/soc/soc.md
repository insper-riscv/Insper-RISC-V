# SoC (`soc`)

🌐 [Português](../../pt-br/soc/soc.md) · [English](../../en/soc/soc.md)

## 1. What it is

The `soc` entity (`src/soc/soc.vhd`) is the board-independent system on chip. It holds the core, the caches, the memory bridges and routers, the interconnect, the CLINT, the PLIC and the I/O peripherals, and connects everything through interface contracts. It has no board pin, no family name and no chip model. Whoever instantiates it supplies the two clocks, the reset and the backends of the memory regions.

The simulation top `modular_sim_top` instantiates it and adds the three-phase clock generator and the chip models. A board top instantiates the same `soc` and adds the PLL, the pin ring and the controllers of the real chips. All the SoC logic exists once, and the choice between simulation and board stays outside it.

## 2. Clocks and reset

| Port | Role |
| :--- | :--- |
| `i_clk_core` | Core, data memories, interconnect, data caches and peripherals |
| `i_clk_fetch` | Instruction memories (BOOT_MEMORY and direct FLASH), in phase with the core clock |
| `i_rst` | Reset, active at `'1'` |

The SoC generates no clock. The top picks the phase of each one and the reset latency.

## 3. Memory faces

Each region the core reaches has a face of ports. The face of a region that is not on the bus stays idle, with outputs at zero and inputs ignored.

| Region | SoC ports | Backend the top connects |
| :--- | :--- | :--- |
| BOOT_MEMORY | `o_if_addr`, `o_if_rden`, `i_boot_data` | FPGA memory block with an initial image |
| Direct FLASH | `o_if_addr`, `o_if_rden`, `i_rom_data`, `o_rom_addr2`, `o_rom_rden2`, `i_rom_data2` | Dual-port memory block |
| FLASH on the bus | `o_flash_*`, `i_flash_*` | FLASH chip, emulated or device |
| Direct RAM | `o_ram_*`, `i_ram_rdata` | FPGA memory block |
| RAM on the bus | `o_ramd_*` and `o_rami_*`, with `i_ramd_*` and `i_rami_*` | RAM chip, emulated or device |

A cache exists only on the bus side: the instruction cache requires `rom_external` and the data cache requires `ram_external`, the strict rule of the `check_isa` of the `config_pkg`. The valid combinations of FLASH, RAM and caches are the 9 that the `check_isa` of the `config_pkg` accepts, and the core reaches each memory over the bus exactly when the platform puts it there.

$$\text{rom\_via\_port} = \text{flash\_on\_bus} \qquad \text{ram\_via\_port} = \text{ram\_on\_bus}$$

Every address outside the BOOT_MEMORY, the FLASH and the RAM leaves through the external port and reaches the interconnect, which sends it to a peripheral of the window table or ends it in an error (see the [interconnect](../interconnect/ext_interconnect.md)). With no interconnect, every external access ends in an error.

The FLASH chip face carries the byte address, the read, the line request, the advance and the 96-bit line, and returns the ready response, the word, the line and the busy signal that feeds the Zihpm. The RAM chip face has a data port and an instruction port, with the same signals as the memory contract. The data paths between the core and these faces are in [modular](../platform/modular.md).

## 4. I/O roles

The I/O roles have their width set by a generic, and a role of width zero is omitted together with its peripheral. The pin polarity is one generic per role, which the top resolves. The program always sees the value active at `'1'`.

| Role | Presence | Width | Polarity | Port |
| :--- | :--- | :--- | :--- | :--- |
| Switches | `has_switches` | `switches_width` | `switches_active_low` | `io_switches` |
| Keys | `has_keys` | `keys_width` | `keys_active_low` | `io_keys` |
| Display | `has_display` | `display_digits` | `display_active_low` | `o_display_hex`, `o_display_value` |

The switches and keys are GPIO blocks, and the display is the `seg_display` register. Both peripherals accept width zero and have the polarity generic, described in the documents of the Peripherals repository. The console in pins mode takes the polarity of its two lines from `uart_tx_invert` and `uart_rx_invert`. The JTAG console and the pins console have the ports `i_uart_*`, `o_uart_tdo`, `i_uart_rx` and `o_uart_tx`, and the timer, the CLINT and the PLIC have no board port.

## 5. Map and generics

The memory map arrives by generics with no default: `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib` and `ram_end_kib`. The values come from `platform.yaml`, through the package that the top reads. The core reads the same map from the `config_pkg` that `platform.yaml` generates for the platform (`generate.config_pkg`), and the SoC checks in assertions that these generics agree with it. The base, the core extensions, the interrupts and the data cache (`IS_E`, `HAS_*`) are not generics: the core and the SoC read them from the `config_pkg`. The instruction cache (`has_icache` and the sizes), the PLIC and CLINT parameters (`plic_*`, `clint_*`) and the table indices of the peripherals are generics. The window table (`periph_count`, `periph_bases`, `periph_masks` and `strict_periph`) comes from the map package of the platform, and the SoC connects each peripheral by its index.

### 5.1. Map and cache generics

| Group | Generics | Default |
| :--- | :--- | :--- |
| Map | `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib` | none |
| Regions on the bus | `rom_external`, `ram_external` | `false` |
| Window table | `periph_count`, `periph_bases`, `periph_masks`, `strict_periph` | the default table of eight 256 MiB windows, 64 KiB of registers and `true` |
| Instruction cache | `has_icache` | `false` |
| Cache sizes | `icache_size_bits`, `dcache_size_bits` | 4096 bits |
| Cache window | `cache_window_bits`, from 26 to 29 (26 is 64 MiB, 27 is 128 MiB, the address window the tag covers) | 26 |
| Zihpm counters | `hpm_counters`, from 0 to 29, and `hpm_width`, from 0 to 64 bits | 29 and 64 |
| Interrupts | `clint_tick_cycles`, `clint_index`, `plic_index`, `plic_n_sources`, `plic_priority_bits`, `plic_addr_width` | 1 cycle, CLINT at index 6 and PLIC at 7, 6 sources, 3 bits, 20 bits |
| Timers | `timer_indices` (the index of each one in the window table) and `timer_irq_ids` (the PLIC source of each one, 0 for no line); one timer per element, no ceiling | empty, no timer |
| Peripheral indices | `switches_index`, `keys_index`, `uart_pins_index`, `uart_jtag_index`, `display_index`, `flash_ctrl_index` | 1, 2, 3, 4, 5 and 3 |
| Peripheral presence | `has_switches`, `has_keys`, `has_display`, `has_uart_jtag`, `has_uart_pins` | `false` |
| Role widths | `switches_width`, `keys_width`, `display_digits` | 10, 4 and 6 |
| Pin polarity | `switches_active_low`, `keys_active_low`, `display_active_low`, `uart_tx_invert`, `uart_rx_invert` | `false`, except the display (`true`) |

### 5.2. Critical path cuts and program update

Five generics turn on what boards with a high clock need, all off by default so the simulation platforms stay as they were.

| Generic | Effect |
| :--- | :--- |
| `registered_irqs` | The three interrupt lines enter the core through a register, one more cycle of latency, and leave the path that decides taking the interrupt |
| `fast_icache_select` | The instruction cache picks the region from the registered address and does not check the address on every lookup; it needs the fetch clock to be staggered from the core clock |
| `has_dcache_bypass` and `bypass_page` | The 4 KiB page given (the one at the top of the RAM) is never kept in the data cache, because the words the host shares with the program live there |
| `has_flash_ctrl` and `flash_ctrl_index` | The program update FLASH controller sits in the window of the given index, with the interrupt on line 6 and the chip commands on `o_flash_cmd_*` and `i_flash_cmd_*` |
| `i_inval_valid`, `i_inval_first` and `i_inval_last` (ports) | The rewritten FLASH region, which drops the lines of both caches |
| `i_display_*`, `o_display_tdo` and `o_display_fail` (ports) | The Virtual JTAG through which the host reads and writes the display register and the failure flag; the board top wires the node of index 2 |

### 5.3. Generic validation

Elaboration of the SoC stops with `severity failure` when a combination of generics makes no sense, and the message names the generic and the cause.

| Rule | Generics |
| :--- | :--- |
| The BOOT_MEMORY is a power of two and a multiple of 1 KiB | `boot_memory_size_bytes` |
| The map is ordered with no overlap: BOOT_MEMORY, FLASH and RAM | `rom_end_kib`, `ram_base_kib`, `ram_end_kib` |
| The regions and the caches agree with the `config_pkg`, and a cache requires its memory on the bus | `rom_external`, `ram_external`, `has_icache` |
| The window table is aligned, has contiguous masks and no overlap | `periph_bases`, `periph_masks`, `periph_count` |
| The FLASH and the RAM on the bus fit the cache windows | `cache_window_bits`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib` |
| Each existing cache has a power-of-two size of at least 256 bits | `icache_size_bits`, `dcache_size_bits` |
| The options of a cache only apply with it | `has_dcache_bypass` requires `HAS_DCACHE` of the `config_pkg`, `fast_icache_select` requires `has_icache` |
| The polarity of the UART pins only applies to the pins role | `uart_tx_invert` and `uart_rx_invert` require `has_uart_pins` |
| A present peripheral has an index inside the table, and two do not share one | `clint_index`, `plic_index`, `switches_index`, `keys_index`, `display_index`, `uart_jtag_index`, `uart_pins_index`, `flash_ctrl_index` |

The coherence among the extensions (the counters require Zicsr, the interrupts and Sscofpmf require Zicsr) is checked by the `config_pkg`, which `riscv-tools generate-config-pkg` generates from `platform.yaml`.

## 6. PLIC lines

Each single-instance peripheral connects its interrupt to a fixed PLIC line, the same on every platform. The timers have no fixed line: each one uses its own, from `timer_irq_ids`, which the generator picks from 5 up, skipping the fixed ones.

| Line | Source |
| ---: | :--- |
| 1 | Console in pins mode |
| 2 | Console over JTAG |
| 3 | Switches |
| 4 | Keys |
| 5, 7, 8 and on | One timer per line, in the order of `peripherals` (5 is the first free one) |
| 6 | FLASH controller |

The number of sources (`plic_n_sources`) covers the highest timer line. `make check-irq-sources` checks the fixed lines against the `interrupts.sources` list of each `platform.yaml` and refuses a timer pinned to one of them.

### 6.1. N timers

The `soc` generates, with a `for generate` over `timer_indices`, one timer instance per element: `p_we`, `p_re` and the `p_rdata` slice of its index, and the interrupt output on the matching `timer_irq_ids` line (zero leaves the timer without a line). The assertions refuse an index outside the table or shared with another peripheral, two equal lines, a line above `plic_n_sources` or on a fixed line. The tables come from the map package (`TIMER_INDICES` and `TIMER_IRQ_IDS`) and the `modular_sim_top` top connects them with `has_timer`.

## 7. Verification

The `SocRoles` entry of `tests.json` instantiates only the `soc`, with no chip model. The test plays the BOOT_MEMORY and the three-phase clock, runs a program that reads four active-low switches and stores the word read in the RAM, and checks that the program sees it with the polarity inverted and that the chip faces stay idle with internal memories. The `SocTimers0`, `SocTimers1` and `SocTimers3` entries instantiate the `soc` through `soc_timers_top` with zero, one and three timers: the program writes a different top value to each of the three windows and reads it back (each timer answers only on its window), starts timers 0 and 2 with the interrupt enabled and reads the pending register of the PLIC (only the lines 5 and 8 of the timers that exist are raised). The `modular_sim_top` platforms prove the SoC with every memory and cache combination, and `make check-tops` elaborates it on the ten platforms.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
