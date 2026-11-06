-- ============================================================================
-- Topo da DE0-CV da plataforma external-data
-- ============================================================================
-- O núcleo na placa com a ROM dentro do chip e a RAM fora dele. A BOOT_ROM e a
-- FLASH ficam na FPGA; a FLASH é uma só cópia de uma memória de duas portas
-- verdadeiras, a mesma da internal-mem: a porta A é lida pelo estágio IF, a
-- porta B pelo estágio MEM (dado) e pelo carregador de FLASH, que a reescreve
-- por JTAG com o núcleo parado. A RAM é a SDRAM da placa em 0x40000000, ligada
-- por uma cache de dados write-through à ponte, ao árbitro e ao controlador do
-- repositório Memory; não há cache de instruções nem chip de FLASH, porque a
-- busca de instruções lê a FLASH direto. O hospedeiro lê e escreve a SDRAM pelo
-- mestre de depuração e a UART, o display e o carregador da FLASH são instâncias
-- do Virtual JTAG. O clock do núcleo é de 50 MHz; o controlador e o mestre de
-- depuração rodam no clock de 142,857 MHz do mesmo PLL.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.external_data_map_pkg.all;

entity core_fpga_external_data is
	generic (
		-- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os índices a partir de 3.
		HPM_COUNTERS : natural range 0 to 29 := 29;
		-- Largura, em bits, de cada contador de eventos do Zihpm.
		HPM_WIDTH    : natural range 0 to 64 := 64
	);
	port (
		-- Clock de 50 MHz da placa.
		CLOCK_50     : in    std_logic;
		-- Botão de reset da placa, ativo em '0'.
		FPGA_RESET_N : in    std_logic := '1';
		-- LEDs vermelhos.
		LEDR         : out   std_logic_vector(9 downto 0) := (others => '0');
		-- Display de sete segmentos 0.
		HEX0         : out   std_logic_vector(6 downto 0);
		-- Display de sete segmentos 1.
		HEX1         : out   std_logic_vector(6 downto 0);
		-- Display de sete segmentos 2.
		HEX2         : out   std_logic_vector(6 downto 0);
		-- Display de sete segmentos 3.
		HEX3         : out   std_logic_vector(6 downto 0);
		-- Display de sete segmentos 4.
		HEX4         : out   std_logic_vector(6 downto 0);
		-- Display de sete segmentos 5.
		HEX5         : out   std_logic_vector(6 downto 0);

		-- Endereço da SDRAM.
		DRAM_ADDR    : out   std_logic_vector(12 downto 0);
		-- Banco da SDRAM.
		DRAM_BA      : out   std_logic_vector(1 downto 0);
		-- Strobe de coluna da SDRAM, ativo em '0'.
		DRAM_CAS_N   : out   std_logic;
		-- Habilita de clock da SDRAM.
		DRAM_CKE     : out   std_logic;
		-- Clock da SDRAM.
		DRAM_CLK     : out   std_logic;
		-- Seleção de chip da SDRAM, ativo em '0'.
		DRAM_CS_N    : out   std_logic;
		-- Barramento de dados da SDRAM.
		DRAM_DQ      : inout std_logic_vector(15 downto 0);
		-- Máscara do byte baixo da SDRAM.
		DRAM_LDQM    : out   std_logic;
		-- Strobe de linha da SDRAM, ativo em '0'.
		DRAM_RAS_N   : out   std_logic;
		-- Máscara do byte alto da SDRAM.
		DRAM_UDQM    : out   std_logic;
		-- Habilita de escrita da SDRAM, ativo em '0'.
		DRAM_WE_N    : out   std_logic
	);
end entity;

architecture behaviour of core_fpga_external_data is

	-- Índice do Virtual JTAG da porta de depuração da SDRAM (quartus.sdram_debug_instance do config.yaml).
	constant SDRAM_DEBUG_INSTANCE : natural := 3;

	-- PLL da placa: o clock do controlador da SDRAM, o do pino da SDRAM e os dois do núcleo.
	component sdram_platform_pll is
		port (
			refclk   : in  std_logic;
			rst      : in  std_logic;
			outclk_0 : out std_logic;
			outclk_1 : out std_logic;
			outclk_2 : out std_logic;
			outclk_3 : out std_logic;
			locked   : out std_logic
		);
	end component;

	-- Endereço de busca de instrução do núcleo.
	signal if_addr : std_logic_vector(31 downto 0);
	-- Habilita de leitura da busca de instrução.
	signal if_rden : std_logic;
	-- Palavra lida da BOOT_ROM.
	signal boot_rom_data : std_logic_vector(31 downto 0);
	-- Palavra lida da porta A da FLASH, pelo estágio IF.
	signal flash_data : std_logic_vector(31 downto 0);

	-- Endereço de byte da leitura de dado do estágio MEM na FLASH.
	signal flash_addr2 : std_logic_vector(31 downto 0);
	-- Habilita da leitura de dado do estágio MEM na FLASH.
	signal flash_rden2 : std_logic;
	-- Palavra lida da porta B da FLASH, pelo estágio MEM.
	signal flash_data2 : std_logic_vector(31 downto 0);

	-- Alternância de comando do carregador da FLASH, vinda do Virtual JTAG.
	signal flash_cmd_tog    : std_logic;
	-- Código do comando do carregador.
	signal flash_op         : std_logic_vector(3 downto 0);
	-- Endereço de palavra do comando do carregador.
	signal flash_cmd_addr   : std_logic_vector(23 downto 0);
	-- Dado do comando do carregador.
	signal flash_cmd_data   : std_logic_vector(31 downto 0);
	-- Alternância de conclusão do carregador.
	signal flash_done_tog   : std_logic;
	-- Endereço da resposta do carregador.
	signal flash_rsp_addr   : std_logic_vector(23 downto 0);
	-- Dado da resposta do carregador.
	signal flash_rsp_data   : std_logic_vector(31 downto 0);
	-- Status da resposta do carregador.
	signal flash_rsp_status : std_logic_vector(7 downto 0);
	-- Núcleo parado pelo carregador da FLASH.
	signal flash_halt       : std_logic;
	-- Índice de palavra da porta B da FLASH.
	signal flash_address_b  : std_logic_vector(log2_exact(ROM_STORAGE_BYTES) - 3 downto 0);
	-- Habilita de leitura da porta B da FLASH.
	signal flash_rden_b     : std_logic;
	-- Habilita de escrita da porta B da FLASH.
	signal flash_wren_b     : std_logic;
	-- Dado de escrita da porta B da FLASH.
	signal flash_data_b     : std_logic_vector(31 downto 0);

	-- Porta de RAM interna do núcleo, sem uso nesta plataforma (a RAM é a SDRAM).
	signal ram_addr : std_logic_vector(31 downto 0);
	-- Dado de escrita da RAM interna, sem uso.
	signal ram_wdata : std_logic_vector(31 downto 0);
	-- Dado lido da RAM interna, fixo em zero.
	signal ram_rdata : std_logic_vector(31 downto 0) := (others => '0');
	-- Habilita da RAM interna, sem uso.
	signal ram_en : std_logic;
	-- Habilita de escrita da RAM interna, sem uso.
	signal ram_wren : std_logic;
	-- Habilita de leitura da RAM interna, sem uso.
	signal ram_rden : std_logic;
	-- Máscara de bytes da RAM interna, sem uso.
	signal ram_byteena : std_logic_vector(3 downto 0);

	-- Pulso do FENCE.I do núcleo, que esvazia a cache de dados.
	signal ic_inval : std_logic;
	-- Falha da cache de dados, evento para os contadores do Zihpm.
	signal dc_miss : std_logic;
	-- Eventos externos do Zihpm: espera da FLASH, falha da cache de dados e falha da cache de instruções.
	signal hpm_ext_events : std_logic_vector(2 downto 0);
	-- A cache de dados não guarda a última página da SDRAM, onde o hospedeiro e o programa se encontram.
	signal dc_bypass : std_logic;
	-- Endereço do lado da memória da cache de dados.
	signal dd_addr   : std_logic_vector(31 downto 0);
	-- Dado de escrita do lado da memória da cache de dados.
	signal dd_wdata  : std_logic_vector(31 downto 0);
	-- Dado lido pelo lado da memória da cache de dados.
	signal dd_rdata  : std_logic_vector(31 downto 0);
	-- Máscara de bytes do lado da memória da cache de dados.
	signal dd_be     : std_logic_vector(3 downto 0);
	-- Pedido de leitura da cache de dados à SDRAM.
	signal dd_rden   : std_logic;
	-- Pedido de escrita da cache de dados à SDRAM.
	signal dd_wren   : std_logic;
	-- Pedido de linha de quatro palavras.
	signal dd_line   : std_logic;
	-- O pedido foi consumido neste ciclo.
	signal dd_adv    : std_logic;
	-- Pedido concluído pela ponte da SDRAM.
	signal dd_ready  : std_logic;
	-- Palavras 1 a 3 da linha escrita.
	signal dd_wdx    : std_logic_vector(95 downto 0);
	-- Palavras 1 a 3 da linha lida.
	signal dd_rdx    : std_logic_vector(95 downto 0);
	-- Fim da invalidação da cache de dados.
	signal dc_done   : std_logic;
	-- A cache de dados está ocupada com uma invalidação.
	signal dc_busy   : std_logic;

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
	signal m_addr    : std_logic_vector(31 downto 0);
	-- Atrás do interconector: dado de escrita.
	signal m_wdata   : std_logic_vector(31 downto 0);
	-- Atrás do interconector: dado lido.
	signal m_rdata   : std_logic_vector(31 downto 0);
	-- Atrás do interconector: máscara de bytes.
	signal m_byteena : std_logic_vector(3 downto 0);
	-- Atrás do interconector: leitura.
	signal m_rden    : std_logic;
	-- Atrás do interconector: escrita.
	signal m_wren    : std_logic;
	-- Atrás do interconector: pedido concluído.
	signal m_ready   : std_logic;
	-- Janela de periféricos: endereço de registrador.
	signal p_addr    : std_logic_vector(7 downto 0);
	-- Janela de periféricos: dado de escrita.
	signal p_wdata   : std_logic_vector(31 downto 0);
	-- Janela de periféricos: máscara de bytes.
	signal p_byteena : std_logic_vector(3 downto 0);
	-- Janela de periféricos: escrita por slot.
	signal p_we, p_re : std_logic_vector(7 downto 0);
	-- Janela de periféricos: dado lido por slot.
	signal p_rdata   : std_logic_vector(8 * 32 - 1 downto 0) := (others => '0');
	-- Segmentos dos seis displays.
	signal display_hex   : std_logic_vector(41 downto 0);
	-- Valor mostrado nos displays.
	signal display_value : std_logic_vector(23 downto 0);
	-- Bandeira de falha do display.
	signal display_fail  : std_logic;

	-- Clock do controlador da SDRAM.
	signal pll_clk_mem    : std_logic;
	-- Clock do pino DRAM_CLK.
	signal pll_clk_dram   : std_logic;
	-- Clock das memórias de instrução.
	signal pll_clk_if     : std_logic;
	-- Clock do núcleo.
	signal pll_clk_idexmem: std_logic;
	-- O PLL travou.
	signal pll_locked     : std_logic;

	-- Reset do núcleo: PLL destravado, botão ou carregador da FLASH.
	signal core_reset : std_logic;

	-- Pulso de um ciclo de o_trap do núcleo (só existe sem Zicsr) e a bandeira que o segura até o próximo reset.
	signal core_trap : std_logic;
	signal trap_seen : std_logic := '0';

	-- Mestre A (a ponte do núcleo) e mestre B (o mestre de depuração) do árbitro.
	signal a_req, a_ack, a_we : std_logic;
	signal a_addr  : std_logic_vector(23 downto 0);
	signal a_wdata, a_rdata : std_logic_vector(31 downto 0);
	signal a_be    : std_logic_vector(3 downto 0);
	signal b_req, b_ack, b_we : std_logic;
	signal b_addr  : std_logic_vector(23 downto 0);
	signal b_wdata, b_rdata : std_logic_vector(31 downto 0);
	signal b_be    : std_logic_vector(3 downto 0);
	-- Comando do mestre de depuração vindo do Virtual JTAG.
	signal cmd_tog, done_tog : std_logic;
	signal d_op, d_be : std_logic_vector(3 downto 0);
	signal d_addr, r_addr : std_logic_vector(23 downto 0);
	signal d_data, r_data : std_logic_vector(31 downto 0);
	signal r_status : std_logic_vector(7 downto 0);

	-- Linha de quatro palavras entre a ponte A e o árbitro.
	signal a_line    : std_logic;
	signal a_wdx, a_rdx : std_logic_vector(95 downto 0);
	signal a_bex     : std_logic_vector(11 downto 0);
	-- Lado do controlador da SDRAM.
	signal c_line    : std_logic;
	signal c_wdx, c_rdx : std_logic_vector(95 downto 0);
	signal c_bex     : std_logic_vector(11 downto 0);

	-- Reset do controlador, solto em passo com o clock dele.
	signal rst_async : std_logic;
	signal rst_sr    : std_logic_vector(1 downto 0) := "11";
	signal rst_mem   : std_logic;
	signal req_tog, ack_tog, init_done, c_we : std_logic;
	signal c_addr    : std_logic_vector(23 downto 0);
	signal c_wdata, c_rdata : std_logic_vector(31 downto 0);
	signal c_be      : std_logic_vector(3 downto 0);
	signal dq_out, dq_in : std_logic_vector(15 downto 0);
	signal dq_oe     : std_logic;
	signal dqm       : std_logic_vector(1 downto 0);

begin

	u_pll : sdram_platform_pll
    port map (
      refclk   => CLOCK_50,
      rst      => not FPGA_RESET_N,
      outclk_0 => pll_clk_mem,
      outclk_1 => pll_clk_dram,
      outclk_2 => pll_clk_if,
      outclk_3 => pll_clk_idexmem,
      locked   => pll_locked
    );

	core_reset <= (not pll_locked) or (not FPGA_RESET_N) or flash_halt;

	-- LEDR9 a LEDR4 mostram as extensões do perfil do núcleo ('1' = presente, e o Zicntr apaga o LEDR7, como o M apaga o LEDR6);
	-- LEDR0 acende quando algum programa da execução em curso falhou (o hospedeiro grava a bandeira); LEDR1 acende quando o
	-- núcleo sinaliza uma exceção em o_trap (só sem Zicsr) e fica aceso até o próximo reset; LEDR2 acende com o núcleo
	-- parado pelo carregador da FLASH; LEDR3 fica apagado.
	LEDR(9) <= '1' when HAS_ZICCLSM else '0';
	LEDR(8) <= '1' when HAS_ZIFENCEI else '0';
	LEDR(7) <= '1' when HAS_ZICSR and not HAS_ZICNTR else '0';
	LEDR(6) <= '1' when HAS_ZMMUL else '0';
	LEDR(5) <= '1' when HAS_ZICNTR else '0';
	LEDR(4) <= '1' when HAS_M else '0';
	LEDR(3) <= '0';
	LEDR(2) <= flash_halt;
	LEDR(1) <= trap_seen;
	LEDR(0) <= display_fail;

	-- o_trap dura um ciclo de clock do núcleo, invisível a olho nu: a bandeira o segura até o reset.
	process (pll_clk_idexmem)
	begin
		if rising_edge(pll_clk_idexmem) then
			if core_reset = '1' then
				trap_seen <= '0';
			elsif core_trap = '1' then
				trap_seen <= '1';
			end if;
		end if;
	end process;

	u_core : entity work.core
		generic map (
			has_m           => HAS_M,
			has_zmmul       => HAS_ZMMUL,
			has_zicsr       => HAS_ZICSR or HAS_ZICNTR,
			has_zicntr      => HAS_ZICNTR,
			tick_cycles     => 50,
			has_zifencei    => HAS_ZIFENCEI,
			has_zicclsm     => HAS_ZICCLSM,
			has_e           => HAS_E,
			boot_rom_bits   => BOOT_ROM_BITS,
			rom_end_kib     => ROM_END_KIB,
			rom_external    => ROM_EXTERNAL,
			ram_base_kib    => RAM_BASE_KIB,
			ram_end_kib     => RAM_END_KIB,
			ram_external    => RAM_EXTERNAL,
			ext_base_kib    => EXT_BASE_KIB,
			periph_base_kib => PERIPH_BASE_KIB,
			has_zihpm       => HAS_ZIHPM,
			hpm_counters    => HPM_COUNTERS,
			hpm_width       => HPM_WIDTH,
			has_zimop       => HAS_ZIMOP,
			has_zicond      => HAS_ZICOND,
			has_zihintntl   => HAS_ZIHINTNTL,
			has_zihintpause => HAS_ZIHINTPAUSE
		)
		port map (
			i_clk           => pll_clk_idexmem,
			i_rst           => core_reset,

			o_if_addr       => if_addr,
			o_if_rden       => if_rden,
			i_boot_rom_data => boot_rom_data,
			i_flash_data    => flash_data,

			o_flash_addr2   => flash_addr2,
			o_flash_rden2   => flash_rden2,
			i_flash_data2   => flash_data2,

			o_ram_addr      => ram_addr,
			o_ram_wdata     => ram_wdata,
			i_ram_rdata     => ram_rdata,
			o_ram_en        => ram_en,
			o_ram_wren      => ram_wren,
			o_ram_rden      => ram_rden,
			o_ram_byteena   => ram_byteena,

			o_sdram_addr    => sdram_addr,
			o_sdram_wdata   => sdram_wdata,
			o_sdram_byteena => sdram_byteena,
			o_sdram_rden    => sdram_rden,
			o_sdram_wren    => sdram_wren,
			i_sdram_rdata   => sdram_rdata,
			i_sdram_ready   => sdram_ready,
			o_mem_advance   => mem_advance,

			o_trap          => core_trap,

			i_hpm_ext_events => hpm_ext_events,
			o_ic_inval      => ic_inval
		);

	-- Sem cache de instruções nem chip de FLASH, só a cache de dados conta eventos.
	hpm_ext_events <= '0' & dc_miss & '0';

	u_boot_rom : entity work.boot_rom
    generic map (size_bytes => BOOT_ROM_SIZE_BYTES)
    port map (
      i_address => if_addr(log2_exact(BOOT_ROM_SIZE_BYTES) - 1 downto 2),
      i_clk     => pll_clk_if,
      i_rden    => if_rden,
      i_wren    => '0',
      i_data    => (others => '0'),
      o_q       => boot_rom_data
    );

	-- A FLASH, uma só cópia de duas portas: A para a busca, B para o dado do estágio MEM e para o carregador.
	u_flash : entity work.flash
    generic map (size_bytes => ROM_STORAGE_BYTES)
    port map (
      i_clk_a     => pll_clk_if,
      i_address_a => if_addr(log2_exact(ROM_STORAGE_BYTES) - 1 downto 2),
      i_rden_a    => if_rden,
      o_q_a       => flash_data,
      i_clk_b     => pll_clk_idexmem,
      i_address_b => flash_address_b,
      i_rden_b    => flash_rden_b,
      i_wren_b    => flash_wren_b,
      i_data_b    => flash_data_b,
      o_q_b       => flash_data2
    );

	-- O carregador da FLASH: com o núcleo parado, escreve a imagem pela porta B; com ele rodando, repassa o estágio MEM.
	u_flash_loader : entity work.flash_loader
    generic map (addr_width => log2_exact(ROM_STORAGE_BYTES) - 2)
    port map (
      i_clk         => pll_clk_idexmem,
      i_rst         => not pll_locked,
      i_cmd_tog     => flash_cmd_tog,
      o_done_tog    => flash_done_tog,
      i_op          => flash_op,
      i_addr        => flash_cmd_addr,
      i_data        => flash_cmd_data,
      o_rsp_addr    => flash_rsp_addr,
      o_rsp_data    => flash_rsp_data,
      o_rsp_status  => flash_rsp_status,
      o_halt        => flash_halt,
      i_mem_address => flash_addr2(log2_exact(ROM_STORAGE_BYTES) - 1 downto 2),
      i_mem_rden    => flash_rden2,
      o_address_b   => flash_address_b,
      o_rden_b      => flash_rden_b,
      o_wren_b      => flash_wren_b,
      o_data_b      => flash_data_b,
      i_q_b         => flash_data2
    );

	u_flash_jtag : entity work.flash_jtag_shell
    port map (
      o_cmd_tog    => flash_cmd_tog,
      o_op         => flash_op,
      o_addr       => flash_cmd_addr,
      o_data       => flash_cmd_data,
      i_done_tog   => flash_done_tog,
      i_rsp_addr   => flash_rsp_addr,
      i_rsp_data   => flash_rsp_data,
      i_rsp_status => flash_rsp_status
    );

	-- As últimas 4 KB da SDRAM guardam as palavras que o hospedeiro divide com o programa: nunca ficam na cache.
	dc_bypass <= '1' when m_addr(31 downto 12) = RAM_LAST_PAGE else '0';

	u_dcache : entity work.dcache
		generic map (size_bits => DCACHE_SIZE_BITS, write_through => true, rom_base_kib => ROM_BASE_KIB, rom_end_kib => ROM_END_KIB)
		port map (
			i_clk => pll_clk_idexmem, i_rst => core_reset,
			i_addr => m_addr, i_wdata => m_wdata, i_byteena => m_byteena,
			i_rden => m_rden, i_wren => m_wren, i_mem_advance => mem_advance,
			o_ready => m_ready, o_rdata => m_rdata,
			i_flush => ic_inval, i_invalidate => '1', o_flush_done => dc_done, o_busy => dc_busy, o_miss => dc_miss,
			i_bypass => dc_bypass,
			o_d_addr => dd_addr, o_d_wdata => dd_wdata, o_d_byteena => dd_be,
			o_d_rden => dd_rden, o_d_wren => dd_wren, o_d_advance => dd_adv, i_d_ready => dd_ready,
			i_d_rdata => dd_rdata, o_d_line => dd_line, o_d_wdata_x => dd_wdx, i_d_rdata_x => dd_rdx
		);

	-- Porta externa do núcleo: o bit 31 em '0' é a SDRAM, em '1' a janela de periféricos.
	u_interconnect : entity work.ext_interconnect
		port map (
			i_clk => pll_clk_idexmem, i_rst => core_reset,
			i_addr => sdram_addr, i_wdata => sdram_wdata, i_byteena => sdram_byteena,
			i_rden => sdram_rden, i_wren => sdram_wren, i_mem_advance => mem_advance,
			o_ready => sdram_ready, o_rdata => sdram_rdata,
			o_m_addr => m_addr, o_m_wdata => m_wdata, o_m_byteena => m_byteena,
			o_m_rden => m_rden, o_m_wren => m_wren, i_m_ready => m_ready, i_m_rdata => m_rdata,
			o_p_addr => p_addr, o_p_wdata => p_wdata, o_p_byteena => p_byteena,
			o_p_we => p_we, o_p_re => p_re, i_p_rdata => p_rdata
		);

	-- A UART cuja outra ponta é um hospedeiro no JTAG (UART_BASE).
	u_jtag_uart : entity work.jtag_uart_shell
		port map (
			i_clk => pll_clk_idexmem, i_rst => core_reset,
			i_addr => p_addr, i_wdata => p_wdata, i_we => p_we(UART_ID), i_re => p_re(UART_ID),
			o_rdata => p_rdata(32 * UART_ID + 31 downto 32 * UART_ID)
		);

	-- O display de sete segmentos e a porta do hospedeiro (DISPLAY_BASE).
	u_display : entity work.seg_display_shell
		port map (
			i_clk => pll_clk_idexmem, i_rst => core_reset,
			i_addr => p_addr, i_wdata => p_wdata, i_we => p_we(DISPLAY_ID), i_re => p_re(DISPLAY_ID),
			o_rdata => p_rdata(32 * DISPLAY_ID + 31 downto 32 * DISPLAY_ID),
			o_hex => display_hex, o_value => display_value, o_fail => display_fail
		);

	HEX0 <= display_hex(6 downto 0);
	HEX1 <= display_hex(13 downto 7);
	HEX2 <= display_hex(20 downto 14);
	HEX3 <= display_hex(27 downto 21);
	HEX4 <= display_hex(34 downto 28);
	HEX5 <= display_hex(41 downto 35);

	-- A SDRAM: a ponte (clock do núcleo), o árbitro e o controlador (clock da SDRAM) e a porta de depuração.
	-- A porta de instruções do árbitro fica ociosa, porque a busca lê a FLASH.
	u_sdram_bridge : entity work.sdram_cpu_bridge
		port map (
			i_clk_cpu => pll_clk_idexmem, i_rst_cpu => core_reset,
			i_addr => dd_addr, i_wdata => dd_wdata, i_byteena => dd_be,
			i_rden => dd_rden, i_wren => dd_wren, i_mem_advance => dd_adv,
			o_ready => dd_ready, o_rdata => dd_rdata,
			i_line => dd_line, i_wdata_x => dd_wdx, i_byteena_x => (others => '0'), o_rdata_x => dd_rdx,
			o_req_tog => a_req, i_ack_tog => a_ack, i_init_done => init_done,
			o_c_we => a_we, o_c_addr => a_addr, o_c_wdata => a_wdata, o_c_be => a_be, i_c_rdata => a_rdata,
			o_c_line => a_line, o_c_wdata_x => a_wdx, o_c_be_x => a_bex, i_c_rdata_x => a_rdx
		);

	u_sdram_arbiter : entity work.sdram_arbiter
		port map (
			i_clk => pll_clk_mem, i_rst => rst_mem,
			i_a_req_tog => a_req, o_a_ack_tog => a_ack, i_a_we => a_we, i_a_addr => a_addr,
			i_a_wdata => a_wdata, i_a_be => a_be, o_a_rdata => a_rdata,
			i_a_line => a_line, i_a_wdata_x => a_wdx, i_a_be_x => a_bex, o_a_rdata_x => a_rdx,
			i_b_req_tog => b_req, o_b_ack_tog => b_ack, i_b_we => b_we, i_b_addr => b_addr,
			i_b_wdata => b_wdata, i_b_be => b_be, o_b_rdata => b_rdata,
			o_c_req_tog => req_tog, i_c_ack_tog => ack_tog, o_c_we => c_we, o_c_addr => c_addr,
			o_c_wdata => c_wdata, o_c_be => c_be, i_c_rdata => c_rdata,
			o_c_line => c_line, o_c_wdata_x => c_wdx, o_c_be_x => c_bex, i_c_rdata_x => c_rdx
		);

	u_sdram_debug : entity work.sdram_dbg_master
		port map (
			i_clk => pll_clk_mem, i_rst => rst_mem,
			i_cmd_tog => cmd_tog, o_done_tog => done_tog, i_op => d_op, i_be => d_be, i_addr => d_addr, i_data => d_data,
			o_rsp_addr => r_addr, o_rsp_data => r_data, o_rsp_status => r_status,
			i_init_done => init_done,
			o_b_req_tog => b_req, i_b_ack_tog => b_ack, o_b_we => b_we, o_b_addr => b_addr,
			o_b_wdata => b_wdata, o_b_be => b_be, i_b_rdata => b_rdata
		);

	-- O índice 3 do Virtual JTAG fica com a porta de depuração da SDRAM: o 0 é do carregador da FLASH (que o Quartus
	-- numera sozinho, pelo menor índice livre) e o 1 e o 2 são da UART e do display.
	u_sdram_jtag : entity work.sdram_jtag_shell
		generic map (instance_index => SDRAM_DEBUG_INSTANCE, auto_instance_index => "NO")
		port map (
			o_cmd_tog => cmd_tog, o_op => d_op, o_be => d_be, o_addr => d_addr, o_data => d_data,
			i_done_tog => done_tog, i_rsp_addr => r_addr, i_rsp_data => r_data, i_rsp_status => r_status
		);

	-- O controlador fica em reset enquanto o PLL não trava ou o botão está apertado, solto em passo com o clock dele.
	rst_async <= (not pll_locked) or (not FPGA_RESET_N);
	process (pll_clk_mem, rst_async)
	begin
		if rst_async = '1' then
			rst_sr <= "11";
		elsif rising_edge(pll_clk_mem) then
			rst_sr <= rst_sr(0) & '0';
		end if;
	end process;
	rst_mem <= rst_sr(1);

	u_sdram_ctrl : entity work.sdram_ctrl
		-- Os pinos de dados passam por um registrador nas células de E/S (ver o projeto do Quartus); a fase do clock
		-- do pino DRAM_CLK faz o dado lido chegar a tempo, sem o clock extra que a simulação modela.
		generic map (capture_extra => 0, sync_req => false)
		port map (
			i_clk => pll_clk_mem, i_rst => rst_mem,
			i_req_tog => req_tog, o_ack_tog => ack_tog, o_init_done => init_done,
			i_we => c_we, i_addr => c_addr, i_wdata => c_wdata, i_be => c_be, o_rdata => c_rdata,
			i_line => c_line, i_wdata_x => c_wdx, i_be_x => c_bex, o_rdata_x => c_rdx,
			o_dram_cke => DRAM_CKE, o_dram_cs_n => DRAM_CS_N, o_dram_ras_n => DRAM_RAS_N,
			o_dram_cas_n => DRAM_CAS_N, o_dram_we_n => DRAM_WE_N, o_dram_ba => DRAM_BA,
			o_dram_addr => DRAM_ADDR, o_dram_dqm => dqm,
			o_dram_dq_out => dq_out, o_dram_dq_oe => dq_oe, i_dram_dq_in => dq_in
		);

	DRAM_CLK  <= pll_clk_dram;
	DRAM_LDQM <= dqm(0);
	DRAM_UDQM <= dqm(1);
	DRAM_DQ   <= dq_out when dq_oe = '1' else (others => 'Z');
	process (pll_clk_mem)
	begin
		if rising_edge(pll_clk_mem) then
			dq_in <= DRAM_DQ;
		end if;
	end process;

end architecture;
