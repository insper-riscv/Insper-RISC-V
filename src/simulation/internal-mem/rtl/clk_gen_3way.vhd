-- =============================================================================
-- Gerador de clock de três fases
--
-- Divide o clock base por três: um contador mod-3, atualizado na borda de descida de i_clk,
-- ativa uma das saídas o_clk0, o_clk1 e o_clk2 por vez durante a fase alta de i_clk.
-- O reset i_rst é assíncrono, ativo em '1', e zera as três saídas imediatamente.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity clk_gen_3way is
    port (
        -- Clock base (entrada).
        i_clk  : in    std_logic;
        -- Reset assíncrono, ativo em '1'.
        i_rst  : in    std_logic;
        -- Pulso da fase 0 (ativo quando o contador vale 0 e i_clk está em '1').
        o_clk0 : out   std_logic;
        -- Pulso da fase 1 (ativo quando o contador vale 1 e i_clk está em '1').
        o_clk1 : out   std_logic;
        -- Pulso da fase 2 (ativo quando o contador vale 2 e i_clk está em '1').
        o_clk2 : out   std_logic
    );
end entity clk_gen_3way;

architecture rtl of clk_gen_3way is

    -- Contador mod-3 que seleciona a fase ativa.
    signal cnt : unsigned(1 downto 0) := (others => '0');

begin

    -- Contador mod-3 atualizado na borda de descida; i_rst assíncrono
    process (i_clk, i_rst) is

        -- Próximo valor do contador mod-3.
        variable next_cnt : unsigned(1 downto 0);

    begin

        if i_rst = '1' then
            cnt <= (others => '0');
        elsif falling_edge(i_clk) then
            if cnt = to_unsigned(2, cnt'length) then
                next_cnt := (others => '0');
            else
                next_cnt := cnt + 1;
            end if;
            cnt <= next_cnt;
        end if;

    end process;

    -- Saídas: ativas apenas durante a fase baixa de i_clk e quando cnt corresponde
    -- Pulso da fase 0 (ativo quando o contador vale 0 e i_clk está em '1').
    o_clk0 <= '0' when i_rst = '1' else
              '1' when (i_clk = '1' and cnt = to_unsigned(0, cnt'length)) else
              '0';

    -- Pulso da fase 1 (ativo quando o contador vale 1 e i_clk está em '1').
    o_clk1 <= '0' when i_rst = '1' else
              '1' when (i_clk = '1' and cnt = to_unsigned(1, cnt'length)) else
              '0';

    -- Pulso da fase 2 (ativo quando o contador vale 2 e i_clk está em '1').
    o_clk2 <= '0' when i_rst = '1' else
              '1' when (i_clk = '1' and cnt = to_unsigned(2, cnt'length)) else
              '0';

end architecture rtl;
