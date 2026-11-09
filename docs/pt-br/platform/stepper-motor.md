# Motor de passos 28BYJ-48 na DE0-CV

🌐 [Português](../../pt-br/platform/stepper-motor.md) · [English](../../en/platform/stepper-motor.md)

## 1. Arquitetura

A plataforma `internal-mem` expõe um GPIO de quatro bits em `0x90000000`. A CPU escreve a sequência das bobinas nesse periférico, e os quatro pinos comandam as entradas do ULN2003. A FPGA não alimenta nem aciona diretamente as bobinas do motor.

A UART física permanece em `0xC0000000` e nos pinos já usados do GPIO_0. Os dois periféricos ocupam janelas diferentes e podem ser usados pelo mesmo programa.

| Periférico | Base | Janela |
| :--- | :--- | ---: |
| GPIO do motor | `0x90000000` | 1 |
| UART física | `0xC0000000` | 4 |

## 2. Ligação elétrica

O ULN2003 recebe os sinais lógicos de 3,3 V da FPGA e comuta a alimentação de 5 V das bobinas. O terra da placa e o terra do driver são comuns.

| JP2 | Sinal da placa | Pino FPGA | ULN2003 |
| ---: | :--- | :--- | :--- |
| 1 | `GPIO_1[0]` | H16 | IN1 |
| 2 | `GPIO_1[1]` | A12 | IN2 |
| 3 | `GPIO_1[2]` | H15 | IN3 |
| 4 | `GPIO_1[3]` | B12 | IN4 |
| 11 | VCC5 | alimentação | `+` |
| 12 | GND | terra | `-` |

Os pinos M16 e C16 do GPIO_0 continuam reservados, respectivamente, à recepção e à transmissão da UART.

Nunca ligue VCC5 a um pino de E/S da FPGA. O motor conecta ao soquete do ULN2003, e os pinos H16, A12, H15 e B12 conectam somente às entradas lógicas IN1 a IN4. Desligue a placa antes de alterar a fiação.

## 3. Registradores

O periférico é o bloco GPIO de quatro bits. Os deslocamentos são endereços de byte a partir de `RV32_MOTOR_BASE`.

| Deslocamento | Registrador | Uso pelo programa |
| :--- | :--- | :--- |
| `0x00` | `DIR` | Escreve `0xF` para habilitar IN1 a IN4 como saídas |
| `0x04` | `OUT_LOAD` | Carrega simultaneamente os quatro sinais |
| `0x08` | `OUT_SET` | Liga os bits escritos com 1 |
| `0x0C` | `OUT_CLR` | Limpa os bits escritos com 1 |
| `0x10` | `OUT_TGL` | Inverte os bits escritos com 1 |
| `0x24` | `PINS` | Lê os pinos depois do sincronizador |

No reset, os quatro pinos começam como entradas. O programa carrega zero em `OUT_LOAD` antes de escrever `0xF` em `DIR`, o que evita habilitar uma combinação antiga ao mudar a direção.

## 4. Sequência de meio passo

O bit 0 comanda IN1, e o bit 3 comanda IN4. O sentido direto usa a sequência abaixo; o sentido inverso percorre a mesma sequência ao contrário.

| Índice | IN4..IN1 | Hexadecimal |
| ---: | :---: | :---: |
| 0 | `0001` | `0x1` |
| 1 | `0011` | `0x3` |
| 2 | `0010` | `0x2` |
| 3 | `0110` | `0x6` |
| 4 | `0100` | `0x4` |
| 5 | `1100` | `0xC` |
| 6 | `1000` | `0x8` |
| 7 | `1001` | `0x9` |

O programa `stepper-motor` começa com um autoteste curto que escreve e lê de volta os oito estados. Depois, mantém cada estado do movimento por 100.000 ciclos do núcleo de 50 MHz, equivalentes a 2 ms. Ele executa 1024 meios passos em cada sentido, com uma pausa de 250 ms entre eles, e grava zero no final. A redução mecânica varia entre versões do 28BYJ-48, então a quantidade exata de passos por volta deve ser medida no conjunto usado.

## 5. Verificação

A simulação confere nos quatro pinos do topo a sequência produzida pelo autoteste. O teste físico confirma o movimento, o sentido e a ligação das bobinas. O autoteste dura somente alguns microssegundos e não causa deslocamento mecânico relevante antes do movimento temporizado.

```bash
cd ~/PFE/Stepper-Motor/Tests
export PATH="$HOME/.local/opt/insper-riscv32-elf/bin:$HOME/.local/opt/insper-spike/bin:$PATH"
riscv-tools --config tools/riscv_build/config.stepper-motor.yaml generate-header
riscv-tools --config tools/riscv_build/config.stepper-motor.yaml compile --emit mif
riscv-tools --config tools/riscv_build/config.stepper-motor.yaml program build-stepper/real/stepper-motor.mif
```

Depois da programação, o motor gira aproximadamente um quarto de volta, pausa, retorna e fica desenergizado. Se ele apenas vibrar, confira a ordem IN1 a IN4. Se o sentido observado estiver invertido, a ligação está funcional e os nomes dos sentidos podem ser trocados no software.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
