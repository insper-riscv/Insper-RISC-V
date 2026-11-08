# Arquitetura multi-FPGA

## 1. Camadas

O projeto tem três camadas. A de cima não conhece a de baixo, e cada ligação entre camadas é um contrato de interface com portas, handshake e latência definidos.

| Camada | Conteúdo | Quem a escreve | Conhece placa? |
| :--- | :--- | :--- | :--- |
| 1. SoC | Núcleo, caches, roteadores, árbitros, interconector, CLINT, PLIC e periféricos, reunidos na entidade `soc` ([../soc/soc.md](../soc/soc.md)) | Pessoas, em VHDL | Não |
| 2. Backends | Uma realização por região de memória e por recurso de E/S, escolhida no `platform.yaml` | Pessoas (RTL do backend) e o Tools (instanciação) | Só o que o chip impõe (largura e tempos), vindo de generics |
| 3. Pacote de placa | Dispositivo, relógios, pinos, chips, capacidades e IDCODE | Dados (`board.yaml`, `pins.yaml`, família e chip) | Sim, e só aqui |

A ligação entre as camadas 2 e 3 é um topo fino gerado pelo Tools ([geracao.md](geracao.md)), que instancia o SoC, os backends escolhidos, o PLL e o anel de pinos. Nenhum RTL escrito à mão cita pino, família ou fornecedor, exceto os invólucros de primitivas de fornecedor, que ficam em pastas com o nome do fornecedor.

Cada dado tem um dono e existe uma só vez.

| Arquivo | Descreve | Onde fica |
| :--- | :--- | :--- |
| `platform.yaml` | O que o SoC pede: mapa, perfil, backends, relógios, E/S, console | `src/<grupo>/<plataforma>/` |
| `board.yaml` e `pins.yaml` | O que a placa oferece e onde estão os pinos | `boards/<placa>/` |
| Família | O que vale para todo dispositivo de uma família | `boards/families/` |
| Chip | Tempos e organização de um chip de memória | `Memory/chips/` |
| Calibração | Custo medido de cada bloco do SoC na família | `boards/calibration/` |

Os esquemas estão em [formato.md](formato.md), [familias.md](familias.md) e [plataforma-e-placa.md](plataforma-e-placa.md).

## 2. Regiões e backends

O `platform.yaml` descreve recursos em quatro grupos, e cada recurso tem um backend.

| Grupo | Recursos | Backend `emulado` | Backend `dispositivo` |
| :--- | :--- | :--- | :--- |
| Boot | `BOOT_MEMORY` | Bloco de memória do FPGA com imagem inicial (único backend) | Não existe |
| Armazenamento de programa | `FLASH` e suas bancas | Bloco de memória de duas portas atrás do modelo de chip, com latência configurável | FLASH NOR paralela, FLASH interna do FPGA, FLASH serial |
| Dados | `RAM` | Bloco de memória do FPGA | SDRAM com largura por generic, SRAM assíncrona |
| E/S | Console, chaves, botões, LEDs, displays | Modelo de simulação, ou ausente | Pinos da placa, JTAG UART |

O campo `memory.<região>.external` diz se a região fica atrás da porta externa do núcleo, e `backend` diz como ela é realizada. O backend `emulado` tem dois alvos: na simulação é o modelo de chip em VHDL, de qualquer tamanho, e no FPGA é um bloco de memória interna, limitado pela RAM interna da placa (seção 6).

| Backend | Região | Contrato | Recurso de placa (`needs`) |
| :--- | :--- | :--- | :--- |
| `emulado/bloco` | BOOT, FLASH, RAM | K3 sob K2 | `block_ram` |
| `dispositivo/sdram` | RAM | K2 sobre pinos | `sdram` |
| `dispositivo/sram` | RAM | K2 sobre pinos | `sram` |
| `dispositivo/nor` | FLASH | K2 e K4 | `nor` |
| `dispositivo/flash-interna` | FLASH | K2 e K4 | `onchip_flash` |
| `dispositivo/serial` | FLASH | K2 e K4 | `serial_flash` |

A latência de um backend de dispositivo, em ciclos de um relógio de período $T$, é

$$ n_{ciclos} = \left\lceil \frac{t_{chip}}{T} \right\rceil $$

para cada tempo $t_{chip}$ do chip no catálogo. O backend `emulado` imita um dispositivo copiando os mesmos $n_{ciclos}$ para `memory.<região>.latency`, o que mantém o tempo de programa comparável entre placas.

### 2.1. Largura de dado diferente de 32 bits

Um dispositivo de largura $W < 32$ entrega uma palavra em $32/W$ acessos.

| Caso | Largura | Forma |
| :--- | ---: | :--- |
| SDRAM de 16 bits (DE0-CV, DE0-Nano, DE10-Lite, MKR Vidor) | 16 | Rajada de 2 por palavra |
| SDRAM de 32 bits (DE2-115) | 32 | Dois chips de 16 bits em paralelo, rajada de 1, `DQM` de 4 bits |
| FLASH NOR da DE2-115 | 8 | Quatro leituras seriais por palavra, leitura em página |
| SRAM da DE2-115 | 16 | Dois acessos por palavra |

## 3. Contratos

Os contratos K1 a K9 são a única superfície entre as camadas, e cada um mora no repositório dono, onde está definido por inteiro.

| Contrato | Assunto | Documento |
| :--- | :--- | :--- |
| K1 | Porta externa do núcleo (`o_ext_*` e `i_ext_*`) | [Core, barramento e memória](../../../Core/docs/pt-br/contracts/02-barramento-e-memoria.md) |
| K2 | Região de memória (avanço `i_advance`, latência, endereço fora da janela lê zero) | [Memory, contrato de memória](../../../Memory/docs/pt-br/contracts/contrato-de-memoria.md), [ram_chip](../../../Memory/docs/pt-br/ram/ram_chip.md) e [flash_chip](../../../Memory/docs/pt-br/rom/flash_chip.md) |
| K3 | Bloco de armazenamento | [Memory, contrato de memória](../../../Memory/docs/pt-br/contracts/contrato-de-memoria.md) |
| K4 | Comandos de FLASH (apagar, gravar, proteger) | [flash_cmd_port](../../../Memory/docs/pt-br/rom/flash_cmd_port.md) e [nor_flash_ctrl](../../../Memory/docs/pt-br/rom/nor_flash_ctrl.md) |
| K5 | Acesso do hospedeiro às memórias | [sdram_debug](../../../Memory/docs/pt-br/ram/sdram_debug.md) e [flash_loader](../../../Memory/docs/pt-br/rom/flash_loader.md) |
| K6 | Periférico no interconector externo | [ext_interconnect](../interconnect/ext_interconnect.md) |
| K7 | Relógios por papel (`core`, `fetch`, `mem`, `mem_pin`, `rst`) e reset | [Core, relógios e reset](../../../Core/docs/pt-br/contracts/03-relogios-e-reset.md) |
| K8 | Vetores de E/S por papel, com largura por generic e polaridade normalizada | [Peripherals, E/S de placa](../../../Peripherals/docs/pt-br/contracts/01-es-de-placa.md) e [soc](../soc/soc.md) |
| K9 | Console `jtag` (padrão) ou `pinos` | [Peripherals, console](../../../Peripherals/docs/pt-br/contracts/02-console.md) |

A porta de depuração do contrato K5 existe em todo backend de memória.

| Realização | Porta de depuração |
| :--- | :--- |
| RAM emulada | Carregador de memória pela JTAG |
| SDRAM | Mestre de depuração, o segundo mestre do controlador |
| FLASH emulada | Porta B do armazenamento, dona do carregador com o núcleo parado |
| FLASH NOR | O controlador de FLASH usando os comandos K4 |

## 4. Invólucros de fornecedor

Todo código de fornecedor fica em pastas com o nome do fornecedor, com um invólucro por primitiva.

| Invólucro | Varia com a família? |
| :--- | :--- |
| Memória em bloco (`altsyncram`), uma entidade com generics de modo, máscara de bytes e arquivo de inicialização | Só pelo generic de família |
| Virtual JTAG (`sld_virtual_jtag`), uma entidade com generics de índice de instância e largura de IR, no Common-Components | Não |
| PLL (`altera_pll` ou `altpll`) | Escrito pelo gerador, por família |
| FLASH interna (`altera_onchip_flash`) | Só a MAX 10 |

## 5. Matriz região, backend e placa

Legenda: `sim` é um recurso que a placa oferece ao backend, `lim` é oferecido com limite de tamanho, `não` não existe na placa. Os backends que o topo gerado instancia estão em [geracao.md](geracao.md).

| Região e backend | DE0-CV | DE2-115 | DE0-Nano | DE10-Lite | DE10-Nano | MKR Vidor |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| BOOT, `emulado/bloco` | sim | sim | sim | sim | sim | sim |
| FLASH, `emulado/bloco` | sim | sim | lim | lim | sim | lim |
| FLASH, `dispositivo/nor` | não | sim (8 MB, 8 bits) | não | não | não | não |
| FLASH, `dispositivo/flash-interna` | não | não | não | sim (até 736 KB) | não | não |
| FLASH, `dispositivo/serial` | não | não | EPCS64 | não | não | QSPI de 2 MB |
| RAM, `emulado/bloco` | lim | lim | lim | lim | lim | lim |
| RAM, `dispositivo/sdram` | sim (16 bits, 64 MB) | sim (32 bits, 128 MB) | sim (16 bits, 32 MB) | sim (16 bits, 64 MB) | não | sim (16 bits, 8 MB) |
| RAM, `dispositivo/sram` | não | sim (16 bits, 2 MB) | não | não | não | não |
| Console `jtag` | sim | sim | sim | sim | sim | sim, pelo cabo emulado |
| Console `pinos` | não | sim (RS-232) | GPIO e adaptador | Arduino IO0 e IO1 | Arduino IO0 e IO1 | D13 e D14 |
| Chaves, botões, LEDs | 10, 4, 10 | 18, 4, 27 | 4, 2, 8 | 10, 2, 10 | 4, 2, 8 | nenhum |
| Display de 7 segmentos | 6 | 8 | nenhum | 6 | nenhum | nenhum |

A tabela das placas, com o dispositivo, o cabo e o nível alvo de cada uma, está em [placas.md](placas.md).

## 6. Orçamento de RAM interna do backend emulado

O backend `emulado` consome blocos de memória do FPGA, e o estimador conta blocos inteiros, porque cada memória arredonda para blocos de 9 kbit (M9K) ou 10 kbit (M10K).

$$ N_{blocos} = \sum_{m} \left\lceil \frac{8\,s_m}{b_{bloco}} \right\rceil + N_{caches} + N_{regs} \qquad u_{mem} = \frac{N_{blocos}}{N_{disponivel}} $$

com $s_m$ o tamanho em bytes de cada memória emulada, $b_{bloco}$ os bits por bloco da família, e a política de cabimento de [cabimento.md](cabimento.md) (erro acima de $u_{mem} = 1$, aviso acima de $0{,}85$).

| Placa | Blocos | Bits por bloco |
| :--- | ---: | ---: |
| DE0-CV | 308 | 10.240 |
| DE2-115 | 432 | 9.216 |
| DE0-Nano | 66 | 9.216 |
| DE10-Lite | 182 | 9.216 |
| DE10-Nano | 557 | 10.240 |
| DE0-Nano-SoC | 246 | 10.240 |
| MKR Vidor | 56 | 9.216 |

Um perfil de certificação com FLASH e RAM de 1 MB só cabe pelo backend de dispositivo, porque nenhuma placa comporta essa memória emulada.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
