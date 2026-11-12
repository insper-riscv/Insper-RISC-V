-- =============================================================================
-- Modelo comportamental do PLL para simulação
--
-- Substitui o pll.vhd gerado pelo Quartus na simulação com GHDL, pois o modelo do altera_pll
-- é SystemVerilog. Mantém o nome e as portas do PLL real, por isso as portas não levam os
-- prefixos i_ e o_ (o top as associa pelos nomes do IP gerado).
--
-- Três saídas na frequência da referência (50 MHz), ciclo de trabalho de 50 %, defasadas em
-- 0 ps, 6667 ps e 13333 ps. O sinal locked sobe LOCK_CYCLES ciclos da referência depois de
-- rst descer. Não faz parte do projeto Quartus, que sintetiza o PLL real.
-- =============================================================================

library IEEE;
use IEEE.std_logic_1164.all;

entity pll is
	port (
		-- Clock de referência (50 MHz).
		refclk   : in  std_logic := '0';
		-- Reset do PLL, ativo em '1'.
		rst      : in  std_logic := '0';
		-- Saída 0, em fase com a referência.
		outclk_0 : out std_logic;
		-- Saída 1, defasada em 6667 ps.
		outclk_1 : out std_logic;
		-- Saída 2, defasada em 13333 ps.
		outclk_2 : out std_logic;
		-- Indica o travamento do PLL ('1' = travado).
		locked   : out std_logic
	);
end entity pll;

architecture sim of pll is
	-- Ciclos da referência entre a liberação de rst e o travamento.
	constant LOCK_CYCLES : natural := 10;
	-- Fases 0, 1 e 2 derivadas da referência.
	signal c0, c1, c2 : std_logic := '0';
	-- Indicador de travamento registrado.
	signal lock_reg   : std_logic := '0';
begin
	c0 <= refclk;
	c1 <= transport refclk after 6667 ps;
	c2 <= transport refclk after 13333 ps;

	outclk_0 <= c0;
	outclk_1 <= c1;
	outclk_2 <= c2;

	process (refclk, rst)
		variable n : natural := 0;
	begin
		if rst = '1' then
			n := 0;
			lock_reg <= '0';
		elsif rising_edge(refclk) then
			if n < LOCK_CYCLES then
				n := n + 1;
			else
				lock_reg <= '1';
			end if;
		end if;
	end process;

	locked <= lock_reg;
end architecture sim;
