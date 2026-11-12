# Manual FPGA Embench validation

This is a separate physical experiment, not the automatic simulation workflow. One complete platform/profile was tested on a DE0-CV: all 19 programs passed three times (57 runs). The DE2-115 was not programmed. No main-branch merge or PR was created.

## Hardware and provenance

CPU/platform sources: `d0a1e096cb06f092b98d11af10efd744f07f6222`; tracked RTL and platform files were unchanged. The additional firmware ports are `hardware_board.c` and `frequency_probe.c`; their hashes are recorded in the context.

Board: DE0-CV, Cyclone V `5CEBA4F23C7`, JTAG ID `02B050DD`, selected cable `USB-Blaster [1-6]`. Profile: `rv32im_zicclsm_zicntr_zihpm_zifencei`, HPM 29x64, with the extras in `src/cyclone-v/de0-cv/platform.yaml`. The platform has 4 KiB instruction/data caches, emulated FLASH in M10K blocks and real 64 MiB SDRAM. This differs from the CI internal-memory/no-cache configuration.

Bitstream SHA-256: `30bebd2b1cd7a5a1abb3aada9ed578be104240d20c03098c3de16322507431e7`. Quartus 25.1std, seed 5. The exact pinned CI compiler image was reused (GCC 16.1, picolibc). The kernel target ISA was `rv32im_zicsr_zifencei`; enabled hardware extensions are a superset, not a claim that every extension was exercised.

RAM cap: 8 GiB, swap disabled, two CPU cores. Observed cgroup memory peak: 1.887 GiB.

## Clock and timing

- Configured CPU/fetch clock: **76.923077 MHz**. SDRAM controller: **100 MHz**.
- Independent host-reference check: **76.93 MHz**, conservative interval **76.21–77.67 MHz**. Two acknowledged cycle-counter snapshots were taken more than 120 seconds apart and bounded by host monotonic timestamps. The host clock is independent of the FPGA. JTAG request/response latency widens the interval; this is not a precision oscilloscope or frequency-counter measurement.
- All 84 entries in the STA summary had nonnegative slack and zero TNS. Minimum setup slack: 0.786 ns; minimum hold slack: 0.127 ns.
- The slow-85 C core domain restricted Fmax report is **85.98 MHz**. That report covers intra-clock paths only: it is not a verified maximum operating frequency of the complete multiclock system. The board was tested at 76.923077 MHz.
- Compilation succeeded with **0 errors and 57 warnings**. The STA report preserves unconstrained reserved JTAG TDI/TMS inputs, asynchronous GPIO inout directions and reserved TDO; no unconstrained clocks were reported. The complete reports and warnings are retained in the evidence package.

## Measurement and verification

The original pinned IoT 2.0 development snapshot and its inputs/verifiers were used. All original LOCAL_SCALE_FACTOR loops were kept, GLOBAL_SCALE_FACTOR=1, warmup=1, GNU C17 kernels at -O2, GNU C23 platform runtime, no LTO. XGBoost retained both its upstream verifier and the exact 126/128 classification guard.

The machine cycle and retirement counters are cleared/enabled in start_trigger and inhibited/snapshotted in stop_trigger. Fixed trigger overhead is included, not subtracted. Counter values are stored in the reserved, uncached stdout payload (offset 768), outside the measured interval; these silent programs do not print into that region. The host accepts data only after a successful verifier exit (`tohost=1`) and a valid result magic/version. CPU time is calculated from the gated counters, not host loading/wait duration. The normal host completion polls use the SDRAM debug port and can contend with CPU memory accesses; these records include that monitoring environment. Additional delayed-read controls are recorded separately.

An independent two-instruction assembly loop ran with 4,096 and 8,192 iterations. Measured retirement counts were 8,196 and 16,388: an exact difference of **8,192**, as independently expected. Cycle counts were 16,391 and 32,775. No performance counters were silently added to bare RV32I/IM: the physical port requires Zicsr/Zicntr and only the complete platform above was tested.

## Results

Each row selects the actual middle-cycle sample of three passing runs. Retired-instruction counts were identical across repetitions for every program. The largest cycle range was **0.0087%** of its program median. All 57 samples remain in the raw JSON. Time and MIPS use the configured operating clock, cross-checked above.

| Program | Passes | Median cycles | Instructions | CPI | IPC | MIPS (nominal clock) | Time ms (nominal clock) | Score/MHz |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aha-mont64 | 3/3 | 7303864 | 4978745 | 1.467 | 0.682 | 52.44 | 94.950 | 0.54793 |
| crc32 | 3/3 | 14187552 | 4005916 | 3.542 | 0.282 | 21.72 | 184.438 | 0.28236 |
| depthconv | 3/3 | 15815360 | 3623854 | 4.364 | 0.229 | 17.63 | 205.600 | 0.24293 |
| edn | 3/3 | 25824274 | 3224429 | 8.009 | 0.125 | 9.60 | 335.716 | 0.15513 |
| huffbench | 3/3 | 7887273 | 2444323 | 3.227 | 0.310 | 23.84 | 102.535 | 0.50626 |
| matmult-int | 3/3 | 21131045 | 2695619 | 7.839 | 0.128 | 9.81 | 274.704 | 0.18977 |
| md5sum | 3/3 | 9835266 | 3274103 | 3.004 | 0.333 | 25.61 | 127.858 | 0.39968 |
| nettle-aes | 3/3 | 12244935 | 4084146 | 2.998 | 0.334 | 25.66 | 159.184 | 0.32307 |
| nettle-sha256 | 3/3 | 24836498 | 4813591 | 5.160 | 0.194 | 14.91 | 322.874 | 0.16097 |
| nsichneu | 3/3 | 43372517 | 2242277 | 19.343 | 0.052 | 3.98 | 563.843 | 0.09921 |
| picojpeg | 3/3 | 14116475 | 2827448 | 4.993 | 0.200 | 15.41 | 183.514 | 0.27734 |
| qrduino | 3/3 | 8451821 | 2802108 | 3.016 | 0.332 | 25.50 | 109.874 | 0.46463 |
| sglib-combined | 3/3 | 13559799 | 2589455 | 5.237 | 0.191 | 14.69 | 176.277 | 0.30465 |
| slre | 3/3 | 14564271 | 2790653 | 5.219 | 0.192 | 14.74 | 189.336 | 0.27430 |
| statemate | 3/3 | 19137802 | 2600765 | 7.359 | 0.136 | 10.45 | 248.791 | 0.33551 |
| tarfind | 3/3 | 14342223 | 2583497 | 5.551 | 0.180 | 13.86 | 186.449 | 0.27925 |
| ud | 3/3 | 13945978 | 2593646 | 5.377 | 0.186 | 14.31 | 181.298 | 0.28209 |
| wikisort | 3/3 | 7081801 | 1757462 | 4.030 | 0.248 | 19.09 | 92.063 | 0.51145 |
| xgboost | 3/3 | 18050510 | 3506537 | 5.148 | 0.194 | 14.94 | 234.657 | 0.19545 |

Geometric mean of all 19 normalized scores: **0.28070/MHz** (**21.593** at the nominal operating clock). Normalization uses the pinned upstream baseline-data/speed.json. This is an experimental port of a development snapshot, not a certified official Embench submission.

No comparison with a previous Insper CPU, PR-base speed delta, power measurement, frequency sweep, or complete 11-profile physical matrix was performed. Simulation instruction-mix percentages were not copied into the hardware records. Automatic PR checks remain simulation-only.



Additional monitoring controls passed: nsichneu, sglib-combined and XGBoost each ran three more times with no RAM polling for three seconds after image loading. All nine first completion reads already reported success; retirement counts matched the original series. The largest absolute change between monitored and quiet medians was **0.0030%**. These selected controls quantify a small effect in this experiment; they do not establish zero monitoring overhead for every possible workload. The raw quiet-control.json preserves all nine measurements.

## Reproducibility

Small raw records, firmware hashes and the numeric table are retained in [evidence/de0-cv-20261111](evidence/de0-cv-20261111/). The laboratory evidence bundle additionally contains the tested standalone build/load/probe scripts, ELFs/disassembly, generated Quartus project, bitstream and full reports. It records a manual experiment; it does not install or register a GitHub self-hosted runner. Reusing it requires the same pinned sources/image and explicit board/cable verification. The FLASH loader uses the raw word address `memory.rom_base / 4`, including the boot gap.
