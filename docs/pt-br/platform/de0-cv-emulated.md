# Plataforma `de0-cv-emulated`: a FLASH emulada com controlador, só em simulação

## 1. O que ela é

É o modelo de memória da DE0-CV anterior à divisão da SDRAM, mantido como topo de simulação. A FLASH é emulada em blocos do FPGA com a latência de um chip serial (24 bordas para a primeira palavra de uma rajada e 4 para cada seguinte), e a RAM é a SDRAM da placa. As duas ficam atrás das caches de instruções e de dados.

A plataforma existe para testar a atualização de programa em campo. O controlador de FLASH e o chip de comandos (apagar setor, gravar página, proteger) só fazem sentido com uma FLASH que o núcleo consegue programar, e a [`de0-cv`](de0-cv.md) não tem essa FLASH, porque a dela está dentro do chip de SDRAM e só a porta de depuração a escreve.

## 2. Diferenças para a `de0-cv`

| Item | `de0-cv` | `de0-cv-emulated` |
| :--- | :--- | :--- |
| FLASH | Janela de 32 MiB do chip de SDRAM | `emulated`, 256 KiB em blocos do FPGA |
| Quem escreve a FLASH | A porta de depuração do chip | O controlador de FLASH, pelo programa |
| RAM | Janela de 32 MiB, deslocada 32 MiB no chip | SDRAM de 64 MB, a partir do byte 0 do chip |
| Bancos de atualização | A e B em 16 MiB cada | A em 124 KiB e B em 128 KiB |
| Placa | Sim | Não, só simulação |

## 3. Uso

O topo é `rv32im_sdram_flash_emulated_sim_test`, com `has_flash_controller` ligado. Os parâmetros `FLASH_ERASE_LATENCY` e `FLASH_PROGRAM_LATENCY` dão a espera do chip em bordas. O projeto que roda os testes usa os cabeçalhos desta plataforma, porque os bancos A e B da `de0-cv` ficam fora da FLASH emulada.
