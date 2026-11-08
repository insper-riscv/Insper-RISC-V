# Resuming the clock work: from 76.9 MHz to 100 MHz

🌐 [Português](../../../pt-br/platform/timing/RETOMADA-DO-CLOCK.md) · [English](RETOMADA-DO-CLOCK.md)

## 1. State

The `de0-cv` platform runs the core and the fetch at 76.923077 MHz (1000 MHz divided by 13), with the core phase at 7500 ps, the values of `pll.core_clock_hz` and `pll.core_phase_ps` in `platform.yaml`. The five seeds close the setup in the slow model at 85 °C and the hold in the fast model at 0 °C in every domain, with a worst core slack of +0.562 ns ([FRENTE-F-ONDA2.md](FRENTE-F-ONDA2.md), section 9). The SDRAM controller and `DRAM_CLK` close at 100 MHz with more than +1.1 ns. The 100 MHz are missing in the loop of stage EX.

| Frequency | Core, worst of 5 seeds | Note |
| :--- | ---: | :--- |
| 76.923 MHz | +0.562 ns | Closes |
| 83.333 MHz | -0.771 ns | Core to core; the core to fetch pair fails in four seeds (-1.268 ns) |
| 100 MHz | -2.300 ns | Best seed -1.220 ns; fetch, SDRAM and `DRAM_CLK` close |

## 2. The EX loop

The loop that limits 100 MHz starts at `r_we_ok` and `r_fwd_match_rs*` (registers of `ID/EX` and `EX/MEM`) and goes through:

| Stretch | LUT levels | Typical delay (ns) |
| :--- | ---: | ---: |
| Forwarding select (`forwarding_unit`, fan-out 98) | 1 | 0.9 to 1.3 |
| Operand A multiplexer (`u_mux_alu_a`) | 2 | 1.6 |
| ALU (adder, shifter, result select) | 4 | 4.5 to 5.0 |
| Address class, branch decision, clear of `IF/ID`, `ID/EX` and `EX/MEM`, PC enable | 3 to 4 | 3.0 to 3.5 |

The sum is 11.0 to 11.5 ns of data against the 10 ns period. The cause is structural, not isolated routing: the forwarding, the ALU and the decision that clears the pipeline are in series within one cycle. The destinations of the same loop that end in `r_alu_out` (11.0 to 11.5 ns) show that cutting only the clear is not enough.

## 3. How to repeat the measurement

The files are in `dados/frente-f-onda2/` and run on PC1, with the Quartus lock.

```
export TIMING_DIR=/tmp/timing          # holds the .tcl files of this folder
flock /tmp/quartus-workstation.lock \
  printf "6000 1\n6000 2\n6000 3\n6000 4\n6000 5\n" | \
  xargs -P 3 -L 1 bash -c './run-sementes.sh cem_p$0 <repository-copy> 100.000000 $0 $1'
```

The script `run-sementes.sh` copies the repository per seed, changes the frequency and the phase of PLL outputs 2 and 3 in the copy, compiles with `de0-cv_synth.tcl` and writes `pares.txt` (the 400 worst paths per clock pair) and `detail-*.rpt`. `agrupa_caminhos.py pares.txt` lists the paths by source and destination, `pior_por_par.py pares.txt` gives the worst slack per pair, and `levels.tcl` with `niveis_resumo.py` makes the list by logic levels. Run at most three seeds at the same time on PC1.

## 4. Ideas not yet tried

1. Forward to the ALU only from registers: the EX result is registered and used in the next cycle. It takes the forwarding select and multiplexer out of the loop, at the cost of one cycle on every immediate data dependency (the CPI of code with short dependency chains goes up). It fits the five stages.
2. Compute the forwarding select in stage ID and register it in `ID/EX`, already combined with the validity of the instructions ahead (today the `ok` comes in last and has fan-out 98).
3. Register the branch and JALR redirect (one more cycle per taken branch, discarding the instruction that enters EX). It cuts the clear destinations but not those that end in `r_alu_out`; it only pays off together with idea 1 or 2.
4. Compute the address class from `rs1` and `imm` in parallel with the sum: the three hypotheses of the carry into the 4 KiB pages, chosen by the carry of the 12-bit adder.
5. A LogicLock region for the EX loop in the versioned `.qsf`, only if it measures a routing gain (1.3 to 1.9 ns between levels on the longest paths).
6. Manual replication of `r_we_ok` and of the selects (the `maxfan` attribute is not accepted by the GHDL of the formal run and Quartus did not gain from it).
7. Replace the shifter with a two-cycle version only for `sll`, `srl` and `sra` (the shift is the longest ALU branch after the adder).

## 5. Done criteria for 100 MHz

| # | Criterion | How to check |
| :--- | :--- | :--- |
| 1 | The five seeds close the setup in the slow model at 85 °C in every domain (core, fetch, SDRAM, `DRAM_CLK`, JTAG) and the hold in the fast model at 0 °C | `output_files/de0-cv.sta.summary` of each seed, table in `FRENTE-F-ONDA2.md` |
| 2 | `platform.yaml` has `pll.core_clock_hz: 100000000`, the phase that closed and a matching `interrupts.clock_hz`; `make check-memory-map` passes | `riscv-tools check-memory-map` |
| 3 | Every board program passes and the ACT4 ELFs of the full profile pass, on the board | `tools/board/board_run.py run` and `certify-board` |
| 4 | `make test` and `make formal` of the Core, the `icache` proof and the platform tests pass | CI of the repositories |
| 5 | The base CPI of the Tests programs is recorded before and after | [CPI-BASE.md](CPI-BASE.md) |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../../LICENSE).
