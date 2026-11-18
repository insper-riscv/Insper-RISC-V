# O estado de boot de referência deste RISC-V bare-metal

O boot neste core passa por dois lados: a BOOT_MEMORY (`base/src/boot/boot_core.S`, incluído pelo `boot_memory.S` de cada plataforma), fixa e compartilhada, programada uma única vez e nunca reescrita por teste, e o `crt0` da picolibc, que vai dentro da imagem de cada teste na FLASH. Este projeto não tem `crt0` nem linker script próprios: ver [runtime.md](runtime.md) pra de onde vêm e como usar. Ver [atualizacao-de-programa.md](atualizacao-de-programa.md) pro como o controle passa de um lado pro outro a cada troca de teste.

Este documento descreve, registrador por registrador e seção por seção, exatamente que estado existe no instante em que `main()` é chamado, e, tão importante quanto, o que **não** é feito. O estado segue a ABI oficial do RISC-V
([riscv-elf-psabi-doc](https://github.com/riscv-non-isa/riscv-elf-psabi-doc)).

## 1. A BOOT_MEMORY comum

Toda plataforma monta a mesma BOOT, o `boot_core.S` comum (`base/src/boot/boot_core.S`). O `boot_memory.S` de cada plataforma é só um invólucro que inclui os cabeçalhos que `riscv-tools generate-memory-map` escreve do `platform.yaml` e, por último, o `boot_core.S`.

| Peça | Papel |
| :--- | :--- |
| `runtime/memory_map.h` | Os endereços de `tohost`, `fromhost`, `stdout` e `RV32_BOOT_ENTRY` |
| `runtime/flash_banks.h` | As duas bancas da FLASH e o formato da imagem (só nas plataformas com bancas) |
| `runtime/boot_config.h` | Um `RV32_HAS_<EXTENSÃO>` por extensão e extra do bloco `core`, `RV32_IS_E` e `RV32_TEST_WAIT`, pela chave `generate.boot_config_h` |
| `Core/src/<Extensão>/boot.inc` | O fragmento de cada extensão, que o `boot_core.S` inclui e que se desliga sozinho com `#if RV32_HAS_<EXTENSÃO>` |

### 1.1. As duas chaves

| Chave | Origem | Efeito |
| :--- | :--- | :--- |
| `RV32_TEST_WAIT` | A chave `boot.wait_restart` do `platform.yaml` | Presente, a BOOT é a de teste: `_reset` limpa `tohost`, `fromhost` e o cabeçalho do `stdout`, e `rv32_wait_restart` fica fixo em `0x100`. Ausente, a BOOT é a de aplicação: nada disso existe e o símbolo não é exportado |
| `RV32_BANK_A_BASE` | `flash_banks.h` | Presente, a BOOT escolhe entre as bancas A e B da FLASH. Ausente, ela salta direto para `RV32_BOOT_ENTRY` |

A plataforma `de2-115` define ainda `RV32_BOOT_RAM_MAGIC` no invólucro, e aceita assim um programa deixado na RAM pelo hospedeiro.

### 1.2. Estado em que a BOOT entrega o núcleo

1. Só na BOOT de teste, `tohost`, `fromhost` e o cabeçalho do `stdout` ficam zerados.
2. `x1` a `x31` ficam em zero (`x1` a `x15` no RV32E).
3. Os fragmentos do Core rodam sempre nesta ordem: Zicsr, Zicntr, Zihpm, Sscofpmf e Zifencei. Cada um usa só `t0`, `t1` e `t2`, e o `fence.i` do fragmento Zifencei só existe com Zifencei.
4. Com bancas, a BOOT valida as duas e salta para a de maior versão com `a0 = 0` e `a1 = 0`. Sem banca válida, ela espera lendo `fromhost` e recomeça em `_reset`. Esta salvaguarda existe nos dois builds, e o `fromhost` é só a campainha, nunca o endereço de salto.

A BOOT não prepara `sp`, `gp`, `tp`, `.data` nem `.bss`, que são do `crt0` do programa. O símbolo `rv32_boot_trap`, o tratador seguro que o fragmento Zicsr escreve em `mtvec`, para o núcleo num laço em vez de reiniciar sem fim.

### 1.3. Layout

`_reset` fica sozinho em `.text.reset`, com um desvio para o resto, que mora em `.text.wait_restart`. Na BOOT de teste essa seção começa em `0x100`, com `rv32_wait_restart` na primeira instrução, como o `boot_memory.ld` gerado fixa. O tamanho depende das extensões ligadas, e o linker reprova a BOOT que passa do tamanho da BOOT_MEMORY.

### 1.4. Verificação

| Prova | Onde |
| :--- | :--- |
| Em cada uma das plataformas, a BOOT monta, só tem `fence.i` com Zifencei e só exporta `rv32_wait_restart` com `RV32_TEST_WAIT`. Também monta no núcleo mínimo sem nenhuma instrução de CSR, no núcleo completo, no RV32E e na versão de aplicação | `tests/python/check_boot_contract.py` |
| As imagens da BOOT real que os testes de simulação carregam estão em dia com os fontes | `tests/python/gen_de0_cv_boot_images.py --check` e `tests/python/gen_real_boot_images.py --check` |
| A BOOT real inicia o programa no núcleo mínimo (`rv32i`), num núcleo com Zicsr e interrupções e no completo, e escolhe a banca certa em 13 casos | Os testes `TemplateRealBoot`, `ModularRealBoot`, `De0CvBootBanks` e `ExternalDataFlashUpdate` do `tests.json` |


## 2. A sequência de boot

1. O reset entra em `_reset` (`0x0`, na BOOT_MEMORY) e a BOOT faz o que a seção 1.2 descreve. Ela salta para `0x1000` (`RV32_BOOT_ENTRY`), ou, nas plataformas com bancas, para o início do programa da banca válida de maior versão (`0x1100` ou `0x20100` na `de0-cv`), e entrega `a0` e `a1` em `0`. Não inicializa `sp` nem `gp` e não copia nada.
2. Em `0x1000` está o `_start` do `crt0-hosted` da picolibc: ajusta `sp` (de `__stack`) e `gp` (de `__global_pointer$`) e chama o `_cstart`.
3. O `_cstart` copia `.data` e `.tdata` da FLASH para a RAM (com `memcpy`), zera `.bss` (com `memset`), prepara o TLS (`_set_tls`) e roda os construtores (`__libc_init_array`).
4. Chama `main(0, 0)` com `jal`, e o que `main` retornar vai para `exit`, que chama o `_exit` do projeto (`src/simulation/internal-mem/runtime/_exit.c`). Um teste que termina por `RV32_PASS()` ou `RV32_FAIL()` escreve o `tohost` e salta direto para o `rv32_wait_restart`, sem passar por `_exit`.

## 3. Registradores de propósito geral no momento em que `main()` roda

| Registrador | Nome ABI | Estado em `main()` | Por quê |
|---|---|---|---|
| `x0` | `zero` | `0`, sempre | Fixo em silício. |
| `x1` | `ra` | Endereço de retorno para o `_cstart` | `main` é chamado com `jal`; o retorno cai no `exit` |
| `x2` | `sp` | `__stack` (`0x0002FBE0`) | Ajustado pelo `_start` a partir do linker script |
| `x3` | `gp` | `__global_pointer$` (depende do tamanho do `.data` normal, `0x8800` quando ele é vazio) | Ajustado pelo `_start` (`auipc` e `addi`, relativos ao PC). Necessário pra qualquer acesso `gp`-relativo a `.sdata`/`.sbss` |
| `x4` | `tp` | Bloco de TLS na RAM | Ajustado pelo `_set_tls` |
| `x10`, `x11` | `a0`, `a1` | `0`, `0` | `argc` e `argv` de `main`; sem linha de comando |
| demais `x5`–`x9`, `x12`–`x17`, `x18`–`x31` | `t`, `s`, `a` | **Não garantido** | Sobras do próprio startup; um programa correto nunca depende do valor inicial de um deles |

## 4. CSRs (registradores de controle e status)

O `crt0-hosted` e a `libc.a` não tocam em nenhum CSR, o que foi conferido no código objeto (nenhuma instrução `csr*`, `ecall`, `ebreak` ou `mret`). Quem deixa o estado de máquina conhecido é a BOOT, pelos fragmentos das extensões do núcleo. Com Zicsr, `mstatus`, `mie`, `mscratch` (e `mip`, com interrupções) saem zerados e `mtvec` aponta para `rv32_boot_trap`. Com Zicntr os contadores de ciclos e de instruções saem zerados e contando, e com Zihpm e Sscofpmf os contadores de eventos saem zerados. Um programa que precise de interrupções ou de outro tratador os configura por conta própria antes de usá-los.

## 5. Seções de memória

Os endereços vêm do `picolibc.ld` e de `rv32im-fpga.specs`, que o `riscv-tools generate-memory-map` escreve do `platform.yaml` (FLASH de `0x1000`, 28 KB; RAM de `0x8000`, menos as regiões reservadas do topo). Não há orçamento fixo por seção: cada uma ocupa o que o programa precisa, e o linker recusa o que não cabe.

| Seção | Região | Estado antes de `main()` |
|---|---|---|
| `.init` | FLASH, `0x1000` | O `_start` e o que a picolibc põe no começo |
| `.text`, `.rodata` (inclui o `.srodata`) | FLASH | Já estão lá, carregados via JTAG; `.rodata` nunca é copiado pra RAM: um `lw` o alcança pela porta B da FLASH (ver [memoria.md](memoria.md)) |
| `.data` (inclui o `.sdata`), `.tdata` | RAM, a partir de `0x8000`; LMA na FLASH | Copiados da FLASH pelo `_cstart` |
| `.bss` (inclui o `.sbss`), `.tbss` | RAM, depois do `.data` | Zerados pelo `_cstart` |
| heap | RAM, de `_end` até `__heap_end` | Gerenciado pelo `malloc` da picolibc, via `sbrk` |
| Pilha | RAM, topo em `0x0002FBE0` | Só o ponteiro (`sp`) é definido; 4 KB reservados |
| `stdout` | RAM, `0x0002FBE0` a `0x0002FFE7` | Cabeçalho zerado pela BOOT_MEMORY (ver [runtime.md](runtime.md)) |
| `tohost` (`0x0002FFE8`) e `fromhost` (`0x0002FFF0`) | RAM | Zerados a cada entrada em `_reset`, cold boot ou restart, pra nunca vazar o resultado do teste anterior. Convenção HTIF, e só o Spike a usa |

## 6. O que essa sequência de boot deliberadamente NÃO faz

- **Tratamento de `ecall` e de interrupções.** A BOOT só aponta `mtvec` para o tratador seguro que para o núcleo, e o programa instala o próprio antes de depender de um trap.
- **Suporte multi-hart.** Assume um único hart, sem `mhartid`; o core é single-hart.
- **Entrada de dados.** Não há dispositivo de entrada: `stdin` devolve fim de arquivo.
- **PMP (Physical Memory Protection) / isolamento.** O núcleo não implementa PMP.
- **Registradores zerados em `main()`.** A BOOT zera `x1` a `x31` na entrada, mas a seleção de banca e o `crt0` os reutilizam, então só os listados na seção 3 têm valor definido em `main()`.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
