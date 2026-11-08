# SoC (`soc`)

🌐 [Português](../../pt-br/soc/soc.md) · [English](../../en/soc/soc.md)

## 1. What it is

The `soc` entity (`src/soc/soc.vhd`) is the board-independent system on chip. It holds the core, the caches, the memory bridges and routers, the interconnect, the CLINT, the PLIC and the I/O peripherals, and connects everything through interface contracts. It has no board pin, no family name and no chip model. Whoever instantiates it supplies the two clocks, the reset and the backends of the memory regions.

The simulation top `modular_sim_top` instantiates it and adds the three-phase clock generator and the chip models. A board top instantiates the same `soc` and adds the PLL, the pin ring and the controllers of the real chips. All the SoC logic exists once, and the choice between simulation and board stays outside it.

## 2. Clocks and reset

| Port | Role |
| :--- | :--- |
| `i_clk_core` | Core, data memories, interconnect, data caches and peripherals |
| `i_clk_fetch` | Instruction memories (BOOT_MEMORY and internal ROM), in phase with the core clock |
| `i_rst` | Reset, active at `'1'` |

The SoC generates no clock. The top picks the phase of each one and the reset latency.

## 3. Memory faces

Each region the core reaches has a face of ports. The face of a region the core does not reach through the external port stays idle, with outputs at zero and inputs ignored.

| Region | SoC ports | Backend the top connects |
| :--- | :--- | :--- |
| BOOT_MEMORY | `o_if_addr`, `o_if_rden`, `i_boot_data` | FPGA memory block with an initial image |
| Internal ROM | `o_if_addr`, `o_if_rden`, `i_rom_data`, `o_rom_addr2`, `o_rom_rden2`, `i_rom_data2` | Dual-port memory block |
| External ROM | `o_flash_*`, `i_flash_*` | FLASH chip, emulated or device |
| Internal RAM | `o_ram_*`, `i_ram_rdata` | FPGA memory block |
| External RAM | `o_ramd_*` and `o_rami_*`, with `i_ramd_*` and `i_rami_*` | RAM chip, emulated or device |

The conditions below say when the core reaches each memory through the port.

$$\text{rom\_via\_port} = \text{rom\_external} \lor \text{has\_icache} \qquad \text{ram\_via\_port} = \text{ram\_external} \lor \text{has\_dcache}$$

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

The memory map arrives by generics with no default: `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib` and `periph_base_kib`. The values come from `platform.yaml`, through the package that the top reads. The SoC does not depend on that package. The core extensions (`has_*`), the caches (`has_icache`, `has_dcache` and the sizes), the interrupts (`has_interrupts`, `plic_*`, `clint_*`) and the window indices of the peripherals are generics with a neutral value.

### 5.1. Map and extension generics

| Group | Generics | Default |
| :--- | :--- | :--- |
| Map | `boot_memory_size_bytes`, `rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib` | none |
| External regions | `rom_external`, `ram_external` | `false` |
| Caches | `has_icache`, `has_dcache` | `false` |
| Cache sizes | `icache_size_bits`, `dcache_size_bits` | 4096 bits |
| Cache window | `cache_window_bits`, from 26 to 29 (26 is 64 MiB, 27 is 128 MiB, the address window the tag covers) | 26 |
| Core base and extensions | `has_e`, `has_zicsr`, `has_zicntr`, `has_zihpm`, `has_zimop`, `has_zicond`, `has_zihintntl`, `has_zihintpause`, `has_m`, `has_zmmul`, `has_zifencei`, `has_zicclsm`, `has_access_faults` | `false` |
| Zihpm counters | `hpm_counters`, from 0 to 29, and `hpm_width`, from 0 to 64 bits | 29 and 64 |
| Interrupts | `has_interrupts`, `has_sscofpmf`, `periph_slots`, `clint_tick_cycles`, `clint_id`, `plic_id`, `plic_n_sources`, `plic_priority_bits`, `plic_addr_width` | off, windows 6 (CLINT) and 7 (PLIC), 6 sources, 3 bits, 20 bits |
| Peripheral windows | `timer_id`, `switches_id`, `keys_id`, `uart_pins_id`, `uart_jtag_id`, `display_id`, `flash_ctrl_id` | 0, 1, 2, 3, 4, 5 and 3 |
| Peripheral presence | `has_timer`, `has_switches`, `has_keys`, `has_display`, `has_uart_jtag`, `has_uart_pins` | `false` |
| Role widths | `switches_width`, `keys_width`, `display_digits` | 10, 4 and 6 |
| Pin polarity | `switches_active_low`, `keys_active_low`, `display_active_low`, `uart_tx_invert`, `uart_rx_invert` | `false`, except the display (`true`) |

### 5.2. Critical path cuts and program update

Five generics turn on what boards with a high clock need, all off by default so the simulation platforms stay as they were.

| Generic | Effect |
| :--- | :--- |
| `registered_irqs` | The three interrupt lines enter the core through a register, one more cycle of latency, and leave the path that decides taking the interrupt |
| `fast_icache_select` | The instruction cache picks the region from the registered address and does not check the address on every lookup; it needs the fetch clock to be staggered from the core clock |
| `has_dcache_bypass` and `bypass_page` | The 4 KiB page given (the one at the top of the RAM) is never kept in the data cache, because the words the host shares with the program live there |
| `has_flash_ctrl` and `flash_ctrl_id` | The program update FLASH controller sits in the given window, with the interrupt on line 6 and the chip commands on `o_flash_cmd_*` and `i_flash_cmd_*` |
| `i_inval_valid`, `i_inval_first` and `i_inval_last` (ports) | The rewritten FLASH region, which drops the lines of both caches |
| `i_display_*`, `o_display_tdo` and `o_display_fail` (ports) | The Virtual JTAG through which the host reads and writes the display register and the failure flag; the board top wires the node of index 2 |

## 6. PLIC lines

Each peripheral connects its interrupt to a fixed PLIC line, the same on every platform.

| Line | Source |
| ---: | :--- |
| 1 | Console in pins mode |
| 2 | Console over JTAG |
| 3 | Switches |
| 4 | Keys |
| 5 | Timer |
| 6 | FLASH controller |

`make check-irq-sources` checks these numbers against the `interrupts.sources` list of each `platform.yaml`.

## 7. Verification

The `SocRoles` entry of `tests.json` instantiates only the `soc`, with no chip model. The test plays the BOOT_MEMORY and the three-phase clock, runs a program that reads four active-low switches and stores the word read in the RAM, and checks that the program sees it with the polarity inverted and that the chip faces stay idle with internal memories. The `modular_sim_top` platforms prove the SoC with every memory and cache combination, and `make check-tops` elaborates it on the ten platforms.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
