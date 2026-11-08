# DE10-Nano and DE0-Nano-SoC

## 1. Reference

Both Terasic boards carry a Cyclone V SoC, with the ARM processor (HPS) beside the FPGA. The package of each is in `boards/de10-nano/` and `boards/de0-nano-soc/`. The package format is in [formato.md](formato.md) and the table of boards in [placas.md](placas.md).

| Board | Device in Quartus | FPGA IDCODE | ALMs | M10K blocks |
| :--- | :--- | :--- | ---: | ---: |
| `de10-nano` | `5CSEBA6U23I7` | `02D020DD` | 41910 | 557 |
| `de0-nano-soc` | `5CSEMA4U23C6` | `02D010DD` | 15094 | 246 |

The device name in Quartus does not carry the `N` suffix of the commercial part (`5CSEMA4U23C6N`): Quartus 25.1 rejects that name with errors 125095 and 281000. The IDCODEs come from the Quartus device database (`pgm_parts.txt`), not from a reading of the boards.

## 2. Family in Quartus

The `cyclone-v-soc` family uses the name `Cyclone V` in Quartus, because Lite does not list `Cyclone V SoC`. Both boards synthesize with `quartus_map` without the HPS: the fabric is programmed over JTAG and the ARM stays out of the project.

## 3. JTAG chain with the HPS

The USB-Blaster II built into the board exposes two parts on the same chain.

| Position | Name in `jtagconfig` | IDCODE |
| :---: | :--- | :--- |
| 1 | `SOCVHPS` (ARM DAP) | `4BA00477` |
| 2 | `5CSE(BA6\|MA6)/..` on the DE10-Nano and `5CSE(BA4\|MA4)/..` on the DE0-Nano-SoC | `02D020DD` and `02D010DD` |

Tools compares the chain it reads with `jtag.chain` of the package by rule V17, and the two boards differ only by the FPGA IDCODE, since they share the cable, the HPS and the USB IDs. The device identity of the FPGA uses position `@2` (`@2: 5CSE(BA6|MA6)/.. (0x02D020DD)`), which is the argument of `quartus_pgm` and `quartus_stp`.

Quartus may fail with error 209025 (silicon ID) when programming. The fix reported in forums is to take the HPS out of the chain in the programmer, and `riscv-tools board doctor` only suggests it and never changes the chain.

## 4. USB-Blaster II cable

| USB ID | State of the cable |
| :--- | :--- |
| `09fb:6010` | Before `jtagd` loads the firmware |
| `09fb:6810` | After the load; `jtagconfig` lists the cable as `DE-SoC [USB-1]` |

The cable name has no `[bus-port]` suffix, so the USB port does not come from the name. `board doctor` warns about the firmware not yet loaded and about ID `6810` with no `DE-SoC` cable listed. `board scan` shows the board that the USB reveals without a readable chain, for example with the cable at `6010`.

## 5. Console

The console of the SoC is the JTAG UART (`console.default: jtag`) through the Virtual JTAG node of the fabric. The Virtual JTAG sits behind the FPGA on the chain, and Tools reaches it by position `@2` without handling the HPS. The USB UART of the board belongs to the HPS and does not reach the fabric; `ARDUINO_IO[0]` (RXD) and `ARDUINO_IO[1]` (TXD) serve an external adapter if the `pinos` backend is chosen.

## 6. Memory and the DDR3 of the HPS

### 6.1. The decision

Neither board has memory wired to the fabric. The package declares only emulated memory in M10K (decision DM4): about 696 KB on the DE10-Nano and 307 KB on the DE0-Nano-SoC, minus caches and register file. The ACT4 profile with 1 MB of RAM does not fit those blocks.

### 6.2. Paths to the DDR3 of the HPS

The 1 GB DDR3 belongs to the hard controller of the HPS. The fabric can use it only after the preloader (U-Boot SPL) has calibrated the controller.

| Path | What it is | Effect |
| :--- | :--- | :--- |
| FPGA-to-SDRAM port | Avalon-MM or AXI port of the DDR3 controller, straight from the fabric | Lower latency and higher throughput; it is the path of the Terasic example (`terasic_hps_ddr3`) |
| FPGA-to-HPS bridge (F2H) | AXI slave of the HPS with a master in the fabric, through the L3 | Reaches all the memory of the HPS, with the latency of the L3 and the firewall filter |

Both need the HPS component in Platform Designer, the configuration of the DDR3 pins and a preloader generated from the handoff of the project and written to the microSD card. Without the preloader the controller does not calibrate and the port does not answer.

### 6.3. Cost of a backend

| Item | Consequence |
| :--- | :--- |
| HPS component and Qsys | New vendor entity in `altera/` of Memory, outside the `soc` |
| Preloader on the microSD | The bring-up flow now needs a card and ARM software |
| Variable latency | The backend needs the K2 contract with variable `latency` and burst, like the SDRAM |
| Schema | A new key in `memories` and a validator rule for the preloader |
| Test | Only with the live board and a working USB-Blaster II cable |

### 6.4. Conclusion of the study

A backend is justified only if the DE10-Nano must run the 1 MB profile. The recommendation is to keep decision DM4 (emulated memory) and resume the study if the lab wants that profile on this board. The statements of this chapter about the bridges and the preloader come from the board manual (sections 5.4 and 7.3 of the sheet) and from knowledge of the HPS architecture, and must be checked against the Cyclone V HPS reference manual, which is not in `Docs/`.

## 7. Support levels

| Level | Criterion | What holds for both boards |
| :--- | :--- | :--- |
| N0 | `board generate` and `quartus_map` without error | The `rv32i` profile with emulated RAM synthesizes on both (3279 registers and 295,424 memory bits) |
| N1 | Fit and timing analysis | `quartus_fit` and `quartus_sta` over the same project |
| N2 | Live board | Needs the USB-Blaster II cable to enumerate |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
