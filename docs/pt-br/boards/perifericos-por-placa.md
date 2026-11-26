# Periféricos externos por placa

## 1. Papéis declarados

Cada placa descreve em `board.yaml` os pinos que o FPGA alcança, por papel de entrada e saída (`io`) e por papel de periférico externo (`buses`, ver [formato.md](formato.md)). A tabela traz o que cada pacote declara hoje.

| Placa | Papéis de `io` | Papéis de `buses` |
| :--- | :--- | :--- |
| `de0-cv` | `leds`, `switches`, `keys`, `display`, `gpio`, `clock_extra`, `video` (VGA de 4 bits) | `ps2` (2), `sd` |
| `de2-115` | `leds`, `leds_green`, `switches`, `keys`, `display`, `gpio`, `ex_io`, `hsmc`, `clock_extra`, `video` (ADV7123 de 8 bits) | `ps2` (2), `sd`, `lcd`, `i2c` (2), `audio`, `eth` (2), `tv`, `usb`, `ir`, `serial` |
| `de0-nano` | `leds`, `switches`, `keys`, `gpio` | `adc` (ADC128S022), `adxl345`, `i2c` |
| `de10-lite` | `leds`, `switches`, `keys`, `display`, `gpio`, `clock_extra`, `video` (VGA de 4 bits) | `adxl345`, `adc` (interno do MAX 10) |
| `de10-nano` | `leds`, `switches`, `keys`, `gpio`, `clock_extra`, `video` (HDMI ADV7513) | `hdmi`, `hdmi_audio`, `adc` (LTC2308) |
| `de0-nano-soc` | `leds`, `switches`, `keys`, `gpio`, `clock_extra` | `adc` (LTC2308) |
| `mkr-vidor-4000` | `gpio` | `i2c`, `spi`, `serial` |

## 2. Papéis novos desta versão

| Placa | Papel | Sinais | Fonte |
| :--- | :--- | :--- | :--- |
| `de2-115` | `serial` | `UART_RXD`, `UART_TXD`, `UART_CTS`, `UART_RTS` | Manual, seção 4.12, tabela 4-18 |
| `de10-nano` | `hdmi_audio` | `HDMI_MCLK`, `HDMI_SCLK`, `HDMI_LRCLK`, `HDMI_I2S0` | Manual, seção 3.6.5, tabela 3-13 |
| `mkr-vidor-4000` | `gpio` | `bMKR_D[14:0]`, `bMKR_A[6:0]` e as 25 redes `PEX` do FPGA | Datasheet ABX00022 (seção 1.2), pinout e esquemático |
| `mkr-vidor-4000` | `i2c` | SDA em `bMKR_D[11]`, SCL em `bMKR_D[12]` | ABX00022-pinout.pdf (SERCOM 2 do SAMD21) |
| `mkr-vidor-4000` | `spi` | COPI em `bMKR_D[8]`, SCK em `bMKR_D[9]`, CIPO em `bMKR_D[10]`, seleção em `bMKR_D[7]` | ABX00022-pinout.pdf (SERCOM 1 do SAMD21); a seleção é escolha do projeto |
| `mkr-vidor-4000` | `serial` | RX em `bMKR_D[13]`, TX em `bMKR_D[14]` | ABX00022-pinout.pdf (SERCOM 5 do SAMD21) |

O papel `gpio` da Vidor numera `bMKR_D[14:0]` de 0 a 14, `bMKR_A[6:0]` de 15 a 21 e as redes `PEX` de 22 a 46, na ordem do número do pino do conector. A referência analógica `bMKR_AREF` fica fora porque pertence ao SAMD21, e as redes `PEX_PIN1`, `PEX_PIN3`, `PEX_PIN5` e `PEX_PIN7` ficam fora porque o módulo Wi-Fi as usa como `bWM_PIO2`, `bWM_PIO3`, `bWM_PIO4` e `bWM_PIO34`.

## 3. Pinos sem papel

Os pinos abaixo constam em `pins.yaml` com selo e fonte e não têm papel no `board.yaml`, porque o registro de papéis do Tools não tem um papel que os descreva.

| Placa | Pinos | Papel que falta no Tools |
| :--- | :--- | :--- |
| `de10-lite` | `HEX0[7]` a `HEX5[7]` (ponto decimal, seção 3.4, tabela 3-6) | Display de oito segmentos por dígito; o papel `display` tem sete |
| `de0-nano` | `GPIO_0_IN[1:0]`, `GPIO_1_IN[1:0]` e `GPIO_2_IN[2:0]` | GPIO só de entrada; o bloco `gpio` usa célula bidirecional |
| `de2-115` | `OTG_DREQ` e `OTG_DACK`, que o manual não lista | Nenhum, pois a placa não tem esses sinais |
| `mkr-vidor-4000` | `oHDMI_TX[2:0]` e `oHDMI_CLK` (TMDS direto), `iMIPI_*`, `bMIPI_*` e `bWM_*` | `hdmi` de TMDS direto, câmera MIPI e ponte Wi-Fi |

A USB da DE2-115 é a interface HPI do CY7C67200, de modo que o acesso de DMA à memória interna do chip passa pelo barramento de dados da própria tabela 4-25 e a placa não leva pinos de requisição nem de confirmação de DMA.

## 4. Selos de certeza dos pinos novos

| Selo | Quando vale | Pinos novos |
| :--- | :--- | :--- |
| `manual` | O número do pino foi lido numa tabela do manual ou no documento da placa | Os da Vidor em `bMKR_*` (bola conferida no pinout) e `bPEX_*` e `iPEX_*` (bola conferida no esquemático) |
| `repo` | O pino foi lido no `.qsf` do repositório | Nenhum pino novo |
| `inferred` | O pino veio de fonte de terceiro | Nenhum pino novo |
| `measured` | O pino foi lido de uma placa real | Nenhum pino novo |

O padrão de E/S dos pinos da Vidor segue a tensão de 3,3 V do datasheet, e a escolha de `3.3-V LVTTL` entre os padrões de 3,3 V do Quartus é do projeto. A direção de `iPEX_*` vem do `.qsf` e o esquemático não a confirma.

## 5. Plataformas de exemplo

Cada placa tem em `src/periph-examples/<placa>/` uma plataforma que pede os periféricos externos do seu pacote, com `base` absoluta e sem sobreposição. Todas partem da plataforma de calibração da placa (perfil completo, FLASH e RAM emuladas em blocos) e acrescentam o bloco `gpio` e os periféricos externos.

| Plataforma | Periféricos externos (nome, `kind`, `base`) |
| :--- | :--- |
| `de0-cv-periph` | `KBD` e `MOUSE` (`ps2`, `0x80007000` e `0x80007100`), `SD` (`sd_native`, `0x80008000`) |
| `de2-115-periph` | `KBD`, `MOUSE`, `SD`, `IR` (`0x80009000`), `LCD` (`0x8000A000`), `USB` (`0x8000B000`), `I2C0` e `I2C1` (`0x8000C000` e `0x8000C100`), `AUDIO` (`0x8000D000`), `ETH0` e `ETH1` (`0x8000E000` e `0x8000E100`), `TV` (`0x8000F000`), `SERIAL` (`uart`, `0x80220000`) |
| `de0-nano-periph` | `ADC0` (`adc` ADC128S022, `0x80010000`), `ACCEL` (`adxl345` em SPI de três fios, `0x80012000`) |
| `de10-lite-periph` | `ADC0` (`adc` interno, `0x80010000`), `ACCEL` (`adxl345` em SPI de quatro fios, `0x80012000`) |
| `de10-nano-periph` | `ADC0` (`adc` LTC2308, `0x80010000`), `HDMI` (`hdmi`, `0x80200000`), `HDMI_AUDIO` (`hdmi_audio`, `0x80240000`) |
| `de0-nano-soc-periph` | `ADC0` (`adc` LTC2308, `0x80010000`) |
| `mkr-vidor-4000-periph` | `I2C0` (`0x8000C000`), `SPI0` (`spi`, `0x80011000`), `SERIAL` (`uart`, `0x80220000`) |

Todas as plataformas ainda têm o bloco `GPIO` (`gpio` do papel `gpio`, `0x80001000`). Na Vidor ele reúne `D0` a `D6`, `A0` a `A6` e o Mini PCI Express em três grupos. A janela do `hdmi` tem 256 KiB, e a `base` de cada periférico é múltipla do tamanho da janela dele.

## 6. Pinos compartilhados

Um par de pinos que dois papéis usam a um só tempo tem um dono por plataforma, porque dois mestres no mesmo fio corrompem o barramento.

### 6.1. DE0-Nano, EEPROM e ADXL345

`I2C_SCLK` (`F2`) e `I2C_SDAT` (`F1`) ligam a EEPROM (seção 3.4, endereços de escrita e leitura `0xA0` e `0xA1`) e o ADXL345 (seção 3.7, tabela 3-10). O nível de `G_SENSOR_CS_N` escolhe o modo do acelerômetro.

| `G_SENSOR_CS_N` | Modo do ADXL345 | Papel do pacote | Uso de `I2C_SCLK` e `I2C_SDAT` |
| :--- | :--- | :--- | :--- |
| Baixo | SPI de três fios | `adxl345` | SCLK e MOSI do SPI |
| Alto | I2C | `i2c` | SCL e SDA do barramento |

Na plataforma, o periférico `adxl345` e o periférico `i2c` não coexistem. Com o `adxl345` em SPI de três fios, o acelerômetro é o único mestre dos pinos e a EEPROM não é acessada. Para usar a EEPROM, a plataforma pede só o periférico `i2c` e deixa `G_SENSOR_CS_N` em nível alto, e o acelerômetro só é lido por esse mestre se a plataforma o endereçar pelo valor que o datasheet do ADXL345 define, que o manual da placa não traz.

### 6.2. DE2-115, codec e decodificador de TV

`I2C_SCLK` e `I2C_SDAT` configuram o WM8731 (seção 4.11) e o ADV7180 (seção 4.15), e ficam na segunda cópia do papel `i2c`. A plataforma usa um único periférico `i2c` nessa cópia, e a EEPROM tem a primeira cópia (`EEP_I2C_SCLK` e `EEP_I2C_SDAT`, seção 4.19).

### 6.3. DE10-Nano, HDMI

`I2C_SCL` e `I2C_SDA` configuram o ADV7513 e pertencem ao papel `hdmi`. O papel `hdmi_audio` leva só o áudio I2S de saída e não usa esse barramento, e o periférico `hdmi` carrega também a tabela de registradores de áudio (`audio_init_table`).

### 6.4. Vidor, cabeçalho e bloco gpio

Os pinos de `i2c`, `spi` e `serial` da Vidor são também pinos do papel `gpio`. A plataforma `mkr-vidor-4000-periph` usa cada pino em um só papel, e o bloco `gpio` dela deixa de fora os índices 7 a 14 (`D7` a `D14`), que o `spi`, o `i2c` e o `serial` ocupam.

---

Copyright 2026 Insper. Licenciado sob a [Apache License, Version 2.0](../../../LICENSE).
