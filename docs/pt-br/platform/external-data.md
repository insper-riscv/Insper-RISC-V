# Plataforma `external-data`: a FLASH de duas portas na FPGA e a SDRAM atrás da cache de dados

## 1. O que ela é

O núcleo guarda a BOOT_ROM e a FLASH, e só a RAM fica fora dele. A FLASH é uma só cópia de uma memória de duas portas verdadeiras na FPGA, a mesma da [internal-mem](internal-mem.md), e a RAM é a SDRAM da placa, alcançada por uma cache de dados write-through. Não há cache de instruções nem chip de FLASH, porque a busca de instruções lê a FLASH direto.

```
                     núcleo
        busca (IF)             estágio MEM
            |                   |        |
      porta A              porta B      cache de dados
            |                   |        (write-through)
            |        carregador de FLASH     |
            |     (porta B livre só com      |
            |        o núcleo parado)        |
            +--------- FLASH ---------+      |
                 (uma só cópia)        SDRAM (ponte, árbitro, controlador)
```

## 2. Mapa de memória

| Região | Base | Tamanho | Acesso |
| :--- | :--- | :--- | :--- |
| BOOT_ROM | `0x00000000` | 4 KiB | Busca e leitura, direto |
| FLASH | `0x00001000` | 252 KiB de janela, até `0x00040000` | Busca pela porta A e leitura de dado pela porta B, somente leitura para o núcleo |
| SDRAM | `0x40000000` | 64 MB | Leitura e escrita de dado pela cache de dados; não há busca de instruções |
| Periféricos | `0x80000000` | janelas de 256 MB | Leitura e escrita, sem cache |

Como a busca de instruções não alcança a SDRAM, nenhum código roda a partir dela. Os 4 KB do topo da SDRAM guardam as palavras que o hospedeiro escreve por trás da cache (`tohost`, `fromhost` e o buffer de `stdout`), e a cache de dados as ignora.

## 3. Comportamento

1. **FLASH.** A porta A é lida pelo estágio de busca e a porta B pelo estágio MEM, quando um load cai na região da FLASH. As duas leituras são do mesmo bloco, sem segunda cópia.
2. **Regravação.** O hospedeiro escreve a FLASH pelo carregador do repositório Memory, que fala com o Virtual JTAG (instância 0). O carregador para o núcleo, escreve a imagem pela porta B, confere a contagem e a soma de verificação e libera o núcleo, que reinicia pela BOOT_ROM. Com o núcleo em execução a porta B é do estágio MEM, e a escrita é recusada em hardware.
3. **SDRAM.** O hospedeiro lê e escreve a SDRAM pela porta de depuração, que é um segundo mestre do controlador (instância 3 do Virtual JTAG). A UART via JTAG e o display usam as instâncias 1 e 2.
4. **Reinício.** A BOOT_ROM executa `fence.i` antes de saltar para a FLASH, e a instrução esvazia a cache de dados.
5. **Acesso desalinhado.** Um load que cruza duas palavras da FLASH (Zicclsm) não conclui nesta plataforma; o mesmo acesso na SDRAM, na BOOT_ROM e em palavra alinhada da FLASH funciona.
6. **Trap e carregador.** O `LEDR1` acende quando o núcleo pulsa `o_trap` e o `LEDR2` acende enquanto o carregador mantém o núcleo parado.

## 4. Tamanhos

| Item | Valor |
| :--- | :--- |
| Armazenamento da FLASH | 256 KB, o que o decodificador de busca exige (ele não subtrai a base da FLASH) |
| Cache de dados | 4 KiB, linhas de 16 bytes, mapeamento direto |
| Imagem inicial | `init.mif` (FLASH) e `boot_rom_init.mif` (BOOT_ROM) |

## 5. Como rodar

| Objetivo | Comando |
| :--- | :--- |
| Compilar a placa | `quartus_sh -t src/cyclone-v/external-data/external-data_synth.tcl` |
| Programar a placa | `src/cyclone-v/external-data/external-data_program.sh`, no mesmo shell da compilação (`&&`) |
| Simulação dos programas | `riscv-tools --config tools/riscv_build/config.sdram-external-data.yaml compile --emit hex`, depois `sim` (no repositório Tests) |
| Programas na placa | `riscv-tools --config tools/riscv_build/config.sdram-external-data.yaml run --skip-reconfigure --skip-recompile` |
| Teste do topo de simulação | `make test TEST=ExternalDataSimTop` |

O `platform.yaml` é a única fonte do mapa, e o `make generate` escreve dele o pacote `external_data_map_pkg.vhd`, as flags de ligação, o linker script da BOOT_ROM e o `memory_map.h`. O `config.yaml` guarda `quartus.sdram_debug_instance`, o índice do Virtual JTAG da porta de depuração da SDRAM, que o `riscv-tools` passa ao script da porta.

## 6. Teste do topo de simulação

A entrada `ExternalDataSimTop` do `tests/python/tests.json` roda o topo `rv32im_external_data_sim_test` com um programa mínimo. A BOOT_ROM guarda uma marca na SDRAM e salta para a FLASH. A FLASH guarda outra marca, lê como dado uma palavra que ela mesma guarda, copia essa palavra para a SDRAM, escreve no display, guarda a terceira marca e escreve em `tohost`. O teste lê a SDRAM pela porta de depuração do chip e confere as marcas, a palavra lida da FLASH, o `tohost` e o valor do display. As imagens saem de `tests/python/gen_external_data_images.py`.

## 7. Medidas da compilação

Cyclone V 5CEBA4F23, Quartus Prime 25.1 Lite, modo `HIGH PERFORMANCE EFFORT` e semente 5.

| Recurso | Uso |
| :--- | :--- |
| ALMs | 8227 de 18480 (45 %) |
| Registradores | 8480 |
| Blocos de RAM M10K | 234 de 308 (76 %) |
| Fmax do domínio do núcleo (modelo lento a 85 °C) | 63,54 MHz |
| Folga de setup no núcleo | -0,204 ns |

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
