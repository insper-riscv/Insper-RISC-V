# Plataformas

Uma plataforma liga o núcleo, as memórias e os periféricos em algo que executa. Este repositório tem cinco.

| Plataforma | Caminho | Descrição |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `src/cyclone-v/de0-cv/` | A placa DE0-CV (Cyclone V), com a BOOT_ROM no núcleo e a FLASH e a SDRAM atrás das caches |
| [external-data](external-data.md) | `src/cyclone-v/external-data/` | A placa DE0-CV, com a BOOT_ROM e a FLASH de duas portas dentro da FPGA e a SDRAM atrás da cache de dados |
| [internal-mem](internal-mem.md) | `src/simulation/internal-mem/` | Plataforma só de simulação, com BOOT_ROM, FLASH e RAM dentro da FPGA |
| [modular](modular.md) | `src/simulation/modular/` | Topo de simulação configurável que cobre os modelos `integrated`, `external-data`, `external-instruction` e `external`, com memórias e caches de tamanho em potência de dois |
| [template](template.md) | `src/simulation/template/` | Plataforma modelo mínima (RAM e ROM internas, UART sobre JTAG opcional, perfil `rv32i`) que o guia de nova arquitetura copia |

Os documentos comuns às duas descrevem o que o programa enxerga.

| Documento | Conteúdo |
| :--- | :--- |
| [memoria.md](memoria.md) | Arquitetura de memória BOOT_ROM, FLASH e RAM |
| [boot.md](boot.md) | Estado de boot, `crt0` da picolibc e `boot_rom.S` |
| [contrato-de-entrada.md](contrato-de-entrada.md) | Contrato de entrada da BOOT_ROM com o firmware |
| [runtime.md](runtime.md) | Runtime C, arquivo de plataforma, `stdout` e Spike |
| [atualizacao-de-programa.md](atualizacao-de-programa.md) | Substituição de um programa por outro e passagem de boot entre testes |
| [timing/README.md](timing/README.md) | Linha de base de tempo (Fmax, caminhos críticos), de ciclos por instrução e dos cruzamentos de domínio da `de0-cv` |
