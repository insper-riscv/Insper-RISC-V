-- =============================================================================
-- Decodificador atrás da porta de dados externa do core
--
-- Todo acesso que o núcleo não atende nas suas memórias diretas chega aqui, e o interconector o envia a um
-- entre dois tipos de escravo, ou o recusa, e devolve ao core o ready, o error e o dado desse escravo:
--
--   memória        o endereço cai na FLASH ou na RAM que a plataforma alcança pelo barramento
--                  (flash_on_bus e ram_on_bus): a porta passa direto, com os pulsos de leitura e
--                  escrita retidos enquanto outro escravo está selecionado
--   periférico i   (endereço and periph_masks(i)) = periph_bases(i): uma janela de periféricos da
--                  tabela da plataforma, com os bits periph_addr_width+1:2 (janela de 64 KiB com o
--                  valor padrão 14, 4 MiB com 20, o que o PLIC pede) como deslocamento de palavra
--   nenhum         o acesso termina com error ligado ao ready, e o dado lido é zero: o núcleo o
--                  trata como falha de acesso de load ou de store (causas 5 e 7)
--
-- O padding de uma janela (o que passa dos periph_sizes(i) bytes de registradores) é um acesso a lugar
-- nenhum quando strict_periph é verdadeiro; senão lê zero e a escrita não tem efeito.
--
-- Um acesso a periférico leva um ciclo do core: um único pulso de we ou re
-- (mesmo enquanto o core espera outra coisa), com ready em nível até mem_advance,
-- como o contrato do core pede. O dado lido de um load fica em rdata até o próximo load
-- completar, e a escolha de qual escravo o forneceu é registrada quando o load completa, de modo que
-- um load ainda no último estágio vê o seu próprio dado enquanto o acesso seguinte já está na porta.
-- O periférico i responde pelo índice i: p_we e p_re são one-hot com o índice e p_rdata guarda uma
-- palavra por índice, o índice i nos bits XLEN i + XLEN - 1 a XLEN i.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.config_pkg.all;
use work.interconnect_pkg.all;

entity ext_interconnect is
    generic (
        -- Número de janelas de periféricos da tabela (PERIPH_COUNT do pacote de mapa da plataforma); zero é uma
        -- plataforma sem periféricos, e todo endereço fora da memória termina em error.
        periph_count      : natural                    := DEFAULT_PERIPH_COUNT;
        -- Base de cada janela (PERIPH_BASES), alinhada ao tamanho da janela.
        periph_bases      : addr_array_t               := default_bases;
        -- Máscara de cada janela (PERIPH_MASKS): um nos bits que a janela fixa e zero nos de dentro dela.
        periph_masks      : addr_array_t               := default_masks;
        -- Bytes de registradores de cada janela (PERIPH_SIZES); o resto da janela é o padding.
        periph_sizes      : addr_array_t               := default_sizes;
        -- O padding de uma janela termina em error; falso, ele lê zero e a escrita não tem efeito.
        strict_periph     : boolean                    := true;
        -- Largura do deslocamento de palavra entregue ao periférico (14 é a janela de 64 KiB; o PLIC pede 20).
        periph_addr_width : positive range 2 to 30     := 14;
        -- A FLASH é alcançada pelo barramento (FLASH_ON_BUS).
        flash_on_bus      : boolean                    := false;
        -- Primeiro endereço da FLASH.
        flash_base        : addr_t                     := (others => '0');
        -- Último endereço da FLASH, inclusive.
        flash_last        : addr_t                     := (others => '0');
        -- A RAM é alcançada pelo barramento (RAM_ON_BUS).
        ram_on_bus        : boolean                    := true;
        -- Primeiro endereço da RAM.
        ram_base          : addr_t                     := std_logic_vector(resize(unsigned'(x"40000000"), ADDR_BITS));
        -- Último endereço da RAM, inclusive.
        ram_last          : addr_t                     := std_logic_vector(resize(unsigned'(x"43FFFFFF"), ADDR_BITS))
    );
    port (
        -- Clock do módulo.
        i_clk : in    std_logic;
        -- Reset, ativo em '1'.
        i_rst : in    std_logic;

        -- Endereço do acesso.
        i_addr        : in    addr_t;
        -- Dado de escrita.
        i_wdata       : in    word_t;
        -- Habilita de bytes da escrita, um bit por byte.
        i_byteena     : in    std_logic_vector(3 downto 0);
        -- Pedido de leitura ('1' = lê).
        i_rden        : in    std_logic;
        -- Pedido de escrita ('1' = escreve).
        i_wren        : in    std_logic;
        -- O pipeline avançou neste ciclo, o acesso em andamento pode ser concluído.
        i_mem_advance : in    std_logic;
        -- Acesso concluído, o dado lido é válido ('1').
        o_ready       : out   std_logic;
        -- Acesso concluído sem escravo que o atenda: falha de acesso, válida junto com o ready ('1').
        o_error       : out   std_logic;
        -- Dado lido.
        o_rdata       : out   word_t;

        -- Lado da memória com ready próprio: endereço do acesso.
        o_m_addr    : out   addr_t;
        -- Lado da memória com ready próprio: dado de escrita.
        o_m_wdata   : out   word_t;
        -- Lado da memória com ready próprio: habilita de bytes da escrita.
        o_m_byteena : out   std_logic_vector(3 downto 0);
        -- Lado da memória com ready próprio: pedido de leitura, retido enquanto outro escravo está selecionado.
        o_m_rden    : out   std_logic;
        -- Lado da memória com ready próprio: pedido de escrita, retido enquanto outro escravo está selecionado.
        o_m_wren    : out   std_logic;
        -- Lado da memória com ready próprio: acesso concluído ('1').
        i_m_ready   : in    std_logic;
        -- Lado da memória com ready próprio: dado lido.
        i_m_rdata   : in    word_t;

        -- Janela de periféricos: deslocamento de palavra dentro do periférico.
        o_p_addr    : out   std_logic_vector(periph_addr_width - 1 downto 0);
        -- Janela de periféricos: dado de escrita.
        o_p_wdata   : out   word_t;
        -- Janela de periféricos: habilita de bytes da escrita.
        o_p_byteena : out   std_logic_vector(3 downto 0);
        -- Janela de periféricos: pulso de escrita, um bit por periférico (one-hot com o índice da tabela).
        o_p_we      : out   std_logic_vector(periph_count - 1 downto 0);
        -- Janela de periféricos: pulso de leitura, um bit por periférico (one-hot com o índice da tabela).
        o_p_re      : out   std_logic_vector(periph_count - 1 downto 0);
        -- Janela de periféricos: dados lidos, uma palavra por periférico (o do índice i nos bits XLEN i + XLEN - 1 a XLEN i).
        i_p_rdata   : in    std_logic_vector(periph_count * XLEN - 1 downto 0)
    );
end entity ext_interconnect;

architecture rtl of ext_interconnect is

    -- Estados do decodificador: livre e acesso concluído aguardando o avanço do pipeline.
    type state_t is (ST_IDLE, ST_DONE);

    -- Bases da tabela, com a faixa normalizada de zero a periph_count - 1.
    constant BASES : addr_array_t(0 to periph_count - 1) := periph_bases;
    -- Máscaras da tabela, com a faixa normalizada.
    constant MASKS : addr_array_t(0 to periph_count - 1) := periph_masks;
    -- Tamanhos da tabela, com a faixa normalizada.
    constant SIZES : addr_array_t(0 to periph_count - 1) := periph_sizes;

    -- Estado atual do decodificador.
    signal st        : state_t                      := ST_IDLE;
    -- Janela acertada por periférico (zero sem janela acertada).
    signal hit       : std_logic_vector(periph_count - 1 downto 0);
    -- O endereço cai nos registradores de cada janela, e não no padding.
    signal in_reg    : std_logic_vector(periph_count - 1 downto 0);
    -- Índice da janela acertada.
    signal idx       : natural range 0 to maximum(periph_count - 1, 0);
    -- O endereço acerta um periférico e, com strict_periph, cai nos registradores dele.
    signal is_periph : std_logic;
    -- O endereço cai numa memória alcançada pelo barramento.
    signal is_mem    : std_logic;
    -- Há um acesso em andamento.
    signal active    : std_logic;
    -- '1': o último load veio de um periférico (ou terminou em error).
    signal sel_wb    : std_logic                    := '0';
    -- O acesso guardado terminou em error.
    signal err_q     : std_logic                    := '0';
    -- Dado lido do periférico, registrado.
    signal p_rdata_q : word_t                       := (others => '0');
    -- Dado do load aguardando o avanço do pipeline.
    signal pending   : word_t                       := (others => '0');
    -- Pulso de leitura ou escrita do periférico neste ciclo.
    signal pulse     : std_logic;

    -- O endereço a está entre lo e hi, inclusive.
    function in_range (
        a  : addr_t;
        lo : addr_t;
        hi : addr_t
    ) return boolean is
    begin

        return unsigned(a) >= unsigned(lo) and unsigned(a) <= unsigned(hi);

    end function in_range;

begin

    assert windows_valid(BASES, MASKS)
        report "periph_bases e periph_masks: cada janela deve ser alinhada, de máscara contígua e sem sobrepor outra"
        severity failure;

    gen_window_check : for i in 0 to periph_count - 1 generate
    begin

        assert window_bits(MASKS(i)) >= 4
            report "periph_masks: a janela de um periférico tem no mínimo 16 bytes"
            severity failure;

        hit(i)    <= '1' when window_hit(i_addr, BASES(i), MASKS(i)) else '0';
        in_reg(i) <= '1' when in_registers(i_addr, MASKS(i), SIZES(i)) else '0';

    end generate gen_window_check;

    p_index : process (hit) is

        -- Índice da janela acertada, zero sem janela acertada.
        variable v_idx : natural range 0 to maximum(periph_count - 1, 0);

    begin

        v_idx := 0;

        for i in 0 to periph_count - 1 loop

            if hit(i) = '1' then
                v_idx := i;
            end if;

        end loop;

        idx <= v_idx;

    end process p_index;

    active    <= i_rden or i_wren;
    is_periph <= '1' when (or hit) = '1' and (not strict_periph or in_reg(idx) = '1') else '0';
    is_mem    <= '1' when (flash_on_bus and in_range(i_addr, flash_base, flash_last)) or
                          (ram_on_bus and in_range(i_addr, ram_base, ram_last)) else '0';

    o_m_addr    <= i_addr;
    o_m_wdata   <= i_wdata;
    o_m_byteena <= i_byteena;
    o_m_rden    <= i_rden and is_mem;
    o_m_wren    <= i_wren and is_mem;

    o_p_addr    <= i_addr(periph_addr_width + 1 downto 2);
    o_p_wdata   <= i_wdata;
    o_p_byteena <= i_byteena;

    pulse <= '1' when st = ST_IDLE and is_periph = '1' and active = '1' else '0';

    p_decode : process (pulse, idx, i_rden, i_wren) is
    begin

        o_p_we <= (others => '0');
        o_p_re <= (others => '0');

        if pulse = '1' then
            o_p_we(idx) <= i_wren;
            o_p_re(idx) <= i_rden;
        end if;

    end process p_decode;

    o_ready <= i_m_ready when is_mem = '1' else
               '1' when st = ST_DONE else
               '0';
    o_error <= '1' when st = ST_DONE and err_q = '1' else '0';
    o_rdata <= p_rdata_q when sel_wb = '1' else i_m_rdata;

    p_registers : process (i_clk) is
    begin

        if rising_edge(i_clk) then
            if i_rst = '1' then
                st        <= ST_IDLE;
                sel_wb    <= '0';
                err_q     <= '0';
                p_rdata_q <= (others => '0');
                pending   <= (others => '0');
            else

                case st is

                    when ST_IDLE =>

                        if is_mem = '0' and active = '1' then
                            if is_periph = '1' then
                                pending <= i_p_rdata(XLEN * idx + XLEN - 1 downto XLEN * idx);
                                err_q   <= '0';
                            else
                                pending <= (others => '0');
                                err_q   <= '1';
                            end if;
                            st <= ST_DONE;
                        end if;

                    when ST_DONE =>

                        if i_mem_advance = '1' then
                            if i_rden = '1' then
                                p_rdata_q <= pending;
                                sel_wb    <= '1';
                            end if;
                            err_q <= '0';
                            st    <= ST_IDLE;
                        end if;

                end case;

                -- um acesso à memória que completa devolve o dado à memória
                if is_mem = '1' and i_rden = '1' and i_m_ready = '1' and i_mem_advance = '1' then
                    sel_wb <= '0';
                end if;
            end if;
        end if;

    end process p_registers;

end architecture rtl;
