-- =============================================================================
-- Pacote do interconector: a tabela de janelas dos periféricos
--
-- O núcleo não sabe quais periféricos existem. Quem os decodifica é o interconector, com a tabela de
-- janelas que o pacote de mapa da plataforma (<plataforma>_map_pkg) gera do platform.yaml: o periférico i
-- é acertado por um endereço a quando (a and PERIPH_MASKS(i)) = PERIPH_BASES(i). Este pacote traz o tipo
-- das tabelas, o valor padrão delas (oito janelas de 256 MiB, as dos testes dos módulos) e as funções que
-- o interconector, o roteador AXI4 e o banco de periféricos AXI4 compartilham.
--
-- Cada janela é a menor potência de dois que contém os registradores do periférico, com no mínimo 16
-- bytes, e fica alinhada ao próprio tamanho. A máscara de uma janela de w bytes tem zero nos log2(w) bits
-- de baixo e um nos de cima. O tamanho de uma janela (PERIPH_SIZES) é o dos registradores; o resto da
-- janela é o padding.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.config_pkg.all;

package interconnect_pkg is

    -- Tabela de endereços, um por periférico (base, máscara ou tamanho da janela de cada um).
    type addr_array_t is array (natural range <>) of addr_t;

    -- Quantidade de janelas da tabela padrão.
    constant DEFAULT_PERIPH_COUNT : positive := 8;

    -- Bases da tabela padrão: 0x80000000 | i << 28, as janelas de 256 MiB do mapa antigo.
    function default_bases return addr_array_t;

    -- Máscaras da tabela padrão: as quatro posições de cima do endereço de 32 bits.
    function default_masks return addr_array_t;

    -- Tamanhos da tabela padrão: 64 KiB de registradores em cada janela.
    function default_sizes return addr_array_t;

    -- O endereço a acerta a janela de base b e máscara m.
    function window_hit (
        a : addr_t;
        b : addr_t;
        m : addr_t
    ) return boolean;

    -- Número de bits de endereço dentro da janela de máscara m (log2 do tamanho da janela).
    function window_bits (
        m : addr_t
    ) return natural;

    -- O endereço a cai dentro dos registradores da janela de máscara m e tamanho s (não no padding).
    function in_registers (
        a : addr_t;
        m : addr_t;
        s : addr_t
    ) return boolean;

    -- Endereço de ADDR_BITS bits de um valor sem sinal (corta os bits de cima).
    function addr_from (
        u : unsigned
    ) return addr_t;

    -- Índice da janela de base b na tabela de bases, ou zero quando nenhuma janela tem essa base.
    function index_of (
        table : addr_array_t;
        b     : addr_t
    ) return natural;

    -- Tamanho de cada janela de uma tabela de máscaras, em bytes (a janela inteira, sem padding).
    function window_sizes (
        masks : addr_array_t
    ) return addr_array_t;

    -- Todas as janelas são alinhadas, têm máscara contígua e não se sobrepõem duas a duas.
    function windows_valid (
        bases : addr_array_t;
        masks : addr_array_t
    ) return boolean;

end package interconnect_pkg;

package body interconnect_pkg is

    function default_bases return addr_array_t is

        -- Tabela devolvida.
        variable table : addr_array_t(0 to DEFAULT_PERIPH_COUNT - 1);

    begin

        for i in table'range loop

            table(i)                                      := (others => '0');
            table(i)(ADDR_BITS - 1)                       := '1';
            table(i)(ADDR_BITS - 2 downto ADDR_BITS - 4)  := std_logic_vector(to_unsigned(i, 3));

        end loop;

        return table;

    end function default_bases;

    function default_masks return addr_array_t is

        -- Tabela devolvida.
        variable table : addr_array_t(0 to DEFAULT_PERIPH_COUNT - 1);

    begin

        for i in table'range loop

            table(i)                                   := (others => '0');
            table(i)(ADDR_BITS - 1 downto ADDR_BITS - 4) := (others => '1');

        end loop;

        return table;

    end function default_masks;

    function default_sizes return addr_array_t is

        -- Tabela devolvida.
        variable table : addr_array_t(0 to DEFAULT_PERIPH_COUNT - 1);

    begin

        for i in table'range loop

            table(i)     := (others => '0');
            table(i)(16) := '1';

        end loop;

        return table;

    end function default_sizes;

    function window_hit (
        a : addr_t;
        b : addr_t;
        m : addr_t
    ) return boolean is
    begin

        return (a and m) = b;

    end function window_hit;

    function window_bits (
        m : addr_t
    ) return natural is

        -- Contagem dos zeros de baixo da máscara.
        variable count : natural := 0;

    begin

        for i in 0 to ADDR_BITS - 1 loop

            if m(i) = '0' then
                count := count + 1;
            else
                exit;
            end if;

        end loop;

        return count;

    end function window_bits;

    function in_registers (
        a : addr_t;
        m : addr_t;
        s : addr_t
    ) return boolean is
    begin

        return unsigned(a and not m) < unsigned(s);

    end function in_registers;

    function addr_from (
        u : unsigned
    ) return addr_t is
    begin

        return std_logic_vector(resize(u, ADDR_BITS));

    end function addr_from;

    function index_of (
        table : addr_array_t;
        b     : addr_t
    ) return natural is
    begin

        for i in table'range loop

            if table(i) = b then
                return i - table'low;
            end if;

        end loop;

        return 0;

    end function index_of;

    function window_sizes (
        masks : addr_array_t
    ) return addr_array_t is

        -- Tabela devolvida.
        variable table : addr_array_t(0 to masks'length - 1);

    begin

        for i in table'range loop

            table(i) := std_logic_vector(unsigned(not masks(masks'low + i)) + 1);

        end loop;

        return table;

    end function window_sizes;

    function windows_valid (
        bases : addr_array_t;
        masks : addr_array_t
    ) return boolean is

        -- A tabela é válida até que uma regra falhe.
        variable ok   : boolean := bases'length = masks'length;
        -- Endereço zero, para comparar.
        constant ZERO : addr_t  := (others => '0');

    begin

        if not ok then
            return false;
        end if;

        for i in 0 to bases'length - 1 loop

            -- A base cabe na janela (os bits de dentro da janela são zero).
            if (bases(bases'low + i) and not masks(masks'low + i)) /= ZERO then
                ok := false;
            end if;

            -- A máscara é contígua: o valor sem os zeros de baixo é só uns até o bit de cima.
            for k in window_bits(masks(masks'low + i)) to ADDR_BITS - 1 loop

                if masks(masks'low + i)(k) = '0' then
                    ok := false;
                end if;

            end loop;

            -- Duas janelas não se sobrepõem: alguma posição que as duas mascaram difere nas bases.
            for j in 0 to i - 1 loop

                if ((bases(bases'low + i) xor bases(bases'low + j)) and masks(masks'low + i) and masks(masks'low + j)) =
                   ZERO then
                    ok := false;
                end if;

            end loop;

        end loop;

        return ok;

    end function windows_valid;

end package body interconnect_pkg;
