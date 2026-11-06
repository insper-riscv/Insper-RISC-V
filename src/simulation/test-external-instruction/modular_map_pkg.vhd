-- ===========================================================================
-- Mapa de memória da plataforma, gerado por
-- `riscv-tools generate-memory-map` a partir de src/simulation/test-external-instruction/platform.yaml.
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
	constant HAS_ZICSR           : boolean  := false;
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
	constant HAS_ZIFENCEI        : boolean  := true;
	-- A extensão Zicclsm está no perfil.
	constant HAS_ZICCLSM         : boolean  := true;
	-- A extensão Interrupts está no perfil.
	constant HAS_INTERRUPTS      : boolean  := false;
	-- A extensão Sscofpmf está no perfil.
	constant HAS_SSCOFPMF        : boolean  := false;
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
	constant ROM_EXTERNAL        : boolean  := true;
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
	constant HAS_ICACHE          : boolean  := true;
	-- Existe cache de dados.
	constant HAS_DCACHE          : boolean  := false;
	-- Tamanho da cache de instruções, em bits (256 se não existe).
	constant ICACHE_SIZE_BITS    : positive := 4096;
	-- Tamanho da cache de dados, em bits (256 se não existe).
	constant DCACHE_SIZE_BITS    : positive := 256;
	-- A ROM é alcançada pela porta do núcleo (externa ou com cache).
	constant ROM_VIA_PORT        : boolean  := ROM_EXTERNAL or HAS_ICACHE;
	-- A RAM é alcançada pela porta do núcleo (externa ou com cache).
	constant RAM_VIA_PORT        : boolean  := RAM_EXTERNAL or HAS_DCACHE;

end package modular_map_pkg;
