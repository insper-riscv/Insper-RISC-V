-- ===========================================================================
-- Mapa de memória da plataforma, gerado por
-- `riscv-tools generate-memory-map` a partir de src/simulation/internal-mem/platform.yaml.
--
-- Não edite à mão: mude o YAML da plataforma e rode o comando de novo. Os
-- limites estão em KiB, como os genéricos do núcleo, e os endereços dos
-- periféricos em bytes.
-- ===========================================================================

library ieee;
use ieee.std_logic_1164.all;

package internal_mem_map_pkg is

	-- Registradores do perfil: 32 no RV32I e 16 no RV32E.
	constant NUM_REGS            : positive := 32;
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
	-- A extensão Zifencei está no perfil.
	constant HAS_ZIFENCEI        : boolean  := false;
	-- A extensão Zicclsm está no perfil.
	constant HAS_ZICCLSM         : boolean  := true;
	-- Expoente do tamanho da BOOT_ROM, que ocupa [0, 2**BOOT_ROM_BITS).
	constant BOOT_ROM_BITS       : natural  := 12;
	-- Tamanho da BOOT_ROM, em bytes.
	constant BOOT_ROM_SIZE_BYTES : positive := 4096;
	-- Base da ROM, em KiB, logo depois da BOOT_ROM.
	constant ROM_BASE_KIB        : natural  := 4;
	-- Fim exclusivo da ROM, em KiB.
	constant ROM_END_KIB         : natural  := 32;
	-- Armazenamento da ROM, em bytes: a menor potência de dois que cobre
	-- [0, fim da ROM).
	constant ROM_STORAGE_BYTES   : positive := 32768;
	-- A ROM fica fora do núcleo.
	constant ROM_EXTERNAL        : boolean  := false;
	-- Base da RAM, em KiB.
	constant RAM_BASE_KIB        : natural  := 32;
	-- Fim exclusivo da RAM, em KiB.
	constant RAM_END_KIB         : natural  := 192;
	-- Armazenamento da RAM, em bytes: a menor potência de dois que cobre
	-- o tamanho da RAM.
	constant RAM_STORAGE_BYTES   : positive := 262144;
	-- Página de 4 KiB no topo da RAM (bits 31:12 do endereço), onde ficam as
	-- palavras que o hospedeiro compartilha com o programa.
	constant RAM_LAST_PAGE       : std_logic_vector(19 downto 0) :=
		x"0002F";
	-- A RAM fica fora do núcleo.
	constant RAM_EXTERNAL        : boolean  := false;
	-- Base da janela externa, em KiB; dali em diante é externo.
	constant EXT_BASE_KIB        : natural  := 2097152;
	-- Base da janela de periféricos, em KiB: os 2 GiB superiores do espaço.
	constant PERIPH_BASE_KIB     : natural  := 2097152;

	-- Endereço base do periférico UART.
	constant UART_BASE : std_logic_vector(31 downto 0) := x"C0000000";
	-- Índice da janela de 256 MiB do periférico UART (bits 30:28 do endereço).
	constant UART_ID   : natural := 4;

end package internal_mem_map_pkg;
