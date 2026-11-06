# Como um novo programa passa a rodar: rewrite de FLASH e handoff de boot

Trocar de teste na placa combina dois mecanismos distintos: um
genérico, do próprio `riscv-tools` (reescrever uma memória via JTAG
sem recompilar/reprogramar a FPGA inteira), e um específico deste
projeto (como o controle chega da BOOT_MEMORY fixa até o programa recém
escrito em FLASH). O segundo é o mesmo problema que qualquer sistema
de atualização remota de firmware precisa resolver (ver "O que a
BOOT_MEMORY e o programa combinam" abaixo): quem recebe a atualização já
está rodando código compilado **antes** da atualização existir, então
os dois lados (o que atualiza e o que é atualizado) precisam
concordar de antemão sobre onde tudo mora.

## 1. A sequência completa

1. **Programação inicial (uma única vez)**: `quartus_sh --flow compile`
   + `quartus_pgm` carrega o bitstream inteiro, incluindo o conteúdo
   inicial de BOOT_MEMORY (`src/simulation/internal-mem/runtime/boot_memory.S`) e da primeira FLASH/RAM.
   BOOT_MEMORY nunca mais é tocada depois disso.
2. **Troca de teste (caminho rápido)**: `riscv-tools run` reescreve
   a FLASH, que tem uma só cópia, pelo carregador JTAG (`quartus.rom_write_method:
   jtag_loader`): para o core, grava a imagem, confere a contagem e a soma de
   verificação e solta o core, que reinicia pela BOOT_MEMORY no passo 5, sem
   recompilar nem reprogramar a FPGA e sem escrever `fromhost`.
3. **O core, do lado de dentro**: entre um teste e outro, o core fica
   parado em `rv32_wait_restart` (endereço fixo `0x100` em BOOT_MEMORY),
   num loop que só faz `lw` de `fromhost_addr` até ler não-zero.
4. Ao ver `fromhost` diferente de zero, `rv32_wait_restart` salta pra
   `_reset` (endereço fixo `0x0`). O teste anterior já escreveu o resultado
   em `tohost` antes de chegar lá.
5. `_reset` zera `tohost`, `fromhost` e o cabeçalho do
   `stdout` (pra não vazar o resultado nem a saída do teste anterior) e
   salta pra `FLASH_BASE` (`0x00001000`). Na `de0-cv`, que tem duas bancas, a
   BOOT_MEMORY antes confere o cabeçalho e o CRC-32 de cada banca e salta pro
   início do programa da banca válida de maior versão (seção 5).
6. No início do programa (`0x1000` nas plataformas sem bancas, `0x1100` na
   banca A da `de0-cv`) está o `_start` do `crt0` da picolibc, dentro da imagem do
   teste: ajusta `sp` e `gp`, copia `.data` de FLASH pra RAM, zera
   `.bss`, prepara o TLS e chama `main`, ver
   [boot.md](boot.md).
7. Ao terminar, o teste escreve o `tohost` (`RV32_PASS()`/`RV32_FAIL(código)`
   em `rv32_test.h`, ou o retorno de `main` via `_exit`) e chama
   `rv32_wait_restart`, voltando ao passo 3.

O contato entre a BOOT_MEMORY e a FLASH é o salto do passo 5 (BOOT_MEMORY
para a FLASH) e o salto do passo 7 (programa para `0x100`). Nas
plataformas sem bancas a BOOT_MEMORY não lê nada da FLASH. Na `de0-cv` ela
lê o cabeçalho e a carga das duas bancas para conferir os CRC-32 antes
do salto.

## 2. Por que a BOOT_MEMORY nunca é reescrita por teste

`_reset` e `rv32_wait_restart` são endereços fixos (`0x0`, `0x100`,
ver `src/simulation/internal-mem/runtime/boot_memory.ld`), resolvidos no link **único e separado** de
`src/simulation/internal-mem/runtime/boot_memory.S`, não no link de cada teste. Se BOOT_MEMORY fosse
reescrita por teste como FLASH é, cada nova compilação poderia mover
esses offsets, e todo teste que já tem esses mesmos endereços fixos
embutidos no próprio binário (via `--defsym=rv32_wait_restart=0x100`
em `rv32im-fpga.specs`) ficaria chamando um endereço errado sem nenhum
erro de link avisando, já que os dois lados são compilados e
linkados completamente separados. Manter BOOT_MEMORY congelada depois da
programação inicial é isso: sem ela fixa, não haveria endereço estável
pro handoff funcionar.

A escolha da banca pelo cabeçalho (seção 5) entra na BOOT_MEMORY da `de0-cv` numa única regravação, junto do bitstream de uma compilação completa do Quartus. Depois dela a BOOT_MEMORY volta a ficar congelada, e é por isso que a política cabe inteira nela: a atualização em campo só troca o conteúdo das bancas.

`rv32_wait_restart` também não pode ficar em FLASH: é nele que o core
espera enquanto o host reescreve a FLASH, então ele precisa estar numa
memória que ninguém reescreve, senão o core executaria instruções de uma
memória em reescrita.

## 3. O que a BOOT_MEMORY e o programa combinam

`src/simulation/internal-mem/runtime/boot_memory.S` é compilado e linkado **antes** de qualquer teste
existir: seu binário não pode conter nada de um teste específico. Esse é o
problema que qualquer atualização remota de firmware enfrenta: um bootloader
fixo, que não pode ser regravado remotamente (o risco de travar o dispositivo
pra sempre é alto demais), recebendo uma imagem de aplicação que pode. Os
dois lados precisam concordar de antemão sobre o mínimo, e aqui esse
mínimo é:

| Combinado | Valor | Quem usa |
| :--- | :--- | :--- |
| Entrada do programa | `0x1000`, o `_start` da picolibc (o `picolibc.ld` põe `.init` no começo da FLASH); na `de0-cv`, `0x1100` ou `0x20100`, o início do programa de cada banca | BOOT_MEMORY salta pra lá |
| `rv32_wait_restart` | `0x100` | o programa salta pra lá ao terminar |
| Palavras do topo da RAM | `fromhost` `0x2FFF0`, `tohost` `0x2FFE8`, cabeçalho do `stdout` `0x2FBE0` (gerados do `platform.yaml` em `memory_map.h`) | BOOT_MEMORY as zera, o programa e o host as usam |

Tudo o mais (onde ficam `.data`, `.bss`, heap e pilha, o tamanho de cada
seção) é decidido no link de cada teste pelo linker script da toolchain, a
partir dos endereços de `rv32im-fpga.specs`; a BOOT_MEMORY não sabe de nada
disso, porque quem copia o `.data` e zera o `.bss` é o `crt0` do próprio
programa. Por isso a imagem de um teste carrega tudo o que varia nela.

O estágio MEM deste core tem, de fato, um caminho de leitura até FLASH
(a porta B da FLASH, ver
[memoria.md](memoria.md#12-flash-o-firmware-de-cada-teste)):
é assim que o `crt0` lê o `.data` inicial da FLASH pra copiá-lo pra RAM, e
é assim que `.rodata` consegue ficar residente em FLASH (nunca copiado pra
RAM, ver [memoria.md](memoria.md)).

Nas plataformas sem bancas nada verifica a integridade da imagem antes de
saltar pra ela, porque o JTAG é um link local, físico e confiável. Na `de0-cv`
a BOOT_MEMORY confere a magia, os dois CRC-32 e o tamanho de cada banca (seção 5),
como um sistema que recebe atualizações por um link não confiável precisa fazer.
Uma assinatura continua fora do escopo: o CRC-32 detecta imagem interrompida ou
corrompida, não imagem forjada.

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

Cada banca começa por uma página de cabeçalho de 256 bytes (magia, tamanho, CRC-32 da carga, versão e CRC do cabeçalho; o formato está no módulo `flash_image` do Tools), e o programa vem logo depois. A rotina de atualização grava a carga primeiro e o cabeçalho por último, então um cabeçalho válido indica uma banca cuja atualização terminou. A memória de boot confere o cabeçalho e o CRC-32 da carga de cada banca e salta para a válida de maior versão, com a banca A vencendo um empate e a espera no `rv32_wait_restart` quando nenhuma vale. A política e o custo da conferência estão no [contrato de entrada](contrato-de-entrada.md), seção 6.6.

O `make generate` escreve, a partir das bancas, os arquivos abaixo.

| Arquivo | Conteúdo |
| :--- | :--- |
| `runtime/rv32im-fpga-bank-a.specs` e `runtime/rv32im-fpga-bank-b.specs` | Flags do linker de um programa para cada banca, com `__flash` no início do programa e `__flash_size` sem a página do cabeçalho |
| `runtime/flash_banks.h` | Magia da imagem, tamanho da página do cabeçalho e, de cada banca, `RV32_BANK_<NOME>_BASE`, `_SIZE` e `_ENTRY`, para a memória de boot e para a rotina de atualização |

Um programa para a banca B compila com `--specs` apontando para o arquivo de specs dela, e `riscv-tools flash-image pack programa.bin --output imagem.bin --version N --platform src/cyclone-v/de0-cv/platform.yaml --bank B` monta a imagem e confere que cabe. O `riscv-tools check-memory-map` valida as bancas (alinhadas ao setor de 4 KiB, dentro da FLASH, sem sobreposição).

## 6. O protocolo de atualização no firmware

O hospedeiro empacota o programa com `riscv-tools flash-image pack` e o envia pela UART sobre JTAG com `riscv-tools flash-image send imagem.bin --config <config>`; `flash-image verify` confere uma imagem sem enviá-la. O fluxo da UART é a imagem sem enquadramento, a página de cabeçalho de 256 bytes primeiro e depois tantos bytes de carga quanto o campo de tamanho do cabeçalho diz. O firmware de uma banca recebe a imagem e atualiza a outra banca em seis passos.

| Passo | O que acontece |
| :--- | :--- |
| 1 | Lê os 256 bytes do cabeçalho e confere a magia, o CRC-32 do cabeçalho e o tamanho, antes de guardar a carga |
| 2 | Lê a carga, tantos bytes quanto o cabeçalho diz, e confere o CRC-32 dela. Um fluxo cortado ou danificado para aqui, sem tocar na FLASH |
| 3 | Copia a rotina de atualização para a SDRAM e executa `fence.i`, porque o código que apaga a FLASH não deve depender de uma região dela |
| 4 | Para cada setor da banca de destino, habilita a escrita, apaga e espera o chip ficar livre |
| 5 | Grava as páginas da carga, uma de 256 bytes por vez pelo buffer do controlador, e por último a página do cabeçalho |
| 6 | Lê a banca de volta, compara com a imagem recebida e reinicia pela BOOT_MEMORY, que escolhe a imagem de maior versão |

O controlador de FLASH ([flash_controller](https://github.com/insper-riscv/Peripherals/blob/main/docs/pt-br/flash-controller/flash_controller.md)) fica no periférico `FLASH_CTRL` do `platform.yaml`, e a rotina lê o estado do chip a cada comando porque o chip ignora um comando que chega ocupado. Uma recusa do chip (setor protegido, endereço fora da janela) encerra a rotina com um código de erro. As caches recebem do chip o pulso de invalidação da região alterada, então a leitura de volta já vê a FLASH nova.

Uma atualização interrompida antes do passo 5 terminar deixa o cabeçalho da banca apagado, e a BOOT_MEMORY ignora a banca. O firmware pode simular esse corte com a opção de não gravar o cabeçalho, que é o que o teste de atualização interrompida usa.

## 7. Os testes

| Teste | Onde | O que prova |
| :--- | :--- | :--- |
| Escolha da banca | `tests/python/unittests/rtl/de0_cv_boot_banks.py`, entrada `De0CvBootBanks` | Com a `boot_memory.S` real, a banca mais nova roda, uma carga corrompida ou um cabeçalho apagado, adulterado ou com tamanho absurdo faz a BOOT_MEMORY voltar para a outra banca, e sem banca válida o núcleo fica no `rv32_wait_restart`. Os registradores `a0` e `a1` chegam em `0` |
| Troca pelo carregador | `tests/python/unittests/rtl/external_data_flash_update.py`, entrada `ExternalDataFlashUpdate` | A sequência da seção 6.2 do contrato: parada, gravação pelo STREAM, conferência da soma, liberação, e o programa novo rodando depois do `_reset`, que zerou `tohost` |
| Atualização completa | `c-sdram-update/flash-update` do repositório Tests | O programa da banca A recebe a imagem da banca B, atualiza, reinicia e a BOOT_MEMORY executa a banca B |
| Atualização interrompida | `c-sdram-update/flash-update-interrupted` | O cabeçalho da banca B não é gravado e a BOOT_MEMORY volta para a banca A |

Os programas de atualização rodam no topo de simulação da `de0-cv` com `HAS_FLASH_CONTROLLER`, que acrescenta o controlador, o armazenamento de duas portas e o chip de comandos, com as esperas de apagar e de gravar nos genéricos `FLASH_ERASE_LATENCY` e `FLASH_PROGRAM_LATENCY`. O repositório Tests os roda com um chip rápido e com um lento.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
