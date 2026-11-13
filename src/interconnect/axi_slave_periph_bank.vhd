-- =============================================================================
-- Escravo AXI4 na frente da janela de periféricos do ext_interconnect
--
-- Os periféricos da tabela da plataforma (periph_bases, periph_masks e periph_sizes, a mesma do
-- ext_interconnect), cada um com uma janela selecionada por (endereço and máscara) = base e a palavra
-- dentro dela pelos bits periph_addr_width+1:2. O lado do periférico é o que o ext_interconnect dá:
-- p_we ou p_re do periférico selecionado é um pulso de um clock por acesso, com p_addr, p_wdata e
-- p_byteena ao lado, e o dado lido do periférico (p_rdata, uma palavra por índice, o índice i nos bits
-- XLEN i + XLEN - 1 a XLEN i) é lido no clock desse pulso.
--
-- Um endereço sem janela acertada é respondido com DECERR, e um acesso ao padding de uma janela (além
-- dos periph_sizes(i) bytes de registradores), com strict_periph, com SLVERR; ambos leem zero, não
-- tocam periférico e completam como qualquer outra transação.
--
-- Periféricos não são memória: só um único beat de 4 bytes (len 0, size de 4
-- bytes, INCR, alinhado) é atendido. Qualquer outra transação é respondida com
-- SLVERR depois de todos os seus beats serem consumidos (escrita) ou dados como
-- zeros (leitura), e nenhum periférico é tocado. Os IDs não são carregados
-- (largura 0). Como no axi_slave_word_bridge: AW primeiro e depois os beats de W,
-- uma leitura cede a uma escrita oferecida, uma transação por vez, e a resposta
-- espera bready ou rready.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.config_pkg.all;
use work.interconnect_pkg.all;

entity axi_slave_periph_bank is
    generic (
        -- Número de janelas de periféricos da tabela (PERIPH_COUNT do pacote de mapa da plataforma).
        periph_count      : positive               := DEFAULT_PERIPH_COUNT;
        -- Base de cada janela (PERIPH_BASES).
        periph_bases      : addr_array_t           := default_bases;
        -- Máscara de cada janela (PERIPH_MASKS).
        periph_masks      : addr_array_t           := default_masks;
        -- Bytes de registradores de cada janela (PERIPH_SIZES); o resto da janela é o padding.
        periph_sizes      : addr_array_t           := default_sizes;
        -- Um acesso ao padding de uma janela é respondido com SLVERR; falso, ele lê zero e a escrita não tem efeito.
        strict_periph     : boolean                := true;
        -- Largura do deslocamento de palavra entregue ao periférico (14 é a janela de 64 KiB).
        periph_addr_width : positive range 2 to 30 := 14
    );
    port (
        -- Clock do módulo.
        i_clk : in    std_logic;
        -- Reset, ativo em '1'.
        i_rst : in    std_logic;

        -- Porta escravo AXI4, canal de endereço de escrita: validade da transferência ('1' = válida).
        i_s_awvalid : in    std_logic;
        -- Porta escravo AXI4, canal de endereço de escrita: destino pronto para aceitar a transferência ('1').
        o_s_awready : out   std_logic;
        -- Porta escravo AXI4, canal de endereço de escrita: endereço do primeiro beat.
        i_s_awaddr  : in    addr_t;
        -- Porta escravo AXI4, canal de endereço de escrita: número de beats da rajada menos um.
        i_s_awlen   : in    std_logic_vector(7 downto 0);
        -- Porta escravo AXI4, canal de endereço de escrita: log2 do número de bytes por beat.
        i_s_awsize  : in    std_logic_vector(2 downto 0);
        -- Porta escravo AXI4, canal de endereço de escrita: tipo de rajada (1 = INCR).
        i_s_awburst : in    std_logic_vector(1 downto 0);
        -- Porta escravo AXI4, canal de dados de escrita: validade da transferência ('1' = válida).
        i_s_wvalid  : in    std_logic;
        -- Porta escravo AXI4, canal de dados de escrita: destino pronto para aceitar a transferência ('1').
        o_s_wready  : out   std_logic;
        -- Porta escravo AXI4, canal de dados de escrita: dados.
        i_s_wdata   : in    word_t;
        -- Porta escravo AXI4, canal de dados de escrita: habilita de bytes.
        i_s_wstrb   : in    std_logic_vector(3 downto 0);
        -- Porta escravo AXI4, canal de dados de escrita: último beat da rajada ('1').
        i_s_wlast   : in    std_logic;
        -- Porta escravo AXI4, canal de resposta de escrita: validade da transferência ('1' = válida).
        o_s_bvalid  : out   std_logic;
        -- Porta escravo AXI4, canal de resposta de escrita: destino pronto para aceitar a transferência ('1').
        i_s_bready  : in    std_logic;
        -- Porta escravo AXI4, canal de resposta de escrita: resposta (0 = OKAY, 2 = SLVERR).
        o_s_bresp   : out   std_logic_vector(1 downto 0);
        -- Porta escravo AXI4, canal de endereço de leitura: validade da transferência ('1' = válida).
        i_s_arvalid : in    std_logic;
        -- Porta escravo AXI4, canal de endereço de leitura: destino pronto para aceitar a transferência ('1').
        o_s_arready : out   std_logic;
        -- Porta escravo AXI4, canal de endereço de leitura: endereço do primeiro beat.
        i_s_araddr  : in    addr_t;
        -- Porta escravo AXI4, canal de endereço de leitura: número de beats da rajada menos um.
        i_s_arlen   : in    std_logic_vector(7 downto 0);
        -- Porta escravo AXI4, canal de endereço de leitura: log2 do número de bytes por beat.
        i_s_arsize  : in    std_logic_vector(2 downto 0);
        -- Porta escravo AXI4, canal de endereço de leitura: tipo de rajada (1 = INCR).
        i_s_arburst : in    std_logic_vector(1 downto 0);
        -- Porta escravo AXI4, canal de dados de leitura: validade da transferência ('1' = válida).
        o_s_rvalid  : out   std_logic;
        -- Porta escravo AXI4, canal de dados de leitura: destino pronto para aceitar a transferência ('1').
        i_s_rready  : in    std_logic;
        -- Porta escravo AXI4, canal de dados de leitura: dados.
        o_s_rdata   : out   word_t;
        -- Porta escravo AXI4, canal de dados de leitura: resposta (0 = OKAY, 2 = SLVERR).
        o_s_rresp   : out   std_logic_vector(1 downto 0);
        -- Porta escravo AXI4, canal de dados de leitura: último beat da rajada ('1').
        o_s_rlast   : out   std_logic;

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
        -- Janela de periféricos: dados lidos, 32 bits por periférico.
        i_p_rdata   : in    std_logic_vector(periph_count * XLEN - 1 downto 0)
    );
end entity axi_slave_periph_bank;

architecture rtl of axi_slave_periph_bank is

    -- Estados do banco: livre, beat de escrita, pulso no periférico, resposta e descarte da leitura.
    type state_t is (ST_IDLE, ST_WBEAT, ST_PULSE, ST_RESP, ST_RDROP);

    -- Estado atual do banco.
    signal st : state_t := ST_IDLE;

    -- A transação em andamento é uma escrita.
    signal we_l    : std_logic                     := '0';
    -- A transação não é atendida (resposta diferente de OKAY).
    signal bad_l   : std_logic                     := '0';
    -- Resposta da transação: 00 OKAY, 10 SLVERR (beat que não é único de 4 bytes ou padding), 11 DECERR (sem janela).
    signal resp_l  : std_logic_vector(1 downto 0)  := "00";
    -- Endereço da transação.
    signal addr_l  : addr_t                        := (others => '0');
    -- Dado de escrita.
    signal wdata_l : word_t                        := (others => '0');
    -- Habilita de bytes da escrita.
    signal strb_l  : std_logic_vector(3 downto 0)  := (others => '0');
    -- Dado lido do periférico, à espera de ser entregue.
    signal rd_q    : word_t                        := (others => '0');
    -- Beats ainda por consumir ou dar, menos um.
    signal left_l  : unsigned(7 downto 0)          := (others => '0');

    -- Bases da tabela, com a faixa normalizada de zero a periph_count - 1.
    constant BASES : addr_array_t(0 to periph_count - 1) := periph_bases;
    -- Máscaras da tabela, com a faixa normalizada.
    constant MASKS : addr_array_t(0 to periph_count - 1) := periph_masks;
    -- Tamanhos da tabela, com a faixa normalizada.
    constant SIZES : addr_array_t(0 to periph_count - 1) := periph_sizes;

    -- Janela acertada por periférico, para o endereço da transação em andamento.
    signal hit : std_logic_vector(periph_count - 1 downto 0);
    -- Índice da janela acertada.
    signal idx : natural range 0 to periph_count - 1;

    -- Resposta a uma transação: DECERR sem janela acertada, SLVERR para o que não é um único beat de 4 bytes
    -- alinhado e, com strict_periph, para o padding; OKAY nos outros casos.
    function classify (
        a     : addr_t;
        len   : std_logic_vector(7 downto 0);
        size  : std_logic_vector(2 downto 0);
        burst : std_logic_vector(1 downto 0)
    ) return std_logic_vector is

        -- Resposta DECERR.
        constant DECERR : std_logic_vector(1 downto 0) := "11";
        -- Resposta SLVERR.
        constant SLVERR : std_logic_vector(1 downto 0) := "10";
        -- Janela acertada, se houver.
        variable found  : boolean                       := false;
        -- Índice da janela acertada.
        variable v_idx  : natural range 0 to periph_count - 1 := 0;

    begin

        for i in 0 to periph_count - 1 loop

            if window_hit(a, BASES(i), MASKS(i)) then
                found := true;
                v_idx := i;
            end if;

        end loop;

        if not found then
            return DECERR;
        end if;

        if len /= "00000000" or size /= "010" or burst /= "01" or a(1 downto 0) /= "00" then
            return SLVERR;
        end if;

        if strict_periph and not in_registers(a, MASKS(v_idx), SIZES(v_idx)) then
            return SLVERR;
        end if;

        return "00";

    end function classify;

begin

    o_s_awready <= '1' when st = ST_IDLE else '0';
    o_s_arready <= '1' when st = ST_IDLE and i_s_awvalid = '0' else '0';
    o_s_wready  <= '1' when st = ST_WBEAT else '0';

    o_p_addr    <= addr_l(periph_addr_width + 1 downto 2);
    o_p_wdata   <= wdata_l;
    o_p_byteena <= strb_l;

    gen_hit : for i in 0 to periph_count - 1 generate
    begin

        hit(i) <= '1' when window_hit(addr_l, BASES(i), MASKS(i)) else '0';

    end generate gen_hit;

    p_index : process (hit) is

        -- Índice da janela acertada, zero sem janela acertada.
        variable v_idx : natural range 0 to periph_count - 1;

    begin

        v_idx := 0;

        for i in 0 to periph_count - 1 loop

            if hit(i) = '1' then
                v_idx := i;
            end if;

        end loop;

        idx <= v_idx;

    end process p_index;

    p_decode : process (st, idx, we_l) is
    begin

        o_p_we <= (others => '0');
        o_p_re <= (others => '0');

        if st = ST_PULSE then
            o_p_we(idx) <= we_l;
            o_p_re(idx) <= not we_l;
        end if;

    end process p_decode;

    o_s_bvalid <= '1' when st = ST_RESP and we_l = '1' else '0';
    o_s_bresp  <= resp_l;
    o_s_rvalid <= '1' when (st = ST_RESP and we_l = '0') or st = ST_RDROP else '0';
    o_s_rresp  <= resp_l;
    o_s_rdata  <= rd_q when bad_l = '0' else (others => '0');
    o_s_rlast  <= '1' when (st = ST_RESP and we_l = '0') or (st = ST_RDROP and left_l = 0) else '0';

    p_registers : process (i_clk) is
    begin

        if rising_edge(i_clk) then
            if i_rst = '1' then
                st    <= ST_IDLE;
                we_l  <= '0';
                bad_l  <= '0';
                resp_l <= "00";
                rd_q   <= (others => '0');
            else

                case st is

                    when ST_IDLE =>

                        if i_s_awvalid = '1' then
                            addr_l <= i_s_awaddr;
                            we_l   <= '1';
                            resp_l <= classify(i_s_awaddr, i_s_awlen, i_s_awsize, i_s_awburst);
                            bad_l  <= '1' when classify(i_s_awaddr, i_s_awlen, i_s_awsize, i_s_awburst) /= "00" else '0';
                            st     <= ST_WBEAT;
                        elsif i_s_arvalid = '1' then
                            addr_l <= i_s_araddr;
                            we_l   <= '0';
                            left_l <= unsigned(i_s_arlen);
                            resp_l <= classify(i_s_araddr, i_s_arlen, i_s_arsize, i_s_arburst);
                            bad_l  <= '1' when classify(i_s_araddr, i_s_arlen, i_s_arsize, i_s_arburst) /= "00" else '0';
                            if classify(i_s_araddr, i_s_arlen, i_s_arsize, i_s_arburst) /= "00" then
                                st <= ST_RDROP;
                            else
                                strb_l <= "1111";
                                st     <= ST_PULSE;
                            end if;
                        end if;

                    when ST_WBEAT =>

                        if i_s_wvalid = '1' then
                            if bad_l = '1' then
                                if i_s_wlast = '1' then
                                    st <= ST_RESP;
                                end if;
                            else
                                wdata_l <= i_s_wdata;
                                strb_l  <= i_s_wstrb;
                                st      <= ST_PULSE;
                            end if;
                        end if;

                    when ST_PULSE =>

                        rd_q <= i_p_rdata(XLEN * idx + XLEN - 1 downto XLEN * idx);
                        st   <= ST_RESP;

                    when ST_RESP =>

                        if (we_l = '1' and i_s_bready = '1') or (we_l = '0' and i_s_rready = '1') then
                            st <= ST_IDLE;
                        end if;

                    when ST_RDROP =>

                        if i_s_rready = '1' then
                            if left_l = 0 then
                                st <= ST_IDLE;
                            else
                                left_l <= left_l - 1;
                            end if;
                        end if;

                end case;

            end if;
        end if;

    end process p_registers;

end architecture rtl;
