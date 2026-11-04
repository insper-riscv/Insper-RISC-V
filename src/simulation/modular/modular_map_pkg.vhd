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

	-- Registradores do perfil: 32 no RV32I e 16 no RV32E.
	constant NUM_REGS            : positive := 32;
	-- A extensão M está no perfil.
	constant HAS_M               : boolean  := true;
	-- A extensão Zmmul está no perfil.
	constant HAS_ZMMUL           : boolean  := false;
	-- A extensão Zicsr está no perfil.
	constant HAS_ZICSR           : boolean  := false;
	-- A extensão Zicntr está no perfil.
	constant HAS_ZICNTR          : boolean  := false;
	-- A extensão Zihpm está no perfil.
	constant HAS_ZIHPM           : boolean  := false;
	-- A extensão Zifencei está no perfil.
	constant HAS_ZIFENCEI        : boolean  := false;
	-- A extensão Zicclsm está no perfil.
	constant HAS_ZICCLSM         : boolean  := true;
	-- Expoente do tamanho da BOOT_ROM, que ocupa [0, 2**BOOT_ROM_BITS).
	constant BOOT_ROM_BITS       : natural  := 11;
	-- Tamanho da BOOT_ROM, em bytes.
	constant BOOT_ROM_SIZE_BYTES : positive := 2048;
	-- Base da ROM, em KiB, logo depois da BOOT_ROM.
	constant ROM_BASE_KIB        : natural  := 2;
	-- Fim exclusivo da ROM, em KiB.
	constant ROM_END_KIB         : natural  := 1024;
	-- Armazenamento da ROM, em bytes: a menor potência de dois que cobre
	-- [0, fim da ROM).
	constant ROM_STORAGE_BYTES   : positive := 1048576;
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
	-- Base da janela externa, em KiB; dali em diante é externo.
	constant EXT_BASE_KIB        : natural  := 2097152;
	-- Base da janela de periféricos, em KiB: os 2 GiB superiores do espaço.
	constant PERIPH_BASE_KIB     : natural  := 2097152;

end package modular_map_pkg;
