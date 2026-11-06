# Conformance with the RISC-V privileged volume

🌐 [Português](../../pt-br/conformance/riscv-privilegiado.md) · [English](riscv-privilegiado.md)

This report checks every normative requirement of the RISC-V privileged volume (version 20260120) that applies to a hart with machine mode only, and to the extensions and modules the project implements, against the evidence that covers it. The hart is the one of the [Core](../../../Core/README.en.md), with five stages, the U, S and H modes absent, no virtual memory and no PMP; the platform is the SoC of this repository, with the CLINT and the PLIC. It is the sibling of the [unprivileged volume report](riscv-nao-privilegiado.md), with the same structure.

## 1. Scope

The section numbering is the one of the privileged volume. Each requirement has a row with the status and the evidence, and no cell is left empty.

| Manual chapter | Subject | Treatment |
| :--- | :--- | :--- |
| 2 | Control and status registers | Sections 3 to 7 and 11 |
| 3.1.1 to 3.1.5 and 3.1.17 | `misa` and the identification registers | Section 3 |
| 3.1.6 | `mstatus` and `mstatush` | Section 4 |
| 3.1.7 | `mtvec` | Section 5 |
| 3.1.8 and 3.1.9 | Delegation, `mip` and `mie` | Section 6 |
| 3.1.10 to 3.1.12 | Counters, `mcounteren` and `mcountinhibit` | Section 11 |
| 3.1.13 to 3.1.16 | `mscratch`, `mepc`, `mcause` and `mtval` | Sections 7 and 8 |
| 3.1.18 and 3.1.19 | `menvcfg` and `mseccfg` | Section 8, row X5 |
| 3.2.1 | `mtime` and `mtimecmp` | Section 13 |
| 3.3 | `ECALL`, `EBREAK`, `MRET`, `WFI` | Sections 9 and 10 |
| 3.4 | Reset | Section 12 |
| 3.5 | Non-maskable interrupts | Section 15 |
| 3.6 and 3.7 | PMA and PMP | Section 14 |
| 14 | Sscofpmf | Section 11.2 |
| 4 to 13 and 15 to 23 | S and H modes, virtual memory, debug, security and control-flow extensions | Section 15, out of scope |

## 2. How to read

### 2.1. Status

| Status | Meaning |
| :--- | :--- |
| Conforming | The Core or the platform meets the requirement and the evidence shows it |
| EEI choice | The manual leaves the choice to the execution environment (EEI) or the platform, and the project records its own. In this project the EEI is the Insper-RISC-V SoC, with one hart in machine mode |
| Not applicable | The requirement belongs to a mode or extension the hart lacks |
| Open gap | The manual requires or strongly recommends it and the project does not meet it; section 16 gives the reason |

### 2.2. Evidence

| Abbreviation | Where it is | How to reproduce |
| :--- | :--- | :--- |
| cocotb `X` | Entry `X` of `tests/python/tests.json` of the Core (or of Peripherals, on the CLINT rows) | `make test TEST=X` in the repository |
| formal `file` or `proof` | `formal/<file>.sv` of the Core, with the mutants the proof rejects; the label `csri_safety` and the like are the proofs of `formal/run.sh` | `make formal` in the Core |
| program `P` | `asm/P` or `asm-irq/P` of the Tests repository | `riscv-tools` of Tests, in simulation and on the board; the `asm-irq/` ones with `tests/python/runner.py irq-programs` |
| ACT4 `folder` | Test folder of the ACT4 (`riscv-arch-test`) that the Certification repository runs; the ACT4 of this version has no machine-mode tests beyond Zicsr, Zicntr, Zihpm and `I` | `certify` flow of the Certification |

## 3. Identification registers

Sections 3.1.1 to 3.1.5 and 3.1.17. The volume demands that all be readable; the identification ones may be zero.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| D1 | `misa` is readable in any implementation (zero would mean it does not exist) | Conforming | cocotb `CsrFile` (`test_reset_values`), programs `csr-rw-basic` and `priv-csr-priority` |
| D2 | The `MXL` field is read-only and is 1 on RV32 | Conforming | cocotb `CsrFile`, `CsrFileNoM` and `CsrFileRveNoM`, formal `csr_file_props`, program `priv-csr-priority` |
| D3 | The `Extensions` field announces the base (`I` or `E`) and the `M` extension; `E` reads as the complement of `I` | Conforming | cocotb `CsrFile`, `CsrFileNoM`, `CsrFileRveNoM`, formal `csr_file_props`, program `priv-csr-priority` |
| D4 | If the environment accepts both `I` and `E`, `I` is selected at reset | EEI choice | Each profile has a single base, chosen at elaboration (`base_e`); the `misa` of the RV32E profile announces only `E`. cocotb `CsrFileRveNoM` |
| D5 | Reserved bits and the bits of extensions the hart lacks (`A`, `C`, `F`, `D`, `S`, `U`, `H`, `V`, `B`) read zero | Conforming | cocotb `CsrFile` (`test_field_masks`), formal `csr_file_props` |
| D6 | `misa` is WARL: a write the hart does not accept leaves the value unchanged | Conforming | The Core does not let an extension be turned off: the write is ignored and raises no exception. cocotb `CsrFile`, program `csr-rw-basic` |
| D7 | `Zmmul` without `M` does not set the `M` bit; the `M` bit means all `M` instructions are present | Conforming | cocotb `CsrFileNoM`, ACT4 `rv32i/Zmmul` (4) |
| D8 | `mvendorid` is readable; zero means no JEDEC identifier or a non-commercial implementation | EEI choice | Reads zero: the project has no JEDEC identifier. cocotb `CsrFile` (`test_read_only_csrs`), programs `trap-illegal` and `priv-csr-priority` |
| D9 | `marchid` is readable; zero means it is not implemented | EEI choice | Reads zero: RISC-V International allocated no architecture identifier to the project. cocotb `CsrFile`, program `priv-csr-priority` |
| D10 | `mimpid` is readable; zero means it is not implemented | EEI choice | Reads zero. cocotb `CsrFile`, program `priv-csr-priority` |
| D11 | `mhartid` is readable and one hart has number zero | Conforming | The Core has one hart, numbered zero. cocotb `CsrFile`, programs `csr-rw-basic` and `priv-csr-priority` |
| D12 | `mconfigptr` is readable, may be zero, and the pointer is aligned to `MXLEN` | EEI choice | Reads zero: there is no hardware configuration structure. cocotb `CsrFile`, program `priv-csr-priority` |
| D13 | These five registers are read-only: an effective write raises an illegal instruction, and `CSRRS`/`CSRRC` with `rs1 = x0` only read | Conforming | cocotb `CsrFile` (`test_read_only_csrs`), formal `csr_file_props`, programs `trap-illegal` and `priv-csr-priority` |

## 4. `mstatus` and `mstatush`

Section 3.1.6.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| S1 | `mstatus` is read/write, and `MIE` (bit 3) and `MPIE` (bit 7) keep the written value | Conforming | cocotb `CsrFile` (`test_field_masks`), formal `csr_file_props`, program `csr-rw-basic` |
| S2 | On a trap, `MPIE` takes `MIE`, `MIE` goes to zero and `MPP` keeps the previous mode | Conforming | cocotb `CsrFile` (`test_trap_records_the_exception_and_closes_the_interrupt_enable`), formal `csr_file_props` (mutant `trap_keeps_mie`), programs `trap-ecall-ebreak` and `irq-timer-basic` |
| S3 | `MRET` copies `MPIE` to `MIE`, sets `MPIE` to 1 and sets `MPP` to the least-privileged supported mode | Conforming | cocotb `CsrFile` (`test_mret_restores_the_interrupt_enable`), formal `csr_file_props` (mutant `mret_no_mpie`), program `irq-timer-basic` |
| S4 | `MPP` is WARL and holds only implemented modes; with a single mode it is fixed | Conforming | The only mode is M, so `MPP` (bits 12:11) always reads `11` and the write is ignored. cocotb `CsrFile` (`test_field_masks`), formal `csr_file_props` |
| S5 | `SIE`, `SPIE` and `SPP` are read-only zero without S-mode | Conforming | They read zero. cocotb `CsrFile` (`test_field_masks`) |
| S6 | `MPRV`, `MXR`, `SUM`, `TVM`, `TW`, `TSR` and `UBE` are read-only zero without U and S modes | Conforming | They read zero. cocotb `CsrFile` |
| S7 | `FS`, `VS`, `XS` and `SD` are read-only zero without the extensions that use the state | Conforming | The Core has no `F`, `D` or `V`. cocotb `CsrFile` |
| S8 | `MBE`, `SBE` and `UBE` control the byte order; `MBE` is 0 at reset, and a little-endian-only hart reads them as zero | Conforming | The Core is little-endian and these bits read zero. cocotb `CsrFile` |
| S9 | `mstatush` exists on RV32 and holds the upper fields of `mstatus` | Conforming | It exists (`0x310`), reads zero and ignores the write, with no exception. cocotb `CsrFile`, program `priv-csr-priority` |
| S10 | `MDT` and `SDT` (Smdbltrp), `MPELP` and `SPELP` (Zicfilp), `MPV` and `GVA` (H): fields of extensions the Core lacks | Not applicable | The bits read zero (the `MDT` with reset at 1 belongs to Smdbltrp, which the Core does not implement) |
| S11 | At reset, `MIE`, `MPRV` and `MBE` are 0 | Conforming | cocotb `CsrFile` (`test_reset_values`) |
| S12 | A CSR write takes effect after the writing instruction completes, and the next instruction already sees it | Conforming | The pipeline is in order, with CSR forwarding. Programs `csr-forwarding`, `csr-back-to-back` and `irq-masked` |

## 5. `mtvec`

Section 3.1.7.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| V1 | `mtvec` exists, is WARL and `BASE` is 4-byte aligned | Conforming | cocotb `CsrFile`, `CsrFileIrq` (`test_mtvec_mode_bit_is_kept_and_base_is_aligned`), formal `csri_safety` |
| V2 | In direct mode (`MODE` = 0) every trap goes to `BASE` | Conforming | Programs `trap-ecall-ebreak`, `trap-illegal` and `irq-timer-basic`, cocotb `CoreTrapTake`, formal `core_trap_take_props` |
| V3 | In vectored mode (`MODE` = 1) the exception goes to `BASE` and the interrupt to `BASE + 4 x cause` | Conforming | cocotb `CoreIrqVectored`, formal `stage_ex_irq_props`, programs `irq-vectored` and `irq-lcofi-priority` |
| V4 | `MODE` of 2 or more is reserved | EEI choice | Bit 1 reads zero and bit 0 keeps the mode: a write with the reserved mode ends up direct or vectored according to bit 0. cocotb `CsrFileIrq`, program `irq-vectored` |
| V5 | The vectored mode may need an alignment greater than 4 bytes | EEI choice | In that mode `BASE` is aligned to 64 bytes (bits 5:2 read zero), so `BASE + 4 x cause` is a bit swap. Formal `csri_safety` (mutant `irq_mtvec_unaligned_vector`), program `irq-vectored` |
| V6 | Without interrupts the vectored mode has no effect | Conforming | Without `has_interrupts` the `MODE` bit reads zero. cocotb `CsrFileNoIrq`, formal `csrio_safety` |
| V7 | The reset value of `mtvec` and the reset and NMI vectors belong to the platform | EEI choice | `mtvec` clears at reset, and the platform reset vector is address 0 of the `BOOT_MEMORY`. cocotb `CsrFile` (`test_reset_values`), `docs/en/platform/boot.md` |
| V8 | NMI vector (Smrnmi) | Not applicable | The Core implements no NMI |

## 6. Interrupts: `mip`, `mie` and the entry

Sections 3.1.8, 3.1.9 and Table 16. Interrupt 13 (counter overflow) belongs to Sscofpmf and is turned on by the `has_sscofpmf` generic.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| Q1 | Bit `i` of `mip` and `mie` corresponds to interrupt cause `i` | Conforming | Bits 3 (software), 7 (timer), 11 (external) and 13 (counter overflow). cocotb `CsrFileIrq`, formal `csri_safety` and `csrof_safety` |
| Q2 | Interrupt `i` traps to M-mode if `MIE` is 1, bit `i` is 1 in `mip` and `mie`, and `mideleg` does not delegate it | Conforming | cocotb `CsrFileIrq` (`test_take_needs_mstatus_mie_and_a_pending_enabled_line`), `CoreIrqSweep`, formal `csri_safety`, program `irq-masked` |
| Q3 | The condition is evaluated in bounded time after the interrupt becomes pending, and right after `MRET` and a write to `mip`, `mie` or `mstatus` | Conforming | The condition is combinational over the registers, evaluated at every instruction. cocotb `CoreIrqSweep` (random instants), programs `irq-masked` (the interrupt takes the instruction after the `mie` write) and `irq-timer-basic` (return by `MRET`) |
| Q4 | The priority of several interrupts to M-mode is MEI, MSI, MTI, SEI, SSI, STI and LCOFI | Conforming | cocotb `CsrFileIrq` (`test_cause_priority_is_external_software_timer`), `CoreIrqPriority`, formal `csri_safety` and `csrof_safety`, programs `irq-priority` and `irq-lcofi-priority` |
| Q5 | `MEIP`, `MTIP` and `MSIP` are read-only in `mip`, and the platform clears them | Conforming | A write to `mip` is legal and does not change them; the lines come from the CLINT and the PLIC. cocotb `CsrFileIrq` (`test_a_write_to_mip_is_legal_and_ignored`), formal `csri_safety` |
| Q6 | A `mie` bit is writable if the interrupt can become pending, and the others read zero | Conforming | `mie` keeps bits 3, 7 and 11 (and 13 with Sscofpmf). cocotb `CsrFileIrq` (`test_mie_keeps_only_bits_3_7_and_11`), formal `csri_safety` |
| Q7 | `SEIP`, `STIP`, `SSIP` and `SEIE`, `STIE`, `SSIE` read zero without S-mode | Conforming | They read zero. cocotb `CsrFileIrq` |
| Q8 | Bits 16 and above of `mip` and `mie` are for platform use | EEI choice | The Core uses no local platform interrupts: these bits read zero. The peripheral sources arrive through `MEIP`, by the PLIC. cocotb `CsrFileIrq` |
| Q9 | `MSIP` and `MTIP` appear in `mip` "eventually, not necessarily immediately" | EEI choice | The lines enter `mip` in the same cycle the CLINT output changes, and the CLINT registers `MTIP` for one cycle. cocotb `CsrFileIrq`, `CLINT` (Peripherals) |
| Q10 | The interrupt is precise: `mepc` is the first instruction that did not complete | Conforming | cocotb `CoreIrqSweep` and `CoreIrqFenceI`, formal `stage_ex_irq_props`, programs `irq-mepc-precise` and `irq-timer-basic` |
| Q11 | When an interrupt and an exception hold for the same instruction, the manual does not set the order | EEI choice | The interrupt wins and the instruction is aborted, so the exception only happens if it executes after the return. cocotb `CoreIrqSweep` (synchronous exceptions under interrupt), `TrapUnitIrq`, program `irq-ecall` |
| Q12 | The exact moment `FENCE.I` lets an interrupt in belongs to the implementation | EEI choice | `FENCE.I` is not aborted, and the interrupt waits one cycle for it. cocotb `CoreIrqFenceI`, formal `trap_unit_props` (`IRQ` mode) |
| Q13 | An interrupt for a more privileged mode is never masked by a less privileged one | Conforming | The Core has M-mode only |
| Q14 | `mideleg` and delegation of interrupts to S-mode | Not applicable | Without S-mode, `mideleg` does not exist and the access is illegal. cocotb `CoreTrapPriority` |
| Q15 | The machine external interrupt is pending while the controller asserts it, and the controller clears it | Conforming | `MEIP` is the PLIC output (one M-mode context); the program clears the source by claim and complete. `plic-*` programs of Tests, `plic_props` proofs of Peripherals |

## 7. `mscratch`, `mepc`, `mcause` and `mtval`

Sections 3.1.13 to 3.1.16.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| T1 | `mscratch` is read/write with `MXLEN` bits | Conforming | cocotb `CsrFile`, programs `csr-rw-basic`, `csr-forwarding` and `csr-x0-no-effect` |
| T2 | `mepc[1:0]` is zero when `IALIGN` is 32, also on the implicit read of `MRET` | Conforming | The two low bits are cleared on write. cocotb `CsrFile` (`test_trap_aligns_mepc`), formal `csr_file_props` (mutant `mepc_odd`), program `priv-csr-priority` |
| T3 | `mepc` is WARL and holds every valid address | Conforming | It keeps the 30 high bits of the 32-bit address. cocotb `CsrFile`, formal `csr_file_props` |
| T4 | On a trap, `mepc` gets the address of the interrupted or faulting instruction, and only a trap or the program writes it | Conforming | Programs `trap-ecall-ebreak`, `trap-misaligned-jump`, `trap-misaligned-ldst`, `trap-mem-squash` and `irq-mepc-precise`, cocotb `CoreTrapTake`, `CoreMemTrapEx` |
| T5 | `mcause` has the interrupt bit and the code; only a trap or the program writes it | Conforming | cocotb `CsrFile`, `CoreTrapSignal`, programs `trap-illegal` and `irq-timer-basic` |
| T6 | The `Exception Code` field is WLRL and only guarantees supported codes | EEI choice | The register keeps the 32 bits written, a superset of the supported codes. cocotb `CsrFile` |
| T7 | On a trap, `mtval` gets zero or exception-specific information; the faulting address, if nonzero, for causes 0, 4 and 6 | Conforming | Causes 0, 4 and 6: faulting address (jump target or effective address). Programs `trap-misaligned-jump` and `trap-misaligned-ldst`, cocotb `TrapUnit`, formal `trap_unit_props` |
| T8 | On `EBREAK`, `mtval` gets zero or the instruction address | EEI choice | Gets zero (the address is already in `mepc`). Program `trap-ecall-ebreak`, formal `trap_unit_props` |
| T9 | On an illegal instruction, `mtval` gets zero or the instruction bits | EEI choice | Gets zero. Program `trap-illegal`, cocotb `CoreIllegalInstruction` and `CoreTrapPriority`, formal `trap_unit_props` |
| T10 | On the other traps (`ECALL`, interrupts), `mtval` gets zero | Conforming | Programs `trap-ecall-ebreak` and `irq-timer-basic`, formal `trap_unit_props` |
| T11 | `mtval` is WARL and holds every valid address and zero | Conforming | It keeps 32 bits and is writable. cocotb `CsrFile`, formal `csr_file_props` |

## 8. Synchronous exceptions and the priority

Section 3.1.15, Tables 16 and 17, and 3.6. The exceptions that depend on modes, virtual memory or absent extensions are marked not applicable.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| X1 | Cause 0 (instruction address misaligned) comes from a taken jump or branch with a misaligned target, with `mepc` at the jump and `mtval` at the target; a branch not taken does not raise it | Conforming | Program `trap-misaligned-jump`, cocotb `CoreMisalignedJump` and `TrapUnit`, formal `trap_unit_props` |
| X2 | Cause 1 (instruction access fault) for an access that violates a PMA; the manual strongly recommends it be precise | Conforming | With `has_access_faults` (on in the `de0-cv` by `extras: [AccessFaults]`) a fetch outside ROM, RAM and the external window traps with `mtval` equal to the PC. cocotb `TrapUnitAccessFaults`, formal `trap_af_safety` (mutants `af_fetch_below_illegal`, `af_fetch_tval_ea`), program `access-fetch-fault` |
| X3 | Cause 2 (illegal instruction) covers a reserved or nonexistent encoding, an unsupported `SYSTEM` instruction, a nonexistent CSR and a write to a read-only CSR | Conforming | cocotb `CoreIllegalInstruction`, `CoreTrapPriority`, `ControlUnit`, `CsrDecode`, programs `trap-illegal`, `conformance-decode` and `priv-csr-priority`, formal `trap_unit_props` |
| X4 | The debug CSRs (`0x7B0` to `0x7BF`) and trigger CSRs (`0x7A0` to `0x7A3`) do not exist outside debug mode and raise an illegal instruction | Conforming | cocotb `CoreTrapPriority` (`dcsr`, `dpc`, `dscratch0`, `dscratch1`, `0x7B4`, `0x7BF`, `tselect`, `tdata1`), program `priv-csr-priority` (debug block) |
| X5 | The CSRs of modes and extensions the hart lacks (`sstatus`, `satp`, `medeleg`, `mideleg`, `mcounteren`, `menvcfg`, `mseccfg`, `mtinst`, `mtval2`, PMP, `scountovf`) raise an illegal instruction | Conforming | cocotb `CoreTrapPriority`, `CsrFile` (`test_unknown_csr_is_illegal`), `CsrFileZihpm`, formal `csr_file_props` and `csr_hpm_props`, program `trap-illegal` |
| X6 | Cause 3 (breakpoint) comes from `EBREAK`, with `mepc` at the instruction and no other operation | Conforming | Program `trap-ecall-ebreak`, cocotb `TrapUnit` and `CoreTrapSignal`, formal `trap_unit_props` |
| X7 | Causes 4 and 6 (misaligned load and store address) are optional, and the hart may execute the access or trap | EEI choice | With Zicclsm the Core executes the misaligned access in main memory and traps outside it (`mtval` is the effective address); without Zicclsm every misaligned access traps. cocotb `TrapUnit`, `TrapUnitNoZicclsm`, `CoreMisaligned`, programs `trap-misaligned-ldst` and `misaligned-crossing`, ACT4 `rv32i/Zicclsm` (13) |
| X8 | Causes 5 and 7 (load and store access fault) for an access that violates a PMA, such as a write to read-only memory | Conforming | With `has_access_faults` a load outside the map traps with cause 5 and a store outside the map or into the ROM with cause 7, with `mtval` equal to the address, before the misalignment, and without touching the memory. cocotb `TrapUnitAccessFaults`, `RegExMemFaults`, formal `trap_af_safety` (mutants `af_load_uses_write_flag`, `af_store_after_misaligned`, `af_store_fault_cause_load`), programs `access-load-fault` and `access-store-fault` |
| X9 | Causes 8 and 9 (`ECALL` from U and S), 10, 12, 13 and 15 (page faults), 14 and 17 | Not applicable | The Core has neither U and S modes nor virtual memory |
| X10 | Causes 16 (double trap, Smdbltrp), 18 (software check, Zicfilp and Zicfiss) and 19 (hardware error) | Not applicable | The Core has neither these extensions nor hardware error detection |
| X11 | Cause 11 (environment call from M-mode) comes from `ECALL`, with `mepc` at the instruction and no other operation | Conforming | Program `trap-ecall-ebreak`, cocotb `TrapUnit` and `CoreTrapSignal`, formal `trap_unit_props`, ACT4 `rv32i/I` (39) |
| X12 | Among the exceptions of one instruction the order of Table 17 holds: illegal instruction (2), instruction address misaligned (0), `ECALL`, `EBREAK` and, last, the memory-access ones | Conforming | A `JALR` or branch with a reserved encoding and a misaligned target raises cause 2. cocotb `TrapUnit` (`test_illegal_goes_before_misaligned_target`), `CoreTrapPriority`, formal `trap_unit_props` (mutants `illegal_ignored` and `misaligned_over_illegal`), program `priv-csr-priority` |
| X13 | The relative order of load and store misalignment and access faults belongs to the implementation | EEI choice | Without access faults there is only misalignment. cocotb `TrapUnit` |
| X14 | The exception is precise: the faulting instruction writes no register, memory or CSR, and the older ones complete | Conforming | Programs `trap-mem-squash`, `trap-muldiv-load-use` and `trap-illegal`, cocotb `CoreMemTrapEx`, `CoreTrapTake` and `CoreIllegalInstruction`, formal `core_trap_take_props` |
| X15 | `ECALL` and `EBREAK` do not retire and do not add to `minstret` | Conforming | Program `cntr-trap-no-retire`, formal `csr_cntr_props` |
| X16 | Causes 24 to 31 and 48 to 63 (custom use) | Not applicable | The Core defines no custom exceptions |

## 9. Trap entry and return

Sections 3.1.6.1, 3.3.1 and 3.3.2.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| E1 | On a trap into M-mode, `mepc`, `mcause` and `mtval` are written, `MPIE` takes `MIE`, `MIE` goes to zero and the `pc` takes the `mtvec` vector | Conforming | cocotb `CsrFile`, `CoreTrapTake`, formal `csr_file_props` and `core_trap_take_props`, programs `trap-ecall-ebreak` and `irq-timer-basic` |
| E2 | `MRET` is always present, restores `MIE` from `MPIE`, sets `MPIE` to 1 and takes the `pc` to `mepc` | Conforming | cocotb `CsrFile`, `TrapUnit`, formal `csr_file_props` and `trap_unit_props` (exactly the word `0x30200073`), programs `trap-ecall-ebreak` and `irq-timer-basic` |
| E3 | `ECALL`, `EBREAK`, `MRET` and `WFI` need `rd` and `rs1` zero and `funct3` zero; the other combinations are reserved | Conforming | The reserved combinations raise cause 2. cocotb `TrapUnit` (`test_unsupported_system_is_illegal`), formal `trap_unit_props` (mutant `mret_any_imm`), program `trap-illegal` |
| E4 | `SRET`, `SFENCE.VMA`, `HFENCE`, `SINVAL` and the S and H mode `SYSTEM` instructions | Not applicable | Without S and H modes they are illegal (the manual says `SRET` must be illegal without S-mode). Program `trap-illegal` (`sret`) |
| E5 | The `SYSTEM` space reserved for custom use defines no instruction in the Core, and an access raises an illegal instruction | Conforming | cocotb `TrapUnit`, `CsrDecode` |

## 10. `WFI`

Section 3.3.3 and the custom `SYSTEM` space of section 3.3.4.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| I1 | `WFI` exists in all privileged modes and is unaffected by `MIE` | Conforming | `WFI` executes as a `nop`, with and without `MIE`. cocotb `TrapUnit` (`test_wfi_is_a_nop`), program `irq-wfi` |
| I2 | `WFI` may stall the hart until an enabled interrupt, or be a `nop`; if it does not stall, the interrupt enters on an instruction of the idle loop | EEI choice | The Core executes it as a `nop`: the interrupt enters over the `WFI` itself, which executes again after the return. Program `irq-wfi`, cocotb `TrapUnit` |
| I3 | The hart may resume for any reason, and the program checks `mip` for what happened | Conforming | As a `nop`, the resume is immediate; the program reads `mip`. Program `irq-wfi` |
| I4 | `TW` of `mstatus` may make `WFI` raise an illegal instruction in less privileged modes | Not applicable | There is only M-mode |

## 11. Counters and Sscofpmf

### 11.1. Counters

Sections 3.1.10 to 3.1.12. The Zihpm conformance, row by row, is also in [Core/docs/en/ISA/Zihpm/conformance.md](../../../Core/docs/en/ISA/Zihpm/conformance.md).

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| C1 | `mcycle` and `minstret` have 64 bits (halves `mcycleh` and `minstreth`) and are writable | Conforming | cocotb `Counter64`, `CsrFileZicntr`, formal `counter64_props` and `csr_cntr_props`, programs `cntr-write` and `cntr-rollover`, ACT4 `rv32i/Zicntr` (2) |
| C2 | The counters have an arbitrary value after reset | EEI choice | They clear at reset. cocotb `CsrFileZicntr` |
| C3 | A CSR write takes effect after the instruction completes, and an explicit write beats the increment of the cycle | Conforming | Formal `counter64_props` and `csr_cntr_props`, programs `cntr-write` and `cntr-instret-exact` |
| C4 | The 29 counters `mhpmcounter3` to `mhpmcounter31` (and the `h` halves) exist as WARL, and a counter fixed at zero is legal | Conforming | The 29 addresses exist, with `hpm_counters` real counters and the others at zero. cocotb `CsrFileZihpm*`, `HpmCounterBank*`, formal `csr_hpm_props`, programs `hpm-full` and `hpm-sweep`, ACT4 `rv32i/Zihpm` (2) |
| C5 | `mhpmevent3` to `mhpmevent31` are 64-bit WARL selectors, event 0 is none and the meaning of the events belongs to the platform | EEI choice | 4-bit code, with the nine-event table documented in `Core/docs/en/ISA/Zihpm/description.md`. cocotb `HpmCounterBankAll64`, programs `hpm-inhibit-select` and `hpm-branch-count` |
| C6 | `mhpmeventnh` exists only with Sscofpmf | Conforming | Without `has_sscofpmf` the addresses `0x723` to `0x73F` are nonexistent. cocotb `CsrFileSscofpmfOff`, formal `csrh_safety` |
| C7 | `mcountinhibit` is a 32-bit WARL: `CY` (bit 0), `IR` (bit 2) and `HPMn` inhibit the increment, bit 1 is zero, and accessibility does not change | Conforming | cocotb `CsrFileZicntr`, `CsrFileZihpm*`, formal `csr_cntr_props` and `csr_hpm_props`, programs `hpm-inhibit-select` and `hpm-sweep` |
| C8 | Without `mcountinhibit` the hart behaves as if it were zero | EEI choice | The register exists with Zicntr or Zihpm, and without both the address is nonexistent. cocotb `CsrFileNoZicntr` |
| C9 | `mcounteren` exists only with U-mode | Conforming | Without U-mode the access is illegal. cocotb `CoreTrapPriority` |
| C10 | `mcyclecfg`, `minstretcfg` and the mode filtering fields (Smcntrpmf) | Not applicable | The Core does not implement Smcntrpmf, and the addresses are illegal |
| C11 | The `time` CSR is the read-only shadow of `mtime` (see row L8) | Conforming | See row L8 |

### 11.2. Sscofpmf

Chapter 14. The extension is optional and the project implements it for Zihpm, behind the `has_sscofpmf` generic (off by default; the `de0-cv` turns it on with `extras: [Sscofpmf]`). The complete matrix, with 13 rows, is in [Core/docs/en/ISA/Sscofpmf/conformance.md](../../../Core/docs/en/ISA/Sscofpmf/conformance.md).

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| F1 | `mhpmeventnh` with `OF` (bit 31) and `MINH` (bit 30) for the 29 counters | Conforming | cocotb `CsrFileSscofpmf`, `CsrFileSscofpmfWide`, formal `csrof_safety` |
| F2 | The overflow sets `OF`, which only a write clears, and asks for an interrupt only with `OF` at zero | Conforming | formal `csrof_safety` (mutants `ofp_request_ignores_of`, `ofp_of_not_sticky`), program `irq-lcofi` |
| F3 | The overflow is the unsigned counter overflow, and a write never overflows | Conforming | formal `counter64_props` (mutants `wrap_without_hi`, `wrap_on_lo_write`), cocotb `CsrFileSscofpmfWide` |
| F4 | Interrupt 13 (`LCOFIP` in `mip` and `LCOFIE` in `mie`) has the lowest priority | Conforming | formal `csrof_safety` (mutant `ofp_lcofi_before_timer`), programs `irq-lcofi` and `irq-lcofi-priority` |
| F5 | `scountovf` and the parts of the extension that depend on S, U and virtualized modes | Not applicable | The Core has M-mode only. cocotb `CoreTrapPriority` (`scountovf` is illegal) |

## 12. Reset

Section 3.4.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| R1 | At reset the mode is M, and `MIE`, `MPRV` and `MBE` are 0 | Conforming | cocotb `CsrFile` (`test_reset_values`), `CsrFileIrq` |
| R2 | The reset `misa` announces the maximal set of extensions | Conforming | `misa` is constant, equal to the set of the profile. cocotb `CsrFile` |
| R3 | The reset `pc` is an implementation vector | EEI choice | Address 0, the start of the `BOOT_MEMORY`, by the memory map of `platform.yaml`. `docs/en/platform/boot.md` |
| R4 | The reset `mcause` is zero when the implementation does not tell reset causes apart | Conforming | `mcause` clears at reset. cocotb `CsrFile` (`test_reset_values`) |
| R5 | No WARL field holds an illegal value at reset | Conforming | Every register clears at reset, and the fixed-value WARL fields hold the fixed value (`MPP` = `11`). cocotb `CsrFile` |

## 13. Platform timer and interrupt controllers

Section 3.2.1 and the sources of `MSIP`, `MTIP` and `MEIP` of 3.1.9. `mtime`, `mtimecmp` and `msip` belong to the CLINT, and `MEIP` to the PLIC, both in the Peripherals repository ([CLINT](../../../Peripherals/docs/en/CLINT/clint.md)); the lines reach the Core with no synchronizer, in its clock domain. The map and the sources are in [interrupcoes.md](../platform/interrupcoes.md).

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| L1 | `mtime` is a memory-mapped 64-bit read/write register that increments at a constant frequency and wraps | Conforming | CLINT of Peripherals: cocotb `CLINT`, `ClintMtime`, `ClintTick`, proofs `clint_mtime_props` and `clint_props`, program `irq-timer-basic` |
| L2 | The platform states the period of the `mtime` tick | Conforming | `interrupts.mtime_hz` of `platform.yaml` generates `MTIME_HZ` and `CLINT_TICK_CYCLES` in the VHDL package and in the runtime header. Tools `test_interrupts`, `docs/en/platform/interrupcoes.md` |
| L3 | `mtimecmp` is a memory-mapped 64-bit register | Conforming | SiFive layout. cocotb `CLINT`, proof `clint_props` |
| L4 | The timer interrupt is pending while `mtime >= mtimecmp` (unsigned) and falls when `mtimecmp` becomes greater | Conforming | Proof `clint_props` (the 64-bit comparison and the fall of `MTIP`), programs `irq-timer-basic` and `plic-timer` |
| L5 | A change in the comparison reaches `MTIP` "eventually, not necessarily immediately" | EEI choice | The CLINT registers the result for one cycle. Proof `clint_props` |
| L6 | Writing `mtimecmp` in two 32-bit halves raises no spurious interrupt from the intermediate value | Conforming | The manual sequence (all ones in the low half, then the high, then the low) is proved. Proof `clint_props` (`SEQ` mode), macro `RVIRQ_TIMER_AFTER` of the programs |
| L7 | `msip` is a memory-mapped 32-bit register with bit 0 in `MSIP` | Conforming | The other bits read zero. cocotb `CLINT`, proof `clint_props`, program `irq-priority` |
| L8 | The `time` CSR is the read-only shadow of `mtime` | Conforming | With `time_external`, on wherever there is a CLINT, `time` and `timeh` read the `o_mtime` output of the CLINT; without a CLINT `time` counts by itself, with the `tick_cycles` period. cocotb `CsrFileTimeExternal` and `CLINT`, formal `csrt_safety` (mutants `time_halves_swapped`, `time_hi_zero`) and `clint_props`, program `time-follows-mtime` |
| L9 | The `mtime` shared among harts and `msip` for inter-processor interrupts | Not applicable | One hart only |

## 14. Physical memory: PMA and PMP

Sections 3.6 and 3.7.

| ID | Requirement | Status | Evidence |
| :--- | :--- | :--- | :--- |
| A1 | The physical memory attributes (PMA) of each region are fixed at design time and known to software | Conforming | The memory map of `platform.yaml` is the source, and `generate-memory-map` writes it to the VHDL, the linker and the runtime header |
| A2 | A PMA violation (execution from a region with no fetch, write to read-only memory, access to a region without memory) raises a precise access fault, wherever possible | Conforming | With `has_access_faults`: see X2 and X8. The valid map (ROM, RAM, external window and occupied peripheral slots) comes from `platform.yaml`. On platforms without the `AccessFaults` extra the Core raises no causes 1, 5 and 7 (a platform choice) |
| A3 | A misaligned access to main memory executes or traps, and execution need not be atomic | Conforming | Zicclsm. Program `misaligned-crossing`, ACT4 `rv32i/Zicclsm` (13) |
| A4 | The atomicity PMAs (AMO, reservability), coherence and cacheability per region | Not applicable | The Core has neither the A extension nor coherence between harts |
| A5 | PMP (`pmpcfg`, `pmpaddr`) and Smepmp (`mseccfg`) | Not applicable | The Core implements no PMP; the addresses `0x3A0` to `0x3EF` and `0x747` are illegal. cocotb `CoreTrapPriority` |
| A6 | Virtual memory (`satp`, Sv32 and family) and paging | Not applicable | The Core has M-mode only |

### 14.1. Access faults

The manual strongly recommends that PMA violations be precise exceptions, "wherever possible". The Core raises them with the `has_access_faults` generic (off by default; the `de0-cv` turns it on with `extras: [AccessFaults]`). The valid map comes from `platform.yaml`: the KiB generics the Core already received (`rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib`) and the `periph_slots` generic, which `riscv-tools` writes as `PERIPH_SLOTS` (one bit per 256 MiB window of the peripheral bus that holds a peripheral).

| Violation | Cause | `mtval` | Where it is decided |
| :--- | :---: | :--- | :--- |
| Fetch outside ROM, RAM and the external window (gap, empty window or peripheral) | 1 | PC | EX stage, from the registered PC |
| Load to an address outside the map | 5 | Effective address | Bit registered in EX/MEM, checked in the MEM stage |
| Store to an address outside the map or into the ROM | 7 | Effective address | The same write bit, registered in EX/MEM |

The validity of the data address leaves EX with the classification `reg_ex_mem` already registers, and the MEM stage only checks the bit, so the path the F front shortened gains no comparator. The access fault beats misalignment, and the fetch fault beats the illegal instruction (Table 17). On platforms without the extra the Core raises no causes 1, 5 and 7, and the validity bit is constant and not synthesized.

## 15. Out of scope

| Item | Chapter | Reason |
| :--- | :--- | :--- |
| S-mode, `sstatus`, `sie`, `sip`, `satp`, `medeleg`, `mideleg`, `scounteren`, `stimecmp` (Sstc) | 4, 12 and 3.1.8 | The hart has M-mode only; the CSRs are illegal |
| U-mode and `mcounteren`, `menvcfg` | 3.1.11 and 3.1.18 | Without U-mode these registers do not exist (the manual says `mcounteren` should not exist) |
| Virtual memory (Sv32, Svnapot, Svpbmt, Svinval, Svadu) | 12 and 13 | No S-mode and no MMU |
| Hypervisor (H) | 15 | Needs S-mode and virtual memory |
| PMP and Smepmp | 3.7 and 3.1.19 | The hart has no physical memory protection |
| Non-maskable interrupts (Smrnmi) and `mnscratch`, `mnepc`, `mncause`, `mnstatus` | 3.5 | No hardware error raises an NMI in the SoC |
| Double trap (Smdbltrp) and `MDT` | 3.1.6.2 | There is no critical state to signal |
| Control flow and shadow stack (Zicfilp, Zicfiss) | 22 and 23 | Outside the extension set of the project |
| Debug (Sdext, Sdtrig) | Debug manual | The CSRs `0x7A0` to `0x7BF` raise an illegal instruction |
| Pointer masking (Smmpm, Ssnpm), Smstateen, Smaia, Smcsrind, Smctr, Smcdeleg, Smcntrpmf | 3.1.18 and extensions | No U or S-mode, or no need in a one-mode hart |
| Counters `scountovf` and `hpmcounter` for S-mode | 14 | No S-mode |
| Extensions A, C, F, D, V | Unprivileged | A, C, F, D and V are not part of the project; see [the unprivileged report](riscv-nao-privilegiado.md) |

## 16. Gaps and choices

There is no open gap. Two rows depend on the platform turning the extension on: access faults 1, 5 and 7 (X2, X8 and A2) only exist where `platform.yaml` has `extras: [AccessFaults]`, today the `de0-cv`, and `time` mirrors `mtime` (L8) where there is a CLINT, today the `de0-cv` and the `modular`.

The EEI choices that change what a program sees are: `mvendorid`, `marchid`, `mimpid` and `mconfigptr` are zero (D8 to D12); `mtval` is zero on the illegal instruction and on `EBREAK` (T8 and T9); the vectored mode of `mtvec` asks for a 64-byte aligned `BASE` (V5); `WFI` is a `nop` (I2); the interrupt beats the exception of the same instruction (Q11); `FENCE.I` makes an interrupt wait one cycle (Q12); the misaligned access to main memory runs in two steps (X7).

A change in what the ACT4 or the Certification expect: the addresses `0x723` to `0x73F` (`mhpmeventNh`) and bit 13 of `mip` and `mie` exist on the platforms that turn Sscofpmf on (the `de0-cv`); the ACT4 profiles do not depend on them.

## 17. How to reproduce

| What | Command |
| :--- | :--- |
| Entity tests of the Core | `make test` in the Core, or `make test TEST=CoreTrapPriority` and the others by name |
| Formal proofs of the Core | `make formal` in the Core, with `FORMAL_ENGINE=bitwuzla`, `yices`, `boolector` or `abc-bmc3` |
| Interrupt programs | `uv run python tests/python/runner.py irq-programs` in Tests |
| Exception and CSR programs | `riscv-tools` of Tests, in simulation and on the board |
| CLINT and PLIC proofs | `make formal` in Peripherals |

---

Copyright 2026 Insper. Licensed under the [Apache License, Version 2.0](../../../LICENSE).
