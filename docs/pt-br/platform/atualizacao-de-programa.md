# Como um novo programa passa a rodar: rewrite de FLASH e handoff de boot

Trocar de teste na placa combina dois mecanismos distintos: um
genérico, do próprio `riscv-tools` (reescrever uma memória via JTAG
sem recompilar/reprogramar a FPGA inteira), e um específico deste
projeto (como o controle chega da BOOT_ROM fixa até o programa recém
escrito em FLASH). O segundo é o mesmo problema que qualquer sistema
de atualização remota de firmware precisa resolver (ver "O que a
BOOT_ROM e o programa combinam" abaixo): quem recebe a atualização já
está rodando código compilado **antes** da atualização existir, então
os dois lados (o que atualiza e o que é atualizado) precisam
concordar de antemão sobre onde tudo mora.

## 1. A sequência completa

1. **Programação inicial (uma única vez)**: `quartus_sh --flow compile`
   + `quartus_pgm` carrega o bitstream inteiro, incluindo o conteúdo
   inicial de BOOT_ROM (`src/simulation/internal-mem/runtime/boot_rom.S`) e da primeira FLASH/RAM.
   BOOT_ROM nunca mais é tocada depois disso.
2. **Troca de teste (caminho rápido)**: `riscv-tools run` reescreve
   a FLASH, que tem uma só cópia, pelo carregador JTAG (`quartus.rom_write_method:
   jtag_loader`): para o core, grava a imagem, confere a contagem e a soma de
   verificação e solta o core, que reinicia pela BOOT_ROM no passo 5, sem
   recompilar nem reprogramar a FPGA e sem escrever `fromhost`.
3. **O core, do lado de dentro**: entre um teste e outro, o core fica
   parado em `rv32_wait_restart` (endereço fixo `0x100` em BOOT_ROM),
   num loop que só faz `lw` de `fromhost_addr` até ler não-zero.
4. Ao ver `fromhost` diferente de zero, `rv32_wait_restart` salta pra
   `_reset` (endereço fixo `0x0`). O teste anterior já escreveu o resultado
   em `tohost` antes de chegar lá.
5. `_reset` zera `tohost`, `fromhost` e o cabeçalho do
   `stdout` (pra não vazar o resultado nem a saída do teste anterior) e
   salta pra `FLASH_BASE` (`0x00001000`).
6. Em `0x1000` está o `_start` do `crt0` da picolibc, dentro da imagem do
   teste: ajusta `sp` e `gp`, copia `.data` de FLASH pra RAM, zera
   `.bss`, prepara o TLS e chama `main`, ver
   [boot.md](boot.md).
7. Ao terminar, o teste escreve o `tohost` (`RV32_PASS()`/`RV32_FAIL(código)`
   em `rv32_test.h`, ou o retorno de `main` via `_exit`) e chama
   `rv32_wait_restart`, voltando ao passo 3.

O contato entre a BOOT_ROM e a FLASH é só o salto do passo 5 (BOOT_ROM
para a FLASH) e o salto do passo 7 (programa para `0x100`): a BOOT_ROM
não lê nada da FLASH.

## 2. Por que a BOOT_ROM nunca é reescrita por teste

`_reset` e `rv32_wait_restart` são endereços fixos (`0x0`, `0x100`,
ver `src/simulation/internal-mem/runtime/boot_rom.ld`), resolvidos no link **único e separado** de
`src/simulation/internal-mem/runtime/boot_rom.S`, não no link de cada teste. Se BOOT_ROM fosse
reescrita por teste como FLASH é, cada nova compilação poderia mover
esses offsets, e todo teste que já tem esses mesmos endereços fixos
embutidos no próprio binário (via `--defsym=rv32_wait_restart=0x100`
em `rv32im-fpga.specs`) ficaria chamando um endereço errado sem nenhum
erro de link avisando, já que os dois lados são compilados e
linkados completamente separados. Manter BOOT_ROM congelada depois da
programação inicial é isso: sem ela fixa, não haveria endereço estável
pro handoff funcionar.

`rv32_wait_restart` também não pode ficar em FLASH: é nele que o core
espera enquanto o host reescreve a FLASH, então ele precisa estar numa
memória que ninguém reescreve, senão o core executaria instruções de uma
memória em reescrita.

## 3. O que a BOOT_ROM e o programa combinam

`src/simulation/internal-mem/runtime/boot_rom.S` é compilado e linkado **antes** de qualquer teste
existir: seu binário não pode conter nada de um teste específico. Esse é o
problema que qualquer atualização remota de firmware enfrenta: um bootloader
fixo, que não pode ser regravado remotamente (o risco de travar o dispositivo
pra sempre é alto demais), recebendo uma imagem de aplicação que pode. Os
dois lados precisam concordar de antemão sobre o mínimo, e aqui esse
mínimo é:

| Combinado | Valor | Quem usa |
| :--- | :--- | :--- |
| Entrada do programa | `0x1000`, o `_start` da picolibc (o `picolibc.ld` põe `.init` no começo da FLASH) | BOOT_ROM salta pra lá |
| `rv32_wait_restart` | `0x100` | o programa salta pra lá ao terminar |
| Palavras do topo da RAM | `fromhost` `0x2FFF0`, `tohost` `0x2FFE8`, cabeçalho do `stdout` `0x2FBE0` (gerados do `platform.yaml` em `memory_map.h`) | BOOT_ROM as zera, o programa e o host as usam |

Tudo o mais (onde ficam `.data`, `.bss`, heap e pilha, o tamanho de cada
seção) é decidido no link de cada teste pelo linker script da toolchain, a
partir dos endereços de `rv32im-fpga.specs`; a BOOT_ROM não sabe de nada
disso, porque quem copia o `.data` e zera o `.bss` é o `crt0` do próprio
programa. Por isso a imagem de um teste carrega tudo o que varia nela.

O estágio MEM deste core tem, de fato, um caminho de leitura até FLASH
(a porta B da FLASH, ver
[memoria.md](memoria.md#12-flash-o-firmware-de-cada-teste)):
é assim que o `crt0` lê o `.data` inicial da FLASH pra copiá-lo pra RAM, e
é assim que `.rodata` consegue ficar residente em FLASH (nunca copiado pra
RAM, ver [memoria.md](memoria.md)).

Uma diferença real em relação a uma atualização remota de verdade (por
rádio, por exemplo): nada aqui verifica a integridade da imagem antes de
saltar pra ela (checksum, assinatura). JTAG é um link local, físico,
confiável, então essa verificação nunca foi necessária aqui; um sistema que
recebesse atualizações por um link não-confiável precisaria dela.

## 4. O caminho lento: recompilar e reprogramar

Se um teste não responder no timeout (`quartus.default_timeout_s`), o
`riscv-tools`' `orchestrator` recorre a tiers progressivamente mais
caros até um recompile+reprogram completo; o módulo `orchestrator` do
Tools tem os detalhes de quando cada tier dispara, e
[placa.md](../guide/placa.md) traz a regra de como compilar e programar
sem quebrar a sessão JTAG.

## 5. As bancas da FLASH e a imagem

A FLASH da `de0-cv` tem duas bancas para a atualização de programa em campo, declaradas em `flash.banks` do `platform.yaml`.

| Banca | Início | Tamanho | Início do programa |
| :--- | :--- | :--- | :--- |
| A | `0x00001000` | 124 KiB | `0x00001100` |
| B | `0x00020000` | 128 KiB | `0x00020100` |

Cada banca começa por uma página de cabeçalho de 256 bytes (magia, tamanho, CRC-32 da carga, versão e CRC do cabeçalho; o formato está no módulo `flash_image` do Tools), e o programa vem logo depois. A rotina de atualização grava a carga primeiro e o cabeçalho por último, então um cabeçalho válido indica uma banca cuja atualização terminou. A boot ROM não confere o cabeçalho antes do salto, como diz o [contrato de entrada](contrato-de-entrada.md).

O `make generate` escreve, a partir das bancas, os arquivos abaixo.

| Arquivo | Conteúdo |
| :--- | :--- |
| `runtime/rv32im-fpga-bank-a.specs` e `runtime/rv32im-fpga-bank-b.specs` | Flags do linker de um programa para cada banca, com `__flash` no início do programa e `__flash_size` sem a página do cabeçalho |
| `runtime/flash_banks.h` | Magia da imagem, tamanho da página do cabeçalho e, de cada banca, `RV32_BANK_<NOME>_BASE`, `_SIZE` e `_ENTRY`, para a boot ROM e para a rotina de atualização |

Um programa para a banca B compila com `--specs` apontando para o arquivo de specs dela, e `riscv-tools flash-image pack programa.bin --output imagem.bin --version N --platform src/cyclone-v/de0-cv/platform.yaml --bank B` monta a imagem e confere que cabe. O `riscv-tools check-memory-map` valida as bancas (alinhadas ao setor de 4 KiB, dentro da FLASH, sem sobreposição).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
