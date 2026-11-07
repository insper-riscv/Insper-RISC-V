# Equivalence of the generated DE0-CV

This report compares the Quartus project that `riscv-tools board generate` writes for the DE0-CV with the project the platform had written by hand (top, `.qsf`, `.sdc` and PLL). The comparison follows the equivalence table of the generation plan.

## 1. How to compare

```bash
uv run riscv-tools --root . board generate --platform src/cyclone-v/de0-cv/platform.yaml --out build \
    --hand-qsf <hand-written .qsf> --hand-sdc <hand-written .sdc> --hand-pll <hand-written PLL>
```

The report normalizes both sides and lists, per section, what only exists by hand, what only exists in the generated one and what changed. A section is equivalent when nothing only exists by hand and nothing changed.

## 2. Result per item

| Item | Comparison | Result |
| :--- | :--- | :--- |
| Pins and I/O standards | Set of (signal, pin, standard) of the `.qsf` | Equivalent, 107 pins |
| Per-instance assignments | Assignments that are not I/O standards | Equivalent |
| Project | Family, device, VHDL version, optimization mode | Equivalent |
| Clocks and constraints | Normalized `.sdc` commands | Equivalent; the generated one adds two false paths, for the switches and the keys |
| PLL | Frequency, phase and ratio of each output | Equivalent: 100 MHz (phase 0 and 4000 ps), 76.923077 MHz (phases 0 and 7500 ps) |
| Sources | VHDL files | Differ only in what the generation replaces (see section 4) |
| Synthesis | ALMs, registers and memory bits | Section 3 |
| Timing | Slack per domain, seeds 1 to 5 | Section 3 |

## 3. Synthesis and timing

Both tables come from the same Quartus, in `HIGH PERFORMANCE EFFORT` mode, and the slacks are the worst case between the 85 C and 0 C models.

Generated project:

| Seed | ALMs | Registers | Memory bits | Core setup (ns) | Fetch setup (ns) | Core hold (ns) | SDRAM hold (ns) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10,382 | 11,193 | 2,205,952 | 0.749 | 0.960 | 0.121 | 0.159 |
| 2 | 10,348 | 11,271 | 2,205,952 | 0.210 | 1.244 | 0.130 | 0.162 |
| 3 | 10,345 | 11,200 | 2,205,952 | 1.079 | 0.724 | 0.122 | 0.163 |
| 4 | 10,349 | 11,171 | 2,205,952 | 1.271 | 0.416 | 0.133 | 0.157 |
| 5 | 10,324 | 11,192 | 2,205,952 | 0.782 | 0.915 | 0.119 | 0.164 |

Hand-written project (seeds 1 to 3):

| Seed | ALMs | Registers | Memory bits | Core setup (ns) | Fetch setup (ns) | Core hold (ns) | SDRAM hold (ns) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 10,382 | 10,768 | 2,205,952 | 0.352 | 0.570 | 0.121 | 0.165 |
| 2 | 10,395 | 10,757 | 2,205,952 | 0.166 | 0.734 | 0.124 | 0.153 |
| 3 | 10,376 | 10,762 | 2,205,952 | 0.694 | 0.465 | 0.119 | 0.166 |

The generated one closes setup and hold in every domain on the five seeds. The memory bits are the same. The ALMs stay inside the spread between seeds (10,324 to 10,382 in the generated one and 10,376 to 10,395 by hand), and the generated one uses about 4 % more registers; the difference comes from the GPIO blocks of the switches and keys and from the console, which the hand-written top did not have.

## 4. What the generation replaces

| Hand-written | Generated |
| :--- | :--- |
| Board top | Thin top that wires the SoC, the FLASH and SDRAM backends, the PLL and the pin ring |
| Verilog PLL | PLL with the same parameters, written from `clocks` |
| `.qsf`, `.qpf` and `.sdc` | The same files, with the sources taken from the `requires` closure of the `top` component |
| `.qip` files of the memories | Parameterized memory block entity |
| Virtual JTAG shells of the UART and the display | Parameterized Virtual JTAG entity, with nodes of index 0 (loader), 1 (UART), 2 (display) and 3 (SDRAM) |
| Extension and exception LEDs | Only the first LED, which lights with the failure flag of the display |

## 5. Board

The programs of the tests repository ran on the DE0-CV board with the bitstream of the generated project (seed 5), through the board runner of the tests repository.

| Stage | Programs | Passed | Failed |
| :--- | ---: | ---: | :--- |
| SDRAM | 20 | 20 | none |
| Interrupts | 13 | 13 | none |
| Regression | 128 | 127 | `hpm-cpi` |

`hpm-cpi` checks that the sum of the cycles attributed by the event counters is within 1 % of `mcycle`, and it fails the same way with the hand-written bitstream built from the same tree (the first result word is 0 where 1 is expected). With the hand-written bitstream the SDRAM stage passes 19 of 20 programs, and `clint-mtip` is the one that fails.

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
