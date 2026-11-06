# A placa rodava a memória de boot de outra plataforma e os testes pareciam passar

## 1. Resumo

A plataforma `sdram` guardava como imagem da memória de boot uma cópia da imagem da `internal-mem`.
O fluxo de execução do `riscv-tools` não recompila a memória de boot a cada rodada: ele grava no
bitstream o que está no arquivo do projeto. A placa passou a rodar uma memória de boot que limpa os
endereços da RAM interna, que a plataforma nova não tem mais.

| | |
| :--- | :--- |
| Sintoma | todos os programas terminavam como PASS em cerca de dois segundos, e os programas com golden falhavam na comparação |
| Causa | a imagem da memória de boot do projeto era a da outra plataforma, com os endereços do mailbox e do `go flag` da RAM interna |
| Correção | a imagem do projeto é a da memória de boot da plataforma, gerada pelo comando `program` |
| Defesa adicionada | o host zera o mailbox antes de cada teste (ver `docs/bugs` do Tools), então uma memória de boot errado já não produz PASS falso |

## 2. O mecanismo

A memória de boot de cada plataforma faz duas coisas: limpa as palavras que o host e o programa
compartilham (mailbox, `go flag`, `tohost`, `fromhost`, cabeçalho do `stdout`) e fica parado
até o host acionar o `go flag`. Os endereços dessas palavras estão dentro do código.

| Plataforma | Fim da RAM | Mailbox |
| :--- | :--- | :--- |
| `internal-mem` | `0x00030000` | `0x0002FFFC` |
| `sdram` | `0x44000000` | `0x43FFFFFC` |

Com a imagem da outra plataforma, a memória de boot escrevia zeros no mailbox antigo, que na
plataforma nova não é memória, e deixava intacto o mailbox da SDRAM. O resultado de um teste
ficava lá quando o teste seguinte começava, e o host lia aquele PASS no primeiro acesso.

## 3. Por que passou despercebido

Os testes sem golden (de unidade) terminavam todos como PASS, porque só o mailbox os julga.
Os testes com golden mostravam a divergência, mas num lote que tinha sido interrompido e
retomado a partir do arquivo de progresso: as primeiras dezenas de resultados eram do lote
interrompido. Foi a soma de "tudo passa em tempo igual" com "o golden discorda do PASS" que
levantou a suspeita.

## 4. A correção

A imagem `boot_memory_init.mif` da plataforma é gerada do `boot_memory.S` dela pelo comando
`riscv-tools program`, que monta a memória de boot, grava o arquivo no projeto, compila e programa a
placa. O arquivo versionado agora é o da plataforma.

## 5. Como evitar

Toda plataforma tem a sua própria imagem de memória de boot, e ela deve ser regenerada sempre que
o `boot_memory.S` ou o mapa de memória mudar. O comando `run` não faz isso. Um lote de
testes deve começar de um arquivo de progresso limpo depois de qualquer interrupção.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
