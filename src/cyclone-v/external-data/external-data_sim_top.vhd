-- ============================================================================
-- Topo de simulação da plataforma external-data
-- ============================================================================
-- O núcleo, a BOOT_MEMORY e a FLASH (vetores VHDL) dentro do chip e a SDRAM fora
-- dele, atrás da cache de dados. A FLASH é uma só cópia de duas portas, como na
-- placa: a porta A é lida pela busca de instrução e a porta B pelo estágio MEM,
-- por meio do carregador de FLASH. O hospedeiro da simulação grava a imagem na
-- elaboração, pelo arquivo de ROM, ou depois, pelos sinais i_flash_*, que são os da
-- instância do Virtual JTAG do carregador: com eles o testbench para o núcleo,
-- grava uma imagem nova e o libera, como o hospedeiro da placa. A SDRAM, com a
-- ponte, o árbitro, o controlador e o modelo de chip do repositório Memory, roda
-- em clock próprio. A FLASH começa logo depois da BOOT_MEMORY e termina em 256 KiB,
-- e a SDRAM fica em 0x40000000.
--
-- i_clk é o clock base do núcleo (um gerador de clock o divide por três, como na
-- internal-mem). i_clk_mem é o clock da SDRAM, conduzido pelo testbench sem
-- relação fixa com i_clk, como na placa. i_dbg_word_addr e o_dbg_word_data leem uma
-- palavra direto do modelo do chip, que é como o testbench compara o conteúdo da
-- memória com um golden.
--
-- A porta externa do núcleo passa pelo interconector: o bit 31 em '0' é a
-- SDRAM, em '1' a janela de periféricos, com a UART JTAG em 0xC0000000 e o
-- registrador do display em 0xD0000000. Os sinais i_uart_* são os da instância do
-- Virtual JTAG da UART (ver jtag_uart), que o testbench conduz para ler o que o
-- programa imprime.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.external_data_map_pkg.all;

entity rv32im_external_data_sim_test is
    generic (
        -- Arquivo com a imagem da BOOT_MEMORY, uma palavra de 32 bits por linha em hexadecimal.
        boot_memory_file       : string                := "default.hex";
        -- Arquivo com a imagem da FLASH, uma palavra de 32 bits por linha em hexadecimal.
        rom_file               : string                := "default.hex";
        -- Largura do endereço de palavra da BOOT_MEMORY.
        boot_memory_addr_width : natural               := 9;
        -- Largura do endereço de palavra da FLASH.
        rom_addr_width         : natural               := 16;
        -- Largura do endereço de palavra da RAM; a RAM é a SDRAM, então a largura não dimensiona nada aqui.
        ram_addr_width         : natural               := 9;
        -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os índices a partir de 3.
        hpm_counters           : natural range 0 to 29 := 29;
        -- Largura, em bits, de cada contador de eventos do Zihpm.
        hpm_width              : natural range 0 to 64 := 64;
        -- A ROM fica fora do núcleo (o modelo de memória do platform.yaml).
        rom_external           : boolean               := work.external_data_map_pkg.ROM_EXTERNAL;
        -- A RAM fica fora do núcleo (o modelo de memória do platform.yaml).
        ram_external           : boolean               := work.external_data_map_pkg.RAM_EXTERNAL;
        -- Existe cache de instruções (o modelo de memória do platform.yaml); o topo monta só a de dados.
        has_icache             : boolean               := work.external_data_map_pkg.HAS_ICACHE;
        -- Existe cache de dados (o modelo de memória do platform.yaml).
        has_dcache             : boolean               := work.external_data_map_pkg.HAS_DCACHE;
        -- Tamanho da cache de instruções, em bits (o modelo de memória do platform.yaml).
        icache_size_bits       : positive              := work.external_data_map_pkg.ICACHE_SIZE_BITS;
        -- Tamanho da cache de dados, em bits (o modelo de memória do platform.yaml).
        dcache_size_bits       : positive              := work.external_data_map_pkg.DCACHE_SIZE_BITS;
        -- Imagem de programa gravada na SDRAM no tempo zero (uma palavra de 32 bits por linha, em
        -- hexadecimal, a partir de 0x40000000): o hospedeiro que carrega o chip pela porta de depuração.
        sdram_file             : string                := "";
        -- Periodo, em picossegundos, do clock CLK_MEM do controlador da SDRAM (o do platform.yaml): base da conversao dos tempos do chip em ciclos.
        sdram_tck_ps           : natural               := work.external_data_map_pkg.SDRAM_TCK_PS
    );
    port (
        -- Clock base do núcleo.
        i_clk             : in    std_logic;
        -- Clock da SDRAM.
        i_clk_mem         : in    std_logic;
        -- Reset, ativo em '1'.
        i_rst             : in    std_logic                     := '0';
        -- Endereço de palavra lido direto do modelo do chip de SDRAM.
        i_dbg_word_addr   : in    std_logic_vector(23 downto 0) := (others => '0');
        -- Palavra lida direto do modelo do chip de SDRAM.
        o_dbg_word_data   : out   std_logic_vector(31 downto 0);
        -- Clock da cadeia JTAG da UART.
        i_uart_tck        : in    std_logic                     := '0';
        -- Dado serial vindo do hospedeiro para a UART.
        i_uart_tdi        : in    std_logic                     := '0';
        -- Dado serial para o hospedeiro vindo da UART.
        o_uart_tdo        : out   std_logic;
        -- Registrador de instrução do Virtual JTAG da UART.
        i_uart_ir_in      : in    std_logic_vector(1 downto 0)  := "00";
        -- Estado Capture-DR da cadeia da UART.
        i_uart_state_cdr  : in    std_logic                     := '0';
        -- Estado Shift-DR da cadeia da UART.
        i_uart_state_sdr  : in    std_logic                     := '0';
        -- Estado Update-DR da cadeia da UART.
        i_uart_state_udr  : in    std_logic                     := '0';
        -- Estado Update-IR da cadeia da UART.
        i_uart_state_uir  : in    std_logic                     := '0';
        -- Clock da cadeia JTAG do carregador da FLASH.
        i_flash_tck       : in    std_logic                     := '0';
        -- Dado serial vindo do hospedeiro para o carregador.
        i_flash_tdi       : in    std_logic                     := '0';
        -- Dado serial para o hospedeiro vindo do carregador.
        o_flash_tdo       : out   std_logic;
        -- Registrador de instrução do Virtual JTAG do carregador.
        i_flash_ir_in     : in    std_logic_vector(1 downto 0)  := "00";
        -- Estado Capture-DR da cadeia do carregador.
        i_flash_state_cdr : in    std_logic                     := '0';
        -- Estado Shift-DR da cadeia do carregador.
        i_flash_state_sdr : in    std_logic                     := '0';
        -- Estado Update-DR da cadeia do carregador.
        i_flash_state_udr : in    std_logic                     := '0';
        -- Estado Update-IR da cadeia do carregador.
        i_flash_state_uir : in    std_logic                     := '0';
        -- Valor do registrador do display (periférico 5, 0xD0000000), cuja porta do hospedeiro fica ociosa aqui.
        o_display_value   : out   std_logic_vector(23 downto 0);
        -- Segmentos dos seis displays.
        o_display_hex     : out   std_logic_vector(41 downto 0)
    );
end entity rv32im_external_data_sim_test;

architecture behaviour of rv32im_external_data_sim_test is

    -- Bytes da FLASH, uma potência de dois.
    constant ROM_BYTES  : positive := 4 * 2 ** rom_addr_width;
    -- Bytes da BOOT_MEMORY, uma potência de dois.
    constant BOOT_BYTES : positive := 4 * 2 ** boot_memory_addr_width;

    -- Exceção sinalizada pelo núcleo sem Zicsr (um ciclo em '1'); com Zicsr fica em '0'.
    signal core_trap       : std_logic;
    -- Pulso de retirada de uma instrução em EX, contado pelo testbench para medir os ciclos por instrução.
    signal core_retire     : std_logic;
    -- Causa da exceção sinalizada, no formato do mcause.
    signal core_trap_cause : std_logic_vector(31 downto 0);
    -- PC da instrução que gerou a exceção sinalizada.
    signal core_trap_pc    : std_logic_vector(31 downto 0);

    -- Endereço de busca de instrução do núcleo.
    signal if_addr          : std_logic_vector(31 downto 0);
    -- Habilita de leitura da busca de instrução.
    signal if_rden          : std_logic;
    -- Palavra lida da BOOT_MEMORY.
    signal boot_memory_data : std_logic_vector(31 downto 0);
    -- Palavra lida da porta A da FLASH, pelo estágio IF.
    signal flash_data       : std_logic_vector(31 downto 0);
    -- Endereço de byte da leitura de dado do estágio MEM na FLASH.
    signal flash_addr2      : std_logic_vector(31 downto 0);
    -- Habilita da leitura de dado do estágio MEM na FLASH.
    signal flash_rden2      : std_logic;
    -- Palavra lida da porta B da FLASH, pelo estágio MEM.
    signal flash_data2      : std_logic_vector(31 downto 0);
    -- Índice de palavra da porta B da FLASH.
    signal flash_address_b  : std_logic_vector(rom_addr_width - 1 downto 0);
    -- Habilita de leitura da porta B da FLASH.
    signal flash_rden_b     : std_logic;
    -- Habilita de escrita da porta B da FLASH.
    signal flash_wren_b     : std_logic;
    -- Dado de escrita da porta B da FLASH.
    signal flash_data_b     : std_logic_vector(31 downto 0);
    -- Núcleo parado pelo carregador da FLASH, em '0' enquanto o hospedeiro não manda o comando de parada.
    signal flash_halt       : std_logic;
    -- Reset do núcleo e do que ele usa: o reset do topo ou a parada do carregador, como na placa.
    signal core_reset       : std_logic;
    -- Comando da porta JTAG ao carregador: alternância, operação, endereço de palavra e dado.
    signal flash_cmd_tog    : std_logic;
    -- Operação do comando da porta JTAG ao carregador de FLASH.
    signal flash_op         : std_logic_vector(3 downto 0);
    -- Endereço de palavra do comando da porta JTAG ao carregador de FLASH.
    signal flash_cmd_addr   : std_logic_vector(23 downto 0);
    -- Dado do comando da porta JTAG ao carregador de FLASH.
    signal flash_cmd_data   : std_logic_vector(31 downto 0);
    -- Resposta do carregador à porta JTAG.
    signal flash_done_tog   : std_logic;
    -- Endereço de palavra da resposta do carregador de FLASH.
    signal flash_rsp_addr   : std_logic_vector(23 downto 0);
    -- Dado da resposta do carregador de FLASH.
    signal flash_rsp_data   : std_logic_vector(31 downto 0);
    -- Estado da resposta do carregador de FLASH.
    signal flash_rsp_status : std_logic_vector(7 downto 0);

    -- Porta de RAM interna do núcleo, sem uso nesta plataforma (a RAM é a SDRAM).
    signal ram_addr    : std_logic_vector(31 downto 0);
    -- Dado de escrita da RAM interna, sem uso.
    signal ram_wdata   : std_logic_vector(31 downto 0);
    -- Dado lido da RAM interna, fixo em zero.
    signal ram_rdata   : std_logic_vector(31 downto 0) := (others => '0');
    -- Habilita da RAM interna, sem uso.
    signal ram_en      : std_logic;
    -- Habilita de escrita da RAM interna, sem uso.
    signal ram_wren    : std_logic;
    -- Habilita de leitura da RAM interna, sem uso.
    signal ram_rden    : std_logic;
    -- Máscara de bytes da RAM interna, sem uso.
    signal ram_byteena : std_logic_vector(3 downto 0);

    -- Porta externa do núcleo: endereço.
    signal sdram_addr    : std_logic_vector(31 downto 0);
    -- Porta externa do núcleo: dado de escrita.
    signal sdram_wdata   : std_logic_vector(31 downto 0);
    -- Porta externa do núcleo: dado lido.
    signal sdram_rdata   : std_logic_vector(31 downto 0);
    -- Porta externa do núcleo: máscara de bytes.
    signal sdram_byteena : std_logic_vector(3 downto 0);
    -- Porta externa do núcleo: leitura.
    signal sdram_rden    : std_logic;
    -- Porta externa do núcleo: escrita.
    signal sdram_wren    : std_logic;
    -- Porta externa do núcleo: pedido concluído.
    signal sdram_ready   : std_logic;
    -- O estágio MEM avança neste ciclo.
    signal mem_advance   : std_logic;

    -- Atrás do interconector: endereço da SDRAM.
    signal m_addr     : std_logic_vector(31 downto 0);
    -- Atrás do interconector: dado de escrita.
    signal m_wdata    : std_logic_vector(31 downto 0);
    -- Atrás do interconector: dado lido.
    signal m_rdata    : std_logic_vector(31 downto 0);
    -- Atrás do interconector: máscara de bytes.
    signal m_byteena  : std_logic_vector(3 downto 0);
    -- Atrás do interconector: leitura.
    signal m_rden     : std_logic;
    -- Atrás do interconector: escrita.
    signal m_wren     : std_logic;
    -- Atrás do interconector: pedido concluído.
    signal m_ready    : std_logic;
    -- Janela de periféricos: endereço de registrador.
    signal p_addr     : std_logic_vector(13 downto 0);
    -- Janela de periféricos: dado de escrita.
    signal p_wdata    : std_logic_vector(31 downto 0);
    -- Janela de periféricos: máscara de bytes.
    signal p_byteena  : std_logic_vector(3 downto 0);
    -- Janela de periféricos: escrita e leitura por slot.
    signal p_we, p_re : std_logic_vector(7 downto 0);
    -- Janela de periféricos: dado lido por slot.
    signal p_rdata    : std_logic_vector(8 * 32 - 1 downto 0) := (others => '0');

    -- Clock do estágio IF.
    signal pll_clk_if      : std_logic;
    -- Clock do núcleo.
    signal pll_clk_idexmem : std_logic;
    -- Clock do estágio WB, sem uso.
    signal pll_clk_wb      : std_logic;

    -- Contagem de renovações do modelo da SDRAM, sem uso.
    signal dbg_refreshes : std_logic_vector(31 downto 0);
    -- Inicialização do modelo da SDRAM terminou, sem uso.
    signal dbg_init_ok   : std_logic;
    -- A SDRAM terminou a inicialização.
    signal sdram_init    : std_logic;

    -- Pulso do FENCE.I do núcleo, que esvazia a cache de dados.
    signal ic_inval       : std_logic;
    -- Pedido de flush da cache de dados que o FENCE.I do núcleo faz antes de invalidar a cache de instruções.
    signal dc_flush       : std_logic;
    -- Falha da cache de dados, evento para os contadores do Zihpm.
    signal dc_miss        : std_logic;
    -- Eventos externos do Zihpm: espera da FLASH, falha da cache de dados e falha da cache de instruções.
    signal hpm_ext_events : std_logic_vector(2 downto 0);

    -- A cache de dados não guarda a última página da SDRAM, onde o hospedeiro e o programa se encontram.
    signal dc_bypass        : std_logic;
    -- Lado da memória da cache de dados, ligado direto ao sdram_system.
    signal dd_addr          : std_logic_vector(31 downto 0);
    signal dd_wdata         : std_logic_vector(31 downto 0);
    signal dd_rdata         : std_logic_vector(31 downto 0);
    -- Porta de memória da cache de dados: habilita de bytes.
    signal dd_be            : std_logic_vector(3 downto 0);
    -- Porta de memória da cache de dados: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço para
    -- a próxima palavra da linha, acesso concluído.
    signal dd_rden          : std_logic;
    signal dd_wren          : std_logic;
    signal dd_line          : std_logic;
    signal dd_adv           : std_logic;
    signal dd_ready         : std_logic;
    -- Porta de memória da cache de dados: linha larga de escrita de 96 bits, linha larga lida de 96 bits.
    signal dd_wdx,  dd_rdx  : std_logic_vector(95 downto 0);
    -- Fim e ocupação da invalidação da cache de dados.
    signal dc_done, dc_busy : std_logic;

begin

    core_reset <= i_rst or flash_halt;

    u_pll : entity work.clk_gen_3way
        port map (
            i_clk  => i_clk,
            i_rst  => i_rst,
            o_clk0 => pll_clk_if,
            o_clk1 => pll_clk_idexmem,
            o_clk2 => pll_clk_wb
        );

    u_core : entity work.core
        generic map (
            hpm_counters => hpm_counters,
            hpm_width    => hpm_width
        )
        port map (
            o_trap       => core_trap,
            o_retire     => core_retire,
            o_trap_cause => core_trap_cause,
            o_trap_pc    => core_trap_pc,
            i_clk        => pll_clk_idexmem,
            i_rst        => core_reset,

            o_if_addr          => if_addr,
            o_if_rden          => if_rden,
            i_boot_memory_data => boot_memory_data,
            i_flash_data       => flash_data,

            o_flash_addr2 => flash_addr2,
            o_flash_rden2 => flash_rden2,
            i_flash_data2 => flash_data2,

            o_ram_addr    => ram_addr,
            o_ram_wdata   => ram_wdata,
            i_ram_rdata   => ram_rdata,
            o_ram_en      => ram_en,
            o_ram_wren    => ram_wren,
            o_ram_rden    => ram_rden,
            o_ram_byteena => ram_byteena,

            o_ext_addr    => sdram_addr,
            o_ext_wdata   => sdram_wdata,
            o_ext_byteena => sdram_byteena,
            o_ext_rden    => sdram_rden,
            o_ext_wren    => sdram_wren,
            i_ext_rdata   => sdram_rdata,
            i_ext_ready   => sdram_ready,
            o_mem_advance => mem_advance,

            i_hpm_ext_events => hpm_ext_events,
            o_ic_inval       => ic_inval,
            o_dc_flush       => dc_flush,
            i_dc_done        => dc_done
        );

    -- Sem cache de instruções nem chip de FLASH, só a cache de dados conta eventos.
    hpm_ext_events <= '0' & dc_miss & '0';

    u_boot_memory : entity work.rom_simulation
        generic map (
            rom_file => boot_memory_file, size_bytes => BOOT_BYTES
        )
        port map (
            i_addr => if_addr(31 downto 2),
            i_clk  => pll_clk_if,
            i_re   => if_rden,
            o_data => boot_memory_data
        );

    -- A FLASH, uma só cópia de duas portas: A para a busca, B para o dado do estágio MEM e para o carregador.
    u_flash : entity work.flash_simulation
        generic map (
            size_bytes => ROM_BYTES, rom_file => rom_file
        )
        port map (
            i_clk_a     => pll_clk_if,
            i_address_a => if_addr(rom_addr_width + 1 downto 2),
            i_rden_a    => if_rden,
            o_q_a       => flash_data,
            i_clk_b     => pll_clk_idexmem,
            i_address_b => flash_address_b,
            i_rden_b    => flash_rden_b,
            i_wren_b    => flash_wren_b,
            i_data_b    => flash_data_b,
            o_q_b       => flash_data2
        );

    -- O carregador da FLASH: repassa a leitura do estágio MEM e, com o núcleo parado por um comando da porta JTAG,
    -- escreve a imagem que o hospedeiro manda.
    u_flash_loader : entity work.flash_loader
        generic map (
            addr_width => rom_addr_width
        )
        port map (
            i_clk         => pll_clk_idexmem,
            i_rst         => i_rst,
            i_cmd_tog     => flash_cmd_tog,
            o_done_tog    => flash_done_tog,
            i_op          => flash_op,
            i_addr        => flash_cmd_addr,
            i_data        => flash_cmd_data,
            o_rsp_addr    => flash_rsp_addr,
            o_rsp_data    => flash_rsp_data,
            o_rsp_status  => flash_rsp_status,
            o_halt        => flash_halt,
            i_mem_address => flash_addr2(rom_addr_width + 1 downto 2),
            i_mem_rden    => flash_rden2,
            o_address_b   => flash_address_b,
            o_rden_b      => flash_rden_b,
            o_wren_b      => flash_wren_b,
            o_data_b      => flash_data_b,
            i_q_b         => flash_data2
        );

    -- A porta JTAG do carregador, a do Virtual JTAG que na placa é o flash_jtag_shell.
    u_flash_jtag : entity work.flash_jtag_core
        port map (
            i_tck        => i_flash_tck,
            i_tdi        => i_flash_tdi,
            o_tdo        => o_flash_tdo,
            i_ir_in      => i_flash_ir_in,
            i_state_cdr  => i_flash_state_cdr,
            i_state_sdr  => i_flash_state_sdr,
            i_state_udr  => i_flash_state_udr,
            i_state_uir  => i_flash_state_uir,
            o_cmd_tog    => flash_cmd_tog,
            o_op         => flash_op,
            o_addr       => flash_cmd_addr,
            o_data       => flash_cmd_data,
            i_done_tog   => flash_done_tog,
            i_rsp_addr   => flash_rsp_addr,
            i_rsp_data   => flash_rsp_data,
            i_rsp_status => flash_rsp_status
        );

    -- As últimas 4 KB da SDRAM guardam as palavras que o hospedeiro divide com o programa (tohost, fromhost,
    -- stdout): o hospedeiro as escreve por trás da cache, então nunca ficam nela.
    dc_bypass <= '1' when m_addr(31 downto 12) = RAM_LAST_PAGE else '0';

    u_dcache : entity work.dcache
        generic map (
            size_bits   => dcache_size_bits, write_through => true, rom_base_kib => ROM_BASE_KIB,
            rom_end_kib => ROM_END_KIB
        )
        port map (
            i_clk         => pll_clk_idexmem,
            i_rst         => core_reset,
            i_addr        => m_addr,
            i_wdata       => m_wdata,
            i_byteena     => m_byteena,
            i_rden        => m_rden,
            i_wren        => m_wren,
            i_mem_advance => mem_advance,
            o_ready       => m_ready,
            o_rdata       => m_rdata,
            i_flush       => dc_flush,
            i_invalidate  => '1',
            o_flush_done  => dc_done,
            o_busy        => dc_busy,
            o_miss        => dc_miss,
            i_bypass      => dc_bypass,
            o_d_addr      => dd_addr,
            o_d_wdata     => dd_wdata,
            o_d_byteena   => dd_be,
            o_d_rden      => dd_rden,
            o_d_wren      => dd_wren,
            o_d_advance   => dd_adv,
            i_d_ready     => dd_ready,
            i_d_rdata     => dd_rdata,
            o_d_line      => dd_line,
            o_d_wdata_x   => dd_wdx,
            i_d_rdata_x   => dd_rdx
        );

    u_interconnect : entity work.ext_interconnect
        port map (
            i_clk         => pll_clk_idexmem,
            i_rst         => core_reset,
            i_addr        => sdram_addr,
            i_wdata       => sdram_wdata,
            i_byteena     => sdram_byteena,
            i_rden        => sdram_rden,
            i_wren        => sdram_wren,
            i_mem_advance => mem_advance,
            o_ready       => sdram_ready,
            o_rdata       => sdram_rdata,
            o_m_addr      => m_addr,
            o_m_wdata     => m_wdata,
            o_m_byteena   => m_byteena,
            o_m_rden      => m_rden,
            o_m_wren      => m_wren,
            i_m_ready     => m_ready,
            i_m_rdata     => m_rdata,
            o_p_addr      => p_addr,
            o_p_wdata     => p_wdata,
            o_p_byteena   => p_byteena,
            o_p_we        => p_we,
            o_p_re        => p_re,
            i_p_rdata     => p_rdata
        );

    u_uart : entity work.jtag_uart
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => core_reset,
            i_addr      => p_addr(7 downto 0),
            i_wdata     => p_wdata,
            i_we        => p_we(UART_ID),
            i_re        => p_re(UART_ID),
            o_rdata     => p_rdata(32 * UART_ID + 31 downto 32 * UART_ID),
            i_tck       => i_uart_tck,
            i_tdi       => i_uart_tdi,
            o_tdo       => o_uart_tdo,
            i_ir_in     => i_uart_ir_in,
            i_state_cdr => i_uart_state_cdr,
            i_state_sdr => i_uart_state_sdr,
            i_state_udr => i_uart_state_udr,
            i_state_uir => i_uart_state_uir
        );

    u_display : entity work.seg_display
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => core_reset,
            i_address   => p_addr(7 downto 0),
            i_data_in   => p_wdata,
            i_write     => p_we(DISPLAY_ID),
            o_rdata     => p_rdata(32 * DISPLAY_ID + 31 downto 32 * DISPLAY_ID),
            i_tck       => '0',
            i_tdi       => '0',
            i_ir_in     => "00",
            i_state_cdr => '0',
            i_state_sdr => '0',
            i_state_udr => '0',
            i_state_uir => '0',
            o_value     => o_display_value,
            o_fail      => open,
            o_hex       => o_display_hex
        );

    -- A SDRAM e o modelo do chip; as portas de depuração do modelo ficam sem uso aqui e a porta de instruções fica ociosa.
    u_sdram : entity work.sdram_system
        generic map (
            tck_ps         => sdram_tck_ps,
            init_cycles    => work.sdram_pkg.cycles(work.sdram_pkg.T_INIT_PS, sdram_tck_ps),
            refresh_cycles => work.sdram_pkg.cycles(work.sdram_pkg.T_REFI_PS, sdram_tck_ps) * 9 / 10,
            init_file      => sdram_file
        )
        port map (
            i_clk_mem       => i_clk_mem,
            i_clk_cpu       => pll_clk_idexmem,
            i_rst_mem       => i_rst,
            i_rst_cpu       => core_reset,
            i_addr          => dd_addr,
            i_wdata         => dd_wdata,
            i_byteena       => dd_be,
            i_rden          => dd_rden,
            i_wren          => dd_wren,
            i_mem_advance   => dd_adv,
            o_ready         => dd_ready,
            o_rdata         => dd_rdata,
            i_line          => dd_line,
            i_wdata_x       => dd_wdx,
            o_rdata_x       => dd_rdx,
            o_init_done     => sdram_init,
            i_dbg_word_addr => i_dbg_word_addr,
            o_dbg_word_data => o_dbg_word_data,
            i_dbg_flip      => '0',
            i_dbg_flip_addr => (others => '0'),
            i_dbg_flip_bit  => (others => '0'),
            o_dbg_refreshes => dbg_refreshes,
            o_dbg_init_ok   => dbg_init_ok
        );

end architecture behaviour;
