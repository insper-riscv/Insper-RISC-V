# Conformidade com o volume não privilegiado do RISC-V

🌐 [Português](riscv-nao-privilegiado.md) · [English](../../en/conformance/riscv-nao-privilegiado.md)

Este relatório confronta cada requisito normativo dos capítulos 1, 2 e 4 a 11 do volume não privilegiado do manual do RISC-V (versão 20260120) com a evidência que o cobre. A implementação está no [Core](../../../Core/README.md), e cada requisito aponta para pelo menos um teste, uma prova ou um programa.

## 1. Escopo

A numeração dos capítulos é a do manual sem a Introdução, a mesma que a documentação do Core usa. O PDF imprime cada capítulo com o número seguinte.

| Capítulo | Tema | Tratamento |
| :--- | :--- | :--- |
| 1 | RV32I | Seção 3 |
| 2 | RV32E | Seção 4 |
| 3 | RV64I | Fora do escopo, porque o projeto é RV32 |
| 4 | Zifencei | Seção 5 |
| 5 | Zicsr | Seção 6 |
| 6 | Zicntr e Zihpm | Seção 7 |
| 7 | Zihintntl | Seção 8 |
| 8 | Zihintpause | Seção 9 |
| 9 | Zimop | Seção 10 |
| 10 | Zicond | Seção 11 |
| 11 | M e Zmmul | Seção 12 |
| 12 | A | Fora do escopo, extensão descartada |

## 2. Como ler

### 2.1. Situação

| Situação | Significado |
| :--- | :--- |
| Conforme | O Core cumpre o requisito e a evidência o demonstra |
| Escolha do EEI | O manual deixa a escolha ao ambiente de execução (EEI), e o Core registra a sua. Neste projeto o EEI é o SoC do Insper-RISC-V, com um hart em modo máquina |

### 2.2. Evidência

| Sigla | Onde fica | Como reproduzir |
| :--- | :--- | :--- |
| cocotb `X` | Entrada `X` de `tests/python/tests.json` do Core | `make test TEST=X` no Core |
| formal `arquivo` | `formal/<arquivo>.sv` do Core, com os mutantes que a prova rejeita | `make formal` no Core |
| programa `P` | `asm/P`, `asm-sdram/P` ou `asm-hpm-reduced/P` do repositório Tests | `riscv-tools` do Tests, em simulação e na placa |
| ACT4 `pasta` | Pasta de testes do ACT4 (`riscv-arch-test`) executada pelo repositório Certification, no perfil mínimo da extensão | Fluxo `certify` da Certification |

O ACT4 cobre toda a pasta citada, e a contagem entre parênteses é o número de testes da pasta no ACT4 fixado em `vendor/riscv-arch-test`.

## 3. Capítulo 1: RV32I

### 3.1. Modelo de programação

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I1 | XLEN é 32 e há 32 registradores de uso geral | Conforme | cocotb `bancoRegistradores`, ACT4 `rv32i/I` (39) |
| I2 | `x0` lê zero e ignora a escrita, também pelo caminho de adiantamento | Conforme | cocotb `bancoRegistradores` e `ForwardingMatch`, programas `x0-readonly` e `conformance-decode` |
| I3 | O contador de programa tem 32 bits e as instruções têm 32 bits alinhadas (IALIGN 32) | Conforme | cocotb `PcFetch` e `CoreMisalignedJump`, ACT4 `rv32i/I` (39) |
| I4 | Os formatos R, I, S, B, U e J têm os imediatos do manual, com extensão de sinal | Conforme | cocotb `ExtenderImm` e `ControlUnit` (contra a tabela de opcodes do manual), ACT4 `rv32i/I` (39) |

### 3.2. Instruções computacionais

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I5 | `ADDI`, `SLTI[U]`, `ANDI`, `ORI`, `XORI` e os deslocamentos com constante, sem exceção aritmética | Conforme | cocotb `ALU`, formal `alu_props` (operadores equivalentes para toda operação), programas `arithmetic-addi-negative`, `compare-slti`, `compare-sltiu`, `logical-andi`, `logical-ori`, `logical-xori`, `shift-left-logical-imm`, `shift-right-logical-imm`, `shift-right-arithmetic-imm` |
| I6 | `ADD`, `SUB`, `SLT[U]`, `AND`, `OR`, `XOR`, `SLL`, `SRL` e `SRA` usam os cinco bits baixos de `rs2` como quantidade de deslocamento | Conforme | cocotb `ALU`, formal `alu_props`, programas `arithmetic-add`, `arithmetic-sub`, `compare-slt`, `compare-sltu`, `logical-and`, `logical-or`, `logical-xor`, `shift-left-logical`, `shift-right-logical-reg`, `shift-right-arithmetic-reg` |
| I7 | `LUI` carrega o imediato nos 20 bits altos e `AUIPC` soma o imediato ao `pc` da própria instrução | Conforme | cocotb `ControlUnit` e `ALU`, programas `load-upper-immediate` e `add-upper-immediate-to-pc`, ACT4 `rv32i/I` (39) |
| I8 | Os deslocamentos com constante só aceitam o campo alto do manual (`imm[11:5]`), e as demais codificações são reservadas | Escolha do EEI | cocotb `ControlUnit` e `CoreIllegalInstruction`: o Core gera instrução ilegal (causa 2) |

### 3.3. Controle de fluxo

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I9 | `JAL` e `JALR` gravam `pc + 4` em `rd` e saltam; `JALR` zera o bit 0 do alvo | Conforme | programas `jump-jal` e `jump-jalr`, cocotb `CoreMisalignedJump`, ACT4 `rv32i/I` (39) |
| I10 | Os seis desvios condicionais comparam com e sem sinal e saltam para `pc` mais o imediato | Conforme | programas `branch-beq`, `branch-bne`, `branch-blt`, `branch-bge`, `branch-bltu`, `branch-bgeu`, formal `alu_props` (flag de desvio), ACT4 `rv32i/I` (39) |
| I11 | A exceção de endereço de instrução desalinhado só ocorre quando o salto é tomado, e é reportada no próprio salto (`mepc` é o salto e `mtval` o alvo) | Conforme | programa `trap-misaligned-jump`, cocotb `CoreMisalignedJump` |

### 3.4. Loads e stores

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I12 | `LB`, `LBU`, `LH`, `LHU`, `LW`, `SB`, `SH` e `SW` com extensão de sinal ou de zero | Conforme | cocotb `ExtenderRAM` e `StoreManager`, programas `load-byte-signed`, `load-byte-unsigned`, `load-halfword-signed`, `load-halfword-unsigned`, `load-word`, `store-byte-roundtrip`, `store-halfword-roundtrip`, `store-word-roundtrip`, `section6-loadstore` |
| I13 | Um load ou store alinhado nunca gera exceção de desalinhamento | Conforme | formal `trap_unit_props` (os acessos alinhados nunca geram as causas 4 e 6, por indução) |
| I14 | Um acesso desalinhado pode ser executado, emulado ou gerar trap, conforme o EEI | Escolha do EEI | Com `has_zicclsm` o Core executa o acesso em duas etapas na memória principal e gera as causas 4 e 6 (com `mtval` igual ao endereço) fora dela. Sem Zicclsm todo acesso desalinhado gera trap. cocotb `MisalignedUnit`, `CoreMisaligned`, `CoreMisalignedHalf`, `TrapUnit`, `TrapUnitNoZicclsm`, `TrapUnitExtFlash`, `TrapUnitExtRom`, formal `trap_unit_props` (os quatro mapas), programas `misaligned-crossing`, `trap-misaligned-ldst` e `misaligned-cache-lines`, ACT4 `rv32i/Zicclsm` (13) |
| I15 | Um acesso desalinhado não precisa ser atômico | Conforme | O Core o faz em dois acessos de palavra no estágio MEM, sem garantia de atomicidade. Programa `misaligned-crossing` |
| I16 | Um load com `rd = x0` ainda gera as exceções e os efeitos colaterais do acesso | Conforme | Programa `conformance-decode` (`lw x0` em endereço ímpar gera a causa 4 com `mtval` igual ao endereço efetivo) e programa `trap-mem-squash` |

### 3.5. Memória e ordenação

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I17 | `FENCE` ignora `rs1`, `rd`, `pred` e `succ`, e um `fm` reservado se comporta como `fm = 0` | Conforme | Programa `conformance-decode` (`fm` de 1, 2, 7 e 15, `pred` e `succ` nulos, `rs1` e `rd` diferentes de zero: nenhum trap e `rd` intacto) |
| I18 | `FENCE.TSO` (`fm = 1000`) pode ser tratado como `FENCE RW,RW` | Conforme | Programa `fence-tso`, ACT4 `rv32i/I` (39) |
| I19 | O modelo de memória RVWMO vale para um hart em ordem | Conforme | O pipeline executa um hart em ordem, e as caches preservam a ordem do programa. Programas `hazard-load-use`, `hazard-forwarding-raw`, `wb-hold-crossing` e `cache-sweep` |
| I20 | Uma busca de instrução precede os acessos de memória que a própria instrução causa | Conforme | Pipeline em ordem, programas `hazard-load-use` e `selfmod-repeat` |

### 3.6. Chamadas de ambiente, pontos de parada e HINTs

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| I21 | `ECALL` e `EBREAK` geram trap preciso (causas 11 e 3, `mepc` igual ao endereço da instrução) | Conforme | Programa `trap-ecall-ebreak`, cocotb `TrapUnit` e `CoreTrapTake`, formal `trap_unit_props` e `core_trap_take_props`, ACT4 `rv32i/I` (39) |
| I22 | `ECALL` e `EBREAK` não contam como instrução retirada | Conforme | Programa `cntr-trap-no-retire` |
| I23 | Um HINT (instrução computacional com `rd = x0`) só altera `pc` e os contadores | Conforme | Programa `conformance-decode` (todas as formas da tabela do manual, com `x0` em zero também pelo adiantamento, nenhum trap e `instret` somando 1 por HINT) |
| I24 | Uma codificação reservada gera instrução ilegal (a escolha é do EEI) | Escolha do EEI | cocotb `ControlUnit`, `CoreIllegalInstruction` e `CoreTrapSignal`, programa `trap-illegal` (causa 2, `mtval` zero) |

## 4. Capítulo 2: RV32E

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| E1 | A RV32E tem 16 registradores de uso geral, `x0` a `x15`, com `x0` em zero | Conforme | cocotb `CoreRv32e`, ACT4 `rv32e/E` |
| E2 | As codificações que usam `x16` a `x31` em `rd`, `rs1` ou `rs2` são reservadas | Escolha do EEI | O Core gera instrução ilegal (causa 2) sem escrever o destino. cocotb `CoreRv32e` e `CoreIllegalInstruction` |
| E3 | Fora o banco de registradores, a RV32E é idêntica à RV32I | Conforme | O pipeline e o adiantamento não mudam com `has_e`. ACT4 `rv32e/E`, `rv32e/M` e `rv32e/Zmmul` |
| E4 | `misa` indica a extensão `E` no lugar da `I` | Conforme | cocotb `CsrFileRveNoM` |
| E5 | A RV32E combina com as extensões M e Zmmul | Conforme | ACT4 `rv32e/M` e `rv32e/Zmmul`, cocotb `CoreRv32e` |

## 5. Capítulo 4: Zifencei

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| F1 | `FENCE.I` torna visíveis à busca os stores anteriores do mesmo hart | Conforme | cocotb `FenceiUnit`, `FenceiUnitDcache`, `CoreFenceI` e `CoreFenceIDcache`, programas `sdram-exec-copy` e `selfmod-repeat`, ACT4 `rv32i/Zifencei` (1) |
| F2 | Os campos `funct12`, `rs1` e `rd` são ignorados | Conforme | Programa `conformance-fencei`, cocotb `CoreFenceILegal` |
| F3 | `FENCE.I` ordena os acessos anteriores antes das buscas posteriores | Conforme | A `fencei_unit` redireciona o fluxo para `pc + 4`, descarta a cache de instruções e espera a confirmação da cache de dados. cocotb `FenceiUnit` e `FenceiUnitDcache`, programa `selfmod-repeat` |
| F4 | Sem a extensão, `FENCE.I` não é uma instrução legal | Conforme | cocotb `CoreIllegalInstruction` (a palavra `0x0000100F` gera a causa 2 sem a extensão) |

## 6. Capítulo 5: Zicsr

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| C1 | As seis instruções leem e modificam um CSR de modo atômico, com o valor antigo zero-estendido em `rd` | Conforme | cocotb `CsrDecode` e `CsrFile`, programa `csr-rw-basic`, formal `csr_file_props`, ACT4 `rv32i/Zicsr` (6) |
| C2 | `CSRRW` e `CSRRWI` com `rd = x0` não leem o CSR nem causam efeito de leitura | Conforme | Programa `csr-x0-no-effect`; a leitura de CSR do Core não tem efeito colateral |
| C3 | `CSRRS`, `CSRRC`, `CSRRSI` e `CSRRCI` com `rs1 = x0` (ou `uimm = 0`) leem e não escrevem | Conforme | Programa `csr-x0-no-effect`, formal `csr_file_props` |
| C4 | Um registrador diferente de `x0` que guarda zero ainda executa a escrita do CSR inteiro | Conforme | Programa `csr-x0-no-effect` (`csrrs` e `csrrc` com registrador em zero) |
| C5 | A escrita em um CSR somente leitura gera instrução ilegal, exceto `CSRRS`/`CSRRC` com `rs1 = x0` | Conforme | Programas `cntr-readonly-illegal` e `trap-illegal`, formal `csr_file_props` e `csr_hpm_props`, cocotb `CsrFile` |
| C6 | Um endereço de CSR que a implementação não tem gera instrução ilegal | Conforme | Programa `trap-illegal`, formal `csr_file_props`, cocotb `CsrFile` |
| C7 | Um CSR modificado como efeito colateral (como `instret`) é lido com o valor anterior à instrução, e a escrita explícita vence a atualização | Conforme | Programas `cntr-write`, `cntr-instret-exact` e `cntr-rollover`, formal `csr_cntr_props` |
| C8 | O efeito de um CSR é visível à instrução seguinte, sem adiantamento perdido | Conforme | Programas `csr-forwarding`, `csr-back-to-back` e `cntr-forwarding` |
| C9 | A leitura de CSR conta como entrada de dispositivo e a escrita como saída, para o `FENCE` | Conforme | O pipeline é em ordem e um hart, então a ordem do programa é a ordem global. Programa `csr-back-to-back` |
| C10 | A instrução `SYSTEM` com `funct3` reservado ou `funct12` não suportado gera instrução ilegal | Conforme | Programa `trap-illegal` (`sret` e `funct3 = 100`), cocotb `CsrDecode` |

## 7. Capítulo 6: Zicntr e Zihpm

### 7.1. Zicntr

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| K1 | O Zicntr depende do Zicsr | Conforme | A matriz de perfis implica `has_zicsr`, e o `core` falha na elaboração sem ele. `make profiles` no Core |
| K2 | `cycle`, `time` e `instret` são contadores de 64 bits, lidos em duas metades no RV32 (`cycleh`, `timeh` e `instreth`) | Conforme | cocotb `Counter64`, `CsrFileZicntr`, formal `counter64_props`, ACT4 `rv32i/Zicntr` (2) |
| K3 | Os contadores são somente leitura nos endereços `0xC00` a `0xC02` e `0xC80` a `0xC82`, e a leitura usa `CSRRS` com `rs1 = x0` | Conforme | Programa `cntr-readonly-illegal`, cocotb `CsrFileZicntr`, ACT4 `rv32i/Zicntr` (2) |
| K4 | `cycle` conta ciclos de clock do núcleo e nunca retrocede | Conforme | Programas `cntr-cycle-monotonic` e `cntr-muldiv-cost`, formal `counter64_props` (monotonia sem escrita) e `csr_cntr_props` (modelo de 64 bits) |
| K5 | `time` soma um a cada tick do relógio de tempo real, com período constante | Conforme | O `tick_divider` gera um tick a cada `tick_cycles` ciclos. cocotb `TickDivider`, programa `cntr-time-rate` |
| K6 | O ambiente informa o período do tick de `time` | Escolha do EEI | O período é $tick\_cycles / f_{clock}$, fixado por generic e documentado em `Core/docs/pt-br/ISA/Zicntr/description.md` |
| K7 | `instret` conta as instruções retiradas, e as que geram exceção não contam | Conforme | Programas `cntr-instret-exact`, `cntr-trap-no-retire` e `trap-mem-squash`, formal `csr_cntr_props` |
| K8 | Uma leitura em alta, baixa e alta recupera um valor de 64 bits válido | Conforme | Programa `cntr-rollover`, formal `counter64_props` (vai-um registrado) |
| K9 | Um contador pode ser inibido, e a escrita em `mcycle` e `minstret` vale | Conforme | Programa `cntr-write`, cocotb `CsrFileZicntr`, formal `csr_cntr_props` |
| K10 | Sem `mcounteren`, todo contador é acessível no único modo do hart | Escolha do EEI | O Core só tem o modo M e o acesso a `mcounteren` é ilegal, como o manual privilegiado permite. cocotb `CsrFile` |

### 7.2. Zihpm

A conformidade do Zihpm tem documento próprio, com a matriz das exigências do capítulo e do volume privilegiado, em [Core/docs/pt-br/ISA/Zihpm/conformance.md](../../../Core/docs/pt-br/ISA/Zihpm/conformance.md). A tabela abaixo reúne as linhas desse documento ao lado das demais.

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| H1 | O Zihpm depende do Zicsr | Conforme | `make profiles` e a asserção do `core` |
| H2 | `hpmcounter3` a `hpmcounter31` e as metades altas `hpmcounter3h` a `hpmcounter31h` são contadores de 64 bits somente leitura | Conforme | cocotb `CsrFileZihpmFull` e `CsrFileZihpm`, formal `csr_hpm_props`, programas `hpm-full` e `hpm-sweep`, ACT4 `rv32i/Zihpm` (2) |
| H3 | Um contador não implementado gera instrução ilegal ou lê uma constante | Escolha do EEI | O Core lê zero e ignora a escrita. cocotb `CsrFileZihpmReduced`, programa `hpm-reduced`, formal `csr_hpm_props` |
| H4 | O número, a largura e os eventos dos contadores são da plataforma | Escolha do EEI | Generics `hpm_counters` (0 a 29) e `hpm_width` (0 a 64). cocotb `HpmCounterBankAll64`, `HpmCounterBankFour33` e `Counter64Width20` a `Counter64Width63`, programas `hpm-reduced` e `hpm-sweep` |
| H5 | Um registrador de evento escolhe o que cada contador conta, e um evento sem significado conta zero | Conforme | Programas `hpm-inhibit-select`, `hpm-branch-count`, `hpm-load-use`, `hpm-muldiv-stall`, `hpm-cpi` e `hpm-fused-high`, cocotb `HpmCounterBankAll64` |
| H6 | `mcountinhibit` inibe `cycle`, `instret` e os contadores de eventos | Conforme | Programas `hpm-inhibit-select` e `hpm-sweep`, formal `csr_hpm_props` |
| H7 | Uma escrita explícita vence o incremento do mesmo ciclo | Conforme | formal `counter64_props` e `csr_hpm_props`, cocotb `HpmCounterBankAll64` |

## 8. Capítulo 7: Zihintntl

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| N1 | `ntl.p1`, `ntl.pall`, `ntl.s1` e `ntl.all` são `ADD x0, x0, x2` a `x5` | Conforme | cocotb `ZihintntlDecode`, formal `zihintntl_props` (exatamente as quatro palavras) |
| N2 | Uma implementação pode ignorar a dica e executá-la como `nop`, sem exceção | Conforme | O Core a executa como `nop`, e o decodificador desliga a escrita em `rd`. cocotb `CoreZihint`, programa `zihintntl-hints` |
| N3 | A dica não altera registradores nem memória | Conforme | Programa `zihintntl-hints` (`x2` a `x5` e `x0` intactos, também pelo adiantamento) |
| N4 | A dica conta como instrução retirada | Conforme | Programa `conformance-decode` (o `ADD` com `rd = x0` retira uma vez e soma 1 em `instret`) |
| N5 | As formas comprimidas (`c.ntl.*`) pertencem à extensão C | Escolha do EEI | O Core não implementa a extensão C |
| N6 | O ACT4 da extensão passa | Conforme | ACT4 `rv32i/Zihintntl` (8) |

## 9. Capítulo 8: Zihintpause

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| P1 | `pause` é o `FENCE` com `pred = W`, `succ = 0`, `fm = 0`, `rs1 = rd = x0` (palavra `0x0100000F`) | Conforme | cocotb `ZihintpauseDecode`, formal `zihintpause_props` (exatamente a palavra) |
| P2 | `pause` é uma dica que pode executar como `nop`, sem exceção | Conforme | O Core a executa como `FENCE`, que é `nop`. cocotb `CoreZihint`, programa `zihintpause-loop` |
| P3 | A pausa não tem duração mínima obrigatória | Escolha do EEI | O Core não atrasa a instrução seguinte |
| P4 | Os demais `FENCE` não são `pause` | Conforme | formal `zihintpause_props`, programa `conformance-decode` |
| P5 | O ACT4 da extensão passa | Conforme | ACT4 `rv32i/Zihintpause` (1) |

## 10. Capítulo 9: Zimop

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| O1 | Há 32 instruções `mop.r.n` (`n` de 0 a 31) e 8 instruções `mop.rr.n` (`n` de 0 a 7) na classe `SYSTEM` | Conforme | cocotb `ZimopDecode`, formal `zimop_props` (exatamente as 40 codificações) |
| O2 | Cada MOP escreve zero em `rd` | Conforme | cocotb `CoreZimop`, formal `zimop_props`, programas `zimop-mop-r` e `zimop-mop-rr` |
| O3 | Uma MOP nunca gera instrução ilegal quando a extensão está presente | Conforme | Programas `zimop-mop-r` e `zimop-mop-rr` (nenhum trap), cocotb `CoreZimop` |
| O4 | Uma MOP com `rd = x0` não altera o estado, e `mop.rr` lê `rs1` e `rs2` | Conforme | cocotb `CoreZimop`, formal `zimop_props` |
| O5 | Sem a extensão, a codificação é uma instrução `SYSTEM` não suportada | Conforme | cocotb `CoreZimopOff` (causa 2, `rd` intacto e o programa retoma) |
| O6 | O ACT4 da extensão passa | Conforme | ACT4 `rv32i/Zimop` (40) |

## 11. Capítulo 10: Zicond

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| Z1 | `czero.eqz rd, rs1, rs2` grava zero se `rs2 = 0` e `rs1` caso contrário | Conforme | cocotb `ZicondUnit` e `CoreZicond`, formal `zicond_props`, programas `zicond-bits` e `zicond-edge` |
| Z2 | `czero.nez rd, rs1, rs2` grava zero se `rs2` é diferente de zero e `rs1` caso contrário | Conforme | cocotb `ZicondUnit` e `CoreZicond`, formal `zicond_props`, programas `zicond-bits` e `zicond-edge` |
| Z3 | A condição olha o registrador `rs2` inteiro, e o valor de `rs1` chega a todos os bits | Conforme | Programa `zicond-bits` (cada bit de `rs2` decide a condição e cada bit de `rs1` chega ao destino) |
| Z4 | A codificação é `opcode = 0110011`, `funct7 = 0000111` e `funct3 = 101` ou `111` | Conforme | cocotb `ZicondDecode`, formal `zicond_decode_props` |
| Z5 | Sem a extensão, a codificação é ilegal | Conforme | cocotb `CoreZicondOff` |
| Z6 | O ACT4 da extensão passa | Conforme | ACT4 `rv32i/Zicond` (2) |

## 12. Capítulo 11: M e Zmmul

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| M1 | `MUL` grava a metade baixa do produto de 32 por 32 bits, e `MULH`, `MULHU` e `MULHSU` a metade alta com e sem sinal | Conforme | cocotb `BoothMultiplier`, `MultDiv`, `MDecode` e `CoreMulDiv`, programas `mul`, `mulh`, `mulhu` e `mulhsu`, ACT4 `rv32i/M` (8) |
| M2 | `DIV`, `DIVU`, `REM` e `REMU` truncam em direção a zero, e o resto tem o sinal do dividendo | Conforme | cocotb `NonRestoringDivider`, `MultDiv` e `CoreMulDiv`, programas `div`, `divu`, `rem` e `remu`, ACT4 `rv32i/M` (8) |
| M3 | A divisão por zero dá quociente com todos os bits em 1 e resto igual ao dividendo, sem trap | Conforme | cocotb `NonRestoringDivider` e `MultDiv`, programas `div`, `divu`, `rem` e `remu` |
| M4 | O estouro com sinal (`-2^31 / -1`) dá quociente igual ao dividendo e resto zero, sem trap | Conforme | cocotb `NonRestoringDivider` e `MultDiv`, programas `div` e `rem` |
| M5 | A fusão de `MULH[[S]U]` seguido de `MUL`, e de `DIV[U]` seguido de `REM[U]`, é recomendada | Conforme | O Core reaproveita o resultado completo quando os operandos coincidem. cocotb `MuldivFusion`, formal `muldiv_fusion_props`, programas `muldiv-fusion` e `hpm-fused-high` |
| M6 | A latência não tem requisito | Conforme | O pipeline para por um número fixo de ciclos. Programas `cntr-muldiv-cost` e `hpm-muldiv-stall`, cocotb `CoreMulDiv` |
| M7 | Os resultados chegam a quem os usa em seguida | Conforme | Programas `hazard-forwarding-mul`, `div-rem-back-to-back` e `trap-muldiv-load-use`, `wb-hold-crossing` |
| M8 | O Zmmul tem só as quatro multiplicações, e a divisão é ilegal | Conforme | cocotb `CoreZmmul` e `MDecode`, ACT4 `rv32i/Zmmul` (4) e `rv32e/Zmmul` |
| M9 | A M implica o Zmmul | Conforme | A matriz de perfis impede a coexistência dos nomes, e `has_m` inclui a multiplicação. `make profiles` no Core |

## 13. Complementos de outros volumes

| ID | Requisito | Situação | Evidência |
| :--- | :--- | :--- | :--- |
| X1 | A extensão Ztso não é declarada, e `FENCE.TSO` executa como `FENCE RW,RW` | Conforme | Programa `fence-tso`, ACT4 `rv32i/I` (39) |
| X2 | Numa implementação só de modo máquina, `mstatush` existe e lê zero | Conforme | cocotb `CsrFile` (`mstatush` lê zero e ignora a escrita) e formal `csr_file_props` (bits fixos) |
| X3 | Numa implementação só de modo máquina, `menvcfg` e `mcounteren` não são exigidos | Escolha do EEI | O Core não os implementa, e o acesso a `mcounteren` (`0x306`), `menvcfg` (`0x30A`) e `menvcfgh` (`0x31A`) gera instrução ilegal. cocotb `CsrFile` |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
