-- =============================================================================
-- Topo de teste do SoC com de zero a três temporizadores
--
-- O SoC com a tabela padrão de oito janelas, o PLIC no índice 7 e `timers` temporizadores nas janelas de índice
-- 0, 1 e 2 (0x80000000, 0x90000000 e 0xA0000000), cada um na sua fonte do PLIC (5, 7 e 8). O testbench faz o
-- papel da BOOT_MEMORY e observa a RAM interna do núcleo. Os generics de tabela do SoC não se passam pelo
-- simulador, então este topo os monta a partir do número de temporizadores.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use work.config_pkg.all;

entity soc_timers_top is
    generic (
        -- Quantidade de temporizadores instanciados no SoC (de 0 a 3).
        timers : natural range 0 to 3 := 0
    );
    port (
        -- Relógio das memórias de instrução (estágio IF).
        i_clk_fetch : in    std_logic;
        -- Relógio do núcleo e das memórias de dados.
        i_clk_core  : in    std_logic;
        -- Reset, ativo em '1'.
        i_rst       : in    std_logic;
        -- Endereço de palavra da busca de instrução.
        o_if_addr   : out   std_logic_vector(ADDR_BITS - 3 downto 0);
        -- Habilitação de leitura da busca de instrução.
        o_if_rden   : out   std_logic;
        -- Palavra de instrução devolvida pelo testbench.
        i_boot_data : in    word_t;
        -- Habilitação geral da RAM interna do núcleo.
        o_ram_en    : out   std_logic;
        -- Habilitação de escrita da RAM interna do núcleo.
        o_ram_wren  : out   std_logic;
        -- Endereço de byte do acesso à RAM interna.
        o_ram_addr  : out   addr_t;
        -- Dado de escrita na RAM interna.
        o_ram_wdata : out   word_t
    );
end entity soc_timers_top;

architecture rtl of soc_timers_top is

    -- Índice na tabela padrão de cada um dos três temporizadores possíveis.
    constant ALL_INDICES : integer_vector(0 to 2) := (0, 1, 2);
    -- Fonte do PLIC de cada um dos três temporizadores possíveis: a primeira linha livre e as duas seguintes.
    constant ALL_LINES   : integer_vector(0 to 2) := (5, 7, 8);

begin

    u_soc : entity work.soc
        generic map (
            boot_memory_size_bytes => 4096,
            rom_end_kib            => 1024,
            ram_base_kib           => 1024,
            ram_end_kib            => 2048,
            plic_n_sources         => 8,
            timer_indices          => ALL_INDICES(0 to timers - 1),
            timer_irq_ids          => ALL_LINES(0 to timers - 1)
        )
        port map (
            i_clk_core  => i_clk_core,
            i_clk_fetch => i_clk_fetch,
            i_rst       => i_rst,
            o_if_addr   => o_if_addr,
            o_if_rden   => o_if_rden,
            i_boot_data => i_boot_data,
            o_ram_en    => o_ram_en,
            o_ram_wren  => o_ram_wren,
            o_ram_addr  => o_ram_addr,
            o_ram_wdata => o_ram_wdata
        );

end architecture rtl;
