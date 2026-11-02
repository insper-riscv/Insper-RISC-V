# Plataformas

Uma plataforma liga o núcleo, as memórias e os periféricos em algo que executa. Este repositório tem duas.

| Plataforma | Caminho | Descrição |
| :--- | :--- | :--- |
| [de0-cv](de0-cv.md) | `src/cyclone-v/de0-cv/` | A placa DE0-CV (Cyclone V), com a BOOT_ROM no núcleo e a FLASH e a SDRAM atrás das caches |
| [internal-mem](internal-mem.md) | `src/simulation/internal-mem/` | Plataforma só de simulação, com BOOT_ROM, FLASH e RAM dentro da FPGA |

Os documentos comuns às duas descrevem o que o programa enxerga.

| Documento | Conteúdo |
| :--- | :--- |
| [memoria.md](memoria.md) | Arquitetura de memória BOOT_ROM, FLASH e RAM |
| [boot.md](boot.md) | Estado de boot, `crt0` da picolibc e `boot_rom.S` |
| [runtime.md](runtime.md) | Runtime C, arquivo de plataforma, `stdout` e Spike |
| [atualizacao-de-programa.md](atualizacao-de-programa.md) | Substituição de um programa por outro e passagem de boot entre testes |
