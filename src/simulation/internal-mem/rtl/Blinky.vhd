-- =============================================================================
-- Piscador de LED de 1 Hz
--
-- Conta HALF_PERIOD ciclos do clock de 50 MHz e inverte o LED a cada meio segundo,
-- indicando que a placa está viva, sem relação com o núcleo.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity Blinky is
  port (
    -- Clock de 50 MHz da placa.
    i_clk  : in  std_logic;       -- 50 MHz
    -- LED piscante (inverte a cada meio segundo).
    o_led  : out std_logic
  );
end entity;

architecture rtl of Blinky is
  -- Ciclos do clock de 50 MHz em meio segundo.
  constant HALF_PERIOD : natural := 25000000;  -- 0.5 s at 50 MHz
  -- Contador de ciclos do meio período (26 bits, maior que 25e6).
  signal cnt   : unsigned(25 downto 0) := (others => '0');  -- 26 bits > 25e6
  -- Estado atual do LED, invertido a cada meio período.
  signal led_r : std_logic := '0';
begin
  process(i_clk)
  begin
    if rising_edge(i_clk) then
      if cnt = to_unsigned(HALF_PERIOD-1, cnt'length) then
        cnt   <= (others => '0');
        led_r <= not led_r;  -- toggle every 0.5 s → 1 Hz blink
      else
        cnt <= cnt + 1;
      end if;
    end if;
  end process;

  o_led <= led_r;
end architecture;
