-- ===========================================================================
-- Mapa de memória da plataforma, gerado por
-- `riscv-tools generate-memory-map` a partir de src/cyclone-v/fpga-uart-pins/platform.yaml.
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

package modular_map_pkg is

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
	constant HAS_ZIHINTNTL       : boolean  := false;
	-- A extensão Zihintpause está no perfil.
	constant HAS_ZIHINTPAUSE     : boolean  := false;
	-- A extensão Zifencei está no perfil.
	constant HAS_ZIFENCEI        : boolean  := true;
	-- A extensão Zicclsm está no perfil.
	constant HAS_ZICCLSM         : boolean  := true;
	-- A extensão Interrupts está no perfil.
	constant HAS_INTERRUPTS      : boolean  := false;
	-- A extensão Sscofpmf está no perfil.
	constant HAS_SSCOFPMF        : boolean  := false;
	-- A extensão Access_faults está no perfil.
	constant HAS_ACCESS_FAULTS   : boolean  := false;
	-- Expoente do tamanho da BOOT_MEMORY, em [0, 2**BOOT_MEMORY_BITS).
	constant BOOT_MEMORY_BITS       : natural  := 12;
	-- Tamanho da BOOT_MEMORY, em bytes.
	constant BOOT_MEMORY_SIZE_BYTES : positive := 4096;
	-- Base da FLASH, em KiB, logo depois da BOOT_MEMORY.
	constant FLASH_BASE_KIB      : natural  := 4;
	-- Fim exclusivo da FLASH, em KiB.
	constant FLASH_END_KIB       : natural  := 256;
	-- Armazenamento da FLASH, em bytes: a menor potência de dois que cobre
	-- [0, fim da FLASH).
	constant FLASH_STORAGE_BYTES : positive := 262144;
	-- A FLASH é alcançada pelo barramento (verdadeiro) ou pela porta direta (falso).
	constant FLASH_ON_BUS        : boolean  := true;
	-- Base da RAM, em KiB.
	constant RAM_BASE_KIB        : natural  := 1048576;
	-- Fim exclusivo da RAM, em KiB.
	constant RAM_END_KIB         : natural  := 1081344;
	-- Armazenamento da RAM, em bytes: a menor potência de dois que cobre
	-- o tamanho da RAM.
	constant RAM_STORAGE_BYTES   : positive := 33554432;
	-- Página de 4 KiB no topo da RAM (bits 31:12 do endereço), onde ficam as
	-- palavras que o hospedeiro compartilha com o programa.
	constant RAM_LAST_PAGE       : std_logic_vector(19 downto 0) :=
		x"41FFF";
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
	constant PERIPH_COUNT : natural := 1;
	-- Periféricos estritos: o interconector termina com erro o acesso ao que sobra da janela depois dos registradores.
	constant STRICT_PERIPH : boolean := true;
	-- Tabela de endereços, um por periférico.
	type periph_addr_array_t is array (natural range <>) of addr_t;

	-- Endereço base do periférico UART.
	constant UART_BASE : addr_t := std_logic_vector(resize(unsigned'(x"B0000000"), ADDR_BITS));
	-- Índice do periférico UART nas tabelas PERIPH_BASES e PERIPH_MASKS.
	constant UART_INDEX : natural := 0;

	-- Base de cada periférico, na ordem de `peripherals`.
	constant PERIPH_BASES : periph_addr_array_t(0 to PERIPH_COUNT - 1) := (
		UART_INDEX => UART_BASE
	);

	-- Máscara de cada janela: o periférico i responde quando (endereço and PERIPH_MASKS(i)) = PERIPH_BASES(i); a janela é a menor potência de dois que cobre o tamanho, com no mínimo 16 bytes.
	constant PERIPH_MASKS : periph_addr_array_t(0 to PERIPH_COUNT - 1) := (
		UART_INDEX => std_logic_vector(resize(unsigned'(x"FFFFFC00"), ADDR_BITS))
	);

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

end package modular_map_pkg;
