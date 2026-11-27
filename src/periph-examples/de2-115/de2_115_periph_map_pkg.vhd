-- ===========================================================================
-- Mapa de memória da plataforma, gerado por
-- `riscv-tools generate-memory-map` a partir de src/periph-examples/de2-115/platform.yaml.
--
-- Não edite à mão: mude o YAML da plataforma e rode o comando de novo. Os
-- limites estão em KiB, como os genéricos do núcleo, e os endereços dos
-- periféricos em bytes.
-- ===========================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.config_pkg.ADDR_BITS;
use work.config_pkg.addr_t;

package de2_115_periph_map_pkg is

	-- O perfil é o RV32E (16 registradores); falso é o RV32I (32).
	constant IS_E                : boolean  := false;
	-- A extensão M está no perfil.
	constant HAS_M               : boolean  := true;
	-- A extensão Zmmul está no perfil.
	constant HAS_ZMMUL           : boolean  := false;
	-- A extensão Zicsr está no perfil.
	constant HAS_ZICSR           : boolean  := true;
	-- A extensão Zicntr está no perfil.
	constant HAS_ZICNTR          : boolean  := true;
	-- A extensão Zihpm está no perfil.
	constant HAS_ZIHPM           : boolean  := true;
	-- A extensão Zimop está no perfil.
	constant HAS_ZIMOP           : boolean  := true;
	-- A extensão Zicond está no perfil.
	constant HAS_ZICOND          : boolean  := true;
	-- A extensão Zihintntl está no perfil.
	constant HAS_ZIHINTNTL       : boolean  := true;
	-- A extensão Zihintpause está no perfil.
	constant HAS_ZIHINTPAUSE     : boolean  := true;
	-- A extensão Zifencei está no perfil.
	constant HAS_ZIFENCEI        : boolean  := true;
	-- A extensão Zicclsm está no perfil.
	constant HAS_ZICCLSM         : boolean  := true;
	-- A extensão Interrupts está no perfil.
	constant HAS_INTERRUPTS      : boolean  := true;
	-- A extensão Sscofpmf está no perfil.
	constant HAS_SSCOFPMF        : boolean  := true;
	-- A extensão Access_faults está no perfil.
	constant HAS_ACCESS_FAULTS   : boolean  := false;
	-- Expoente do tamanho da BOOT_MEMORY, em [0, 2**BOOT_MEMORY_BITS).
	constant BOOT_MEMORY_BITS       : natural  := 12;
	-- Tamanho da BOOT_MEMORY, em bytes.
	constant BOOT_MEMORY_SIZE_BYTES : positive := 4096;
	-- Base da FLASH, em KiB, logo depois da BOOT_MEMORY.
	constant FLASH_BASE_KIB      : natural  := 4;
	-- Fim exclusivo da FLASH, em KiB.
	constant FLASH_END_KIB       : natural  := 32;
	-- Armazenamento da FLASH, em bytes: a menor potência de dois que cobre
	-- [0, fim da FLASH).
	constant FLASH_STORAGE_BYTES : positive := 32768;
	-- A FLASH é alcançada pelo barramento (verdadeiro) ou pela porta direta (falso).
	constant FLASH_ON_BUS        : boolean  := true;
	-- Base da RAM, em KiB.
	constant RAM_BASE_KIB        : natural  := 1048576;
	-- Fim exclusivo da RAM, em KiB.
	constant RAM_END_KIB         : natural  := 1048640;
	-- Armazenamento da RAM, em bytes: a menor potência de dois que cobre
	-- o tamanho da RAM.
	constant RAM_STORAGE_BYTES   : positive := 65536;
	-- Página de 4 KiB no topo da RAM (bits 31:12 do endereço), onde ficam as
	-- palavras que o hospedeiro compartilha com o programa.
	constant RAM_LAST_PAGE       : std_logic_vector(19 downto 0) :=
		x"4000F";
	-- A RAM é alcançada pelo barramento (verdadeiro) ou pela porta direta (falso).
	constant RAM_ON_BUS          : boolean  := true;
	-- Existe cache de instruções.
	constant HAS_ICACHE          : boolean  := true;
	-- Existe cache de dados.
	constant HAS_DCACHE          : boolean  := true;
	-- Tamanho da cache de instruções, em bits (256 se não existe).
	constant ICACHE_SIZE_BITS    : positive := 32768;
	-- Tamanho da cache de dados, em bits (256 se não existe).
	constant DCACHE_SIZE_BITS    : positive := 32768;
	-- Largura da janela de endereços da cache de instruções, em bits: a tag guarda os bits abaixo dela (26 é 64 MiB, 27 é 128 MiB).
	constant I_CACHE_WINDOW_BITS : natural  := 26;
	-- Largura da janela de endereços da cache de dados, em bits: a tag guarda os bits abaixo dela (26 é 64 MiB, 27 é 128 MiB).
	constant D_CACHE_WINDOW_BITS : natural  := 26;

	-- Número de periféricos do mapa, o tamanho das tabelas abaixo.
	constant PERIPH_COUNT : natural := 19;
	-- Periféricos estritos: o interconector termina com erro o acesso ao que sobra da janela depois dos registradores.
	constant STRICT_PERIPH : boolean := true;
	-- Tabela de endereços, um por periférico.
	type periph_addr_array_t is array (natural range <>) of addr_t;

	-- Endereço base do periférico FLASH_CTRL.
	constant FLASH_CTRL_BASE : addr_t := std_logic_vector(resize(unsigned'(x"B0000000"), ADDR_BITS));
	-- Índice do periférico FLASH_CTRL nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant FLASH_CTRL_INDEX : natural := 0;

	-- Endereço base do periférico UART.
	constant UART_BASE : addr_t := std_logic_vector(resize(unsigned'(x"C0000000"), ADDR_BITS));
	-- Índice do periférico UART nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant UART_INDEX : natural := 1;

	-- Endereço base do periférico DISPLAY.
	constant DISPLAY_BASE : addr_t := std_logic_vector(resize(unsigned'(x"D0000000"), ADDR_BITS));
	-- Índice do periférico DISPLAY nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant DISPLAY_INDEX : natural := 2;

	-- Endereço base do periférico CLINT.
	constant CLINT_BASE : addr_t := std_logic_vector(resize(unsigned'(x"E0000000"), ADDR_BITS));
	-- Índice do periférico CLINT nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant CLINT_INDEX : natural := 3;

	-- Endereço base do periférico PLIC.
	constant PLIC_BASE : addr_t := std_logic_vector(resize(unsigned'(x"F0000000"), ADDR_BITS));
	-- Índice do periférico PLIC nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant PLIC_INDEX : natural := 4;

	-- Endereço base do periférico GPIO.
	constant GPIO_BASE : addr_t := std_logic_vector(resize(unsigned'(x"80001000"), ADDR_BITS));
	-- Índice do periférico GPIO nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant GPIO_INDEX : natural := 5;

	-- Endereço base do periférico KBD.
	constant KBD_BASE : addr_t := std_logic_vector(resize(unsigned'(x"80007000"), ADDR_BITS));
	-- Índice do periférico KBD nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant KBD_INDEX : natural := 6;

	-- Endereço base do periférico MOUSE.
	constant MOUSE_BASE : addr_t := std_logic_vector(resize(unsigned'(x"80007100"), ADDR_BITS));
	-- Índice do periférico MOUSE nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant MOUSE_INDEX : natural := 7;

	-- Endereço base do periférico SD.
	constant SD_BASE : addr_t := std_logic_vector(resize(unsigned'(x"80008000"), ADDR_BITS));
	-- Índice do periférico SD nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant SD_INDEX : natural := 8;

	-- Endereço base do periférico IR.
	constant IR_BASE : addr_t := std_logic_vector(resize(unsigned'(x"80009000"), ADDR_BITS));
	-- Índice do periférico IR nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant IR_INDEX : natural := 9;

	-- Endereço base do periférico LCD.
	constant LCD_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000A000"), ADDR_BITS));
	-- Índice do periférico LCD nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant LCD_INDEX : natural := 10;

	-- Endereço base do periférico USB.
	constant USB_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000B000"), ADDR_BITS));
	-- Índice do periférico USB nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant USB_INDEX : natural := 11;

	-- Endereço base do periférico I2C0.
	constant I2C0_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000C000"), ADDR_BITS));
	-- Índice do periférico I2C0 nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant I2C0_INDEX : natural := 12;

	-- Endereço base do periférico I2C1.
	constant I2C1_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000C100"), ADDR_BITS));
	-- Índice do periférico I2C1 nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant I2C1_INDEX : natural := 13;

	-- Endereço base do periférico AUDIO.
	constant AUDIO_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000D000"), ADDR_BITS));
	-- Índice do periférico AUDIO nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant AUDIO_INDEX : natural := 14;

	-- Endereço base do periférico ETH0.
	constant ETH0_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000E000"), ADDR_BITS));
	-- Índice do periférico ETH0 nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant ETH0_INDEX : natural := 15;

	-- Endereço base do periférico ETH1.
	constant ETH1_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000E100"), ADDR_BITS));
	-- Índice do periférico ETH1 nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant ETH1_INDEX : natural := 16;

	-- Endereço base do periférico TV.
	constant TV_BASE : addr_t := std_logic_vector(resize(unsigned'(x"8000F000"), ADDR_BITS));
	-- Índice do periférico TV nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant TV_INDEX : natural := 17;

	-- Endereço base do periférico SERIAL.
	constant SERIAL_BASE : addr_t := std_logic_vector(resize(unsigned'(x"80220000"), ADDR_BITS));
	-- Índice do periférico SERIAL nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant SERIAL_INDEX : natural := 18;

	-- Base de cada periférico, na ordem de `peripherals`.
	constant PERIPH_BASES : periph_addr_array_t(0 to PERIPH_COUNT - 1) := (
		FLASH_CTRL_INDEX => FLASH_CTRL_BASE,
		UART_INDEX => UART_BASE,
		DISPLAY_INDEX => DISPLAY_BASE,
		CLINT_INDEX => CLINT_BASE,
		PLIC_INDEX => PLIC_BASE,
		GPIO_INDEX => GPIO_BASE,
		KBD_INDEX => KBD_BASE,
		MOUSE_INDEX => MOUSE_BASE,
		SD_INDEX => SD_BASE,
		IR_INDEX => IR_BASE,
		LCD_INDEX => LCD_BASE,
		USB_INDEX => USB_BASE,
		I2C0_INDEX => I2C0_BASE,
		I2C1_INDEX => I2C1_BASE,
		AUDIO_INDEX => AUDIO_BASE,
		ETH0_INDEX => ETH0_BASE,
		ETH1_INDEX => ETH1_BASE,
		TV_INDEX => TV_BASE,
		SERIAL_INDEX => SERIAL_BASE
	);

	-- Máscara de cada janela: o periférico i responde quando (endereço and PERIPH_MASKS(i)) = PERIPH_BASES(i); a janela é a menor potência de dois que cobre o tamanho, com no mínimo 16 bytes.
	constant PERIPH_MASKS : periph_addr_array_t(0 to PERIPH_COUNT - 1) := (
		FLASH_CTRL_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFE0"), ADDR_BITS)),
		UART_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFC00"), ADDR_BITS)),
		DISPLAY_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFC00"), ADDR_BITS)),
		CLINT_INDEX => std_logic_vector(resize(unsigned'(x"FFFF0000"), ADDR_BITS)),
		PLIC_INDEX => std_logic_vector(resize(unsigned'(x"FFC00000"), ADDR_BITS)),
		GPIO_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFC0"), ADDR_BITS)),
		KBD_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFF0"), ADDR_BITS)),
		MOUSE_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFE0"), ADDR_BITS)),
		SD_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFC0"), ADDR_BITS)),
		IR_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFE0"), ADDR_BITS)),
		LCD_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFE0"), ADDR_BITS)),
		USB_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFC0"), ADDR_BITS)),
		I2C0_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFE0"), ADDR_BITS)),
		I2C1_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFE0"), ADDR_BITS)),
		AUDIO_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFC0"), ADDR_BITS)),
		ETH0_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFF00"), ADDR_BITS)),
		ETH1_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFF00"), ADDR_BITS)),
		TV_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFC0"), ADDR_BITS)),
		SERIAL_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFFF0"), ADDR_BITS))
	);

	-- Frequência do clock do domínio do núcleo e do CLINT, em Hz.
	constant CLOCK_HZ          : positive := 50000000;
	-- Frequência com que o mtime do CLINT conta, em Hz; é independente do CSR time.
	constant MTIME_HZ          : positive := 1000000;
	-- Ciclos de clock por incremento do mtime (tick_cycles do CLINT).
	constant CLINT_TICK_CYCLES : positive := 50;

	-- Número de fontes do PLIC (o maior identificador de fonte).
	constant PLIC_N_SOURCES     : positive := 18;
	-- Largura da prioridade e do limiar do PLIC, em bits.
	constant PLIC_PRIORITY_BITS : positive := 3;
	-- Largura do endereço de palavra da janela do PLIC.
	constant PLIC_ADDR_WIDTH    : positive := 20;
	-- Identificador da fonte UART_JTAG no PLIC.
	constant IRQ_UART_JTAG : positive := 2;
	-- Identificador da fonte FLASH no PLIC.
	constant IRQ_FLASH : positive := 6;
	-- Identificador da fonte KBD no PLIC.
	constant IRQ_KBD : positive := 5;
	-- Identificador da fonte MOUSE no PLIC.
	constant IRQ_MOUSE : positive := 7;
	-- Identificador da fonte SD no PLIC.
	constant IRQ_SD : positive := 8;
	-- Identificador da fonte IR no PLIC.
	constant IRQ_IR : positive := 9;
	-- Identificador da fonte LCD no PLIC.
	constant IRQ_LCD : positive := 10;
	-- Identificador da fonte USB no PLIC.
	constant IRQ_USB : positive := 11;
	-- Identificador da fonte I2C0 no PLIC.
	constant IRQ_I2C0 : positive := 12;
	-- Identificador da fonte I2C1 no PLIC.
	constant IRQ_I2C1 : positive := 13;
	-- Identificador da fonte AUDIO no PLIC.
	constant IRQ_AUDIO : positive := 14;
	-- Identificador da fonte ETH0 no PLIC.
	constant IRQ_ETH0 : positive := 15;
	-- Identificador da fonte ETH1 no PLIC.
	constant IRQ_ETH1 : positive := 16;
	-- Identificador da fonte TV no PLIC.
	constant IRQ_TV : positive := 17;
	-- Identificador da fonte SERIAL no PLIC.
	constant IRQ_SERIAL : positive := 18;

	-- Número de temporizadores de uso geral do mapa (`kind: timer`), o tamanho das tabelas abaixo.
	constant TIMER_COUNT : natural := 0;
	-- Índice de cada temporizador nas tabelas PERIPH_BASES e PERIPH_MASKS, na ordem de `peripherals`.
	constant TIMER_INDICES : integer_vector(0 to TIMER_COUNT - 1) := (
		others => 0
	);
	-- Fonte do PLIC de cada temporizador, na mesma ordem (zero sem PLIC).
	constant TIMER_IRQ_IDS : integer_vector(0 to TIMER_COUNT - 1) := (
		others => 0
	);

	-- Número de periféricos externos do mapa (`kind` de `Peripherals`), o tamanho das tabelas abaixo.
	constant EXT_COUNT : natural := 14;
	-- Índice de cada periférico externo nas tabelas PERIPH_BASES e PERIPH_MASKS, na ordem de `peripherals`.
	constant EXT_INDICES : integer_vector(0 to EXT_COUNT - 1) := (
		0 => KBD_INDEX,
		1 => MOUSE_INDEX,
		2 => SD_INDEX,
		3 => IR_INDEX,
		4 => LCD_INDEX,
		5 => USB_INDEX,
		6 => I2C0_INDEX,
		7 => I2C1_INDEX,
		8 => AUDIO_INDEX,
		9 => ETH0_INDEX,
		10 => ETH1_INDEX,
		11 => TV_INDEX,
		12 => SERIAL_INDEX,
		13 => GPIO_INDEX
	);
	-- Fonte do PLIC de cada periférico externo, na mesma ordem (zero sem linha ou sem PLIC).
	constant EXT_IRQ_IDS : integer_vector(0 to EXT_COUNT - 1) := (
		0 => IRQ_KBD,
		1 => IRQ_MOUSE,
		2 => IRQ_SD,
		3 => IRQ_IR,
		4 => IRQ_LCD,
		5 => IRQ_USB,
		6 => IRQ_I2C0,
		7 => IRQ_I2C1,
		8 => IRQ_AUDIO,
		9 => IRQ_ETH0,
		10 => IRQ_ETH1,
		11 => IRQ_TV,
		12 => IRQ_SERIAL,
		13 => 0
	);
	-- Posição de KBD nas tabelas EXT_*.
	constant KBD_EXT_POS : natural := 0;
	-- Posição de MOUSE nas tabelas EXT_*.
	constant MOUSE_EXT_POS : natural := 1;
	-- Posição de SD nas tabelas EXT_*.
	constant SD_EXT_POS : natural := 2;
	-- Posição de IR nas tabelas EXT_*.
	constant IR_EXT_POS : natural := 3;
	-- Posição de LCD nas tabelas EXT_*.
	constant LCD_EXT_POS : natural := 4;
	-- Posição de USB nas tabelas EXT_*.
	constant USB_EXT_POS : natural := 5;
	-- Posição de I2C0 nas tabelas EXT_*.
	constant I2C0_EXT_POS : natural := 6;
	-- Posição de I2C1 nas tabelas EXT_*.
	constant I2C1_EXT_POS : natural := 7;
	-- Posição de AUDIO nas tabelas EXT_*.
	constant AUDIO_EXT_POS : natural := 8;
	-- Posição de ETH0 nas tabelas EXT_*.
	constant ETH0_EXT_POS : natural := 9;
	-- Posição de ETH1 nas tabelas EXT_*.
	constant ETH1_EXT_POS : natural := 10;
	-- Posição de TV nas tabelas EXT_*.
	constant TV_EXT_POS : natural := 11;
	-- Posição de SERIAL nas tabelas EXT_*.
	constant SERIAL_EXT_POS : natural := 12;
	-- Posição de GPIO nas tabelas EXT_*.
	constant GPIO_EXT_POS : natural := 13;

	-- Frequência do clock do controlador da SDRAM, em Hz.
	constant SDRAM_CLOCK_HZ : positive := 100000000;
	-- Período desse clock, em picossegundos: a base da conversão dos tempos do chip em ciclos.
	constant SDRAM_TCK_PS   : positive := 10000;

end package de2_115_periph_map_pkg;
