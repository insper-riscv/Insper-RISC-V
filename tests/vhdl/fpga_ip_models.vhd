-- =============================================================================
-- Modelos comportamentais dos IPs da Intel do topo de hardware internal-mem
--
-- O core_fpga_test instancia a BOOT_MEMORY, a FLASH, a RAM e o invólucro do
-- Virtual JTAG da FLASH, que são IPs da Intel (altsyncram e sld_virtual_jtag)
-- e só analisam com a biblioteca altera_mf do Quartus, que a imagem de
-- ferramentas não tem. Estas quatro entidades têm os mesmos nomes, genéricos e
-- portas dos invólucros de Memory/src/*/Cyclone-V, em VHDL puro, para o
-- GHDL elaborar e simular o topo de hardware real, sem alterá-lo.
--
-- A BOOT_MEMORY guarda o salto para a entrada da FLASH (0x1000) e a FLASH guarda
-- o programa mínimo nessa entrada: guarda 0x5A na base da RAM (0x8000), lê de
-- volta, soma 1 e guarda o resultado na palavra seguinte. O invólucro do
-- Virtual JTAG fica sem hospedeiro: nenhum comando chega ao carregador.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;

package fpga_ip_models_pkg is

    -- Índice da palavra de entrada do programa na FLASH (0x1000 / 4).
    constant ENTRY_WORD : natural := 1024;

    -- Número de palavras do programa mínimo.
    constant PROGRAM_WORDS : natural := 7;

    -- Vetor de palavras do programa mínimo (lui, addi, sw, lw, addi, sw, jal).
    type program_t is array(0 to PROGRAM_WORDS - 1) of std_logic_vector(31 downto 0);

    -- Programa mínimo da FLASH, a partir da entrada.
    constant PROGRAM : program_t :=
    (
        x"000082B7",
        x"05A00313",
        x"0062A023",
        x"0002A383",
        x"00138393",
        x"0072A223",
        x"0000006F"
    );

    -- Instrução jal x0, 0x1000 da BOOT_MEMORY.
    constant BOOT_JUMP : std_logic_vector(31 downto 0) := x"0000106F";

end package fpga_ip_models_pkg;

-- -----------------------------------------------------------------------------
-- BOOT_MEMORY de uma porta com leitura registrada
-- -----------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.fpga_ip_models_pkg.all;

entity boot_memory is
    generic (
        -- Tamanho da memória em bytes, uma potência de dois.
        size_bytes : positive := 4096
    );
    port (
        -- Índice da palavra lida.
        i_address : in    std_logic_vector(log2_exact(size_bytes) - 3 downto 0);
        -- Clock da leitura.
        i_clk     : in    std_logic                     := '1';
        -- Habilita a leitura.
        i_rden    : in    std_logic                     := '1';
        -- Habilita a escrita (a BOOT_MEMORY não escreve).
        i_wren    : in    std_logic                     := '0';
        -- Dado de escrita (não usado).
        i_data    : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Palavra lida, um ciclo depois do endereço.
        o_q       : out   std_logic_vector(31 downto 0)
    );
end entity boot_memory;

architecture sim of boot_memory is

    -- Vetor de palavras da BOOT_MEMORY.
    type words_t is array(0 to size_bytes / 4 - 1) of std_logic_vector(31 downto 0);

    -- Conteúdo da BOOT_MEMORY: o salto para a FLASH na palavra 0.
    constant CONTENT : words_t := (0 => BOOT_JUMP, others => (others => '0'));

    -- Registrador de saída.
    signal q_r : std_logic_vector(31 downto 0) := (others => '0');

begin

    o_q <= q_r;

    p_read : process (i_clk) is
    begin

        if rising_edge(i_clk) then
            if i_rden = '1' then
                q_r <= CONTENT(to_integer(unsigned(i_address)));
            end if;
        end if;

    end process p_read;

end architecture sim;

-- -----------------------------------------------------------------------------
-- FLASH de duas portas, a B com escrita
-- -----------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.fpga_ip_models_pkg.all;

entity flash is
    generic (
        -- Tamanho da memória em bytes, uma potência de dois.
        size_bytes : positive := 32768
    );
    port (
        -- Clock da porta A.
        i_clk_a     : in    std_logic                     := '1';
        -- Índice da palavra lida pela porta A.
        i_address_a : in    std_logic_vector(log2_exact(size_bytes) - 3 downto 0);
        -- Habilita a leitura da porta A.
        i_rden_a    : in    std_logic                     := '1';
        -- Palavra lida pela porta A.
        o_q_a       : out   std_logic_vector(31 downto 0);
        -- Clock da porta B.
        i_clk_b     : in    std_logic                     := '1';
        -- Índice da palavra acessada pela porta B.
        i_address_b : in    std_logic_vector(log2_exact(size_bytes) - 3 downto 0);
        -- Habilita a leitura da porta B.
        i_rden_b    : in    std_logic                     := '1';
        -- Habilita a escrita da porta B.
        i_wren_b    : in    std_logic                     := '0';
        -- Dado de escrita da porta B.
        i_data_b    : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Palavra lida pela porta B.
        o_q_b       : out   std_logic_vector(31 downto 0)
    );
end entity flash;

architecture sim of flash is

    -- Vetor de palavras da FLASH.
    type words_t is array(0 to size_bytes / 4 - 1) of std_logic_vector(31 downto 0);

    -- Monta o conteúdo inicial: o programa mínimo a partir da entrada.

    function initial return words_t is

        -- Conteúdo montado.
        variable words : words_t := (others => (others => '0'));

    begin

        for i in 0 to PROGRAM_WORDS - 1 loop

            words(ENTRY_WORD + i) := PROGRAM(i);

        end loop;

        return words;

    end function initial;

    -- Conteúdo da FLASH.
    signal mem : words_t := initial;

    -- Registrador de saída da porta A.
    signal q_a_r : std_logic_vector(31 downto 0) := (others => '0');

    -- Registrador de saída da porta B.
    signal q_b_r : std_logic_vector(31 downto 0) := (others => '0');

begin

    o_q_a <= q_a_r;
    o_q_b <= q_b_r;

    -- Porta A: só lê.
    p_port_a : process (i_clk_a) is
    begin

        if rising_edge(i_clk_a) then
            if i_rden_a = '1' then
                q_a_r <= mem(to_integer(unsigned(i_address_a)));
            end if;
        end if;

    end process p_port_a;

    -- Porta B: lê e escreve.
    p_port_b : process (i_clk_b) is
    begin

        if rising_edge(i_clk_b) then
            if i_wren_b = '1' then
                mem(to_integer(unsigned(i_address_b))) <= i_data_b;
                q_b_r                                  <= i_data_b;
            elsif i_rden_b = '1' then
                q_b_r <= mem(to_integer(unsigned(i_address_b)));
            end if;
        end if;

    end process p_port_b;

end architecture sim;

-- -----------------------------------------------------------------------------
-- RAM de uma porta com habilita de bytes
-- -----------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;

entity ram is
    generic (
        -- Tamanho da memória em bytes, uma potência de dois.
        size_bytes : positive := 262144;
        -- Número de palavras do IP (não usado no modelo).
        word_count : positive := 65536
    );
    port (
        -- Índice da palavra acessada.
        i_address : in    std_logic_vector(log2_exact(size_bytes) - 3 downto 0);
        -- Habilita de bytes da escrita, um bit por byte.
        i_byteena : in    std_logic_vector(3 downto 0) := (others => '1');
        -- Clock do acesso.
        i_clk     : in    std_logic                    := '1';
        -- Dado de escrita.
        i_data    : in    std_logic_vector(31 downto 0);
        -- Habilita a leitura.
        i_rden    : in    std_logic                    := '1';
        -- Habilita a escrita.
        i_wren    : in    std_logic;
        -- Palavra lida, um ciclo depois do endereço.
        o_q       : out   std_logic_vector(31 downto 0)
    );
end entity ram;

architecture sim of ram is

    -- Vetor de palavras da RAM.
    type words_t is array(0 to size_bytes / 4 - 1) of std_logic_vector(31 downto 0);

    -- Registrador de saída.
    signal q_r : std_logic_vector(31 downto 0) := (others => '0');

begin

    o_q <= q_r;

    p_ram : process (i_clk) is

        -- Conteúdo da RAM.
        variable mem   : words_t := (others => (others => '0'));
        -- Índice da palavra acessada.
        variable index : natural;

    begin

        if rising_edge(i_clk) then
            index := to_integer(unsigned(i_address));
            if i_wren = '1' then

                for b in 0 to 3 loop

                    if i_byteena(b) = '1' then
                        mem(index)(8 * b + 7 downto 8 * b) := i_data(8 * b + 7 downto 8 * b);
                    end if;

                end loop;

            end if;
            if i_rden = '1' then
                q_r <= mem(index);
            end if;
        end if;

    end process p_ram;

end architecture sim;

-- -----------------------------------------------------------------------------
-- Invólucro do Virtual JTAG da FLASH, sem hospedeiro
-- -----------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;

entity flash_jtag_shell is
    port (
        -- Alternância que pede um comando ao carregador (parada).
        o_cmd_tog    : out   std_logic;
        -- Operação do comando.
        o_op         : out   std_logic_vector(3 downto 0);
        -- Endereço de palavra do comando.
        o_addr       : out   std_logic_vector(23 downto 0);
        -- Dado do comando.
        o_data       : out   std_logic_vector(31 downto 0);
        -- Alternância que confirma o comando concluído (não usada).
        i_done_tog   : in    std_logic;
        -- Endereço da resposta do comando (não usado).
        i_rsp_addr   : in    std_logic_vector(23 downto 0);
        -- Dado da resposta do comando (não usado).
        i_rsp_data   : in    std_logic_vector(31 downto 0);
        -- Status da resposta do comando (não usado).
        i_rsp_status : in    std_logic_vector(7 downto 0)
    );
end entity flash_jtag_shell;

architecture sim of flash_jtag_shell is

begin

    o_cmd_tog <= '0';
    o_op      <= (others => '0');
    o_addr    <= (others => '0');
    o_data    <= (others => '0');

end architecture sim;
