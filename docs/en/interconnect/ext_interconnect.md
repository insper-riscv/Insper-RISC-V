# External interconnect

## 1. What it is

The core knows only the BOOT_MEMORY, the FLASH and the RAM. Every data access outside them, and every access to a region that the platform puts on the bus, leaves through one external port with a `ready` and an `error` handshake. The interconnect behind that port decides where the access goes: to the bus memory, to a peripheral or to no slave. It decodes the window table of the platform, which is why it lives in this repository (`src/interconnect/`) and not in Memory or Peripherals, which it connects without either depending on the other.

| Block | Role |
| :--- | :--- |
| Interconnect (`ext_interconnect.vhd`) | Decodes the address, gives the core the ready, the error and the data of the slave that answered |
| Interconnect package (`interconnect_pkg.vhd`) | The `addr_array_t` type of the tables, the default table of eight windows and the decode functions that the interconnect, the AXI4 router and the peripheral bank share |
| SDRAM bridge | The memory slave (see [sdram_debug.md](https://github.com/insper-riscv/Memory/blob/main/docs/en/ram/sdram_debug.md) in Memory for the host path to the same chip) |
| JTAG UART | A peripheral with transmit and receive queues of 64 bytes and a Virtual JTAG instance for the host (see [jtag_uart.md](https://github.com/insper-riscv/Peripherals/blob/main/docs/en/UART/jtag_uart.md) in Peripherals) |

## 2. Address map

### 2.1. The window table

The platform generates the table of the peripherals in the map package (`<platform>_map_pkg`) from the `peripherals` list of `platform.yaml`, where each entry has `base` and `size`.

| Constant | Meaning |
| :--- | :--- |
| `PERIPH_COUNT` | Number of windows; zero is a platform with no peripherals |
| `PERIPH_BASES` | Base of each window, aligned to its size |
| `PERIPH_MASKS` | Mask of each window: one in the bits the window fixes, zero in the ones inside it |
| `STRICT_PERIPH` | The padding of a window ends in an error |
| `<NAME>_BASE`, `<NAME>_INDEX`, `<NAME>_SIZE` | Base, table index and size of each peripheral, in the order of the `platform.yaml` list |

Peripheral $i$ is hit by an address $a$ when

$$a \wedge \texttt{PERIPH\_MASKS}(i) = \texttt{PERIPH\_BASES}(i)$$

The window is the smallest power of two that holds the registers, with at least 16 bytes, and bits `periph_addr_width + 1` to 2 of the address are the word offset in it (14 bits and 64 KiB by default, 20 bits and 4 MiB for the PLIC). What lies beyond the bytes of registers inside the window is the padding: with `STRICT_PERIPH` the access ends in an error, and without it a read gives 0 and a write has no effect.

### 2.2. The decision for each access

| The address | Slave | Answer |
| :--- | :--- | :--- |
| Falls in the FLASH (with `flash_on_bus`) or in the RAM (with `ram_on_bus`) | The bus memory | The `ready` and the data of the memory |
| Hits a window, inside the registers | The peripheral of the window | A pulse and the `ready` of the interconnect |
| Hits a window, in the padding, with `strict_periph` | None | `ready` and `error`, read gives 0 |
| Hits no window and no memory | None | `ready` and `error`, read gives 0 |

The `error` rises together with the `ready` and stays until `mem_advance`. The core receives it on `i_ext_error` and raises the load or store access fault (causes 5 and 7), with the address in `mtval`.

### 2.3. The generics

| Generic | Meaning |
| :--- | :--- |
| `periph_count` | Number of windows (natural) |
| `periph_bases`, `periph_masks`, `periph_sizes` | The window tables; the SoC derives `periph_sizes` from the masks (the whole window, no padding) |
| `strict_periph` | The padding ends in an error |
| `periph_addr_width` | Width of the word offset handed to the peripheral |
| `flash_on_bus`, `flash_base`, `flash_last` | The FLASH is on the bus, and its first and last address |
| `ram_on_bus`, `ram_base`, `ram_last` | The same for the RAM |

The default value of the generics is the table of eight windows at `0x80000000 | i << 28`, mask `0xF0000000` and 64 KiB of registers, with only the RAM at `0x40000000` to `0x43FFFFFF` on the bus: the entity tests use it. The `p_we` and `p_re` ports are one-hot by table index, and `p_rdata` holds one word of `XLEN` bits per index.

On the `de0-cv` the table has five windows.

| Index | Base | Peripheral |
| ---: | :--- | :--- |
| 0 | `0xB0000000` | FLASH controller |
| 1 | `0xC0000000` | JTAG UART |
| 2 | `0xD0000000` | Seven-segment display |
| 3 | `0xE0000000` | CLINT (`msip`, `mtimecmp` and `mtime`; 64 KiB window) |
| 4 | `0xF0000000` | PLIC (4 MiB window; see [Platform interrupts](../platform/interrupcoes.md)) |

### 2.4. Machine interrupts

The CLINT and the PLIC enter as slaves by the same path as the other peripherals, in the clock domain of the core, with no synchronizer. The three outputs reach the ports of the core.

| Output | Core port | Bit of `mip` |
| :--- | :--- | :--- |
| `o_irq_software` of the CLINT (`msip`) | `i_irq_software` | MSIP, bit 3 |
| `o_irq_timer` of the CLINT (`mtime >= mtimecmp`) | `i_irq_timer` | MTIP, bit 7 |
| `o_meip` of the PLIC | `i_irq_external` | MEIP, bit 11 |

The `mtime` of the CLINT is a counter of its own, which adds 1 every $\texttt{CLINT\_TICK\_CYCLES} = clock\_hz / mtime\_hz$ core cycles and the CSR `time` of Zicntr, which the core serves, is its read-only shadow: the `o_mtime` output of the CLINT reaches the `i_mtime` port of the core. The base of the CLINT, `mtime_hz` and `clock_hz` come from the `interrupts` section of `platform.yaml`, and no address of the CLINT is written by hand in the top or in the runtime. The core enables the interrupts only with `has_interrupts` and Zicsr, and the lines of `EXT_IRQ` stay at zero while no peripheral of the top raises one.

## 3. The handshake

The core holds the access on the port until `ready`, which stays high as a level until `mem_advance`.

1. A memory access passes through: the read and write strobes go to the bridge and its `ready` and data come back, whatever the number of cycles it takes.
2. A peripheral access takes one cycle: the interconnect sends one pulse of read or write to the slave, then keeps `ready` high until `mem_advance`. An access with no slave takes the same cycle, with no pulse, and keeps `ready` and `error` high until `mem_advance`. A pipeline that stays stopped for another reason does not repeat the pulse, so a read that removes a byte from a queue removes one.
3. The data of a load is copied when the load advances, and the choice of slave is registered at the same time. The next access, already on the port while the load is in its last stage, does not disturb it.

## 4. The AXI4 variant

`ext_axi_interconnect.vhd` does the same decode over AXI4: the data cache and the master bridge of Memory in front, then `axi_router.vhd` and, behind it, the SDRAM slave bridge of Memory and `axi_slave_periph_bank.vhd`. The native AXI4 responses play the role of `error`.

| Block | Generics | Behavior |
| :--- | :--- | :--- |
| `axi_router` | `mem_base`, `mem_last`, `periph_count`, `periph_bases`, `periph_masks` | Sends `mem_base` to `mem_last` to the SDRAM and the windows of the table to the peripherals; any other address gets DECERR |
| `axi_slave_periph_bank` | The whole table, `strict_periph` and `periph_addr_width` | With no window hit it answers DECERR; the padding with `strict_periph` and a beat that is not a single aligned 4-byte one answer SLVERR; no peripheral is touched in these cases |
| `ext_axi_interconnect` | The two above and `cache_ctrl_index` | `o_error` rises together with `o_ready` when the master receives SLVERR or DECERR; the table index `cache_ctrl_index` is the control of the cache itself (a write flushes, a read gives the busy state) and does not show on the external strobes |

The whole chain is described in [dcache_axi.md](https://github.com/insper-riscv/Memory/blob/main/docs/en/barramento/dcache_axi.md) in Memory.

## 5. Verification

The tests run here, with the bus of Memory and the JTAG UART of Peripherals together (`make test TEST=<name>`):

| Test | What it covers |
| :--- | :--- |
| `ExtBus` | The interconnect with the JTAG UART at index 4 of the default table: bytes in order, a stopped pipeline pops once, full queues, a window with no peripheral reads 0, load data stays while the next access runs, and the `error` of a hole of the map and of the padding of a window |
| `ExtAxiBus` | The same tests over the AXI4 chain, with a word memory behind the SDRAM slave |
| `ExtAxiCache` | The data cache over AXI4: flush, invalidate, the master shared with the core |
| `AxiRouter` | The router alone: both slaves, bursts, W before AW, DECERR |
| `AxiSlavePeriphBank` | The peripheral bank alone: one pulse per beat, SLVERR for a malformed beat and for the padding, DECERR with no window |
| `ExtInterconnect` | The interconnect alone, with the default table: one pulse per access, the `error` of a hole of the map and of the padding, and the `error` held until the advance |

The defect found in the router by reading the handshake rules is in [ROUTER_W_BEFORE_AW.md](../bugs/ROUTER_W_BEFORE_AW.md).

The formal proof (`formal/ext_interconnect_props.sv`, SymbiYosys on the netlist GHDL synthesizes, with the Core's method) covers the interconnect alone, with the default window table (eight windows, `strict_periph` on and only the RAM on the bus), the core, the memory and the eight peripherals free and held to the contract by assumptions.

| Property | Proof |
| :--- | :--- |
| One slave selected per access: at most one select bit, the one of the window the address hits | Induction |
| Memory and peripheral exclude each other: only a memory address reaches it, and it does not reach a peripheral | Induction |
| The address, the data and the mask pass unchanged | Induction |
| The pulse to the peripheral lasts one cycle, only with the interconnect free, and the access ends in the next cycle with the answer held until the advance (no access hangs) | Induction |
| The data read from a peripheral is the one of the slave selected at the pulse, and the memory data comes straight from it | Induction |
| The `error` rises together with the `ready` of an access with no slave (outside the memory and every window, or in the padding of a window), only in it, lasts until the advance, and the read gives 0 | Induction |

Twelve deliberate defects of the VHDL (window always decoded as the first, pulse without the free state, memory that sees the peripheral address, ready always high, wrong slave data, data select that never returns to the memory, write that reads shifted word address, a hole of the map with no error, padding treated as a peripheral, a hole treated as memory and an error that does not fall at the advance) make the proof fail. `make formal` runs only this proof, and `formal/aggregate.sh` decides the result of the engines.

## 6. Warnings are errors

A warning from GHDL, Yosys or SymbiYosys points to code outside the standard or at its limit, so it makes the run of the proof fail. The fix is in the code, the proof or the netlist, and neither a `-Wno-*` option nor a list of ignored warnings is allowed.

| Step | Where the warning is detected | Effect |
| :--- | :--- | :--- |
| `ghdl -a` and `ghdl --synth` | Standard error of GHDL, read by `ghdl_run` | The command fails and prints each warning with the VHDL file and line |
| `sby` of each proof and each mutant | Whole log of the proof, read by `prove` | The verdict becomes `error`, even when the exit code was 0 or 2, and the message points to `<log>:<line>` |

A warning is a line with the word `warning` or `warnings`, in any case, as a whole word. Names that only contain the word (`no_warnings.sv`) and the Yosys summary with a count of zero (`Warnings: 0 unique messages, 0 total`) do not count. The only exception is three ABC messages, accepted only in the log of the `abc-bmc3` engine (the undriven clock of the property module, the count of undriven bits and the outputs read as constraints), because the way ABC reads the netlist produces them. Yices, Bitwuzla and Boolector have no exception, and any other ABC message is still an error.

Two rules keep the netlists free of warnings.

1. A signal exposed as `dbg_<signal>` that GHDL removed from the netlist (because a mutant took away its only reader) is tied to zero, never left without a driver, since a wire without a driver is free and could make a property fail without the defect being the cause.
2. `ext_interconnect.vhd` is analyzed without any file of a submodule, so no Quartus attribute reaches the netlist. If a future proof needs a file with `altera_attribute`, the formal netlist must be generated from a copy without that attribute.

The tests of the guard are in `formal/aggregate_test.sh`, which injects a warning into GHDL and into `sby` of a real run and requires it to fail.
