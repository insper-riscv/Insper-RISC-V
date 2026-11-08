# Identificação da placa pelo JTAG

## 1. Objetivo

O `riscv-tools` descobre qual placa está ligada ao host, escolhe a placa certa para a plataforma, a trava para uso exclusivo e programa pelo cabo certo. O IDCODE, o cabo e a trava não se escrevem em nenhum `config.yaml`: o dado da placa está no `board.yaml` ([formato.md](formato.md)), e o resto vem do que o host enxerga. A referência dos comandos é o módulo `board` do Tools.

## 2. O que identifica uma placa

Quatro fontes de identidade existem, e duas servem.

| Fonte | Estabilidade | Distingue duas placas iguais? | Uso |
| :--- | :--- | :--- | :--- |
| IDCODE do FPGA na cadeia, sem os 4 bits de versão | Fixa | Não | Identifica o dispositivo e as placas candidatas |
| Nome do cabo (`USB-Blaster [1-2]`) | Muda ao reconectar | Só durante a sessão | Argumento `-c` do `quartus_pgm`, nunca chave |
| Número de série USB | Fixo | Não, o mesmo valor aparece em vários cabos | Descartado |
| Caminho estável da porta USB (`ID_PATH` do udev) | Fixo enquanto o cabo ficar na mesma porta | Sim | Chave de desambiguação |

A placa é o par formado pelo dispositivo (IDCODE) e pela porta USB. O IDCODE diz o que a placa pode ser, e a porta diz qual das candidatas é.

## 3. Algoritmo

1. O `jtagconfig` lista os cabos e a cadeia de cada um.
2. O nome `[bus-porta]` de cada cabo vira o caminho de porta do sistema, e o `ID_PATH` do udev é lido.
3. Cada IDCODE é comparado com `jtag.chain` do `board.yaml` de todas as placas conhecidas, o que dá as candidatas por cabo.
4. O inventário do host liga o caminho da porta a uma placa e fixa a escolha.
5. Sem entrada no inventário, uma só candidata é a escolha, e mais de uma é ambiguidade.

A escolha entre candidatas nunca segue a ordem de listagem do `jtagconfig`.

## 4. Inventário do host

O inventário é `~/.config/riscv-tools/boards.yaml`, ou `/etc/riscv-tools/boards.yaml`, e o primeiro que existe vale.

```yaml
host: ws
lock_dir: /tmp
boards:
- {id: de0-cv-ws, board: de0-cv, usb_path: "pci-0000:00:14.0-usb-0:2"}
- {id: de2-115-ws, board: de2-115, usb_path: "pci-0000:00:14.0-usb-0:3"}
```

O comando `riscv-tools board scan --save` grava os cabos que identifica, e um cabo com várias candidatas pede `--assign PORTA=PLACA`.

## 5. Casos de ambiguidade

| # | Caso | Resolução |
| :--- | :--- | :--- |
| 1 | Um cabo, uma candidata | Escolhida |
| 2 | Duas placas iguais no mesmo host | O inventário desempata; sem ele, erro com a lista de cabos |
| 3 | Placas iguais em hosts diferentes | Cada host tem o seu inventário, e o `id` leva o nome do host |
| 4 | Mesmo IDCODE de dispositivos diferentes (`020F70DD` serve ao 10CL120, ao EP3C120 e ao EP4CE115) | As candidatas são todas as placas que citam o IDCODE |
| 5 | Mesmo dispositivo em placas diferentes | O inventário, ou `--board`, desempata |
| 6 | Revisões do mesmo dispositivo (`031050DD` não separa `10M50DA` de `10M50DC`) | A placa declara `device`, e o Tools avisa que o IDCODE não prova a variante |
| 7 | IDCODE desconhecido | Erro com os IDCODEs procurados e os cabos vistos |
| 8 | Cadeia quebrada | Erro de infraestrutura; só desligar e ligar a placa resolve |
| 9 | Cabo ocupado | A trava recusa e mostra o dono; `--wait` espera |

## 6. Seleção na linha de comando

Da fonte mais forte para a mais fraca vale `--cable`, `--board-id`, `--board`, o campo `board` do `platform.yaml` e `auto`.

| Forma | Efeito |
| :--- | :--- |
| `board: auto` | Escolhe entre as placas de `boards` presentes e livres |
| `board: <nome>` ou `--board <nome>` | Fixa a placa; a cadeia ainda é conferida contra o `board.yaml` (regra V17) |
| `--board-id <id>` | Escolhe uma entrada do inventário |
| `--cable "<nome>"` | Força o cabo e dispensa o inventário |

## 7. Trava por placa

Cada placa tem um arquivo de trava, tomado com `flock` exclusivo durante a sessão inteira, nomeado pelo identificador da placa sem hífens mais o host (`de0cv-ws.lock`). O dono grava host, usuário, processo, comando e instante, e quem encontra a placa ocupada lê esse registro. Sem `--wait`, a trava falha na hora; com `--wait`, espera até 4 horas.

## 8. Placas sem USB-Blaster padrão

| Placa | Cabo | Tratamento |
| :--- | :--- | :--- |
| `de10-nano` | USB-Blaster II (`DE-SoC [USB-1]`), IDs USB `09fb:6010` antes da carga do firmware e `09fb:6810` depois | A cadeia tem o HPS (`4BA00477`) e o FPGA (`02D020DD`), e o FPGA é o item `@2`; o `doctor` avisa do firmware ainda não carregado e sugere remover o HPS da cadeia no programador diante do erro 209025, sem aplicar nada |
| `de0-nano-soc` | O mesmo da `de10-nano` | Distingue-se pelo IDCODE do FPGA (`02D010DD`) |
| `mkr-vidor-4000` | A USB liga só ao SAMD21 (`2341:8056`) | O `board scan` reconhece a placa pelo ID USB, e o `doctor` diz que falta o sketch `USBBlaster` no SAMD21, que as ferramentas nunca gravam |

O `board scan` lista também as placas que a USB mostra sem cadeia legível. A regra lê os IDs de `jtag.usb` de cada pacote, e por isso uma placa nova com cabo próprio não pede código. O ID do USB-Blaster comum (`09fb:6001`) não nomeia placa.

## 9. Sem placa

| Comando | Sem placa ligada |
| :--- | :--- |
| `platform sync`, `board generate`, simulação e `check-*` | Funcionam, sem JTAG |
| `program --compile-only` com `board: auto` | Erro com a lista de placas compatíveis e o pedido de `--board`; com a placa nomeada, compila |
| `program`, `run` e a certificação em placa | Erro `no board found`, com os IDCODEs procurados |

O subcomando `board doctor` verifica cabo, cadeia, processos que usam o cabo e as placas especiais, e imprime o que falta sem alterar nada. Os subcomandos `board scan`, `board select` e `board lock` estão descritos no módulo `board` do [Tools](https://github.com/insper-riscv/Tools).

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
