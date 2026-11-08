# Conformidade com o volume privilegiado do RISC-V

🌐 [Português](riscv-privilegiado.md) · [English](../../en/conformance/riscv-privilegiado.md)

Este relatório confronta cada requisito normativo do volume privilegiado do manual do RISC-V (versão 20260120) que se aplica a um hart só com o modo máquina, e às extensões e módulos que o projeto implementa, com a evidência que o cobre. O hart é o do [Core](../../../Core/README.md), com cinco estágios, os modos U, S e H ausentes, sem memória virtual e sem PMP; a plataforma é o SoC deste repositório, com o CLINT e o PLIC. É o irmão do [relatório do volume não privilegiado](riscv-nao-privilegiado.md), com a mesma estrutura.

## 1. Escopo

A numeração das seções é a do volume privilegiado. Cada requisito tem uma linha com a situação e a evidência, e nenhuma célula fica vazia.

| Capítulo do manual | Tema | Tratamento |
| :--- | :--- | :--- |
| 2 | Registradores de controle e estado | Seções 3 a 7 e 11 |
| 3.1.1 a 3.1.5 e 3.1.17 | `misa` e os registradores de identificação | Seção 3 |
| 3.1.6 | `mstatus` e `mstatush` | Seção 4 |
| 3.1.7 | `mtvec` | Seção 5 |
| 3.1.8 e 3.1.9 | Delegação, `mip` e `mie` | Seção 6 |
| 3.1.10 a 3.1.12 | Contadores, `mcounteren` e `mcountinhibit` | Seção 11 |
| 3.1.13 a 3.1.16 | `mscratch`, `mepc`, `mcause` e `mtval` | Seções 7 e 8 |
| 3.1.18 e 3.1.19 | `menvcfg` e `mseccfg` | Seção 8, linha X5 |
| 3.2.1 | `mtime` e `mtimecmp` | Seção 13 |
| 3.3 | `ECALL`, `EBREAK`, `MRET`, `WFI` | Seções 9 e 10 |
| 3.4 | Reset | Seção 12 |
| 3.5 | Interrupções não mascaráveis | Seção 15 |
| 3.6 e 3.7 | PMA e PMP | Seção 14 |
| 14 | Sscofpmf | Seção 11.2 |
| 4 a 13 e 15 a 23 | Modos S e H, memória virtual, depuração, extensões de segurança e de controle de fluxo | Seção 15, fora do escopo |

## 2. Como ler

### 2.1. Situação

| Situação | Significado |
| :--- | :--- |
| Conforme | O Core ou a plataforma cumpre o requisito e a evidência o demonstra |
| Escolha do EEI | O manual deixa a escolha ao ambiente de execução (EEI) ou à plataforma, e o projeto registra a sua. Neste projeto o EEI é o SoC do Insper-RISC-V, com um hart em modo máquina |
| Não aplicável | O requisito pertence a um modo ou a uma extensão que o hart não tem |
| Lacuna aberta | O manual manda ou recomenda com ênfase, e o projeto não cumpre; a seção 16 traz o motivo |

### 2.2. Evidência

| Sigla | Onde fica | Como reproduzir |
| :--- | :--- | :--- |
| cocotb `X` | Entrada `X` de `tests/python/tests.json` do Core (ou do Peripherals, nas linhas do CLINT) | `make test TEST=X` no repositório |
| formal `arquivo` ou `prova` | `formal/<arquivo>.sv` do Core, com os mutantes que a prova rejeita; o rótulo `csri_safety` e os parecidos são as provas de `formal/run.sh` | `make formal` no Core |
| programa `P` | `asm/P` ou `asm-irq/P` do repositório Tests | `riscv-tools` do Tests, em simulação e na placa; os de `asm-irq/` com `tests/python/runner.py irq-programs` |
| ACT4 `pasta` | Pasta de testes do ACT4 (`riscv-arch-test`) que o repositório Certification executa; o ACT4 desta versão não traz testes do modo máquina além dos de Zicsr, Zicntr, Zihpm e `I` | Fluxo `certify` da Certification |

## 3. Registradores de identificação

Seções 3.1.1 a 3.1.5 e 3.1.17. O volume manda que todos sejam legíveis; os de identificação podem valer zero.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| D1 | `misa` é legível em qualquer implementação (zero indicaria que não existe) | Conforme | cocotb `CsrFile` (`test_reset_values`), programas `csr-rw-basic` e `priv-csr-priority` |
| D2 | O campo `MXL` é somente leitura e vale 1 no RV32 | Conforme | cocotb `CsrFile`, `CsrFileNoM` e `CsrFileRveNoM`, formal `csr_file_props`, programa `priv-csr-priority` |
| D3 | O campo `Extensions` anuncia a base (`I` ou `E`) e a extensão `M`; `E` lê o complemento de `I` | Conforme | cocotb `CsrFile`, `CsrFileNoM`, `CsrFileRveNoM`, formal `csr_file_props`, programa `priv-csr-priority` |
| D4 | Se o ambiente aceita `I` e `E`, `I` é escolhido no reset | Escolha do EEI | Cada perfil tem uma só base, escolhida na elaboração (`base_e`); o `misa` do perfil RV32E anuncia só `E`. cocotb `CsrFileRveNoM` |
| D5 | Os bits reservados e os das extensões que o hart não tem (`A`, `C`, `F`, `D`, `S`, `U`, `H`, `V`, `B`) leem zero | Conforme | cocotb `CsrFile` (`test_field_masks`), formal `csr_file_props` |
| D6 | `misa` é WARL: uma escrita que o hart não aceita não muda o valor | Conforme | O Core não deixa desligar extensão: a escrita é ignorada e não gera exceção. cocotb `CsrFile`, programa `csr-rw-basic` |
| D7 | `Zmmul` sem `M` não acende o bit `M`; o bit `M` só vale com todas as instruções de `M` | Conforme | cocotb `CsrFileNoM`, ACT4 `rv32i/Zmmul` (4) |
| D8 | `mvendorid` é legível; zero indica sem identificador JEDEC ou implementação não comercial | Escolha do EEI | Lê zero: o projeto não tem identificador JEDEC. cocotb `CsrFile` (`test_read_only_csrs`), programas `trap-illegal` e `priv-csr-priority` |
| D9 | `marchid` é legível; zero indica que não foi implementado | Escolha do EEI | Lê zero: a RISC-V International não alocou identificador de arquitetura ao projeto. cocotb `CsrFile`, programa `priv-csr-priority` |
| D10 | `mimpid` é legível; zero indica que não foi implementado | Escolha do EEI | Lê zero. cocotb `CsrFile`, programa `priv-csr-priority` |
| D11 | `mhartid` é legível e um hart tem o número zero | Conforme | O Core tem um hart, de número zero. cocotb `CsrFile`, programas `csr-rw-basic` e `priv-csr-priority` |
| D12 | `mconfigptr` é legível, pode valer zero, e o ponteiro tem o alinhamento de `MXLEN` | Escolha do EEI | Lê zero: não há estrutura de configuração de hardware. cocotb `CsrFile`, programa `priv-csr-priority` |
| D13 | `mvendorid`, `marchid`, `mimpid`, `mhartid` e `mconfigptr` são somente leitura: a escrita efetiva gera instrução ilegal, e `CSRRS`/`CSRRC` com `rs1 = x0` só leem | Conforme | cocotb `CsrFile` (`test_read_only_csrs`), formal `csr_file_props`, programas `trap-illegal` e `priv-csr-priority` |

## 4. `mstatus` e `mstatush`

Seção 3.1.6.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| S1 | `mstatus` é de leitura e escrita, e `MIE` (bit 3) e `MPIE` (bit 7) guardam o valor escrito | Conforme | cocotb `CsrFile` (`test_field_masks`), formal `csr_file_props`, programa `csr-rw-basic` |
| S2 | Numa trap, `MPIE` recebe `MIE`, `MIE` vai a zero e `MPP` guarda o modo de origem | Conforme | cocotb `CsrFile` (`test_trap_records_the_exception_and_closes_the_interrupt_enable`), formal `csr_file_props` (mutante `trap_keeps_mie`), programas `trap-ecall-ebreak` e `irq-timer-basic` |
| S3 | `MRET` copia `MPIE` em `MIE`, põe `MPIE` em 1 e põe `MPP` no modo menos privilegiado suportado | Conforme | cocotb `CsrFile` (`test_mret_restores_the_interrupt_enable`), formal `csr_file_props` (mutante `mret_no_mpie`), programa `irq-timer-basic` |
| S4 | `MPP` é WARL e só guarda modos implementados; com um só modo ele é fixo | Conforme | O único modo é o M, então `MPP` (bits 12:11) lê sempre `11` e a escrita é ignorada. cocotb `CsrFile` (`test_field_masks`), formal `csr_file_props` |
| S5 | `SIE`, `SPIE` e `SPP` são somente leitura zero sem o modo S | Conforme | Leem zero. cocotb `CsrFile` (`test_field_masks`) |
| S6 | `MPRV`, `MXR`, `SUM`, `TVM`, `TW`, `TSR` e `UBE` são somente leitura zero sem os modos U e S | Conforme | Leem zero. cocotb `CsrFile` |
| S7 | `FS`, `VS`, `XS` e `SD` são somente leitura zero sem as extensões que usam o estado | Conforme | O Core não tem `F`, `D` nem `V`. cocotb `CsrFile` |
| S8 | `MBE`, `SBE` e `UBE` controlam a ordem dos bytes; `MBE` vale 0 no reset, e um hart só little-endian os lê zero | Conforme | O Core é little-endian e esses bits leem zero. cocotb `CsrFile` |
| S9 | `mstatush` existe no RV32 e leva os campos altos de `mstatus` | Conforme | Existe (`0x310`), lê zero e ignora a escrita, sem exceção. cocotb `CsrFile`, programa `priv-csr-priority` |
| S10 | `MDT` e `SDT` (Smdbltrp), `MPELP` e `SPELP` (Zicfilp), `MPV` e `GVA` (H): campos de extensões que o Core não tem | Não aplicável | Os bits leem zero (o `MDT` com reset em 1 pertence à Smdbltrp, que o Core não implementa) |
| S11 | No reset, `MIE`, `MPRV` e `MBE` valem 0 | Conforme | cocotb `CsrFile` (`test_reset_values`) |
| S12 | Uma escrita em CSR vale depois que a instrução que escreve termina, e a instrução seguinte já a vê | Conforme | O pipeline é em ordem, com adiantamento dos CSRs. Programas `csr-forwarding`, `csr-back-to-back` e `irq-masked` |

## 5. `mtvec`

Seção 3.1.7.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| V1 | `mtvec` existe, é WARL e `BASE` fica alinhada a 4 bytes | Conforme | cocotb `CsrFile`, `CsrFileIrq` (`test_mtvec_mode_bit_is_kept_and_base_is_aligned`), formal `csri_safety` |
| V2 | No modo direto (`MODE` = 0) toda trap vai a `BASE` | Conforme | Programas `trap-ecall-ebreak`, `trap-illegal` e `irq-timer-basic`, cocotb `CoreTrapTake`, formal `core_trap_take_props` |
| V3 | No modo vetorado (`MODE` = 1) a exceção vai a `BASE` e a interrupção a `BASE + 4 x causa` | Conforme | cocotb `CoreIrqVectored`, formal `stage_ex_irq_props`, programas `irq-vectored` e `irq-lcofi-priority` |
| V4 | `MODE` de 2 ou mais é reservado | Escolha do EEI | O bit 1 lê zero e o bit 0 guarda o modo: uma escrita com o modo reservado resulta no direto ou no vetorado conforme o bit 0. cocotb `CsrFileIrq`, programa `irq-vectored` |
| V5 | O modo vetorado pode exigir alinhamento maior que 4 bytes | Escolha do EEI | Nesse modo `BASE` tem alinhamento de 64 bytes (bits 5:2 leem zero), para que `BASE + 4 x causa` seja a troca de bits. Formal `csri_safety` (mutante `irq_mtvec_unaligned_vector`), programa `irq-vectored` |
| V6 | Sem interrupções o modo vetorado não tem efeito | Conforme | Sem `has_interrupts` o bit `MODE` lê zero. cocotb `CsrFileNoIrq`, formal `csrio_safety` |
| V7 | O valor de reset de `mtvec` e os vetores de reset e de NMI são da plataforma | Escolha do EEI | `mtvec` zera no reset, e o vetor de reset da plataforma é o endereço 0 da `BOOT_MEMORY`. cocotb `CsrFile` (`test_reset_values`), `docs/pt-br/platform/boot.md` |
| V8 | Vetor de NMI (Smrnmi) | Não aplicável | O Core não implementa NMI |

## 6. Interrupções: `mip`, `mie` e a tomada

Seções 3.1.8, 3.1.9 e a Tabela 16. A interrupção 13 (estouro de contador) pertence à Sscofpmf e está ligada pelo generic `has_sscofpmf`.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| Q1 | O bit `i` de `mip` e de `mie` corresponde à causa de interrupção `i` | Conforme | Bits 3 (software), 7 (timer), 11 (externa) e 13 (estouro de contador). cocotb `CsrFileIrq`, formal `csri_safety` e `csrof_safety` |
| Q2 | A interrupção `i` vai ao modo M se `MIE` vale 1, o bit `i` vale 1 em `mip` e em `mie`, e `mideleg` não a delega | Conforme | cocotb `CsrFileIrq` (`test_take_needs_mstatus_mie_and_a_pending_enabled_line`), `CoreIrqSweep`, formal `csri_safety`, programa `irq-masked` |
| Q3 | A condição é avaliada em tempo limitado depois que a interrupção passa a pender, e logo depois de `MRET` e de escrita em `mip`, `mie` ou `mstatus` | Conforme | A condição é combinacional sobre os registradores, avaliada a cada instrução. cocotb `CoreIrqSweep` (instantes sorteados), programas `irq-masked` (a interrupção toma a instrução seguinte à escrita de `mie`) e `irq-timer-basic` (retorno por `MRET`) |
| Q4 | A prioridade de várias interrupções ao modo M é MEI, MSI, MTI, SEI, SSI, STI e LCOFI | Conforme | cocotb `CsrFileIrq` (`test_cause_priority_is_external_software_timer`), `CoreIrqPriority`, formal `csri_safety` e `csrof_safety`, programas `irq-priority` e `irq-lcofi-priority` |
| Q5 | `MEIP`, `MTIP` e `MSIP` são somente leitura em `mip`, e quem os limpa é a plataforma | Conforme | Uma escrita em `mip` é legal e não os altera; as linhas vêm do CLINT e do PLIC. cocotb `CsrFileIrq` (`test_a_write_to_mip_is_legal_and_ignored`), formal `csri_safety` |
| Q6 | Um bit de `mie` é gravável se a interrupção pode pender, e os demais leem zero | Conforme | `mie` guarda os bits 3, 7 e 11 (e 13 com Sscofpmf). cocotb `CsrFileIrq` (`test_mie_keeps_only_bits_3_7_and_11`), formal `csri_safety` |
| Q7 | `SEIP`, `STIP`, `SSIP` e `SEIE`, `STIE`, `SSIE` leem zero sem o modo S | Conforme | Leem zero. cocotb `CsrFileIrq` |
| Q8 | Os bits 16 e acima de `mip` e `mie` são de uso da plataforma | Escolha do EEI | O Core não usa interrupções locais de plataforma: esses bits leem zero. As fontes dos periféricos chegam por `MEIP`, pelo PLIC. cocotb `CsrFileIrq` |
| Q9 | O `MSIP` e o `MTIP` aparecem em `mip` "eventualmente, não necessariamente de imediato" | Escolha do EEI | As linhas entram no `mip` no mesmo ciclo em que a saída do CLINT muda, e o CLINT registra o `MTIP` por um ciclo. cocotb `CsrFileIrq`, `CLINT` (Peripherals) |
| Q10 | A interrupção é precisa: `mepc` é a primeira instrução que não completou | Conforme | cocotb `CoreIrqSweep` e `CoreIrqFenceI`, formal `stage_ex_irq_props`, programas `irq-mepc-precise` e `irq-timer-basic` |
| Q11 | Quando uma interrupção e uma exceção valem para a mesma instrução, o manual não manda a ordem | Escolha do EEI | A interrupção vence e a instrução é abortada, de modo que a exceção só ocorre se ela executar depois do retorno. cocotb `CoreIrqSweep` (síncronas sob interrupção), `TrapUnitIrq`, programa `irq-ecall` |
| Q12 | O instante exato em que `FENCE.I` deixa uma interrupção entrar é da implementação | Escolha do EEI | A `FENCE.I` não é abortada, e a interrupção espera um ciclo por ela. cocotb `CoreIrqFenceI`, formal `trap_unit_props` (modo `IRQ`) |
| Q13 | Uma interrupção de um modo mais privilegiado nunca é mascarada por um modo menos privilegiado | Conforme | O Core só tem o modo M |
| Q14 | `mideleg` e a delegação de interrupções ao modo S | Não aplicável | Sem o modo S, `mideleg` não existe e o acesso é ilegal. cocotb `CoreTrapPriority` |
| Q15 | A interrupção externa de máquina é pendente enquanto o controlador a afirma, e quem a limpa é o controlador | Conforme | `MEIP` é a saída do PLIC (um contexto de modo M); o programa limpa a fonte pelo claim e complete. Programas `plic-*` do Tests, provas `plic_props` do Peripherals |

## 7. `mscratch`, `mepc`, `mcause` e `mtval`

Seções 3.1.13 a 3.1.16.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| T1 | `mscratch` é de leitura e escrita com `MXLEN` bits | Conforme | cocotb `CsrFile`, programas `csr-rw-basic`, `csr-forwarding` e `csr-x0-no-effect` |
| T2 | `mepc[1:0]` vale zero quando `IALIGN` é 32, também na leitura implícita do `MRET` | Conforme | Os dois bits baixos são zerados na escrita. cocotb `CsrFile` (`test_trap_aligns_mepc`), formal `csr_file_props` (mutante `mepc_odd`), programa `priv-csr-priority` |
| T3 | `mepc` é WARL e guarda todo endereço válido | Conforme | Guarda os 30 bits altos do endereço de 32 bits. cocotb `CsrFile`, formal `csr_file_props` |
| T4 | Numa trap, `mepc` recebe o endereço da instrução interrompida ou que falhou, e só uma trap ou o programa o escreve | Conforme | Programas `trap-ecall-ebreak`, `trap-misaligned-jump`, `trap-misaligned-ldst`, `trap-mem-squash` e `irq-mepc-precise`, cocotb `CoreTrapTake`, `CoreMemTrapEx` |
| T5 | `mcause` tem o bit de interrupção e o código; só uma trap ou o programa o escreve | Conforme | cocotb `CsrFile`, `CoreTrapSignal`, programas `trap-illegal` e `irq-timer-basic` |
| T6 | O campo `Exception Code` é WLRL e só garante os códigos suportados | Escolha do EEI | O registrador guarda os 32 bits escritos, um superconjunto dos códigos suportados. cocotb `CsrFile` |
| T7 | Numa trap, `mtval` recebe zero ou uma informação da exceção; o endereço faltante, se não nulo, nas causas 0, 4 e 6 | Conforme | Causas 0, 4 e 6: endereço faltante (alvo do salto ou endereço efetivo). Programas `trap-misaligned-jump` e `trap-misaligned-ldst`, cocotb `TrapUnit`, formal `trap_unit_props` |
| T8 | No `EBREAK`, `mtval` recebe zero ou o endereço da instrução | Escolha do EEI | Recebe zero (o endereço já está em `mepc`). Programa `trap-ecall-ebreak`, formal `trap_unit_props` |
| T9 | Na instrução ilegal, `mtval` recebe zero ou os bits da instrução | Escolha do EEI | Recebe zero. Programa `trap-illegal`, cocotb `CoreIllegalInstruction` e `CoreTrapPriority`, formal `trap_unit_props` |
| T10 | Nas demais traps (`ECALL`, interrupções), `mtval` recebe zero | Conforme | Programas `trap-ecall-ebreak` e `irq-timer-basic`, formal `trap_unit_props` |
| T11 | `mtval` é WARL e guarda todo endereço válido e o zero | Conforme | Guarda 32 bits e é gravável. cocotb `CsrFile`, formal `csr_file_props` |

## 8. Exceções síncronas e a prioridade

Seção 3.1.15, Tabelas 16 e 17, e 3.6. As exceções que dependem de modos, de memória virtual ou de extensões ausentes estão marcadas como não aplicáveis.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| X1 | A causa 0 (endereço de instrução desalinhado) vem de salto ou desvio tomado com alvo não alinhado, com `mepc` no salto e `mtval` no alvo; um desvio não tomado não gera | Conforme | Programa `trap-misaligned-jump`, cocotb `CoreMisalignedJump` e `TrapUnit`, formal `trap_unit_props` |
| X2 | A causa 1 (falha de acesso de instrução) para um acesso que viola um PMA; o manual recomenda com ênfase que seja precisa | Conforme | Com `has_access_faults` (ligado na `de0-cv` por `extras: [AccessFaults]`) a busca fora de ROM, RAM e janela externa trapa com `mtval` igual ao PC. cocotb `TrapUnitAccessFaults`, formal `trap_af_safety` (mutantes `af_fetch_below_illegal`, `af_fetch_tval_ea`), programa `access-fetch-fault` |
| X3 | A causa 2 (instrução ilegal) cobre codificação reservada ou inexistente, `SYSTEM` não suportada, CSR inexistente e escrita em CSR somente leitura | Conforme | cocotb `CoreIllegalInstruction`, `CoreTrapPriority`, `ControlUnit`, `CsrDecode`, programas `trap-illegal`, `conformance-decode` e `priv-csr-priority`, formal `trap_unit_props` |
| X4 | Os CSRs do bloco de depuração (`0x7B0` a `0x7BF`) e de gatilhos (`0x7A0` a `0x7A3`) não existem fora do modo de depuração e geram instrução ilegal | Conforme | cocotb `CoreTrapPriority` (`dcsr`, `dpc`, `dscratch0`, `dscratch1`, `0x7B4`, `0x7BF`, `tselect`, `tdata1`), programa `priv-csr-priority` (bloco de depuração) |
| X5 | Os CSRs de modos e extensões que o hart não tem (`sstatus`, `satp`, `medeleg`, `mideleg`, `mcounteren`, `menvcfg`, `mseccfg`, `mtinst`, `mtval2`, PMP, `scountovf`) geram instrução ilegal | Conforme | cocotb `CoreTrapPriority`, `CsrFile` (`test_unknown_csr_is_illegal`), `CsrFileZihpm`, formal `csr_file_props` e `csr_hpm_props`, programa `trap-illegal` |
| X6 | A causa 3 (breakpoint) vem do `EBREAK`, com `mepc` na instrução e sem outra operação | Conforme | Programa `trap-ecall-ebreak`, cocotb `TrapUnit` e `CoreTrapSignal`, formal `trap_unit_props` |
| X7 | As causas 4 e 6 (endereço de load e de store desalinhado) são opcionais, e o hart pode executar o acesso ou trapar | Escolha do EEI | Com Zicclsm o Core executa o desalinhado na memória principal e trapa fora dela (`mtval` é o endereço efetivo); sem Zicclsm todo desalinhado trapa. cocotb `TrapUnit`, `TrapUnitNoZicclsm`, `CoreMisaligned`, programas `trap-misaligned-ldst` e `misaligned-crossing`, ACT4 `rv32i/Zicclsm` (13) |
| X8 | As causas 5 e 7 (falha de acesso de load e de store) para um acesso que viola um PMA, como a escrita em memória só de leitura | Conforme | Com `has_access_faults` o load fora do mapa trapa com a causa 5 e o store fora do mapa ou na ROM com a 7, com `mtval` igual ao endereço, antes do desalinhamento, e sem acessar a memória. cocotb `TrapUnitAccessFaults`, `RegExMemFaults`, formal `trap_af_safety` (mutantes `af_load_uses_write_flag`, `af_store_after_misaligned`, `af_store_fault_cause_load`), programas `access-load-fault` e `access-store-fault` |
| X9 | As causas 8 e 9 (`ECALL` de U e S), 10, 12, 13 e 15 (falhas de página), 14 e 17 | Não aplicável | O Core não tem os modos U e S nem memória virtual |
| X10 | As causas 16 (double trap, Smdbltrp), 18 (software check, Zicfilp e Zicfiss) e 19 (hardware error) | Não aplicável | O Core não tem essas extensões nem detecção de erro de hardware |
| X11 | A causa 11 (chamada de ambiente do modo M) vem do `ECALL`, com `mepc` na instrução e sem outra operação | Conforme | Programa `trap-ecall-ebreak`, cocotb `TrapUnit` e `CoreTrapSignal`, formal `trap_unit_props`, ACT4 `rv32i/I` (39) |
| X12 | Entre as exceções de uma mesma instrução vale a ordem da Tabela 17: instrução ilegal (2), endereço de instrução desalinhado (0), `ECALL`, `EBREAK` e, por último, as de acesso à memória | Conforme | Um `JALR` ou desvio de codificação reservada com alvo desalinhado gera a causa 2. cocotb `TrapUnit` (`test_illegal_goes_before_misaligned_target`), `CoreTrapPriority`, formal `trap_unit_props` (mutantes `illegal_ignored` e `misaligned_over_illegal`), programa `priv-csr-priority` |
| X13 | A ordem relativa do desalinhamento de load e store e das falhas de acesso é da implementação | Escolha do EEI | Sem falhas de acesso, só há o desalinhamento. cocotb `TrapUnit` |
| X14 | A exceção é precisa: a instrução que falha não escreve registrador, memória nem CSR, e as anteriores completam | Conforme | Programas `trap-mem-squash`, `trap-muldiv-load-use` e `trap-illegal`, cocotb `CoreMemTrapEx`, `CoreTrapTake` e `CoreIllegalInstruction`, formal `core_trap_take_props` |
| X15 | `ECALL` e `EBREAK` não retiram e não somam a `minstret` | Conforme | Programa `cntr-trap-no-retire`, formal `csr_cntr_props` |
| X16 | As causas 24 a 31 e 48 a 63 (uso personalizado) | Não aplicável | O Core não define exceções personalizadas |

## 9. Entrada e saída de trap

Seções 3.1.6.1, 3.3.1 e 3.3.2.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| E1 | Numa trap ao modo M, `mepc`, `mcause` e `mtval` são escritos, `MPIE` recebe `MIE`, `MIE` vai a zero e o `pc` recebe o vetor de `mtvec` | Conforme | cocotb `CsrFile`, `CoreTrapTake`, formal `csr_file_props` e `core_trap_take_props`, programas `trap-ecall-ebreak` e `irq-timer-basic` |
| E2 | O `MRET` está sempre presente, restaura `MIE` a partir de `MPIE`, põe `MPIE` em 1 e leva o `pc` a `mepc` | Conforme | cocotb `CsrFile`, `TrapUnit`, formal `csr_file_props` e `trap_unit_props` (a palavra `0x30200073` exata), programas `trap-ecall-ebreak` e `irq-timer-basic` |
| E3 | `ECALL`, `EBREAK`, `MRET` e `WFI` exigem `rd` e `rs1` em zero e `funct3` zero; as demais combinações são reservadas | Conforme | As combinações reservadas geram a causa 2. cocotb `TrapUnit` (`test_unsupported_system_is_illegal`), formal `trap_unit_props` (mutante `mret_any_imm`), programa `trap-illegal` |
| E4 | `SRET`, `SFENCE.VMA`, `HFENCE`, `SINVAL` e as instruções de `SYSTEM` dos modos S e H | Não aplicável | Sem os modos S e H elas são ilegais (o manual manda `SRET` ser ilegal sem o modo S). Programa `trap-illegal` (`sret`) |
| E5 | O espaço `SYSTEM` reservado ao uso personalizado não define instrução no Core, e o acesso gera instrução ilegal | Conforme | cocotb `TrapUnit`, `CsrDecode` |

## 10. `WFI`

Seção 3.3.3 e o espaço `SYSTEM` personalizado da seção 3.3.4.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I1 | `WFI` existe em todos os modos privilegiados e não é afetada por `MIE` | Conforme | A `WFI` executa como `nop`, com e sem `MIE`. cocotb `TrapUnit` (`test_wfi_is_a_nop`), programa `irq-wfi` |
| I2 | A `WFI` pode parar o hart até uma interrupção habilitada, ou ser um `nop`; se não para, a interrupção entra numa instrução do laço de espera | Escolha do EEI | O Core a executa como `nop`: a interrupção entra sobre a própria `WFI`, que volta a executar depois do retorno. Programa `irq-wfi`, cocotb `TrapUnit` |
| I3 | O hart pode retomar por qualquer motivo, e o programa confere em `mip` o que aconteceu | Conforme | Como `nop`, a retomada é imediata; o programa lê `mip`. Programa `irq-wfi` |
| I4 | `TW` de `mstatus` pode fazer a `WFI` gerar instrução ilegal nos modos menos privilegiados | Não aplicável | Só há o modo M |

## 11. Contadores e Sscofpmf

### 11.1. Contadores

Seções 3.1.10 a 3.1.12. A conformidade do Zihpm, linha a linha, também está em [Core/docs/pt-br/ISA/Zihpm/conformance.md](../../../Core/docs/pt-br/ISA/Zihpm/conformance.md).

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| C1 | `mcycle` e `minstret` têm 64 bits (metades `mcycleh` e `minstreth`) e são graváveis | Conforme | cocotb `Counter64`, `CsrFileZicntr`, formal `counter64_props` e `csr_cntr_props`, programas `cntr-write` e `cntr-rollover`, ACT4 `rv32i/Zicntr` (2) |
| C2 | Os contadores têm valor arbitrário depois do reset | Escolha do EEI | Zeram no reset. cocotb `CsrFileZicntr` |
| C3 | Uma escrita em CSR vale depois que a instrução termina, e a escrita explícita vence o incremento do ciclo | Conforme | Formal `counter64_props` e `csr_cntr_props`, programas `cntr-write` e `cntr-instret-exact` |
| C4 | Os 29 contadores `mhpmcounter3` a `mhpmcounter31` (e as metades `h`) existem como WARL, e um contador fixo em zero é legal | Conforme | Os 29 endereços existem, com `hpm_counters` contadores reais e os outros em zero. cocotb `CsrFileZihpm*`, `HpmCounterBank*`, formal `csr_hpm_props`, programas `hpm-full` e `hpm-sweep`, ACT4 `rv32i/Zihpm` (2) |
| C5 | `mhpmevent3` a `mhpmevent31` são seletores WARL de 64 bits, o evento 0 é nenhum e o significado dos eventos é da plataforma | Escolha do EEI | Código de 4 bits, com a tabela de nove eventos documentada em `Core/docs/pt-br/ISA/Zihpm/description.md`. cocotb `HpmCounterBankAll64`, programas `hpm-inhibit-select` e `hpm-branch-count` |
| C6 | `mhpmeventnh` só existe com a Sscofpmf | Conforme | Sem `has_sscofpmf` os endereços `0x723` a `0x73F` são inexistentes. cocotb `CsrFileSscofpmfOff`, formal `csrh_safety` |
| C7 | `mcountinhibit` é WARL de 32 bits: `CY` (bit 0), `IR` (bit 2) e `HPMn` inibem o incremento, o bit 1 vale zero, e a acessibilidade não muda | Conforme | cocotb `CsrFileZicntr`, `CsrFileZihpm*`, formal `csr_cntr_props` e `csr_hpm_props`, programas `hpm-inhibit-select` e `hpm-sweep` |
| C8 | Sem `mcountinhibit` o hart se comporta como se ele valesse zero | Escolha do EEI | O registrador existe com Zicntr ou Zihpm, e sem as duas o endereço é inexistente. cocotb `CsrFileNoZicntr` |
| C9 | `mcounteren` existe só com o modo U | Conforme | Sem o modo U o acesso é ilegal. cocotb `CoreTrapPriority` |
| C10 | `mcyclecfg`, `minstretcfg` e os campos de filtragem por modo (Smcntrpmf) | Não aplicável | O Core não implementa a Smcntrpmf, e os endereços são ilegais |
| C11 | O CSR `time` é o sombreamento somente leitura de `mtime` (ver a linha L8) | Conforme | Ver a linha L8 |

### 11.2. Sscofpmf

Capítulo 14. A extensão é opcional e o projeto a implementa para o Zihpm, atrás do generic `has_sscofpmf` (desligado por padrão; a `de0-cv` a liga com `extras: [Sscofpmf]`). A matriz completa, com 13 linhas, está em [Core/docs/pt-br/ISA/Sscofpmf/conformance.md](../../../Core/docs/pt-br/ISA/Sscofpmf/conformance.md).

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| F1 | `mhpmeventnh` com `OF` (bit 31) e `MINH` (bit 30) para os 29 contadores | Conforme | cocotb `CsrFileSscofpmf`, `CsrFileSscofpmfWide`, formal `csrof_safety` |
| F2 | O estouro põe `OF`, que só a escrita limpa, e só pede interrupção com `OF` em zero | Conforme | formal `csrof_safety` (mutantes `ofp_request_ignores_of`, `ofp_of_not_sticky`), programa `irq-lcofi` |
| F3 | O estouro é o do contador sem sinal, e a escrita nunca estoura | Conforme | formal `counter64_props` (mutantes `wrap_without_hi`, `wrap_on_lo_write`), cocotb `CsrFileSscofpmfWide` |
| F4 | A interrupção 13 (`LCOFIP` em `mip` e `LCOFIE` em `mie`) tem a menor prioridade | Conforme | formal `csrof_safety` (mutante `ofp_lcofi_before_timer`), programas `irq-lcofi` e `irq-lcofi-priority` |
| F5 | `scountovf` e as partes da extensão que dependem dos modos S, U e virtualizados | Não aplicável | O Core só tem o modo M. cocotb `CoreTrapPriority` (`scountovf` é ilegal) |

## 12. Reset

Seção 3.4.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| R1 | No reset o modo é M, e `MIE`, `MPRV` e `MBE` valem 0 | Conforme | cocotb `CsrFile` (`test_reset_values`), `CsrFileIrq` |
| R2 | O `misa` do reset anuncia o conjunto máximo de extensões | Conforme | O `misa` é constante, igual ao conjunto do perfil. cocotb `CsrFile` |
| R3 | O `pc` do reset é um vetor da implementação | Escolha do EEI | O endereço 0, o início da `BOOT_MEMORY`, pelo mapa de memória do `platform.yaml`. `docs/pt-br/platform/boot.md` |
| R4 | O `mcause` do reset vale zero quando a implementação não distingue causas de reset | Conforme | O `mcause` zera no reset. cocotb `CsrFile` (`test_reset_values`) |
| R5 | Nenhum campo WARL guarda um valor ilegal no reset | Conforme | Todos os registradores zeram no reset, e os campos WARL de valor fixo valem o fixo (`MPP` = `11`). cocotb `CsrFile` |

## 13. Temporizador e controladores de interrupção da plataforma

Seção 3.2.1 e as fontes de `MSIP`, `MTIP` e `MEIP` de 3.1.9. O `mtime`, o `mtimecmp` e o `msip` são do CLINT, e o `MEIP` é do PLIC, ambos do repositório Peripherals ([CLINT](../../../Peripherals/docs/pt-br/CLINT/clint.md)); as linhas chegam ao Core sem sincronizador, no domínio de clock dele. O mapa e as fontes estão em [interrupcoes.md](../platform/interrupcoes.md).

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| L1 | `mtime` é um registrador de 64 bits mapeado em memória, de leitura e escrita, que incrementa a frequência constante e dá a volta | Conforme | CLINT do Peripherals: cocotb `CLINT`, `ClintMtime`, `ClintTick`, provas `clint_mtime_props` e `clint_props`, programa `irq-timer-basic` |
| L2 | A plataforma informa o período do tick de `mtime` | Conforme | `interrupts.mtime_hz` do `platform.yaml` gera `MTIME_HZ` e `CLINT_TICK_CYCLES` no pacote VHDL e no cabeçalho do runtime. Tools `test_interrupts`, `docs/pt-br/platform/interrupcoes.md` |
| L3 | `mtimecmp` é um registrador de 64 bits mapeado em memória | Conforme | Leiaute da SiFive. cocotb `CLINT`, prova `clint_props` |
| L4 | A interrupção de timer pende enquanto `mtime >= mtimecmp` (sem sinal) e cai quando `mtimecmp` passa a ser maior | Conforme | Prova `clint_props` (a comparação de 64 bits e a queda do `MTIP`), programas `irq-timer-basic` e `plic-timer` |
| L5 | Uma mudança na comparação chega ao `MTIP` "eventualmente, não necessariamente de imediato" | Escolha do EEI | O CLINT registra o resultado por um ciclo. Prova `clint_props` |
| L6 | A escrita de `mtimecmp` em duas metades de 32 bits não gera interrupção espúria pelo valor intermediário | Conforme | A sequência do manual (todos os bits em 1 na metade baixa, depois a alta, depois a baixa) é provada. Prova `clint_props` (modo `SEQ`), macro `RVIRQ_TIMER_AFTER` dos programas |
| L7 | `msip` é um registrador de 32 bits mapeado em memória, com o bit 0 em `MSIP` | Conforme | Os demais bits leem zero. cocotb `CLINT`, prova `clint_props`, programa `irq-priority` |
| L8 | O CSR `time` é o sombreamento somente leitura de `mtime` | Conforme | Com `time_external`, ligado onde há CLINT, `time` e `timeh` leem a saída `o_mtime` do CLINT; sem CLINT o `time` conta por conta própria, com o período de `tick_cycles`. cocotb `CsrFileTimeExternal` e `CLINT`, formal `csrt_safety` (mutantes `time_halves_swapped`, `time_hi_zero`) e `clint_props`, programa `time-follows-mtime` |
| L9 | O `mtime` compartilhado entre harts e o `msip` para interrupção entre processadores | Não aplicável | Um só hart |

## 14. Memória física: PMA e PMP

Seções 3.6 e 3.7.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| A1 | Os atributos de memória física (PMA) de cada região são fixos em projeto e conhecidos do software | Conforme | O mapa de memória do `platform.yaml` é a fonte, e o `generate-memory-map` o escreve no VHDL, no ligador e no cabeçalho do runtime |
| A2 | Uma violação de PMA (execução em região sem busca, escrita em memória só de leitura, acesso a região sem memória) gera falha de acesso precisa, sempre que possível | Conforme | Com `has_access_faults`: ver X2 e X8. O mapa válido (ROM, RAM, janela externa e slots de periférico ocupados) vem do `platform.yaml`. Nas plataformas sem o extra `AccessFaults` o Core não gera as causas 1, 5 e 7 (escolha da plataforma) |
| A3 | O acesso desalinhado a memória principal é executado ou trapa, e a execução não precisa ser atômica | Conforme | Zicclsm. Programa `misaligned-crossing`, ACT4 `rv32i/Zicclsm` (13) |
| A4 | Os PMAs de atomicidade (AMO, reservabilidade), coerência e cache por região | Não aplicável | O Core não tem a extensão A nem coerência entre harts |
| A5 | PMP (`pmpcfg`, `pmpaddr`) e Smepmp (`mseccfg`) | Não aplicável | O Core não implementa PMP; os endereços `0x3A0` a `0x3EF` e `0x747` são ilegais. cocotb `CoreTrapPriority` |
| A6 | Memória virtual (`satp`, Sv32 e família) e a paginação | Não aplicável | O Core só tem o modo M |

### 14.1. Falhas de acesso

O manual recomenda com ênfase que as violações de PMA sejam exceções precisas, "sempre que possível". O Core as gera com o generic `has_access_faults` (desligado por padrão; a `de0-cv` o liga com `extras: [AccessFaults]`). O mapa válido vem do `platform.yaml`: os genéricos de KiB que o Core já recebia (`rom_end_kib`, `ram_base_kib`, `ram_end_kib`, `ext_base_kib`, `periph_base_kib`) e o genérico `periph_slots`, que o `riscv-tools` escreve como `PERIPH_SLOTS` (um bit por janela de 256 MiB do barramento de periféricos que tem periférico).

| Violação | Causa | `mtval` | Onde é decidida |
| :--- | :---: | :--- | :--- |
| Busca fora de ROM, RAM e janela externa (buraco, janela vazia ou periférico) | 1 | PC | Estágio EX, a partir do PC registrado |
| Load para endereço fora do mapa | 5 | Endereço efetivo | Bit registrado em EX/MEM, conferido no estágio MEM |
| Store para endereço fora do mapa ou na ROM | 7 | Endereço efetivo | O mesmo bit de escrita, registrado em EX/MEM |

A validade do endereço de dados sai de EX junto da classificação que o `reg_ex_mem` já registra, e o estágio MEM só confere o bit, de modo que o caminho que a frente F encurtou não ganha comparador. O desalinhamento que o hardware não executa vence a falha de acesso (a ordem opcional da Tabela 17), e a busca vence a instrução ilegal. Nas plataformas sem o extra o Core não gera as causas 1, 5 e 7, e o bit de validade é constante e não é sintetizado.

## 15. Fora do escopo

| Item | Capítulo | Motivo |
| :--- | :--- | :--- |
| Modo S, `sstatus`, `sie`, `sip`, `satp`, `medeleg`, `mideleg`, `scounteren`, `stimecmp` (Sstc) | 4, 12 e 3.1.8 | O hart só tem o modo M; os CSRs são ilegais |
| Modo U e `mcounteren`, `menvcfg` | 3.1.11 e 3.1.18 | Sem o modo U esses registradores não existem (o manual manda que `mcounteren` não exista) |
| Memória virtual (Sv32, Svnapot, Svpbmt, Svinval, Svadu) | 12 e 13 | Sem modo S e sem MMU |
| Hipervisor (H) | 15 | Exige o modo S e memória virtual |
| PMP e Smepmp | 3.7 e 3.1.19 | O hart não tem proteção de memória física |
| Interrupções não mascaráveis (Smrnmi) e `mnscratch`, `mnepc`, `mncause`, `mnstatus` | 3.5 | Nenhum erro de hardware gera NMI no SoC |
| Double trap (Smdbltrp) e `MDT` | 3.1.6.2 | Não há estado crítico para sinalizar |
| Fluxo de controle e pilha sombra (Zicfilp, Zicfiss) | 22 e 23 | Fora do conjunto de extensões do projeto |
| Depuração (Sdext, Sdtrig) | Parte do manual de depuração | Os CSRs `0x7A0` a `0x7BF` geram instrução ilegal |
| Máscara de ponteiros (Smmpm, Ssnpm), Smstateen, Smaia, Smcsrind, Smctr, Smcdeleg, Smcntrpmf | 3.1.18 e extensões | Sem o modo U ou S, ou sem necessidade num hart de um modo |
| Contadores `scountovf` e `hpmcounter` para o modo S | 14 | Sem o modo S |
| Extensão A, C, F, D, V | Não privilegiado | A, C, F, D e V não fazem parte do projeto; ver [o relatório não privilegiado](riscv-nao-privilegiado.md) |

## 16. Lacunas e escolhas

Não há lacuna aberta. Duas linhas dependem de a plataforma ligar a extensão: as falhas de acesso 1, 5 e 7 (X2, X8 e A2) só existem onde o `platform.yaml` tem `extras: [AccessFaults]`, hoje a `de0-cv`, e o `time` espelha o `mtime` (L8) onde há CLINT, hoje a `de0-cv` e a `modular`.

As escolhas do EEI que mudam o que o programa vê são: `mvendorid`, `marchid`, `mimpid` e `mconfigptr` valem zero (D8 a D12); `mtval` é zero na instrução ilegal e no `EBREAK` (T8 e T9); o modo vetorado de `mtvec` pede `BASE` alinhada a 64 bytes (V5); a `WFI` é um `nop` (I2); a interrupção vence a exceção da mesma instrução (Q11); a `FENCE.I` espera um ciclo uma interrupção (Q12); o acesso desalinhado à memória principal é executado em duas etapas (X7).

Uma mudança no que o ACT4 ou a Certification esperam: os endereços `0x723` a `0x73F` (`mhpmeventNh`) e o bit 13 de `mip` e `mie` passam a existir nas plataformas que ligam a Sscofpmf (a `de0-cv`); os perfis do ACT4 não dependem deles.

## 17. Como reproduzir

| O que | Comando |
| :--- | :--- |
| Testes de entidade do Core | `make test` no Core, ou `make test TEST=CoreTrapPriority` e os outros por nome |
| Provas formais do Core | `make formal` no Core, com `FORMAL_ENGINE=bitwuzla`, `yices`, `boolector` ou `abc-bmc3` |
| Programas de interrupção | `uv run python tests/python/runner.py irq-programs` no Tests |
| Programas de exceção e de CSR | `riscv-tools` do Tests, em simulação e na placa |
| Provas do CLINT e do PLIC | `make formal` no Peripherals |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
