# Arquitetura de memória: BOOT_ROM + FLASH + RAM (Harvard modificado)

Este documento descreve a memória da plataforma `internal-mem`. A da `de0-cv`, com a FLASH e a SDRAM atrás das caches, está em [de0-cv.md](de0-cv.md).

## Resumo

O core (`rv32im_pipeline_core`) modela a hierarquia de memória de uma SoC de
verdade com **3 papéis lógicos**, implementados em **3 instâncias físicas**
de memória:

| Papel     | Instância física | Reescrita via JTAG?          | Quem acessa                    |
|-----------|------------------|-------------------------------|---------------------------------|
| BOOT_ROM  | `BOOT_ROM`       | Não: só no compile inicial   | Só busca de instrução (IF)     |
| FLASH     | `FLASH`          | Sim: a cada troca de teste, pelo carregador JTAG | Porta A: IF. Porta B: MEM e carregador |
| RAM       | `RAM`            | Não (JTAG só lê/escreve dado) | IF nunca. MEM sempre.          |

Isso é chamado de **"Harvard modificado"**: um Harvard "de verdade" teria
barramentos de instrução e dado totalmente independentes, sem nenhuma
sobreposição. Aqui, IF busca instrução de BOOT_ROM/FLASH (nunca de RAM), e o
estágio MEM (load/store) só toca RAM, **exceto** por uma abertura
deliberada: o estágio MEM também consegue ler a FLASH pela porta B dela, só
para o bootloader copiar `.data` de FLASH pra RAM no boot. Essa é a única
exceção à separação instrução/dado: ver
[FLASH: o "firmware" de cada teste](#12-flash-o-firmware-de-cada-teste)
abaixo.

## 1. Os três papéis, em detalhe

### 1.1. BOOT_ROM: bootloader fixo

Programado **uma única vez**, como parte do compile completo inicial do
Quartus (`quartus_sh --flow compile` + `quartus_pgm`); nunca reescrito via
JTAG depois disso, diferente de FLASH. Contém `boot_rom.S`
(`src/simulation/internal-mem/runtime/boot_rom.S`): o vetor de reset, que limpa
tohost/fromhost e o cabeçalho do `stdout` e salta pra
FLASH, e o loop de espera/restart (`rv32_wait_restart`) que deixa
`riscv-tools run` trocar de teste sem reprogramar a FPGA inteira; ver
[atualizacao-de-programa.md](atualizacao-de-programa.md) pro fluxo
completo dessa troca.

É genérico de propósito e não sabe nada de um teste: o `crt0` da picolibc,
dentro da imagem de cada teste (começando em `0x1000`), copia o `.data`,
zera o `.bss` e chama `main`; o que a BOOT_ROM e o programa combinam é só
o ponto de entrada, o endereço do `rv32_wait_restart` e as palavras do topo
da RAM. Ver [runtime.md](runtime.md) e
[atualizacao-de-programa.md](atualizacao-de-programa.md).

### 1.2. FLASH: o "firmware" de cada teste

O programa de verdade de cada teste (`.init` + `.text` + `.rodata`, mais a imagem inicial de `.data`), reescrito
pelo carregador JTAG (`flash_loader`, do Memory) toda vez que um teste troca;
mesmo papel que a antiga `ROM` tinha antes do redesign. Fisicamente é uma
`altsyncram` de duas portas verdadeiras (não uma flash de verdade), **uma só cópia**,
mas architeturalmente representa o armazenamento não-volátil: só é regravada
explicitamente entre execuções, nunca pela CPU em tempo de execução.

A porta A é a busca de instrução (IF) e a porta B é a leitura de dado do estágio
MEM, que o loop de cópia de `.data` de `boot_rom.S` usa (`lw a0, 0(t1)`, onde `t1`
aponta pra dentro de FLASH, o LMA de `.data`). O carregador para o core (a saída
de parada dele entra no `core_reset`), escreve a imagem pela porta B e solta o core,
que reinicia pela BOOT_ROM; com o core em execução a escrita é forçada a `'0'` em
hardware, e o core só lê. O protocolo está na documentação do Memory (`flash_loader`),
e o host escolhe esse caminho com `quartus.rom_write_method: jtag_loader`.

### 1.3. RAM: dado de verdade

`.data`/`.sdata`/`.sbss`/`.bss`/pilha/heap. A única memória que o estágio
MEM (load/store) sempre alcança para escrita; `.rodata` (constantes
grandes) fica residente em FLASH, nunca copiado pra cá, ver "FLASH: o
firmware de cada teste" acima. Os últimos 1056 bytes do espaço
físico da IP são reservados (fora do `__ram_size` que `rv32im-fpga.specs`
dá ao teste) para: tohost/fromhost (4
palavras, convenção HTIF, com 2 palavras livres) e o buffer do `stdout`
(1032 bytes, ver [runtime.md](runtime.md)).

## 2. Mapa de memória

| Região                | Base         | Tamanho          | Words  | widthad |
|------------------------|--------------|------------------|--------|---------|
| BOOT_ROM               | `0x00000000` | 4K               | 1024   | 10      |
| FLASH                  | `0x00001000` | 28K              | 7168   | 13      |
| RAM (espaço físico)    | `0x00008000` | 160K             | 40960  | 16      |
| RAM (útil, `rv32im-fpga.specs`) | `0x00008000` | 160K − 24 − 1032 bytes | N/A | N/A |
| `stdout` (cabeçalho e dados) | `0x0002FBE0` | 1032 bytes | N/A | N/A |
| fromhost               | `0x0002FFF0` | 2 palavras       | N/A      | N/A       |
| tohost                 | `0x0002FFE8` | 2 palavras       | N/A      | N/A       |
| `__stack` (sp inicial) | `0x0002FBE0` | N/A                | N/A      | N/A       |

A FLASH ocupa `0x00001000` a `0x00008000` (**28K**), onde começa a RAM. O topo da RAM (`ram_base + ram_words*4 = 0x30000`) e a base precisam cair em múltiplos de 4096 bytes, porque o boot ROM monta o fim da RAM com `lui t0, 0x30` (sem `addi` depois), e o `lui` só zera os 12 bits baixos. Como a FLASH começa em `0x1000`, o fim dela tem de ser múltiplo de 4096 também:

$$0x1000 + \text{FLASH\_SIZE} \equiv 0 \pmod{4096}$$

Isso exige que `FLASH_SIZE` seja múltiplo de 4096, e 28K ($7 \times 4096 = 28672$) serve e termina exatamente na base da RAM.

### 2.1. O limite de blocos de RAM

A Cyclone V 5CEBA4F23 tem 308 blocos M10K de 10 Kbit, um limite de quantidade de blocos além do de bits totais. O relatório do Fitter do mapa atual registra o uso abaixo, 288 blocos (94 % do teto).

| Memória | Blocos M10K |
| :--- | ---: |
| `BOOT_ROM` | 4 |
| `FLASH` | 28 |
| `RAM` | 256 |
| **Total** | **288 de 308** |

## 3. Índices JTAG (`config.yaml: quartus:`)

Só a `RAM` declara `ENABLE_RUNTIME_MOD`, então ela é a única instância do In-System
Memory Content Editor e tem o índice 0 (`quartus.ram_mem_instance`; `tohost` e
`fromhost` moram dentro da RAM, então compartilham o índice dela). A `BOOT_ROM` é
gravada só no compile inicial, e a `FLASH`, regravada pelo carregador, não tem índice
(`quartus.rom_mem_instances: []`).

## 4. LEDs (`core_fpga_test.vhd`)

| LED     | Sinal              | Significado                                                        |
|---------|--------------------|----------------------------------------------------------------------|
| o_ledr(0) | `Blinky`           | Pisca direto do `i_clock_50`, sem relação com o core, "placa viva".  |
| o_ledr(1) | `pll_locked`       | Deveria ficar **sempre aceso** depois de configurar a FPGA. Apagado = PLL nunca travou. |
| o_ledr(2) | `i_fpga_reset_n`     | Aceso = botão físico de reset **solto**. Apagado = botão pressionado. |
| o_ledr(3) | `not core_reset`   | Aceso = core fora de reset, rodando. Apagado = core em reset (PLL sem lock, ou botão pressionado). |
| o_ledr(4) | `flash_halt`       | Aceso = core parado pelo carregador da FLASH (reset mantido enquanto a imagem é gravada). |
| o_ledr(5-9) | (não usados)     | Livres: usados como latches de debug temporários durante o bring-up da placa, removidos depois de servirem seu propósito. |

Como diagnóstico rápido sem precisar abrir uma sessão JTAG: se o_ledr(1) ou
o_ledr(3) estiverem apagados, o problema está **antes** do core (PLL/reset);
nenhum teste vai rodar. Se ambos estão acesos e mesmo assim um teste não
passa, o problema está no software/lógica do core, não na configuração da
placa.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
