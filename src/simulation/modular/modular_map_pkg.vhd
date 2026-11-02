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

	-- Expoente do tamanho da BOOT_ROM, que ocupa [0, 2**BOOT_ROM_BITS).
	constant BOOT_ROM_BITS  : natural := 11;
	-- Fim exclusivo da ROM, em KiB, logo depois da BOOT_ROM.
	constant ROM_END_KIB    : natural := 1024;
	-- Base da RAM, em KiB.
	constant RAM_BASE_KIB   : natural := 1024;
	-- Fim exclusivo da RAM, em KiB.
	constant RAM_END_KIB    : natural := 2048;
	-- Base da janela externa, em KiB.
	constant EXT_BASE_KIB   : natural := 1048576;
	-- Base da janela de periféricos, em KiB.
	constant PERIPH_BASE_KIB : natural := 2097152;

end package modular_map_pkg;
