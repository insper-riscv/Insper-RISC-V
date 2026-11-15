-- =============================================================================
-- Porta de dados externa do core sobre AXI4
--
-- O que o ext_interconnect e a sdram_cpu_bridge fazem num barramento privado,
-- aqui como um mestre AXI4 com dois escravos atrás. A cache move uma linha como
-- uma rajada de quatro beats; todo o resto é um único beat.
--
--   mem_base a mem_last   o espaço da SDRAM: pela cache de dados, em linhas de quatro
--                palavras, exceto os últimos 4 KB (os da página de mem_last), que
--                não passam pela cache: as palavras que o hospedeiro compartilha
--                com o programa (tohost, fromhost,
--                stdout) moram ali, e o hospedeiro as lê e escreve pela porta de
--                debug da SDRAM
--   janelas       uma janela de periféricos da tabela (endereço and máscara = base,
--                bits periph_addr_width+1:2 a palavra), sem cache
--   nenhum        o roteador responde DECERR e o o_error sobe junto com o ready
--
-- O periférico de índice cache_ctrl_index é o controle da própria cache, não um externo: uma escrita na
-- sua primeira palavra pede à cache que escreva de volta toda linha suja (um
-- programa faz isso antes de terminar, para o hospedeiro ler o que o programa
-- escreveu), e uma leitura dele dá 1 enquanto isso está em andamento e 0 no
-- resto. Um acesso que não passa pela cache espera enquanto um flush está em
-- andamento, como os acessos da própria cache.
--
-- Lado do core, o contrato do ext_interconnect: o acesso fica na porta enquanto
-- o estágio de memória está parado; ready é um nível até mem_advance; rdata só
-- muda quando um load completa e permanece até o próximo, porque o load no
-- último estágio ainda o lê enquanto o acesso seguinte já está na porta.
--
-- O escravo 0 do roteador (a SDRAM) é a porta mestre AXI4-Lite m0_* desta
-- entidade, para o axi_slave_word_bridge ou qualquer outro escravo AXI4; a
-- janela de periféricos é a porta p_* do ext_interconnect, atrás do
-- axi_slave_periph_bank.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.config_pkg.all;
use work.interconnect_pkg.all;

entity ext_axi_interconnect is
    generic (
        -- Bits 31:26 dos endereços da SDRAM (0x40000000), para a cache de dados.
        base              : std_logic_vector(5 downto 0) := "010000";
        -- Verdadeiro: a cache escreve também na memória a cada store (veja a dcache).
        write_through     : boolean                      := false;
        -- Primeiro endereço da SDRAM, o escravo 0 do roteador.
        mem_base          : addr_t                       := std_logic_vector(resize(unsigned'(x"40000000"), ADDR_BITS));
        -- Último endereço da SDRAM, inclusive.
        mem_last          : addr_t                       := std_logic_vector(resize(unsigned'(x"43FFFFFF"), ADDR_BITS));
        -- Número de janelas de periféricos da tabela (PERIPH_COUNT do pacote de mapa da plataforma).
        periph_count      : positive                     := DEFAULT_PERIPH_COUNT;
        -- Base de cada janela (PERIPH_BASES).
        periph_bases      : addr_array_t                 := default_bases;
        -- Máscara de cada janela (PERIPH_MASKS).
        periph_masks      : addr_array_t                 := default_masks;
        -- Bytes de registradores de cada janela (PERIPH_SIZES).
        periph_sizes      : addr_array_t                 := default_sizes;
        -- Um acesso ao padding de uma janela é respondido com SLVERR.
        strict_periph     : boolean                      := true;
        -- Largura do deslocamento de palavra entregue ao periférico.
        periph_addr_width : positive range 2 to 30       := 14;
        -- Índice da tabela que é o controle da própria cache, e não um periférico externo.
        cache_ctrl_index  : natural                      := DEFAULT_PERIPH_COUNT - 1
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
        -- Acesso concluído com resposta de erro do barramento (DECERR ou SLVERR), válida junto com o ready ('1').
        o_error       : out   std_logic;
        -- Dado lido.
        o_rdata       : out   word_t;

        -- Pede a escrita de todas as linhas sujas na memória ('1').
        i_flush      : in    std_logic := '0';
        -- A escrita das linhas sujas terminou ('1').
        o_flush_done : out   std_logic;
        -- O módulo está ocupado ('1').
        o_busy       : out   std_logic;

        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de escrita: validade da transferência ('1' = válida).
        o_m0_awvalid : out   std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de escrita: destino pronto para aceitar a transferência ('1').
        i_m0_awready : in    std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de escrita: endereço da transferência.
        o_m0_awaddr  : out   addr_t;
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de escrita: número de beats da rajada menos um.
        o_m0_awlen   : out   std_logic_vector(7 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de escrita: tamanho de cada beat da rajada (log2 de bytes).
        o_m0_awsize  : out   std_logic_vector(2 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de escrita: tipo da rajada.
        o_m0_awburst : out   std_logic_vector(1 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de escrita: validade da transferência ('1' = válida).
        o_m0_wvalid  : out   std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de escrita: destino pronto para aceitar a transferência ('1').
        i_m0_wready  : in    std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de escrita: palavra de dados.
        o_m0_wdata   : out   word_t;
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de escrita: habilita de bytes.
        o_m0_wstrb   : out   std_logic_vector(3 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de escrita: último beat da rajada ('1').
        o_m0_wlast   : out   std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de resposta de escrita: validade da transferência ('1' = válida).
        i_m0_bvalid  : in    std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de resposta de escrita: origem pronta para aceitar a resposta ('1').
        o_m0_bready  : out   std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de resposta de escrita: código de resposta.
        i_m0_bresp   : in    std_logic_vector(1 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de leitura: validade da transferência ('1' = válida).
        o_m0_arvalid : out   std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de leitura: destino pronto para aceitar a transferência ('1').
        i_m0_arready : in    std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de leitura: endereço da transferência.
        o_m0_araddr  : out   addr_t;
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de leitura: número de beats da rajada menos um.
        o_m0_arlen   : out   std_logic_vector(7 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de leitura: tamanho de cada beat da rajada (log2 de bytes).
        o_m0_arsize  : out   std_logic_vector(2 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de endereço de leitura: tipo da rajada.
        o_m0_arburst : out   std_logic_vector(1 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de leitura: validade da transferência ('1' = válida).
        i_m0_rvalid  : in    std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de leitura: origem pronta para aceitar o dado ('1').
        o_m0_rready  : out   std_logic;
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de leitura: dados.
        i_m0_rdata   : in    word_t;
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de leitura: código de resposta.
        i_m0_rresp   : in    std_logic_vector(1 downto 0);
        -- Porta mestre AXI4 0 (SDRAM), canal de dados de leitura: último beat da rajada ('1').
        i_m0_rlast   : in    std_logic;

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
end entity ext_axi_interconnect;

architecture rtl of ext_axi_interconnect is

    -- O endereço não passa pela cache.
    signal mmio      : std_logic;
    -- Um acesso que não passa pela cache é o dono do mestre.
    signal direct    : std_logic;
    -- Um acesso direto começou e ainda não foi avançado.
    signal own       : std_logic := '0';
    -- A cache está ocupada com um flush.
    signal c_busy    : std_logic;
    -- Pedido de flush à cache, gerado pela escrita no controle da cache.
    signal flush_i   : std_logic;
    -- Pulsos de escrita da janela de periféricos, antes do controle da cache.
    signal p_we_i    : std_logic_vector(periph_count - 1 downto 0);
    -- Pulsos de leitura da janela de periféricos, antes do controle da cache.
    signal p_re_i    : std_logic_vector(periph_count - 1 downto 0);
    -- Dado de escrita da janela de periféricos.
    signal p_wdata_i : word_t;
    -- Dados lidos dos periféricos, com o do controle da cache acrescentado.
    signal p_rdata_i : std_logic_vector(periph_count * XLEN - 1 downto 0);

    -- Pedido de leitura à cache.
    signal c_rden    : std_logic;
    -- Pedido de escrita à cache.
    signal c_wren    : std_logic;
    -- Acesso à cache concluído.
    signal c_ready   : std_logic;
    -- Dado lido da cache.
    signal c_rdata   : word_t;
    -- Lado da memória da cache: endereço.
    signal d_addr    : addr_t;
    -- Lado da memória da cache: dado de escrita.
    signal d_wdata   : word_t;
    -- Lado da memória da cache: dado lido.
    signal d_rdata   : word_t;
    -- Lado da memória da cache: habilita de bytes.
    signal d_be      : std_logic_vector(3 downto 0);
    -- Lado da memória da cache: pedido de leitura.
    signal d_rden    : std_logic;
    -- Lado da memória da cache: pedido de escrita.
    signal d_wren    : std_logic;
    -- Lado da memória da cache: avanço do acesso.
    signal d_advance : std_logic;
    -- Lado da memória da cache: acesso concluído.
    signal d_ready   : std_logic;
    -- Lado da memória da cache: acesso de linha.
    signal d_line    : std_logic;
    -- Lado da memória da cache: palavras 1 a 3 da escrita de linha.
    signal d_wdata_x : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Lado da memória da cache: palavras 1 a 3 da leitura de linha.
    signal d_rdata_x : std_logic_vector(3 * XLEN - 1 downto 0);

    -- Entrada da ponte mestre AXI4: endereço.
    signal b_addr    : addr_t;
    -- Entrada da ponte mestre AXI4: dado de escrita.
    signal b_wdata   : word_t;
    -- Saída da ponte mestre AXI4: dado lido.
    signal b_rdata   : word_t;
    -- Entrada da ponte mestre AXI4: habilita de bytes.
    signal b_be      : std_logic_vector(3 downto 0);
    -- Entrada da ponte mestre AXI4: pedido de leitura.
    signal b_rden    : std_logic;
    -- Entrada da ponte mestre AXI4: pedido de escrita.
    signal b_wren    : std_logic;
    -- Entrada da ponte mestre AXI4: avanço do acesso.
    signal b_advance : std_logic;
    -- Saída da ponte mestre AXI4: acesso concluído.
    signal b_ready   : std_logic;
    -- Saída da ponte mestre AXI4: resposta de erro.
    signal b_err     : std_logic;
    -- Entrada da ponte mestre AXI4: acesso de linha.
    signal b_line    : std_logic;
    -- Entrada da ponte mestre AXI4: palavras 1 a 3 da escrita de linha.
    signal b_wdata_x : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Saída da ponte mestre AXI4: palavras 1 a 3 da leitura de linha.
    signal b_rdata_x : std_logic_vector(3 * XLEN - 1 downto 0);

    -- Barramento AXI4 do mestre, canal de endereço de escrita: validade da transferência ('1' = válida).
    signal awvalid : std_logic;
    -- Barramento AXI4 do mestre, canal de endereço de escrita: destino pronto para aceitar a transferência ('1').
    signal awready : std_logic;
    -- Barramento AXI4 do mestre, canal de dados de escrita: validade da transferência ('1' = válida).
    signal wvalid  : std_logic;
    -- Barramento AXI4 do mestre, canal de dados de escrita: destino pronto para aceitar a transferência ('1').
    signal wready  : std_logic;
    -- Barramento AXI4 do mestre, canal de resposta de escrita: validade da transferência ('1' = válida).
    signal bvalid  : std_logic;
    -- Barramento AXI4 do mestre, canal de resposta de escrita: destino pronto para aceitar a transferência ('1').
    signal bready  : std_logic;
    -- Barramento AXI4 do mestre, canal de endereço de leitura: validade da transferência ('1' = válida).
    signal arvalid : std_logic;
    -- Barramento AXI4 do mestre, canal de endereço de leitura: destino pronto para aceitar a transferência ('1').
    signal arready : std_logic;
    -- Barramento AXI4 do mestre, canal de dados de leitura: validade da transferência ('1' = válida).
    signal rvalid  : std_logic;
    -- Barramento AXI4 do mestre, canal de dados de leitura: destino pronto para aceitar a transferência ('1').
    signal rready  : std_logic;
    -- Barramento AXI4 do mestre, canal de endereço de escrita: endereço do primeiro beat.
    signal awaddr  : addr_t;
    -- Barramento AXI4 do mestre, canal de dados de escrita: dados.
    signal wdata_a : word_t;
    -- Barramento AXI4 do mestre, canal de endereço de leitura: endereço do primeiro beat.
    signal araddr  : addr_t;
    -- Barramento AXI4 do mestre, canal de dados de leitura: dados.
    signal rdata_a : word_t;
    -- Barramento AXI4 do mestre, canal de endereço de escrita: número de beats da rajada menos um.
    signal awlen   : std_logic_vector(7 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de leitura: número de beats da rajada menos um.
    signal arlen   : std_logic_vector(7 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de escrita: log2 do número de bytes por beat.
    signal awsize  : std_logic_vector(2 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de leitura: log2 do número de bytes por beat.
    signal arsize  : std_logic_vector(2 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de escrita: atributos de proteção.
    signal awprot  : std_logic_vector(2 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de leitura: atributos de proteção.
    signal arprot  : std_logic_vector(2 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de escrita: tipo de rajada (1 = INCR).
    signal awburst : std_logic_vector(1 downto 0);
    -- Barramento AXI4 do mestre, canal de endereço de leitura: tipo de rajada (1 = INCR).
    signal arburst : std_logic_vector(1 downto 0);
    -- Barramento AXI4 do mestre, canal de dados de escrita: habilita de bytes.
    signal wstrb   : std_logic_vector(3 downto 0);
    -- Barramento AXI4 do mestre, canal de dados de escrita: último beat da rajada ('1').
    signal wlast   : std_logic;
    -- Barramento AXI4 do mestre, canal de dados de leitura: último beat da rajada ('1').
    signal rlast   : std_logic;
    -- Barramento AXI4 do mestre, canal de resposta de escrita: resposta (0 = OKAY, 2 = SLVERR).
    signal bresp   : std_logic_vector(1 downto 0);
    -- Barramento AXI4 do mestre, canal de dados de leitura: resposta (0 = OKAY, 2 = SLVERR).
    signal rresp   : std_logic_vector(1 downto 0);

    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de escrita: validade da transferência ('1' =
    -- válida).
    signal m1_awvalid : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de escrita: destino pronto para aceitar a
    -- transferência ('1').
    signal m1_awready : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de escrita: validade da transferência ('1' = válida).
    signal m1_wvalid  : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de escrita: destino pronto para aceitar a
    -- transferência ('1').
    signal m1_wready  : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de resposta de escrita: validade da transferência ('1' =
    -- válida).
    signal m1_bvalid  : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de resposta de escrita: destino pronto para aceitar a
    -- transferência ('1').
    signal m1_bready  : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de leitura: validade da transferência ('1' =
    -- válida).
    signal m1_arvalid : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de leitura: destino pronto para aceitar a
    -- transferência ('1').
    signal m1_arready : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de leitura: validade da transferência ('1' = válida).
    signal m1_rvalid  : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de leitura: destino pronto para aceitar a
    -- transferência ('1').
    signal m1_rready  : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de escrita: último beat da rajada ('1').
    signal m1_wlast   : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de leitura: último beat da rajada ('1').
    signal m1_rlast   : std_logic;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de escrita: endereço do primeiro beat.
    signal m1_awaddr  : addr_t;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de escrita: dados.
    signal m1_wdata   : word_t;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de leitura: endereço do primeiro beat.
    signal m1_araddr  : addr_t;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de leitura: dados.
    signal m1_rdata   : word_t;
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de escrita: número de beats da rajada menos um.
    signal m1_awlen   : std_logic_vector(7 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de leitura: número de beats da rajada menos um.
    signal m1_arlen   : std_logic_vector(7 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de escrita: log2 do número de bytes por beat.
    signal m1_awsize  : std_logic_vector(2 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de leitura: log2 do número de bytes por beat.
    signal m1_arsize  : std_logic_vector(2 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de escrita: tipo de rajada (1 = INCR).
    signal m1_awburst : std_logic_vector(1 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de endereço de leitura: tipo de rajada (1 = INCR).
    signal m1_arburst : std_logic_vector(1 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de escrita: habilita de bytes.
    signal m1_wstrb   : std_logic_vector(3 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de resposta de escrita: resposta (0 = OKAY, 2 = SLVERR).
    signal m1_bresp   : std_logic_vector(1 downto 0);
    -- Barramento AXI4 do escravo 1 (periféricos), canal de dados de leitura: resposta (0 = OKAY, 2 = SLVERR).
    signal m1_rresp   : std_logic_vector(1 downto 0);

    -- Origem do dado lido: 00 cache, 01 ponte AXI (acesso direto), outro valor: o dado guardado em hold_q.
    signal sel    : std_logic_vector(1 downto 0)  := "00";
    -- Último dado de load completado, entregue enquanto nenhum load novo completa.
    signal hold_q : word_t := (others => '0');

begin

    -- passa pela cache só o que cai na SDRAM, menos a última página de 4 KiB e o que nenhum escravo atende
    mmio   <= '0' when unsigned(i_addr) >= unsigned(mem_base) and unsigned(i_addr) <= unsigned(mem_last)
                          and i_addr(ADDR_BITS - 1 downto 12) /= mem_last(ADDR_BITS - 1 downto 12) else '1';
    -- o acesso do próprio core toma o mestre quando a cache não está em flush, ou quando já o tem
    direct <= mmio and (i_rden or i_wren) and (own or not c_busy);
    o_busy <= c_busy;
    c_rden <= i_rden and not mmio;
    c_wren <= i_wren and not mmio;

    u_cache : entity work.dcache
        generic map (
            base_sdram => base, write_through => write_through
        )
        port map (
            i_clk         => i_clk,
            i_rst         => i_rst,
            i_addr        => i_addr,
            i_wdata       => i_wdata,
            i_byteena     => i_byteena,
            i_rden        => c_rden,
            i_wren        => c_wren,
            i_mem_advance => i_mem_advance,
            o_ready       => c_ready,
            o_rdata       => c_rdata,
            i_flush       => flush_i,
            i_invalidate  => p_wdata_i(1) and p_we_i(cache_ctrl_index),
            o_flush_done  => o_flush_done,
            o_busy        => c_busy,
            o_d_addr      => d_addr,
            o_d_wdata     => d_wdata,
            o_d_byteena   => d_be,
            o_d_rden      => d_rden,
            o_d_wren      => d_wren,
            o_d_advance   => d_advance,
            i_d_ready     => d_ready,
            i_d_rdata     => d_rdata,
            o_d_line      => d_line,
            o_d_wdata_x   => d_wdata_x,
            i_d_rdata_x   => d_rdata_x
        );

    -- um acesso por vez no mestre AXI4-Lite: o do próprio core (sem cache) ou o da cache; o
    -- do core ganha só enquanto tem um acesso na porta, então uma porta parada em um endereço de periférico
    -- não impede a cache de fazer os seus acessos
    b_addr    <= i_addr when direct = '1' else d_addr;
    b_wdata   <= i_wdata when direct = '1' else d_wdata;
    b_be      <= i_byteena when direct = '1' else d_be;
    b_rden    <= i_rden when direct = '1' else d_rden;
    b_wren    <= i_wren when direct = '1' else d_wren;
    b_advance <= i_mem_advance when direct = '1' else d_advance;
    b_line    <= '0' when direct = '1' else d_line;
    b_wdata_x <= d_wdata_x;
    d_ready   <= b_ready and not direct;
    d_rdata   <= b_rdata;
    d_rdata_x <= b_rdata_x;

    o_ready <= (b_ready and direct) when mmio = '1' else c_ready;
    o_error <= b_err and direct;
    o_rdata <= c_rdata when sel = "00" else
               b_rdata when sel = "01" else
               hold_q;

    p_registers : process (i_clk) is
    begin

        if rising_edge(i_clk) then
            if i_rst = '1' then
                sel    <= "00";
                hold_q <= (others => '0');
                own    <= '0';
            elsif i_rden = '1' and i_mem_advance = '1'
                  and ((mmio = '1' and b_ready = '1' and direct = '1') or (mmio = '0' and c_ready = '1')) then
                if mmio = '1' then
                    sel <= "01";
                else
                    sel <= "00";
                end if;
            elsif sel = "01" then
                hold_q <= b_rdata;
                sel    <= "10";
            end if;
            if direct = '1' then
                own <= '1';
            end if;
            if direct = '1' and i_mem_advance = '1' and b_ready = '1' then
                own <= '0';
            end if;
        end if;

    end process p_registers;

    u_master : entity work.axi_master_bridge
        port map (
            i_clk         => i_clk,
            i_rst         => i_rst,
            i_addr        => b_addr,
            i_wdata       => b_wdata,
            i_byteena     => b_be,
            i_rden        => b_rden,
            i_wren        => b_wren,
            i_mem_advance => b_advance,
            o_ready       => b_ready,
            o_rdata       => b_rdata,
            i_line        => b_line,
            i_wdata_x     => b_wdata_x,
            i_byteena_x   => (others => '1'),
            o_rdata_x     => b_rdata_x,
            o_err         => b_err,
            o_m_awvalid   => awvalid,
            i_m_awready   => awready,
            o_m_awaddr    => awaddr,
            o_m_awlen     => awlen,
            o_m_awsize    => awsize,
            o_m_awburst   => awburst,
            o_m_awprot    => awprot,
            o_m_wvalid    => wvalid,
            i_m_wready    => wready,
            o_m_wdata     => wdata_a,
            o_m_wstrb     => wstrb,
            o_m_wlast     => wlast,
            i_m_bvalid    => bvalid,
            o_m_bready    => bready,
            i_m_bresp     => bresp,
            o_m_arvalid   => arvalid,
            i_m_arready   => arready,
            o_m_araddr    => araddr,
            o_m_arlen     => arlen,
            o_m_arsize    => arsize,
            o_m_arburst   => arburst,
            o_m_arprot    => arprot,
            i_m_rvalid    => rvalid,
            o_m_rready    => rready,
            i_m_rdata     => rdata_a,
            i_m_rresp     => rresp,
            i_m_rlast     => rlast
        );

    u_router : entity work.axi_router
        generic map (
            mem_base     => mem_base,
            mem_last     => mem_last,
            periph_count => periph_count,
            periph_bases => periph_bases,
            periph_masks => periph_masks
        )
        port map (
            i_clk        => i_clk,
            i_rst        => i_rst,
            i_s_awvalid  => awvalid,
            o_s_awready  => awready,
            i_s_awaddr   => awaddr,
            i_s_awlen    => awlen,
            i_s_awsize   => awsize,
            i_s_awburst  => awburst,
            i_s_wvalid   => wvalid,
            o_s_wready   => wready,
            i_s_wdata    => wdata_a,
            i_s_wstrb    => wstrb,
            i_s_wlast    => wlast,
            o_s_bvalid   => bvalid,
            i_s_bready   => bready,
            o_s_bresp    => bresp,
            i_s_arvalid  => arvalid,
            o_s_arready  => arready,
            i_s_araddr   => araddr,
            i_s_arlen    => arlen,
            i_s_arsize   => arsize,
            i_s_arburst  => arburst,
            o_s_rvalid   => rvalid,
            i_s_rready   => rready,
            o_s_rdata    => rdata_a,
            o_s_rresp    => rresp,
            o_s_rlast    => rlast,
            o_m0_awvalid => o_m0_awvalid,
            i_m0_awready => i_m0_awready,
            o_m0_awaddr  => o_m0_awaddr,
            o_m0_awlen   => o_m0_awlen,
            o_m0_awsize  => o_m0_awsize,
            o_m0_awburst => o_m0_awburst,
            o_m0_wvalid  => o_m0_wvalid,
            i_m0_wready  => i_m0_wready,
            o_m0_wdata   => o_m0_wdata,
            o_m0_wstrb   => o_m0_wstrb,
            o_m0_wlast   => o_m0_wlast,
            i_m0_bvalid  => i_m0_bvalid,
            o_m0_bready  => o_m0_bready,
            i_m0_bresp   => i_m0_bresp,
            o_m0_arvalid => o_m0_arvalid,
            i_m0_arready => i_m0_arready,
            o_m0_araddr  => o_m0_araddr,
            o_m0_arlen   => o_m0_arlen,
            o_m0_arsize  => o_m0_arsize,
            o_m0_arburst => o_m0_arburst,
            i_m0_rvalid  => i_m0_rvalid,
            o_m0_rready  => o_m0_rready,
            i_m0_rdata   => i_m0_rdata,
            i_m0_rresp   => i_m0_rresp,
            i_m0_rlast   => i_m0_rlast,
            o_m1_awvalid => m1_awvalid,
            i_m1_awready => m1_awready,
            o_m1_awaddr  => m1_awaddr,
            o_m1_awlen   => m1_awlen,
            o_m1_awsize  => m1_awsize,
            o_m1_awburst => m1_awburst,
            o_m1_wvalid  => m1_wvalid,
            i_m1_wready  => m1_wready,
            o_m1_wdata   => m1_wdata,
            o_m1_wstrb   => m1_wstrb,
            o_m1_wlast   => m1_wlast,
            i_m1_bvalid  => m1_bvalid,
            o_m1_bready  => m1_bready,
            i_m1_bresp   => m1_bresp,
            o_m1_arvalid => m1_arvalid,
            i_m1_arready => m1_arready,
            o_m1_araddr  => m1_araddr,
            o_m1_arlen   => m1_arlen,
            o_m1_arsize  => m1_arsize,
            o_m1_arburst => m1_arburst,
            i_m1_rvalid  => m1_rvalid,
            o_m1_rready  => m1_rready,
            i_m1_rdata   => m1_rdata,
            i_m1_rresp   => m1_rresp,
            i_m1_rlast   => m1_rlast
        );

    u_periph : entity work.axi_slave_periph_bank
        generic map (
            periph_count      => periph_count,
            periph_bases      => periph_bases,
            periph_masks      => periph_masks,
            periph_sizes      => periph_sizes,
            strict_periph     => strict_periph,
            periph_addr_width => periph_addr_width
        )
        port map (
            i_clk       => i_clk,
            i_rst       => i_rst,
            i_s_awvalid => m1_awvalid,
            o_s_awready => m1_awready,
            i_s_awaddr  => m1_awaddr,
            i_s_awlen   => m1_awlen,
            i_s_awsize  => m1_awsize,
            i_s_awburst => m1_awburst,
            i_s_wvalid  => m1_wvalid,
            o_s_wready  => m1_wready,
            i_s_wdata   => m1_wdata,
            i_s_wstrb   => m1_wstrb,
            i_s_wlast   => m1_wlast,
            o_s_bvalid  => m1_bvalid,
            i_s_bready  => m1_bready,
            o_s_bresp   => m1_bresp,
            i_s_arvalid => m1_arvalid,
            o_s_arready => m1_arready,
            i_s_araddr  => m1_araddr,
            i_s_arlen   => m1_arlen,
            i_s_arsize  => m1_arsize,
            i_s_arburst => m1_arburst,
            o_s_rvalid  => m1_rvalid,
            i_s_rready  => m1_rready,
            o_s_rdata   => m1_rdata,
            o_s_rresp   => m1_rresp,
            o_s_rlast   => m1_rlast,
            o_p_addr    => o_p_addr,
            o_p_wdata   => p_wdata_i,
            o_p_byteena => o_p_byteena,
            o_p_we      => p_we_i,
            o_p_re      => p_re_i,
            i_p_rdata   => p_rdata_i
        );

    -- o índice cache_ctrl_index é o controle da cache
    flush_i   <= i_flush or p_we_i(cache_ctrl_index);
    o_p_wdata <= p_wdata_i;

    p_ctrl_mask : process (p_we_i, p_re_i, i_p_rdata, c_busy) is
    begin

        o_p_we    <= p_we_i;
        o_p_re    <= p_re_i;
        p_rdata_i <= i_p_rdata;

        o_p_we(cache_ctrl_index) <= '0';
        o_p_re(cache_ctrl_index) <= '0';

        p_rdata_i(XLEN * cache_ctrl_index + XLEN - 1 downto XLEN * cache_ctrl_index) <= (others => '0');
        p_rdata_i(XLEN * cache_ctrl_index)                                           <= c_busy;

    end process p_ctrl_mask;

end architecture rtl;
