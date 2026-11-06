# Platform interrupts

🌐 [Português](../../pt-br/platform/interrupcoes.md) · [English](../../en/platform/interrupcoes.md)

## 1. Overview

The core receives three machine interrupt lines, as levels, in the core clock domain and with no synchronizer.

| Line | Origin | `mip` bit |
| :--- | :--- | :--- |
| `MSIP` | `o_irq_software` of the CLINT | 3 |
| `MTIP` | `o_irq_timer` of the CLINT | 7 |
| `MEIP` | `o_meip` of the PLIC | 11 |

Every peripheral with events the software cares about exposes a level output `o_irq`. The outputs are the sources of the PLIC, and the PLIC (`riscv-plic-1.0.0`, one hart, the machine-mode context) hands the core a single `MEIP`. The handler reads the claim register, services the source and writes the identifier back to the same register (complete). The PLIC is documented in `Peripherals/docs/en/PLIC/plic.md`.

## 2. Sources

The identifier of a source is the same in every platform that has it. It comes from the `interrupts.sources` list of the `platform.yaml`, from which `generate-memory-map` writes `IRQ_<NAME>` into the VHDL package and `RV32_IRQ_<NAME>` into the runtime header. The modular top repeats the numbers in the `LINE_<NAME>` constants, and `make check-irq-sources` checks both sides.

| Id | Name | Peripheral | Platforms |
| ---: | :--- | :--- | :--- |
| 1 | `UART` | Serial UART on pins | `modular` |
| 2 | `UART_JTAG` | UART over JTAG | `modular`, `de0-cv` |
| 3 | `SWITCHES` | GPIO of the SW slide switches | `modular` |
| 4 | `KEYS` | GPIO of the KEY push buttons | `modular` |
| 5 | `TIMER` | General-purpose timer | `modular` |
| 6 | `FLASH` | FLASH controller | `de0-cv` (simulation top) |

## 3. Events of each peripheral

The table lists every event the software may want as an interrupt, its status register, its enable and how the cause is cleared. The new registers do not change the map of the existing ones: they use a bit or a register that was unused.

| Peripheral | Event | Status | Enable | Clear |
| :--- | :--- | :--- | :--- | :--- |
| Serial UART | Byte received | `STATUS.RX_VALID` | `CONTROL.RX_IRQ_ENABLE` (bit 0) | Read `RX_DATA` until empty |
| Serial UART | Transmitter empty | `STATUS.TX_EMPTY` | `CONTROL.TX_EMPTY_IRQ_ENABLE` (bit 1) | Write `TX_DATA` or disable |
| Serial UART | Error: receive overrun or transmit drop | `STATUS.RX_OVERRUN`, `STATUS.TX_DROPPED` | `CONTROL.ERROR_IRQ_ENABLE` (bit 2) | Write 1 to the bit in `STATUS` |
| UART over JTAG | Byte received | `STATUS` bits 15:8 not zero | `CONTROL` bit 0 | Read `RXDATA` until empty |
| UART over JTAG | Transmit queue empty (the host took everything) | `STATUS` bits 7:0 equal to the depth | `CONTROL` bit 1 | Write `TXDATA` or disable |
| UART over JTAG | Byte dropped | `STATUS` bit 16 | `CONTROL` bit 2 | Read `STATUS` |
| GPIO | Rising edge, falling edge or change, per pin | `IRQ_STAT` | `IRQ_MASK` and `RISE_MASK`, `FALL_MASK` | Read `IRQ_STAT` |
| GPIO | High or low level, per pin | `IRQ_STAT` | `IRQ_MASK`, `LEVEL_MASK` and `RISE_MASK` (high), `FALL_MASK` (low) | Remove the level or mask the pin, and read `IRQ_STAT` |
| TIMER | Counter overflow | `OVF_STATUS` | Bit 3 of `CONFIG` | Read `OVF_STATUS` |
| FLASH controller | Command finished (erase or program) | `IRQ_STATUS.DONE` | `IRQ_ENABLE` bit 0 | Write 1 to the bit |
| FLASH controller | Command refused | `IRQ_STATUS.REFUSED` | `IRQ_ENABLE` bit 1 | Write 1 to the bit |
| CLINT | `mtime >= mtimecmp` and `msip` | `mip.MTIP` and `mip.MSIP` | `mie.MTIE`, `mie.MSIE` | Rewrite `mtimecmp`, clear `msip` |
| Display, SDRAM, caches, bridges, ROM and RAM | None: they raise no event the software wants to receive | | | |

## 4. PLIC map

The PLIC window is 4 MiB, at the base given by the `platform.yaml` (`0xF0000000` in the current platforms), and its size gives the address width (`PLIC_ADDR_WIDTH`). The `ext_interconnect` hands the peripheral as many bits as its `periph_addr_width` generic, which platforms with a PLIC set to `PLIC_ADDR_WIDTH`.

| Register | Address | Runtime constant |
| :--- | :--- | :--- |
| Priority of source $n$ | base $+ 4n$ | `RV32_PLIC_PRIORITY` $+ 4n$ |
| Pending | base $+ \texttt{0x1000}$ | `RV32_PLIC_PENDING` |
| Enable of context 0 | base $+ \texttt{0x2000}$ | `RV32_PLIC_ENABLE` |
| Threshold | base $+ \texttt{0x200000}$ | `RV32_PLIC_THRESHOLD` |
| Claim and complete | base $+ \texttt{0x200004}$ | `RV32_PLIC_CLAIM` |

## 5. Verification

Each peripheral has an entity test and a formal proof of what its interrupt adds (documents of each peripheral in the Peripherals repository). The programs of `asm-plic/` in the Tests repository exercise every source end to end on the simulated `modular` platform: they enable the cause in the peripheral and in the PLIC, raise the event, enter the handler, claim, service, complete and check; a separate program checks priority, tie, threshold and priority zero with two sources.
