# Benchmark da SDRAM na placa

Este documento registra a execução do autoteste (BIST) da SDRAM de 64 MB na DE0-CV, sem o core, e as margens de timing do projeto que foi gravado. Ele complementa o benchmark de simulação em `BENCHMARK_SDRAM.md`, que mede o custo em ciclos de usar a SDRAM como RAM.

## 1. Ambiente

| Item | Valor |
| :--- | :--- |
| Placa | DE0-CV, FPGA Cyclone V `5CEBA4F23` (JTAG `0x02B050DD`) |
| Cabo | USB-Blaster `[3-5]` |
| Memória | SDRAM SDR 32M x 16, 143 MHz |
| Ferramenta | Quartus Prime Lite 25.1std.0, no host |
| Projeto | `sdram-bringup` do TopLevel, branch `feat/sdram-bringup`, commit `e37c149` |
| Controlador e autoteste | Memory, branch `feat/sdram-bist`, commit `4e339b5` |

O projeto liga a SDRAM a um controlador e ao autoteste, sem o core. O PLL gera 142,857 MHz para o controlador e para o pino `DRAM_CLK`, este deslocado em 2750 ps, e 50 MHz para o lado do core, que o autoteste não usa.

## 2. Procedimento

1. Compilar: `quartus_sh --flow compile sdram_bringup`, em `platforms/sdram-bringup/quartus`.
2. Gravar o bitstream na SRAM do FPGA: `quartus_pgm -c "USB-Blaster [3-5]" -m JTAG -o "p;output_files/sdram_bringup.sof"`.
3. Rodar cada modo do autoteste pelo JTAG: `quartus_stp -t jtag/sdram_bist.tcl <modo> 120`, de dentro de `platforms/sdram-bringup`.

A compilação levou 45 s. A gravação é volátil: ao desligar a placa, o FPGA perde a configuração.

## 3. Resultado do autoteste

Cada modo foi executado uma vez, em sequência, depois da gravação. Todos passaram, sem palavra errada e sem estouro do controlador.

| Modo | Teste | Palavras movidas | Palavras erradas | Resultado |
| :--- | :--- | ---: | ---: | :--- |
| 0 | rápido, com máscaras de byte | 458 752 | 0 | PASS |
| 1 | padrões (zeros, uns, `0xAAAAAAAA`, `0x55555555`, bit andando, endereço e complemento) | 1 048 576 | 0 | PASS |
| 2 | varredura do chip inteiro, $2^{24}$ palavras | 67 108 864 | 0 | PASS |
| 3 | endereços pseudo-aleatórios, $2^{20}$ palavras escritas e relidas | 2 097 152 | 0 | PASS |

A varredura completa levou cerca de 6 s; o relógio do script tem resolução de 1 s, então o tempo vale como ordem de grandeza. Ela move $4 \cdot 2^{24}$ palavras (escrita e leitura, com o dado do endereço e com seu complemento), o que dá algo em torno de 11 milhões de palavras por segundo.

O controlador gasta 10 ciclos de 7 ns por acesso de uma palavra (ativar a linha, ler ou escrever em dois ciclos de 16 bits e pré-carregar), ou seja, no máximo

$$
\frac{1}{10 \cdot 7\ \text{ns}} \approx 14{,}3 \text{ milhões de palavras por segundo}
$$

com os tempos provisórios do chip. A taxa medida fica abaixo desse teto, como se espera.

## 4. Timing do projeto gravado

Margens (slack) do Quartus com as restrições de entrada e saída do chip. Valores negativos indicam que o caminho não fecha naquele modelo.

| Verificação | Modelo lento 85 C | Modelo lento 0 C |
| :--- | ---: | ---: |
| Leitura de dado, setup (domínio do controlador) | -0,201 ns | +0,057 ns |
| Comandos e dado de escrita, setup (`DRAM_CLK`) | -0,051 ns | -0,029 ns |
| Comandos e dado de escrita, hold | +2,974 ns | +3,068 ns |
| Hold no domínio do controlador | +0,337 ns | +0,314 ns |

Recursos: 521 ALMs de 18 480 (3 %), 923 registradores, 65 pinos de 224 e nenhum bit de memória em bloco.

## 5. Limites desta medição

1. Os tempos do chip nas restrições (setup de entrada 1,5 ns, hold de entrada 0,8 ns, acesso 5,4 ns, hold de saída 2,5 ns) são valores usuais de uma SDR de 143 MHz, ainda não conferidos com o datasheet da peça. As margens negativas dos modelos lentos dependem deles.
2. O autoteste passou na placa mesmo com margem negativa no modelo lento, o que indica que o modelo é conservador; ele não prova folga em outra temperatura, outra placa ou outro lote.
3. Foi uma execução de cada modo. Não houve repetição para medir variação nem varredura da fase do clock.
4. Este benchmark não inclui o core. O custo em ciclos de rodar programas com a SDRAM como RAM, na placa, depende da plataforma `sdram` completa e não foi medido aqui.
