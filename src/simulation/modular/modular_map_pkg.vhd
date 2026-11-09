-- ===========================================================================
-- Mapa de memória da plataforma, gerado por
-- `riscv-tools generate-memory-map` a partir de src/simulation/modular/platform.yaml.
--
-- Não edite à mão: mude o YAML da plataforma e rode o comando de novo. Os
-- limites estão em KiB, como os genéricos do núcleo, e os endereços dos
-- periféricos em bytes.
-- ===========================================================================

library ieee;
use ieee.std_logic_1164.all;

package modular_map_pkg is

	-- O perfil é o RV32E (16 registradores); falso é o RV32I (32).
	constant HAS_E               : boolean  := false;
	-- A extensão M está no perfil.
	constant HAS_M               : boolean  := true;
	-- A extensão Zmmul está no perfil.
	constant HAS_ZMMUL           : boolean  := false;
	-- A extensão Zicsr está no perfil.
	constant HAS_ZICSR           : boolean  := true;
	-- A extensão Zicntr está no perfil.
	constant HAS_ZICNTR          : boolean  := false;
	-- A extensão Zihpm está no perfil.
	constant HAS_ZIHPM           : boolean  := false;
	-- A extensão Zimop está no perfil.
	constant HAS_ZIMOP           : boolean  := true;
	-- A extensão Zicond está no perfil.
	constant HAS_ZICOND          : boolean  := true;
	-- A extensão Zihintntl está no perfil.
	constant HAS_ZIHINTNTL       : boolean  := false;
	-- A extensão Zihintpause está no perfil.
	constant HAS_ZIHINTPAUSE     : boolean  := false;
	-- A extensão Zifencei está no perfil.
	constant HAS_ZIFENCEI        : boolean  := false;
	-- A extensão Zicclsm está no perfil.
	constant HAS_ZICCLSM         : boolean  := true;
	-- A extensão Interrupts está no perfil.
	constant HAS_INTERRUPTS      : boolean  := true;
	-- A extensão Sscofpmf está no perfil.
	constant HAS_SSCOFPMF        : boolean  := false;
	-- A extensão Access_faults está no perfil.
	constant HAS_ACCESS_FAULTS   : boolean  := false;
	-- Expoente do tamanho da BOOT_MEMORY, em [0, 2**BOOT_MEMORY_BITS).
	constant BOOT_MEMORY_BITS       : natural  := 12;
	-- Tamanho da BOOT_MEMORY, em bytes.
	constant BOOT_MEMORY_SIZE_BYTES : positive := 4096;
	-- Base da ROM, em KiB, logo depois da BOOT_MEMORY.
	constant ROM_BASE_KIB        : natural  := 4;
	-- Fim exclusivo da ROM, em KiB.
	constant ROM_END_KIB         : natural  := 1024;
	-- Armazenamento da ROM, em bytes: a menor potência de dois que cobre
	-- [0, fim da ROM).
	constant ROM_STORAGE_BYTES   : positive := 1048576;
	-- A ROM fica fora do núcleo.
	constant ROM_EXTERNAL        : boolean  := false;
	-- Base da RAM, em KiB.
	constant RAM_BASE_KIB        : natural  := 1024;
	-- Fim exclusivo da RAM, em KiB.
	constant RAM_END_KIB         : natural  := 2048;
	-- Armazenamento da RAM, em bytes: a menor potência de dois que cobre
	-- o tamanho da RAM.
	constant RAM_STORAGE_BYTES   : positive := 1048576;
	-- Página de 4 KiB no topo da RAM (bits 31:12 do endereço), onde ficam as
	-- palavras que o hospedeiro compartilha com o programa.
	constant RAM_LAST_PAGE       : std_logic_vector(19 downto 0) :=
		x"001FF";
	-- A RAM fica fora do núcleo.
	constant RAM_EXTERNAL        : boolean  := false;
	-- Base da janela externa, em KiB; dali em diante é externo.
	constant EXT_BASE_KIB        : natural  := 2097152;
	-- Base da janela de periféricos, em KiB: os 2 GiB superiores do espaço.
	constant PERIPH_BASE_KIB     : natural  := 2097152;
	-- Existe cache de instruções.
	constant HAS_ICACHE          : boolean  := false;
	-- Existe cache de dados.
	constant HAS_DCACHE          : boolean  := false;
	-- Tamanho da cache de instruções, em bits (256 se não existe).
	constant ICACHE_SIZE_BITS    : positive := 256;
	-- Tamanho da cache de dados, em bits (256 se não existe).
	constant DCACHE_SIZE_BITS    : positive := 256;
	-- Largura da janela de endereços das caches, em bits: a tag guarda os bits abaixo dela (26 é 64 MiB, 27 é 128 MiB).
	constant CACHE_WINDOW_BITS   : natural  := 26;
	-- A ROM é alcançada pela porta do núcleo (externa ou com cache).
	constant ROM_VIA_PORT        : boolean  := ROM_EXTERNAL or HAS_ICACHE;
	-- A RAM é alcançada pela porta do núcleo (externa ou com cache).
	constant RAM_VIA_PORT        : boolean  := RAM_EXTERNAL or HAS_DCACHE;

	-- Janelas de 256 MiB do barramento de periféricos que têm periférico (bit n para o índice n, bits 30:28 do endereço).
	constant PERIPH_SLOTS : std_logic_vector(7 downto 0) := "11111111";

	-- Endereço base do periférico TIMER.
	constant TIMER_BASE : std_logic_vector(31 downto 0) := x"80000000";
	-- Índice da janela de 256 MiB do periférico TIMER (bits 30:28 do endereço).
	constant TIMER_ID   : natural := 0;

	-- Endereço base do periférico SWITCHES.
	constant SWITCHES_BASE : std_logic_vector(31 downto 0) := x"90000000";
	-- Índice da janela de 256 MiB do periférico SWITCHES (bits 30:28 do endereço).
	constant SWITCHES_ID   : natural := 1;

	-- Endereço base do periférico KEYS.
	constant KEYS_BASE : std_logic_vector(31 downto 0) := x"A0000000";
	-- Índice da janela de 256 MiB do periférico KEYS (bits 30:28 do endereço).
	constant KEYS_ID   : natural := 2;

	-- Endereço base do periférico UART.
	constant UART_BASE : std_logic_vector(31 downto 0) := x"B0000000";
	-- Índice da janela de 256 MiB do periférico UART (bits 30:28 do endereço).
	constant UART_ID   : natural := 3;

	-- Endereço base do periférico UART_JTAG.
	constant UART_JTAG_BASE : std_logic_vector(31 downto 0) := x"C0000000";
	-- Índice da janela de 256 MiB do periférico UART_JTAG (bits 30:28 do endereço).
	constant UART_JTAG_ID   : natural := 4;

	-- Endereço base do periférico DISPLAY.
	constant DISPLAY_BASE : std_logic_vector(31 downto 0) := x"D0000000";
	-- Índice da janela de 256 MiB do periférico DISPLAY (bits 30:28 do endereço).
	constant DISPLAY_ID   : natural := 5;

	-- Endereço base do periférico CLINT.
	constant CLINT_BASE : std_logic_vector(31 downto 0) := x"E0000000";
	-- Índice da janela de 256 MiB do periférico CLINT (bits 30:28 do endereço).
	constant CLINT_ID   : natural := 6;

	-- Endereço base do periférico PLIC.
	constant PLIC_BASE : std_logic_vector(31 downto 0) := x"F0000000";
	-- Índice da janela de 256 MiB do periférico PLIC (bits 30:28 do endereço).
	constant PLIC_ID   : natural := 7;

	-- Frequência do clock do domínio do núcleo e do CLINT, em Hz.
	constant CLOCK_HZ          : positive := 10000000;
	-- Frequência com que o mtime do CLINT conta, em Hz; é independente do CSR time.
	constant MTIME_HZ          : positive := 10000000;
	-- Ciclos de clock por incremento do mtime (tick_cycles do CLINT).
	constant CLINT_TICK_CYCLES : positive := 1;

	-- Número de fontes do PLIC (o maior identificador de fonte).
	constant PLIC_N_SOURCES     : positive := 6;
	-- Largura da prioridade e do limiar do PLIC, em bits.
	constant PLIC_PRIORITY_BITS : positive := 3;
	-- Largura do endereço de palavra da janela do PLIC.
	constant PLIC_ADDR_WIDTH    : positive := 20;
	-- Identificador da fonte UART no PLIC.
	constant IRQ_UART : positive := 1;
	-- Identificador da fonte UART_JTAG no PLIC.
	constant IRQ_UART_JTAG : positive := 2;
	-- Identificador da fonte SWITCHES no PLIC.
	constant IRQ_SWITCHES : positive := 3;
	-- Identificador da fonte KEYS no PLIC.
	constant IRQ_KEYS : positive := 4;
	-- Identificador da fonte TIMER no PLIC.
	constant IRQ_TIMER : positive := 5;
	-- Identificador da fonte FLASH no PLIC.
	constant IRQ_FLASH : positive := 6;

end package modular_map_pkg;
