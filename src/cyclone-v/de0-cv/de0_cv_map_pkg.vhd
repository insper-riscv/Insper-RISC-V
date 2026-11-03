-- ===========================================================================
-- Mapa de memória da plataforma, gerado por
-- `riscv-tools generate-memory-map` a partir de src/cyclone-v/de0-cv/platform.yaml.
--
-- Não edite à mão: mude o YAML da plataforma e rode o comando de novo. Os
-- limites estão em KiB, como os genéricos do núcleo, e os endereços dos
-- periféricos em bytes.
-- ===========================================================================

library ieee;
use ieee.std_logic_1164.all;

package de0_cv_map_pkg is

	-- Expoente do tamanho da BOOT_ROM, que ocupa [0, 2**BOOT_ROM_BITS).
	constant BOOT_ROM_BITS       : natural  := 11;
	-- Tamanho da BOOT_ROM, em bytes.
	constant BOOT_ROM_SIZE_BYTES : positive := 2048;
	-- Base da ROM, em KiB, logo depois da BOOT_ROM.
	constant ROM_BASE_KIB        : natural  := 2;
	-- Fim exclusivo da ROM, em KiB.
	constant ROM_END_KIB         : natural  := 256;
	-- Armazenamento da ROM, em bytes: a menor potência de dois que cobre
	-- [0, fim da ROM).
	constant ROM_STORAGE_BYTES   : positive := 262144;
	-- A ROM fica fora do núcleo.
	constant ROM_EXTERNAL       : boolean  := true;
	-- Base da RAM, em KiB.
	constant RAM_BASE_KIB        : natural  := 1048576;
	-- Fim exclusivo da RAM, em KiB.
	constant RAM_END_KIB         : natural  := 1114112;
	-- Armazenamento da RAM, em bytes: a menor potência de dois que cobre
	-- o tamanho da RAM.
	constant RAM_STORAGE_BYTES   : positive := 67108864;
	-- Página de 4 KiB no topo da RAM (bits 31:12 do endereço), onde ficam as
	-- palavras que o hospedeiro compartilha com o programa.
	constant RAM_LAST_PAGE       : std_logic_vector(19 downto 0) :=
		x"43FFF";
	-- A RAM fica fora do núcleo.
	constant RAM_EXTERNAL       : boolean  := true;
	-- Base da janela externa, em KiB; dali em diante é externo.
	constant EXT_BASE_KIB        : natural  := 2097152;
	-- Base da janela de periféricos, em KiB: os 2 GiB superiores do espaço.
	constant PERIPH_BASE_KIB     : natural  := 2097152;

	-- Endereço base do periférico UART.
	constant UART_BASE : std_logic_vector(31 downto 0) := x"C0000000";
	-- Índice da janela de 256 MiB do periférico UART (bits 30:28 do endereço).
	constant UART_ID   : natural := 4;

	-- Endereço base do periférico DISPLAY.
	constant DISPLAY_BASE : std_logic_vector(31 downto 0) := x"D0000000";
	-- Índice da janela de 256 MiB do periférico DISPLAY (bits 30:28 do endereço).
	constant DISPLAY_ID   : natural := 5;

end package de0_cv_map_pkg;
