-- =============================================================================
-- Topo mínimo da medição M.0.6 (tests/multifpga/m0): uma instância do sld_virtual_jtag, como a do
-- sdram_jtag_shell, com um registrador de deslocamento de 8 bits atrás dela, para
-- o sintetizador manter a instância. Só serve ao quartus_map das famílias.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;

library altera_mf;
use altera_mf.altera_mf_components.all;

entity m0_vjtag_top is
    port (
        -- Saída do registrador de deslocamento.
        o_bit : out   std_logic
    );
end entity m0_vjtag_top;

architecture rtl of m0_vjtag_top is

    -- Relógio do TAP virtual.
    signal tck    : std_logic;
    -- Entrada de dados do TAP virtual.
    signal tdi    : std_logic;
    -- Saída de dados do TAP virtual.
    signal tdo    : std_logic;
    -- Instrução carregada no registrador de instrução virtual.
    signal ir_in  : std_logic_vector(1 downto 0);
    -- Estado Shift-DR da cadeia virtual.
    signal st_sdr : std_logic;
    -- Registrador de deslocamento atrás da instância.
    signal shreg  : std_logic_vector(7 downto 0) := (others => '0');

begin

    u_vjtag : component sld_virtual_jtag
        generic map (
            lpm_type                => "sld_virtual_jtag",
            lpm_hint                => "sld_instance_index=0",
            sld_auto_instance_index => "YES",
            sld_instance_index      => 0,
            sld_ir_width            => 2,
            sld_sim_n_scan          => 0,
            sld_sim_total_length    => 0,
            sld_sim_action          => ""
        )
        port map (
            tdo                => tdo,
            ir_out             => (others => '0'),
            tck                => tck,
            tdi                => tdi,
            ir_in              => ir_in,
            virtual_state_cdr  => open,
            virtual_state_sdr  => st_sdr,
            virtual_state_e1dr => open,
            virtual_state_pdr  => open,
            virtual_state_e2dr => open,
            virtual_state_udr  => open,
            virtual_state_cir  => open,
            virtual_state_uir  => open
        );

    process (tck) is
    begin

        if rising_edge(tck) then
            if st_sdr = '1' then
                shreg <= tdi & shreg(7 downto 1);
            end if;
        end if;

    end process;

    tdo   <= shreg(0);
    o_bit <= shreg(7) xor ir_in(0);

end architecture rtl;
