# External interconnect

## 1. What it is

Every data access of the core at or above `0x40000000` leaves through one external port with a `ready` handshake. The interconnect behind that port decides where it goes: to the SDRAM or to a peripheral. It decodes the address map of the platform, which is why it lives in this repository (`src/interconnect/`) and not in Memory or Peripherals, which it connects without either depending on the other.

| Block | Role |
| :--- | :--- |
| Interconnect (`ext_interconnect.vhd`) | Decodes the address, gives the core the ready and the data of the slave that answered |
| SDRAM bridge | The memory slave (see [sdram_debug.md](https://github.com/insper-riscv/Memory/blob/main/docs/en/ram/sdram_debug.md) in Memory for the host path to the same chip) |
| JTAG UART | The only peripheral today: transmit and receive queues of 64 bytes and a Virtual JTAG instance for the host (see [jtag_uart.md](https://github.com/insper-riscv/Peripherals/blob/main/docs/en/UART/jtag_uart.md) in Peripherals) |

## 2. Address map

| Range | Slave |
| :--- | :--- |
| bit 31 = 0 (from `0x40000000`) | the SDRAM bridge |
| bit 31 = 1 | a peripheral window: bits 30:28 are the id, bits `periph_addr_width + 1` to 2 the word offset in the window (14 bits and 64 KiB by default, 20 bits and 4 MiB for the PLIC) |

| Id | Window | Peripheral |
| ---: | :--- | :--- |
| 4 | `0xC0000000` | JTAG UART |
| 5 | `0xD0000000` | Seven-segment display |
| 6 | `0xE0000000` | CLINT (`msip`, `mtimecmp` and `mtime`; 64 KiB window) |
| 7 | `0xF0000000` | External interrupt controller (`EXT_IRQ`, 4 registers) |
| 0 to 3 | | none: a read gives 0, a write has no effect, the access completes |

## 2.1. Machine interrupts

The CLINT (id 6) and the external interrupt controller `EXT_IRQ` (id 7) enter as slaves by the same path as the other peripherals, in the clock domain of the core, with no synchronizer. The three outputs reach the ports of the core.

| Output | Core port | Bit of `mip` |
| :--- | :--- | :--- |
| `o_irq_software` of the CLINT (`msip`) | `i_irq_software` | MSIP, bit 3 |
| `o_irq_timer` of the CLINT (`mtime >= mtimecmp`) | `i_irq_timer` | MTIP, bit 7 |
| `o_irq_external` of `EXT_IRQ` | `i_irq_external` | MEIP, bit 11 |

The `mtime` of the CLINT is a counter of its own, which adds 1 every $\texttt{CLINT\_TICK\_CYCLES} = clock\_hz / mtime\_hz$ core cycles and is independent of the CSR `time` of Zicntr, which the core serves. The base of the CLINT, `mtime_hz` and `clock_hz` come from the `interrupts` section of `platform.yaml`, and no address of the CLINT is written by hand in the top or in the runtime. The core enables the interrupts only with `has_interrupts` and Zicsr, and the lines of `EXT_IRQ` stay at zero while no peripheral of the top raises one.

## 3. The handshake

The core holds the access on the port until `ready`, which stays high as a level until `mem_advance`.

1. A memory access passes through: the read and write strobes go to the bridge and its `ready` and data come back, whatever the number of cycles it takes.
2. A peripheral access takes one cycle: the interconnect sends one pulse of read or write to the slave, then keeps `ready` high until `mem_advance`. A pipeline that stays stopped for another reason does not repeat the pulse, so a read that removes a byte from a queue removes one.
3. The data of a load is copied when the load advances, and the choice of slave is registered at the same time. The next access, already on the port while the load is in its last stage, does not disturb it.

## 4. The AXI4 variant

`ext_axi_interconnect.vhd` does the same decode over AXI4: the data cache and the master bridge of Memory in front, then `axi_router.vhd` and, behind it, the SDRAM slave bridge of Memory and `axi_slave_periph_bank.vhd`. The router sends `0x40000000` to `0x43FFFFFF` to the SDRAM and `0x80000000` and above to the peripherals, and answers DECERR anywhere else. The peripheral bank serves eight windows of 16384 words (64 KiB), selected by bits 30:28. The whole chain is described in [dcache_axi.md](https://github.com/insper-riscv/Memory/blob/main/docs/en/barramento/dcache_axi.md) in Memory.

## 5. Verification

The tests run here, with the bus of Memory and the JTAG UART of Peripherals together (`make test TEST=<name>`):

| Test | What it covers |
| :--- | :--- |
| `ExtBus` | The interconnect with the JTAG UART in peripheral slot 4: bytes in order, a stopped pipeline pops once, full queues, an unmapped window reads 0, load data stays while the next access runs |
| `ExtAxiBus` | The same tests over the AXI4 chain, with a word memory behind the SDRAM slave |
| `ExtAxiCache` | The data cache over AXI4: flush, invalidate, the master shared with the core |
| `AxiRouter` | The router alone: both slaves, bursts, W before AW, DECERR |

The defect found in the router by reading the handshake rules is in [ROUTER_W_BEFORE_AW.md](../bugs/ROUTER_W_BEFORE_AW.md).

The formal proof (`formal/ext_interconnect_props.sv`, SymbiYosys on the netlist GHDL synthesizes, with the Core's method) covers the interconnect alone, with the core, the memory and the eight peripherals free and held to the contract by assumptions.

| Property | Proof |
| :--- | :--- |
| One slave selected per access: at most one select bit, the one of the identification field of the address | Induction |
| Memory and peripheral exclude each other: a peripheral address does not reach the memory, and a memory address does not reach a peripheral | Induction |
| The address, the data and the mask pass unchanged | Induction |
| The pulse to the peripheral lasts one cycle, only with the interconnect free, and the access ends in the next cycle with the answer held until the advance (no access hangs) | Induction |
| The data read from a peripheral is the one of the slave selected at the pulse, and the memory data comes straight from it | Induction |

Eight deliberate defects of the VHDL (shifted slave identification, pulse without the free state, memory that sees the peripheral address, ready always high, wrong slave data, data select that never returns to the memory, write that reads and shifted word address) make the proof fail. `make formal` runs only this proof, and `formal/aggregate.sh` decides the result of the engines.

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
