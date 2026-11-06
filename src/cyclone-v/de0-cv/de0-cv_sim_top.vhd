library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.de0_cv_map_pkg.all;

-- Simulation top of the SDRAM platform with the FLASH as a chip behind the caches: the core, the
-- BOOT_MEMORY (a VHDL array), the instruction and data caches, the FLASH chip model with its storage (a
-- VHDL array) and the SDRAM (bridge, arbiter, controller and chip model of the Memory repository) on
-- its own 143 MHz clock. The SDRAM is the RAM: there is no other data memory. The FLASH starts right after the BOOT_MEMORY and
-- ends at 256 KiB, and the SDRAM is at 0x40000000; both are reached only through the caches, whose line
-- requests a region router sends to the FLASH (through its arbiter) or to the SDRAM.
--
-- CLK is the base clock of the core (a clock generator divides it by three, as in internal-mem).
-- CLK_MEM is the SDRAM clock, driven by the testbench with no fixed relation to CLK, as on the
-- board. DBG_WORD_ADDR and DBG_WORD_DATA read a word straight out of the chip model, which is how
-- the testbench compares the content of the memory with a golden.
--
-- The core's external port goes through the interconnect of the Memory repository: bit 31 = 0 is
-- the SDRAM, bit 31 = 1 a peripheral window, with the JTAG UART at 0xC0000000 and the display register at 0xD0000000. UART_* stand for the
-- Virtual JTAG instance of the UART (see jtag_uart); the testbench drives them to read what the
-- program prints.
entity rv32im_sdram_flash_sim_test is
	generic (
	  BOOT_MEMORY_FILE : string := "default.hex";
	  ROM_FILE : string := "default.hex";
	  boot_memory_addr_width : natural := 9;
	  rom_addr_width : natural := 18;
	  -- Bordas até a primeira palavra do chip de FLASH e entre as palavras de uma linha.
	  FLASH_FIRST_LATENCY : natural := 24;
	  FLASH_NEXT_LATENCY  : natural := 4;
	  ram_addr_width : natural := 9;
	  -- Zicsr no core (instrucoes CSR reais); false mantem o comportamento de NOP.
	  HAS_ZICSR : boolean := false;
	  -- Habilita os contadores da extensão Zicntr (implica Zicsr).
	  HAS_ZICNTR : boolean := false;
	  -- Extensao M completa no core.
	  HAS_M : boolean := true;
	  -- Multiplicacao sem divisao (Zmmul) no core.
	  HAS_ZMMUL : boolean := false;
	  -- Zifencei no core (FENCE.I invalida a cache de instrucoes); false mantem o NOP.
	  HAS_ZIFENCEI : boolean := false;
	  -- Acesso desalinhado a memoria principal executado em hardware (Zicclsm).
	  HAS_ZICCLSM : boolean := true;
	  -- Interrupcoes de maquina: o CLINT e o controlador externo na janela de periféricos, e as tres linhas no core.
	  HAS_INTERRUPTS : boolean := true;
	  -- Ciclos de clock do core por incremento do mtime do CLINT.
	  CLINT_TICK_CYCLES : positive := work.de0_cv_map_pkg.CLINT_TICK_CYCLES;
	  -- Contadores de eventos da extensao Zihpm (quatro, indices 3 a 6); exige Zicsr.
	  HAS_ZIHPM : boolean := false;
	  -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os indices a partir de 3.
	  HPM_COUNTERS : natural range 0 to 29 := 29;
	  -- Largura, em bits, de cada contador de eventos do Zihpm.
	  HPM_WIDTH : natural range 0 to 64 := 64;
	  -- Extensao Zimop no core (mop.r.n e mop.rr.n escrevem zero em rd).
	  HAS_ZIMOP : boolean := work.de0_cv_map_pkg.HAS_ZIMOP;
	  -- Extensao Zicond no core (czero.eqz e czero.nez).
	  HAS_ZICOND : boolean := work.de0_cv_map_pkg.HAS_ZICOND;
	  -- Dicas ntl.* da extensao Zihintntl no core (executam como nop).
	  HAS_ZIHINTNTL : boolean := work.de0_cv_map_pkg.HAS_ZIHINTNTL;
	  -- Dica pause da extensao Zihintpause no core (executa como nop).
	  HAS_ZIHINTPAUSE : boolean := work.de0_cv_map_pkg.HAS_ZIHINTPAUSE;
	  -- A ROM fica fora do core (o modelo de memória do platform.yaml).
	  ROM_EXTERNAL : boolean := work.de0_cv_map_pkg.ROM_EXTERNAL;
	  -- A RAM fica fora do core (o modelo de memória do platform.yaml).
	  RAM_EXTERNAL : boolean := work.de0_cv_map_pkg.RAM_EXTERNAL;
	  -- Existe cache de instruções (o modelo de memória do platform.yaml).
	  HAS_ICACHE : boolean := work.de0_cv_map_pkg.HAS_ICACHE;
	  -- Existe cache de dados (o modelo de memória do platform.yaml).
	  HAS_DCACHE : boolean := work.de0_cv_map_pkg.HAS_DCACHE;
	  -- Tamanho da cache de instruções, em bits (o modelo de memória do platform.yaml).
	  ICACHE_SIZE_BITS : positive := work.de0_cv_map_pkg.ICACHE_SIZE_BITS;
	  -- Tamanho da cache de dados, em bits (o modelo de memória do platform.yaml).
	  DCACHE_SIZE_BITS : positive := work.de0_cv_map_pkg.DCACHE_SIZE_BITS;
	  -- Base RV32E (16 registradores) no core; false e o RV32I (o perfil da plataforma por padrao).
	  HAS_E : boolean := work.de0_cv_map_pkg.HAS_E;
	  -- Controlador de FLASH na janela de periferico 3 (0xB0000000), com a FLASH de duas portas e o chip de comandos
	  -- (apagar, gravar, proteger) atras dele: a atualizacao de programa em campo. Desligado, a FLASH e so de leitura.
	  HAS_FLASH_CONTROLLER : boolean := false;
	  -- Bordas de espera de um apagar de setor do chip de FLASH, antes da varredura do setor.
	  FLASH_ERASE_LATENCY   : natural := 2000;
	  -- Bordas de espera de uma gravacao de pagina do chip de FLASH, antes da varredura da pagina.
	  FLASH_PROGRAM_LATENCY : natural := 200;
	  -- Imagem de programa gravada na SDRAM no tempo zero (uma palavra de 32 bits por linha, em
	  -- hexadecimal, a partir de 0x40000000): o hospedeiro que carrega o chip pela porta de debug.
	  SDRAM_FILE : string := ""
  	);
	port (
    	CLK     : in  std_logic;
    	CLK_MEM : in  std_logic;
		reset   : in  std_logic := '0';
		DBG_WORD_ADDR : in  std_logic_vector(23 downto 0) := (others => '0');
		DBG_WORD_DATA : out std_logic_vector(31 downto 0);
		UART_TCK       : in  std_logic := '0';
		UART_TDI       : in  std_logic := '0';
		UART_TDO       : out std_logic;
		UART_IR_IN     : in  std_logic_vector(1 downto 0) := "00";
		UART_STATE_CDR : in  std_logic := '0';
		UART_STATE_SDR : in  std_logic := '0';
		UART_STATE_UDR : in  std_logic := '0';
		UART_STATE_UIR : in  std_logic := '0';
		-- value and segments of the display register (peripheral 5, 0xD0000000), whose host port stays idle here
		DISPLAY_VALUE  : out std_logic_vector(23 downto 0);
		DISPLAY_HEX    : out std_logic_vector(41 downto 0)
  	);
end entity;

architecture behaviour of rv32im_sdram_flash_sim_test is



	-- Exceção sinalizada pelo core sem Zicsr (um ciclo em '1'); com Zicsr fica em '0'.
	signal core_trap       : std_logic;
	-- Pulso de retirada de uma instrução em EX, contado pelo testbench para medir os ciclos por instrução.
	signal core_retire : std_logic;
	-- Causa da exceção sinalizada, no formato do mcause.
	signal core_trap_cause : std_logic_vector(31 downto 0);
	-- PC da instrução que gerou a exceção sinalizada.
	signal core_trap_pc    : std_logic_vector(31 downto 0);

	signal if_addr : std_logic_vector(31 downto 0);
	signal if_rden : std_logic;
	signal boot_memory_data : std_logic_vector(31 downto 0);
	signal flash_data : std_logic_vector(31 downto 0);

	signal flash_addr2 : std_logic_vector(31 downto 0);
	signal flash_rden2 : std_logic;
	signal flash_data2 : std_logic_vector(31 downto 0) := (others => '0');

	signal ram_addr : std_logic_vector(31 downto 0);
	signal ram_wdata : std_logic_vector(31 downto 0);
	signal ram_rdata : std_logic_vector(31 downto 0) := (others => '0');   -- no RAM inside the FPGA
	signal ram_en : std_logic;
	signal ram_wren : std_logic;
	signal ram_rden : std_logic;
	signal ram_byteena : std_logic_vector(3 downto 0);

	signal sdram_addr    : std_logic_vector(31 downto 0);
	signal sdram_wdata   : std_logic_vector(31 downto 0);
	signal sdram_rdata   : std_logic_vector(31 downto 0);
	signal sdram_byteena : std_logic_vector(3 downto 0);
	signal sdram_rden    : std_logic;
	signal sdram_wren    : std_logic;
	signal sdram_ready   : std_logic;
	signal mem_advance   : std_logic;

	-- behind the interconnect: the SDRAM, and the peripheral slots
	signal m_addr    : std_logic_vector(31 downto 0);
	signal m_wdata   : std_logic_vector(31 downto 0);
	signal m_rdata   : std_logic_vector(31 downto 0);
	signal m_byteena : std_logic_vector(3 downto 0);
	signal m_rden    : std_logic;
	signal m_wren    : std_logic;
	signal m_ready   : std_logic;
	signal p_addr    : std_logic_vector(PLIC_ADDR_WIDTH - 1 downto 0);
	-- Linhas de interrupção dos periféricos para o PLIC; uma ausente fica em zero.
	signal irq_lines : std_logic_vector(PLIC_N_SOURCES downto 1) := (others => '0');
	signal p_wdata   : std_logic_vector(31 downto 0);
	signal p_byteena : std_logic_vector(3 downto 0);
	signal p_we, p_re : std_logic_vector(7 downto 0);
	signal p_rdata   : std_logic_vector(8 * 32 - 1 downto 0) := (others => '0');
	-- the three machine interrupt lines of the core
	signal irq_timer, irq_software, irq_external : std_logic := '0';

	signal pll_clk_if     : std_logic;
	signal pll_clk_idexmem: std_logic;
	signal pll_clk_wb     : std_logic;

	signal dbg_refreshes  : std_logic_vector(31 downto 0);
	signal dbg_init_ok    : std_logic;
	signal sdram_init     : std_logic;

	-- Busca de instrucao em SDRAM: cache de instrucoes no clock do IF
	signal ic_data   : std_logic_vector(31 downto 0);
	signal ic_ready  : std_logic;
	signal ic_sel    : std_logic;
	signal ic_inval  : std_logic;
	signal id_addr   : std_logic_vector(31 downto 0);
	signal id_rden   : std_logic;
	signal id_adv    : std_logic;
	signal id_ready  : std_logic;
	signal id_rdata  : std_logic_vector(31 downto 0);
	signal id_line   : std_logic;
	signal id_rdx    : std_logic_vector(95 downto 0);
	-- Eventos das caches e da FLASH para os contadores do Zihpm: falha da cache de instrucoes, falha da cache de
	-- dados e ciclo de espera do chip de FLASH.
	signal ic_miss, dc_miss, flash_busy : std_logic;
	signal hpm_ext_events : std_logic_vector(2 downto 0);

	-- Roteador da cache de instruções: lado da SDRAM (porta de instruções do sdram_system)
	signal si_addr   : std_logic_vector(31 downto 0);
	signal si_wdata  : std_logic_vector(31 downto 0);
	signal si_be     : std_logic_vector(3 downto 0);
	signal si_rden, si_wren, si_line, si_adv, si_ready : std_logic;
	signal si_wdx    : std_logic_vector(95 downto 0);
	signal si_rdata  : std_logic_vector(31 downto 0);
	signal si_rdx    : std_logic_vector(95 downto 0);

	-- Cache de dados: lado da memória
	signal dc_bypass : std_logic;
	signal dd_addr, dd_wdata, dd_rdata : std_logic_vector(31 downto 0);
	signal dd_be     : std_logic_vector(3 downto 0);
	signal dd_rden, dd_wren, dd_line, dd_adv, dd_ready : std_logic;
	signal dd_wdx, dd_rdx : std_logic_vector(95 downto 0);
	signal dc_done, dc_busy : std_logic;

	-- Roteador da cache de dados: lado da SDRAM (porta de dados do sdram_system)
	signal sd_addr, sd_wdata, sd_rdata : std_logic_vector(31 downto 0);
	signal sd_be     : std_logic_vector(3 downto 0);
	signal sd_rden, sd_wren, sd_line, sd_adv, sd_ready : std_logic;
	signal sd_wdx, sd_rdx : std_logic_vector(95 downto 0);

	-- Lado da FLASH dos dois roteadores, o árbitro e o chip
	signal fa_addr, fa_rdata, fb_addr, fb_rdata, fc_addr, fc_rdata : std_logic_vector(31 downto 0);
	signal fa_rden, fa_line, fa_adv, fa_ready, fb_rden, fb_line, fb_adv, fb_ready : std_logic;
	signal fc_rden, fc_line, fc_adv, fc_ready : std_logic;
	signal fa_rdx, fb_rdx, fc_rdx : std_logic_vector(95 downto 0);
	signal flash_mem_addr, flash_mem_data : std_logic_vector(31 downto 0);

	-- Controlador de FLASH e chip de comandos (so com HAS_FLASH_CONTROLLER): comando, estado, buffer de pagina,
	-- porta B do armazenamento e invalidacao por regiao das duas caches.
	signal fl_cmd_valid, fl_busy, fl_wel, fl_refused : std_logic := '0';
	signal fl_cmd_op       : std_logic_vector(2 downto 0);
	signal fl_cmd_addr     : std_logic_vector(31 downto 0);
	signal fl_buf_idx      : std_logic_vector(5 downto 0);
	signal fl_buf_data     : std_logic_vector(31 downto 0);
	signal fl_b_addr, fl_b_wdata, fl_b_data : std_logic_vector(31 downto 0) := (others => '0');
	signal fl_b_we         : std_logic := '0';
	signal fl_inval_valid  : std_logic := '0';
	signal fl_inval_first, fl_inval_last : std_logic_vector(31 downto 0) := (others => '0');

begin

	pll_inst : entity work.clk_gen_3way
    port map (
      i_clk    => CLK,
      i_rst    => reset,
      o_clk0 => pll_clk_if,
      o_clk1 => pll_clk_idexmem,
      o_clk2 => pll_clk_wb
    );

	CORE : entity work.core
		generic map (has_m => HAS_M, has_zmmul => HAS_ZMMUL, has_zicsr => HAS_ZICSR, has_zicntr => HAS_ZICNTR, has_zifencei => HAS_ZIFENCEI, has_zicclsm => HAS_ZICCLSM, has_e => HAS_E, boot_memory_bits => BOOT_MEMORY_BITS, rom_end_kib => ROM_END_KIB, rom_external => ROM_EXTERNAL, ram_base_kib => RAM_BASE_KIB, ram_end_kib => RAM_END_KIB, ram_external => RAM_EXTERNAL, ext_base_kib => EXT_BASE_KIB, periph_base_kib => PERIPH_BASE_KIB, has_zihpm => HAS_ZIHPM, hpm_counters => HPM_COUNTERS, hpm_width => HPM_WIDTH, has_zimop => HAS_ZIMOP, has_zicond => HAS_ZICOND, has_zihintntl => HAS_ZIHINTNTL, has_zihintpause => HAS_ZIHINTPAUSE, has_interrupts => HAS_INTERRUPTS and (HAS_ZICSR or HAS_ZICNTR or HAS_ZIHPM))
		port map (
			o_trap       => core_trap,
			o_retire     => core_retire,
			o_trap_cause => core_trap_cause,
			o_trap_pc    => core_trap_pc,

			i_clk          => pll_clk_idexmem,
			i_rst 		=> reset,

			o_if_addr       => if_addr,
			o_if_rden       => if_rden,
			i_boot_memory_data => boot_memory_data,
			i_flash_data    => flash_data,

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

			o_sdram_addr    => sdram_addr,
			o_sdram_wdata   => sdram_wdata,
			o_sdram_byteena => sdram_byteena,
			o_sdram_rden    => sdram_rden,
			o_sdram_wren    => sdram_wren,
			i_sdram_rdata   => sdram_rdata,
			i_sdram_ready   => sdram_ready,
			o_mem_advance   => mem_advance,

			i_hpm_ext_events => hpm_ext_events,
			i_irq_software => irq_software,
			i_irq_timer    => irq_timer,
			i_irq_external => irq_external,
			i_ic_data  => ic_data,
			i_ic_ready => ic_ready,
			o_ic_sel   => ic_sel,
			o_ic_inval => ic_inval
	);

	ICACHE : entity work.icache
		generic map (size_bits => ICACHE_SIZE_BITS, rom_base_kib => ROM_BASE_KIB, rom_end_kib => ROM_END_KIB, sel_from_kib => ROM_BASE_KIB, check_addr => false)
		port map (
			i_clk => pll_clk_if, i_clk_cpu => pll_clk_idexmem, i_rst => reset,
			i_addr => if_addr, i_sel => ic_sel, o_ready => ic_ready, o_data => ic_data,
			i_invalidate => ic_inval, o_miss => ic_miss,
			i_inval_region => fl_inval_valid, i_inval_first => fl_inval_first, i_inval_last => fl_inval_last,
			o_d_addr => id_addr, o_d_rden => id_rden, o_d_advance => id_adv, i_d_ready => id_ready,
			i_d_rdata => id_rdata, o_d_line => id_line, i_d_rdata_x => id_rdx
	);

	ROUTER_I : entity work.mem_region_router
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => id_addr, i_wdata => (others => '0'), i_byteena => (others => '0'),
			i_rden => id_rden, i_wren => '0', i_line => id_line, i_advance => id_adv,
			o_ready => id_ready, o_rdata => id_rdata, o_rdata_x => id_rdx,
			o_s_addr => si_addr, o_s_wdata => si_wdata, o_s_byteena => si_be, o_s_rden => si_rden,
			o_s_wren => si_wren, o_s_line => si_line, o_s_wdata_x => si_wdx, o_s_advance => si_adv,
			i_s_ready => si_ready, i_s_rdata => si_rdata, i_s_rdata_x => si_rdx,
			o_f_addr => fa_addr, o_f_rden => fa_rden, o_f_line => fa_line, o_f_advance => fa_adv,
			i_f_ready => fa_ready, i_f_rdata => fa_rdata, i_f_rdata_x => fa_rdx
	);

	-- the last 4 KB of the SDRAM hold the words the host shares with the program (tohost, fromhost,
	-- stdout): the host writes them behind the cache, so they are never kept in it
	dc_bypass <= '1' when m_addr(31 downto 12) = RAM_LAST_PAGE else '0';

	DCACHE : entity work.dcache
		generic map (size_bits => DCACHE_SIZE_BITS, write_through => true, rom_base_kib => ROM_BASE_KIB, rom_end_kib => ROM_END_KIB)
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => m_addr, i_wdata => m_wdata, i_byteena => m_byteena,
			i_rden => m_rden, i_wren => m_wren, i_mem_advance => mem_advance,
			o_ready => m_ready, o_rdata => m_rdata,
			i_flush => ic_inval, i_invalidate => '1', o_flush_done => dc_done, o_busy => dc_busy, o_miss => dc_miss,
			i_inval_region => fl_inval_valid, i_inval_first => fl_inval_first, i_inval_last => fl_inval_last,
			i_bypass => dc_bypass,
			o_d_addr => dd_addr, o_d_wdata => dd_wdata, o_d_byteena => dd_be,
			o_d_rden => dd_rden, o_d_wren => dd_wren, o_d_advance => dd_adv, i_d_ready => dd_ready,
			i_d_rdata => dd_rdata, o_d_line => dd_line, o_d_wdata_x => dd_wdx, i_d_rdata_x => dd_rdx
	);

	ROUTER_D : entity work.mem_region_router
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => dd_addr, i_wdata => dd_wdata, i_byteena => dd_be,
			i_rden => dd_rden, i_wren => dd_wren, i_line => dd_line, i_wdata_x => dd_wdx, i_advance => dd_adv,
			o_ready => dd_ready, o_rdata => dd_rdata, o_rdata_x => dd_rdx,
			o_s_addr => sd_addr, o_s_wdata => sd_wdata, o_s_byteena => sd_be, o_s_rden => sd_rden,
			o_s_wren => sd_wren, o_s_line => sd_line, o_s_wdata_x => sd_wdx, o_s_advance => sd_adv,
			i_s_ready => sd_ready, i_s_rdata => sd_rdata, i_s_rdata_x => sd_rdx,
			o_f_addr => fb_addr, o_f_rden => fb_rden, o_f_line => fb_line, o_f_advance => fb_adv,
			i_f_ready => fb_ready, i_f_rdata => fb_rdata, i_f_rdata_x => fb_rdx
	);

	hpm_ext_events <= flash_busy & dc_miss & ic_miss;

	FLASH_ARBITER : entity work.flash_arbiter
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_a_addr => fa_addr, i_a_rden => fa_rden, i_a_line => fa_line, i_a_advance => fa_adv,
			o_a_ready => fa_ready, o_a_rdata => fa_rdata, o_a_rdata_x => fa_rdx,
			i_b_addr => fb_addr, i_b_rden => fb_rden, i_b_line => fb_line, i_b_advance => fb_adv,
			o_b_ready => fb_ready, o_b_rdata => fb_rdata, o_b_rdata_x => fb_rdx,
			o_addr => fc_addr, o_rden => fc_rden, o_line => fc_line, o_advance => fc_adv,
			i_ready => fc_ready, i_rdata => fc_rdata, i_rdata_x => fc_rdx
	);

	FLASH_CHIP : entity work.flash_chip
		generic map (first_latency => FLASH_FIRST_LATENCY, next_latency => FLASH_NEXT_LATENCY, size_bytes => ROM_STORAGE_BYTES)
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => fc_addr, i_rden => fc_rden, i_line => fc_line, i_advance => fc_adv,
			o_ready => fc_ready, o_busy => flash_busy, o_rdata => fc_rdata, o_rdata_x => fc_rdx,
			o_mem_addr => flash_mem_addr, i_mem_data => flash_mem_data
	);

	g_plain : if not HAS_FLASH_CONTROLLER generate
	-- the storage behind the chip: a read-registered array loaded from the program image
	FLASH_STORAGE : entity work.ROM_simulation
		generic map (rom_file => ROM_FILE, size_bytes => 4 * 2 ** rom_addr_width)
		port map (
			i_addr => flash_mem_addr(31 downto 2),
			i_clk  => pll_clk_idexmem,
			i_re   => '1',
			o_data => flash_mem_data
	);
	end generate g_plain;

	-- With the controller the storage has two ports: A is read by the chip behind the caches and B is the one the
	-- command port of the chip writes (erase, program), as in the two-port FLASH of the board.
	g_update : if HAS_FLASH_CONTROLLER generate
	FLASH_STORAGE : entity work.flash_simulation
		generic map (size_bytes => 4 * 2 ** rom_addr_width, rom_file => ROM_FILE)
		port map (
			i_clk_a => pll_clk_idexmem, i_address_a => flash_mem_addr(rom_addr_width + 1 downto 2),
			i_rden_a => '1', o_q_a => flash_mem_data,
			i_clk_b => pll_clk_idexmem, i_address_b => fl_b_addr(rom_addr_width + 1 downto 2),
			i_rden_b => '1', i_wren_b => fl_b_we, i_data_b => fl_b_wdata, o_q_b => fl_b_data
	);

	FLASH_CMD : entity work.flash_cmd_port
		generic map (
			size_bytes => 4 * 2 ** rom_addr_width, base_addr => (others => '0'),
			erase_latency => FLASH_ERASE_LATENCY, program_latency => FLASH_PROGRAM_LATENCY
		)
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_cmd_valid => fl_cmd_valid, i_cmd_op => fl_cmd_op, i_cmd_addr => fl_cmd_addr,
			o_busy => fl_busy, o_wel => fl_wel, o_refused => fl_refused,
			o_buf_idx => fl_buf_idx, i_buf_data => fl_buf_data,
			o_mem_addr => fl_b_addr, o_mem_we => fl_b_we, o_mem_wdata => fl_b_wdata, i_mem_data => fl_b_data,
			o_inval_valid => fl_inval_valid, o_inval_first => fl_inval_first, o_inval_last => fl_inval_last
	);

	FLASH_CTRL : entity work.flash_controller
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_data_in => p_wdata, i_address => p_addr(2 downto 0),
			i_write => p_we(FLASH_CTRL_ID), i_read => p_re(FLASH_CTRL_ID),
			o_data_out => p_rdata(32 * FLASH_CTRL_ID + 31 downto 32 * FLASH_CTRL_ID),
			o_irq => irq_lines(IRQ_FLASH),
			o_cmd_valid => fl_cmd_valid, o_cmd_op => fl_cmd_op, o_cmd_addr => fl_cmd_addr,
			i_busy => fl_busy, i_wel => fl_wel, i_refused => fl_refused,
			i_buf_idx => fl_buf_idx, o_buf_data => fl_buf_data
	);
	end generate g_update;

	INTERCONNECT : entity work.ext_interconnect
		generic map (periph_addr_width => PLIC_ADDR_WIDTH)
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => sdram_addr, i_wdata => sdram_wdata, i_byteena => sdram_byteena,
			i_rden => sdram_rden, i_wren => sdram_wren, i_mem_advance => mem_advance,
			o_ready => sdram_ready, o_rdata => sdram_rdata,
			o_m_addr => m_addr, o_m_wdata => m_wdata, o_m_byteena => m_byteena,
			o_m_rden => m_rden, o_m_wren => m_wren, i_m_ready => m_ready, i_m_rdata => m_rdata,
			o_p_addr => p_addr, o_p_wdata => p_wdata, o_p_byteena => p_byteena,
			o_p_we => p_we, o_p_re => p_re, i_p_rdata => p_rdata
		);

	UART : entity work.jtag_uart
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => p_addr(7 downto 0), i_wdata => p_wdata, i_we => p_we(4), i_re => p_re(4),
			o_rdata => p_rdata(32 * 4 + 31 downto 32 * 4), o_irq => irq_lines(IRQ_UART_JTAG),
			i_tck => UART_TCK, i_tdi => UART_TDI, o_tdo => UART_TDO, i_ir_in => UART_IR_IN,
			i_state_cdr => UART_STATE_CDR, i_state_sdr => UART_STATE_SDR,
			i_state_udr => UART_STATE_UDR, i_state_uir => UART_STATE_UIR
		);

	-- The CLINT (msip, mtimecmp, mtime) and the PLIC (the controller of the external interrupt lines), in the clock
	-- domain of the core: their outputs are the MSIP, MTIP and MEIP of the core, with no synchronizer. The JTAG UART
	-- and the FLASH controller raise their lines (IRQ_UART_JTAG and IRQ_FLASH); the others stay at zero.
	g_irq : if HAS_INTERRUPTS generate
	CLINT : entity work.clint
		generic map (tick_cycles => CLINT_TICK_CYCLES)
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_data_in => p_wdata, i_address => p_addr(13 downto 0), i_write => p_we(CLINT_ID), i_read => p_re(CLINT_ID),
			o_data_out => p_rdata(32 * CLINT_ID + 31 downto 32 * CLINT_ID),
			o_irq_timer => irq_timer, o_irq_software => irq_software
		);

	PLIC : entity work.plic
		generic map (n_sources => PLIC_N_SOURCES, priority_bits => PLIC_PRIORITY_BITS, addr_width => PLIC_ADDR_WIDTH)
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_sources => irq_lines, i_data_in => p_wdata, i_address => p_addr,
			i_write => p_we(PLIC_ID), i_read => p_re(PLIC_ID),
			o_data_out => p_rdata(32 * PLIC_ID + 31 downto 32 * PLIC_ID),
			o_meip => irq_external
		);
	end generate g_irq;

	DISPLAY : entity work.seg_display
		port map (
			i_clk => pll_clk_idexmem, i_rst => reset,
			i_addr => p_addr(7 downto 0), i_wdata => p_wdata, i_we => p_we(5), i_re => p_re(5),
			o_rdata => p_rdata(32 * 5 + 31 downto 32 * 5),
			i_tck => '0', i_tdi => '0', i_ir_in => "00",
			i_state_cdr => '0', i_state_sdr => '0', i_state_udr => '0', i_state_uir => '0',
			o_value => DISPLAY_VALUE, o_fail => open, o_hex => DISPLAY_HEX
		);

	-- the SDRAM and its chip model; the debug ports of the model stay unused here
	SDRAM : entity work.sdram_system
		generic map (init_file => SDRAM_FILE)
		port map (
			i_clk_mem => CLK_MEM, i_clk_cpu => pll_clk_idexmem,
			i_rst_mem => reset,   i_rst_cpu => reset,
			i_addr => sd_addr, i_wdata => sd_wdata, i_byteena => sd_be,
			i_rden => sd_rden, i_wren => sd_wren, i_mem_advance => sd_adv,
			o_ready => sd_ready, o_rdata => sd_rdata,
			i_line => sd_line, i_wdata_x => sd_wdx, o_rdata_x => sd_rdx,
			i_ins_addr => si_addr, i_ins_rden => si_rden, i_ins_advance => si_adv, o_ins_ready => si_ready,
			o_ins_rdata => si_rdata, i_ins_line => si_line, o_ins_rdata_x => si_rdx,
			o_init_done => sdram_init,
			i_dbg_word_addr => DBG_WORD_ADDR, o_dbg_word_data => DBG_WORD_DATA,
			i_dbg_flip => '0', i_dbg_flip_addr => (others => '0'), i_dbg_flip_bit => (others => '0'),
			o_dbg_refreshes => dbg_refreshes, o_dbg_init_ok => dbg_init_ok
	);

	BOOT_MEMORY : entity work.ROM_simulation
		generic map (rom_file => BOOT_MEMORY_FILE, size_bytes => 4 * 2 ** boot_memory_addr_width)
		port map (
			i_addr 	=> if_addr(31 downto 2),
			i_clk 	=> pll_clk_if,
			i_re 		=> if_rden,
			o_data	=> boot_memory_data
	);

end architecture;
