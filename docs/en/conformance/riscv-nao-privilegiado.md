# Conformance with the RISC-V unprivileged volume

🌐 [Português](../../pt-br/conformance/riscv-nao-privilegiado.md) · [English](riscv-nao-privilegiado.md)

This report matches every normative requirement of chapters 1, 2 and 4 to 11 of the RISC-V unprivileged manual (version 20260120) with the evidence that covers it. The implementation is in the [Core](../../../Core/README.en.md), and each requirement points to at least one test, proof or program.

## 1. Scope

Chapters are numbered as in the manual without the Introduction, the same numbering the Core documentation uses. The PDF prints each chapter with the next number.

| Chapter | Subject | Treatment |
| :--- | :--- | :--- |
| 1 | RV32I | Section 3 |
| 2 | RV32E | Section 4 |
| 3 | RV64I | Out of scope, because the project is RV32 |
| 4 | Zifencei | Section 5 |
| 5 | Zicsr | Section 6 |
| 6 | Zicntr and Zihpm | Section 7 |
| 7 | Zihintntl | Section 8 |
| 8 | Zihintpause | Section 9 |
| 9 | Zimop | Section 10 |
| 10 | Zicond | Section 11 |
| 11 | M and Zmmul | Section 12 |
| 12 | A | Out of scope, extension discarded |

## 2. How to read

### 2.1. Status

| Status | Meaning |
| :--- | :--- |
| Conforming | The Core meets the requirement and the evidence demonstrates it |
| EEI choice | The manual leaves the choice to the execution environment (EEI), and the Core records its own. In this project the EEI is the Insper-RISC-V SoC, with one hart in machine mode |

### 2.2. Evidence

| Tag | Where it lives | How to reproduce |
| :--- | :--- | :--- |
| cocotb `X` | Entry `X` of `tests/python/tests.json` in the Core | `make test TEST=X` in the Core |
| formal `file` | `formal/<file>.sv` in the Core, with the mutants the proof rejects | `make formal` in the Core |
| program `P` | `asm/P`, `asm-sdram/P` or `asm-hpm-reduced/P` of the Tests repository | `riscv-tools` of Tests, in simulation and on the board |
| ACT4 `folder` | ACT4 test folder (`riscv-arch-test`) run by the Certification repository, on the minimal profile of the extension | `certify` flow of Certification |

ACT4 covers the whole folder named, and the count in parentheses is the number of tests of the folder in the ACT4 pinned in `vendor/riscv-arch-test`.

## 3. Chapter 1: RV32I

### 3.1. Programming model

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I1 | XLEN is 32 and there are 32 general-purpose registers | Conforming | cocotb `bancoRegistradores`, ACT4 `rv32i/I` (39) |
| I2 | `x0` reads zero and ignores writes, also through the forwarding path | Conforming | cocotb `bancoRegistradores` and `ForwardingMatch`, programs `x0-readonly` and `conformance-decode` |
| I3 | The program counter has 32 bits and instructions are 32 bits aligned (IALIGN 32) | Conforming | cocotb `PcFetch` and `CoreMisalignedJump`, ACT4 `rv32i/I` (39) |
| I4 | Formats R, I, S, B, U and J have the manual immediates, sign-extended | Conforming | cocotb `ExtenderImm` and `ControlUnit` (against the opcode table of the manual), ACT4 `rv32i/I` (39) |

### 3.2. Computational instructions

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I5 | `ADDI`, `SLTI[U]`, `ANDI`, `ORI`, `XORI` and the constant shifts, with no arithmetic exception | Conforming | cocotb `ALU`, formal `alu_props` (plain operators for every operation), programs `arithmetic-addi-negative`, `compare-slti`, `compare-sltiu`, `logical-andi`, `logical-ori`, `logical-xori`, `shift-left-logical-imm`, `shift-right-logical-imm`, `shift-right-arithmetic-imm` |
| I6 | `ADD`, `SUB`, `SLT[U]`, `AND`, `OR`, `XOR`, `SLL`, `SRL` and `SRA` use the low five bits of `rs2` as the shift amount | Conforming | cocotb `ALU`, formal `alu_props`, programs `arithmetic-add`, `arithmetic-sub`, `compare-slt`, `compare-sltu`, `logical-and`, `logical-or`, `logical-xor`, `shift-left-logical`, `shift-right-logical-reg`, `shift-right-arithmetic-reg` |
| I7 | `LUI` loads the immediate into the upper 20 bits and `AUIPC` adds the immediate to the `pc` of the instruction itself | Conforming | cocotb `ControlUnit` and `ALU`, programs `load-upper-immediate` and `add-upper-immediate-to-pc`, ACT4 `rv32i/I` (39) |
| I8 | Constant shifts accept only the upper field of the manual (`imm[11:5]`), and the other encodings are reserved | EEI choice | cocotb `ControlUnit` and `CoreIllegalInstruction`: the Core raises an illegal instruction (cause 2) |

### 3.3. Control flow

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I9 | `JAL` and `JALR` write `pc + 4` to `rd` and jump; `JALR` clears bit 0 of the target | Conforming | programs `jump-jal` and `jump-jalr`, cocotb `CoreMisalignedJump`, ACT4 `rv32i/I` (39) |
| I10 | The six conditional branches compare signed and unsigned and jump to `pc` plus the immediate | Conforming | programs `branch-beq`, `branch-bne`, `branch-blt`, `branch-bge`, `branch-bltu`, `branch-bgeu`, formal `alu_props` (branch flag), ACT4 `rv32i/I` (39) |
| I11 | The misaligned instruction address exception happens only when the jump is taken, and is reported at the jump itself (`mepc` is the jump and `mtval` the target) | Conforming | program `trap-misaligned-jump`, cocotb `CoreMisalignedJump` |

### 3.4. Loads and stores

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I12 | `LB`, `LBU`, `LH`, `LHU`, `LW`, `SB`, `SH` and `SW` with sign or zero extension | Conforming | cocotb `ExtenderRAM` and `StoreManager`, programs `load-byte-signed`, `load-byte-unsigned`, `load-halfword-signed`, `load-halfword-unsigned`, `load-word`, `store-byte-roundtrip`, `store-halfword-roundtrip`, `store-word-roundtrip`, `section6-loadstore` |
| I13 | An aligned load or store never raises a misalignment exception | Conforming | formal `trap_unit_props` (aligned accesses never raise causes 4 and 6, by induction) |
| I14 | A misaligned access may be executed, emulated or trap, as the EEI decides | EEI choice | With `has_zicclsm` the Core runs the access in two steps in the main memory and raises causes 4 and 6 (with `mtval` equal to the address) outside it. Without Zicclsm every misaligned access traps. cocotb `MisalignedUnit`, `CoreMisaligned`, `CoreMisalignedHalf`, `TrapUnit`, `TrapUnitNoZicclsm`, `TrapUnitExtFlash`, `TrapUnitExtRom`, formal `trap_unit_props` (the four maps), programs `misaligned-crossing`, `trap-misaligned-ldst` and `misaligned-cache-lines`, ACT4 `rv32i/Zicclsm` (13) |
| I15 | A misaligned access need not be atomic | Conforming | The Core does it as two word accesses in the MEM stage, with no atomicity guarantee. Program `misaligned-crossing` |
| I16 | A load with `rd = x0` still raises the exceptions and side effects of the access | Conforming | Program `conformance-decode` (`lw x0` at an odd address raises cause 4 with `mtval` equal to the effective address) and program `trap-mem-squash` |

### 3.5. Memory and ordering

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I17 | `FENCE` ignores `rs1`, `rd`, `pred` and `succ`, and a reserved `fm` behaves as `fm = 0` | Conforming | Program `conformance-decode` (`fm` of 1, 2, 7 and 15, `pred` and `succ` zero, `rs1` and `rd` nonzero: no trap and `rd` intact) |
| I18 | `FENCE.TSO` (`fm = 1000`) may be treated as `FENCE RW,RW` | Conforming | Program `fence-tso`, ACT4 `rv32i/I` (39) |
| I19 | The RVWMO memory model holds for an in-order hart | Conforming | The pipeline runs one hart in order, and the caches keep program order. Programs `hazard-load-use`, `hazard-forwarding-raw`, `wb-hold-crossing` and `cache-sweep` |
| I20 | An instruction fetch precedes the memory accesses the instruction itself causes | Conforming | In-order pipeline, programs `hazard-load-use` and `selfmod-repeat` |

### 3.6. Environment calls, breakpoints and HINTs

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I21 | `ECALL` and `EBREAK` raise a precise trap (causes 11 and 3, `mepc` equal to the instruction address) | Conforming | Program `trap-ecall-ebreak`, cocotb `TrapUnit` and `CoreTrapTake`, formal `trap_unit_props` and `core_trap_take_props`, ACT4 `rv32i/I` (39) |
| I22 | `ECALL` and `EBREAK` do not count as retired instructions | Conforming | Program `cntr-trap-no-retire` |
| I23 | A HINT (computational instruction with `rd = x0`) changes only `pc` and the counters | Conforming | Program `conformance-decode` (every form of the manual table, `x0` zero also through forwarding, no trap, and `instret` adding 1 per HINT) |
| I24 | A reserved encoding raises an illegal instruction (the choice is the EEI's) | EEI choice | cocotb `ControlUnit`, `CoreIllegalInstruction` and `CoreTrapSignal`, program `trap-illegal` (cause 2, `mtval` zero) |

## 4. Chapter 2: RV32E

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| E1 | The RV32E has 16 general-purpose registers, `x0` to `x15`, with `x0` zero | Conforming | cocotb `CoreRv32e`, ACT4 `rv32e/E` |
| E2 | Encodings that use `x16` to `x31` in `rd`, `rs1` or `rs2` are reserved | EEI choice | The Core raises an illegal instruction (cause 2) without writing the destination. cocotb `CoreRv32e` and `CoreIllegalInstruction` |
| E3 | Apart from the register file, the RV32E is identical to the RV32I | Conforming | The pipeline and the forwarding do not change with `has_e`. ACT4 `rv32e/E`, `rv32e/M` and `rv32e/Zmmul` |
| E4 | `misa` reports the `E` extension in place of `I` | Conforming | cocotb `CsrFileRveNoM` |
| E5 | The RV32E combines with the M and Zmmul extensions | Conforming | ACT4 `rv32e/M` and `rv32e/Zmmul`, cocotb `CoreRv32e` |

## 5. Chapter 4: Zifencei

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| F1 | `FENCE.I` makes earlier stores of the same hart visible to fetch | Conforming | cocotb `FenceiUnit`, `FenceiUnitDcache`, `CoreFenceI` and `CoreFenceIDcache`, programs `sdram-exec-copy` and `selfmod-repeat`, ACT4 `rv32i/Zifencei` (1) |
| F2 | The `funct12`, `rs1` and `rd` fields are ignored | Conforming | Program `conformance-fencei`, cocotb `CoreFenceILegal` |
| F3 | `FENCE.I` orders earlier accesses before later fetches | Conforming | The `fencei_unit` redirects the flow to `pc + 4`, drops the instruction cache and waits for the data cache acknowledgement. cocotb `FenceiUnit` and `FenceiUnitDcache`, program `selfmod-repeat` |
| F4 | Without the extension, `FENCE.I` is not a legal instruction | Conforming | cocotb `CoreIllegalInstruction` (the word `0x0000100F` raises cause 2 without the extension) |

## 6. Chapter 5: Zicsr

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| C1 | The six instructions atomically read and modify a CSR, with the old value zero-extended in `rd` | Conforming | cocotb `CsrDecode` and `CsrFile`, program `csr-rw-basic`, formal `csr_file_props`, ACT4 `rv32i/Zicsr` (6) |
| C2 | `CSRRW` and `CSRRWI` with `rd = x0` do not read the CSR nor cause read effects | Conforming | Program `csr-x0-no-effect`; a CSR read in the Core has no side effect |
| C3 | `CSRRS`, `CSRRC`, `CSRRSI` and `CSRRCI` with `rs1 = x0` (or `uimm = 0`) read and do not write | Conforming | Program `csr-x0-no-effect`, formal `csr_file_props` |
| C4 | A register other than `x0` holding zero still performs the write of the whole CSR | Conforming | Program `csr-x0-no-effect` (`csrrs` and `csrrc` with a register at zero) |
| C5 | A write to a read-only CSR raises an illegal instruction, except `CSRRS`/`CSRRC` with `rs1 = x0` | Conforming | Programs `cntr-readonly-illegal` and `trap-illegal`, formal `csr_file_props` and `csr_hpm_props`, cocotb `CsrFile` |
| C6 | A CSR address the implementation lacks raises an illegal instruction | Conforming | Program `trap-illegal`, formal `csr_file_props`, cocotb `CsrFile` |
| C7 | A CSR modified as a side effect (such as `instret`) is read with the value before the instruction, and the explicit write wins over the update | Conforming | Programs `cntr-write`, `cntr-instret-exact` and `cntr-rollover`, formal `csr_cntr_props` |
| C8 | The effect of a CSR is visible to the next instruction, with no lost forwarding | Conforming | Programs `csr-forwarding`, `csr-back-to-back` and `cntr-forwarding` |
| C9 | A CSR read counts as device input and a write as device output, for `FENCE` | Conforming | The pipeline is in order with one hart, so program order is the global order. Program `csr-back-to-back` |
| C10 | A `SYSTEM` instruction with a reserved `funct3` or unsupported `funct12` raises an illegal instruction | Conforming | Program `trap-illegal` (`sret` and `funct3 = 100`), cocotb `CsrDecode` |

## 7. Chapter 6: Zicntr and Zihpm

### 7.1. Zicntr

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| K1 | Zicntr depends on Zicsr | Conforming | The profile matrix implies `has_zicsr`, and the `core` fails elaboration without it. `make profiles` in the Core |
| K2 | `cycle`, `time` and `instret` are 64-bit counters, read in two halves on RV32 (`cycleh`, `timeh` and `instreth`) | Conforming | cocotb `Counter64`, `CsrFileZicntr`, formal `counter64_props`, ACT4 `rv32i/Zicntr` (2) |
| K3 | The counters are read-only at addresses `0xC00` to `0xC02` and `0xC80` to `0xC82`, and the read uses `CSRRS` with `rs1 = x0` | Conforming | Program `cntr-readonly-illegal`, cocotb `CsrFileZicntr`, ACT4 `rv32i/Zicntr` (2) |
| K4 | `cycle` counts core clock cycles and never goes backwards | Conforming | Programs `cntr-cycle-monotonic` and `cntr-muldiv-cost`, formal `counter64_props` (monotonic without a write) and `csr_cntr_props` (64-bit model) |
| K5 | `time` adds one per tick of the real-time clock, with a constant period | Conforming | The `tick_divider` produces a tick every `tick_cycles` cycles. cocotb `TickDivider`, program `cntr-time-rate` |
| K6 | The environment reports the tick period of `time` | EEI choice | The period is $tick\_cycles / f_{clock}$, set by a generic and documented in `Core/docs/en/ISA/Zicntr/description.md` |
| K7 | `instret` counts retired instructions, and those that raise an exception do not count | Conforming | Programs `cntr-instret-exact`, `cntr-trap-no-retire` and `trap-mem-squash`, formal `csr_cntr_props` |
| K8 | A high, low, high read recovers a valid 64-bit value | Conforming | Program `cntr-rollover`, formal `counter64_props` (registered carry) |
| K9 | A counter may be inhibited, and a write to `mcycle` and `minstret` takes effect | Conforming | Program `cntr-write`, cocotb `CsrFileZicntr`, formal `csr_cntr_props` |
| K10 | Without `mcounteren`, every counter is accessible in the hart single mode | EEI choice | The Core has only M-mode and access to `mcounteren` is illegal, as the privileged manual allows. cocotb `CsrFile` |

### 7.2. Zihpm

Zihpm conformance has its own document, with the matrix of the requirements of the chapter and of the privileged volume, in [Core/docs/en/ISA/Zihpm/conformance.md](../../../Core/docs/en/ISA/Zihpm/conformance.md). The table below gathers the lines of that document next to the others.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| H1 | Zihpm depends on Zicsr | Conforming | `make profiles` and the `core` assertion |
| H2 | `hpmcounter3` to `hpmcounter31` and the high halves `hpmcounter3h` to `hpmcounter31h` are read-only 64-bit counters | Conforming | cocotb `CsrFileZihpmFull` and `CsrFileZihpm`, formal `csr_hpm_props`, programs `hpm-full` and `hpm-sweep`, ACT4 `rv32i/Zihpm` (2) |
| H3 | An unimplemented counter raises an illegal instruction or reads a constant | EEI choice | The Core reads zero and ignores the write. cocotb `CsrFileZihpmReduced`, program `hpm-reduced`, formal `csr_hpm_props` |
| H4 | The number, width and events of the counters belong to the platform | EEI choice | Generics `hpm_counters` (0 to 29) and `hpm_width` (0 to 64). cocotb `HpmCounterBankAll64`, `HpmCounterBankFour33` and `Counter64Width20` to `Counter64Width63`, programs `hpm-reduced` and `hpm-sweep` |
| H5 | An event register selects what each counter counts, and an event with no meaning counts zero | Conforming | Programs `hpm-inhibit-select`, `hpm-branch-count`, `hpm-load-use`, `hpm-muldiv-stall`, `hpm-cpi` and `hpm-fused-high`, cocotb `HpmCounterBankAll64` |
| H6 | `mcountinhibit` inhibits `cycle`, `instret` and the event counters | Conforming | Programs `hpm-inhibit-select` and `hpm-sweep`, formal `csr_hpm_props` |
| H7 | An explicit write wins over the increment of the same cycle | Conforming | formal `counter64_props` and `csr_hpm_props`, cocotb `HpmCounterBankAll64` |

## 8. Chapter 7: Zihintntl

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| N1 | `ntl.p1`, `ntl.pall`, `ntl.s1` and `ntl.all` are `ADD x0, x0, x2` to `x5` | Conforming | cocotb `ZihintntlDecode`, formal `zihintntl_props` (exactly the four words) |
| N2 | An implementation may ignore the hint and run it as a `nop`, with no exception | Conforming | The Core runs it as a `nop`, and the decoder turns off the write to `rd`. cocotb `CoreZihint`, program `zihintntl-hints` |
| N3 | The hint changes neither registers nor memory | Conforming | Program `zihintntl-hints` (`x2` to `x5` and `x0` intact, also through forwarding) |
| N4 | The hint counts as a retired instruction | Conforming | Program `conformance-decode` (the `ADD` with `rd = x0` retires once and adds 1 to `instret`) |
| N5 | The compressed forms (`c.ntl.*`) belong to the C extension | EEI choice | The Core does not implement the C extension |
| N6 | The ACT4 of the extension passes | Conforming | ACT4 `rv32i/Zihintntl` (8) |

## 9. Chapter 8: Zihintpause

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| P1 | `pause` is the `FENCE` with `pred = W`, `succ = 0`, `fm = 0`, `rs1 = rd = x0` (word `0x0100000F`) | Conforming | cocotb `ZihintpauseDecode`, formal `zihintpause_props` (exactly the word) |
| P2 | `pause` is a hint that may run as a `nop`, with no exception | Conforming | The Core runs it as `FENCE`, which is a `nop`. cocotb `CoreZihint`, program `zihintpause-loop` |
| P3 | The pause has no mandatory minimum duration | EEI choice | The Core does not delay the next instruction |
| P4 | The other `FENCE` instructions are not `pause` | Conforming | formal `zihintpause_props`, program `conformance-decode` |
| P5 | The ACT4 of the extension passes | Conforming | ACT4 `rv32i/Zihintpause` (1) |

## 10. Chapter 9: Zimop

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| O1 | There are 32 `mop.r.n` instructions (`n` from 0 to 31) and 8 `mop.rr.n` instructions (`n` from 0 to 7) in the `SYSTEM` class | Conforming | cocotb `ZimopDecode`, formal `zimop_props` (exactly the 40 encodings) |
| O2 | Each MOP writes zero to `rd` | Conforming | cocotb `CoreZimop`, formal `zimop_props`, programs `zimop-mop-r` and `zimop-mop-rr` |
| O3 | A MOP never raises an illegal instruction when the extension is present | Conforming | Programs `zimop-mop-r` and `zimop-mop-rr` (no trap), cocotb `CoreZimop` |
| O4 | A MOP with `rd = x0` changes no state, and `mop.rr` reads `rs1` and `rs2` | Conforming | cocotb `CoreZimop`, formal `zimop_props` |
| O5 | Without the extension, the encoding is an unsupported `SYSTEM` instruction | Conforming | cocotb `CoreZimopOff` (cause 2, `rd` intact and the program resumes) |
| O6 | The ACT4 of the extension passes | Conforming | ACT4 `rv32i/Zimop` (40) |

## 11. Chapter 10: Zicond

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| Z1 | `czero.eqz rd, rs1, rs2` writes zero if `rs2 = 0` and `rs1` otherwise | Conforming | cocotb `ZicondUnit` and `CoreZicond`, formal `zicond_props`, programs `zicond-bits` and `zicond-edge` |
| Z2 | `czero.nez rd, rs1, rs2` writes zero if `rs2` is nonzero and `rs1` otherwise | Conforming | cocotb `ZicondUnit` and `CoreZicond`, formal `zicond_props`, programs `zicond-bits` and `zicond-edge` |
| Z3 | The condition looks at the whole `rs2` register, and the value of `rs1` reaches every bit | Conforming | Program `zicond-bits` (every bit of `rs2` decides the condition and every bit of `rs1` reaches the destination) |
| Z4 | The encoding is `opcode = 0110011`, `funct7 = 0000111` and `funct3 = 101` or `111` | Conforming | cocotb `ZicondDecode`, formal `zicond_decode_props` |
| Z5 | Without the extension, the encoding is illegal | Conforming | cocotb `CoreZicondOff` |
| Z6 | The ACT4 of the extension passes | Conforming | ACT4 `rv32i/Zicond` (2) |

## 12. Chapter 11: M and Zmmul

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| M1 | `MUL` writes the low half of the 32 by 32 bit product, and `MULH`, `MULHU` and `MULHSU` the high half, signed and unsigned | Conforming | cocotb `BoothMultiplier`, `MultDiv`, `MDecode` and `CoreMulDiv`, programs `mul`, `mulh`, `mulhu` and `mulhsu`, ACT4 `rv32i/M` (8) |
| M2 | `DIV`, `DIVU`, `REM` and `REMU` truncate toward zero, and the remainder has the sign of the dividend | Conforming | cocotb `NonRestoringDivider`, `MultDiv` and `CoreMulDiv`, programs `div`, `divu`, `rem` and `remu`, ACT4 `rv32i/M` (8) |
| M3 | Division by zero gives an all-ones quotient and a remainder equal to the dividend, with no trap | Conforming | cocotb `NonRestoringDivider` and `MultDiv`, programs `div`, `divu`, `rem` and `remu` |
| M4 | Signed overflow (`-2^31 / -1`) gives a quotient equal to the dividend and a zero remainder, with no trap | Conforming | cocotb `NonRestoringDivider` and `MultDiv`, programs `div` and `rem` |
| M5 | Fusing `MULH[[S]U]` followed by `MUL`, and `DIV[U]` followed by `REM[U]`, is recommended | Conforming | The Core reuses the full result when the operands match. cocotb `MuldivFusion`, formal `muldiv_fusion_props`, programs `muldiv-fusion` and `hpm-fused-high` |
| M6 | Latency has no requirement | Conforming | The pipeline stalls for a fixed number of cycles. Programs `cntr-muldiv-cost` and `hpm-muldiv-stall`, cocotb `CoreMulDiv` |
| M7 | Results reach whoever uses them next | Conforming | Programs `hazard-forwarding-mul`, `div-rem-back-to-back`, `trap-muldiv-load-use` and `wb-hold-crossing` |
| M8 | Zmmul has only the four multiplications, and division is illegal | Conforming | cocotb `CoreZmmul` and `MDecode`, ACT4 `rv32i/Zmmul` (4) and `rv32e/Zmmul` |
| M9 | M implies Zmmul | Conforming | The profile matrix forbids the two names together, and `has_m` includes the multiplication. `make profiles` in the Core |

## 13. Additions from other volumes

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| X1 | The Ztso extension is not declared, and `FENCE.TSO` runs as `FENCE RW,RW` | Conforming | Program `fence-tso`, ACT4 `rv32i/I` (39) |
| X2 | In a machine-mode-only implementation, `mstatush` exists and reads zero | Conforming | cocotb `CsrFile` (`mstatush` reads zero and ignores the write) and formal `csr_file_props` (fixed bits) |
| X3 | In a machine-mode-only implementation, `menvcfg` and `mcounteren` are not required | EEI choice | The Core does not implement them, and access to `mcounteren` (`0x306`), `menvcfg` (`0x30A`) and `menvcfgh` (`0x31A`) raises an illegal instruction. cocotb `CsrFile` |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
