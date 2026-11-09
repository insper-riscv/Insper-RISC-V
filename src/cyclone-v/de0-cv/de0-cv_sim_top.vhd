-- ============================================================================
-- Topo de simulação da plataforma de0-cv (SDRAM com a FLASH atrás das caches)
-- ============================================================================
-- O núcleo, a BOOT_MEMORY (vetor VHDL), as caches de instruções e de dados, o
-- modelo de chip da FLASH com o seu armazenamento (vetor VHDL) e a SDRAM (ponte,
-- árbitro, controlador e modelo de chip do repositório Memory) em clock próprio de
-- 143 MHz. A SDRAM é a RAM: não há outra memória de dados. A FLASH começa logo
-- depois da BOOT_MEMORY e termina em 256 KiB, e a SDRAM fica em 0x40000000; as
-- duas só são alcançadas pelas caches, cujos pedidos de linha um roteador de
-- região envia à FLASH (pelo árbitro) ou à SDRAM.
--
-- i_clk é o clock base do núcleo (um gerador de clock o divide por três, como na
-- internal-mem). i_clk_mem é o clock da SDRAM, conduzido pelo testbench sem
-- relação fixa com i_clk, como na placa. i_dbg_word_addr e o_dbg_word_data leem
-- uma palavra direto do modelo do chip, que é como o testbench compara o
-- conteúdo da memória com um golden.
--
-- A porta externa do núcleo passa pelo interconector do repositório Memory: o
-- bit 31 em '0' é a SDRAM e em '1' a janela de periféricos, com a UART JTAG em
-- 0xC0000000 e o registrador do display em 0xD0000000. Os sinais i_uart_* são os
-- da instância do Virtual JTAG da UART (ver jtag_uart), que o testbench conduz
-- para ler o que o programa imprime.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.de0_cv_map_pkg.all;

entity rv32im_sdram_flash_sim_test is
	generic (
	  -- Arquivo com a imagem da BOOT_MEMORY, uma palavra de 32 bits por linha em hexadecimal.
	  boot_memory_file : string := "default.hex";
	  -- Arquivo com a imagem da FLASH, uma palavra de 32 bits por linha em hexadecimal.
	  rom_file : string := "default.hex";
	  -- Largura do endereço de palavra da BOOT_MEMORY.
	  boot_memory_addr_width : natural := 9;
	  -- Largura do endereço de palavra da FLASH.
	  rom_addr_width : natural := 18;
	  -- Bordas até a primeira palavra do chip de FLASH e entre as palavras de uma linha.
	  flash_first_latency : natural := 24;
	  -- Bordas de espera entre as palavras de uma linha do chip de FLASH.
	  flash_next_latency  : natural := 4;
	  -- Largura do endereço de palavra da RAM interna; com a SDRAM como RAM não dimensiona nada.
	  ram_addr_width : natural := 9;
	  -- Zicsr no core (instrucoes CSR reais); false mantem o comportamento de NOP.
	  has_zicsr : boolean := false;
	  -- Habilita os contadores da extensão Zicntr (implica Zicsr).
	  has_zicntr : boolean := false;
	  -- Extensao M completa no core.
	  has_m : boolean := true;
	  -- Multiplicacao sem divisao (Zmmul) no core.
	  has_zmmul : boolean := false;
	  -- Zifencei no core (FENCE.I invalida a cache de instrucoes); false mantem o NOP.
	  has_zifencei : boolean := false;
	  -- Acesso desalinhado a memoria principal executado em hardware (Zicclsm).
	  has_zicclsm : boolean := true;
	  -- Interrupcoes de maquina: o CLINT e o controlador externo na janela de periféricos, e as tres linhas no core.
	  has_interrupts : boolean := true;
	  -- Interrupcao de estouro de contador (Sscofpmf): exige Zihpm e as interrupcoes.
	  has_sscofpmf : boolean := work.de0_cv_map_pkg.HAS_SSCOFPMF;
	  -- Falhas de acesso (causas 1, 5 e 7) fora das regioes validas do mapa; exige Zicsr.
	  has_access_faults : boolean := work.de0_cv_map_pkg.HAS_ACCESS_FAULTS;
	  -- Ciclos de clock do core por incremento do mtime do CLINT.
	  clint_tick_cycles : positive := work.de0_cv_map_pkg.CLINT_TICK_CYCLES;
	  -- Contadores de eventos da extensao Zihpm (quatro, indices 3 a 6); exige Zicsr.
	  has_zihpm : boolean := false;
	  -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os indices a partir de 3.
	  hpm_counters : natural range 0 to 29 := 29;
	  -- Largura, em bits, de cada contador de eventos do Zihpm.
	  hpm_width : natural range 0 to 64 := 64;
	  -- Extensao Zimop no core (mop.r.n e mop.rr.n escrevem zero em rd).
	  has_zimop : boolean := work.de0_cv_map_pkg.HAS_ZIMOP;
	  -- Extensao Zicond no core (czero.eqz e czero.nez).
	  has_zicond : boolean := work.de0_cv_map_pkg.HAS_ZICOND;
	  -- Dicas ntl.* da extensao Zihintntl no core (executam como nop).
	  has_zihintntl : boolean := work.de0_cv_map_pkg.HAS_ZIHINTNTL;
	  -- Dica pause da extensao Zihintpause no core (executa como nop).
	  has_zihintpause : boolean := work.de0_cv_map_pkg.HAS_ZIHINTPAUSE;
	  -- A ROM fica fora do core (o modelo de memória do platform.yaml).
	  rom_external : boolean := work.de0_cv_map_pkg.ROM_EXTERNAL;
	  -- A RAM fica fora do core (o modelo de memória do platform.yaml).
	  ram_external : boolean := work.de0_cv_map_pkg.RAM_EXTERNAL;
	  -- Existe cache de instruções (o modelo de memória do platform.yaml).
	  has_icache : boolean := work.de0_cv_map_pkg.HAS_ICACHE;
	  -- Existe cache de dados (o modelo de memória do platform.yaml).
	  has_dcache : boolean := work.de0_cv_map_pkg.HAS_DCACHE;
	  -- Tamanho da cache de instruções, em bits (o modelo de memória do platform.yaml).
	  icache_size_bits : positive := work.de0_cv_map_pkg.ICACHE_SIZE_BITS;
	  -- Tamanho da cache de dados, em bits (o modelo de memória do platform.yaml).
	  dcache_size_bits : positive := work.de0_cv_map_pkg.DCACHE_SIZE_BITS;
	  -- Base RV32E (16 registradores) no core; false e o RV32I (o perfil da plataforma por padrao).
	  has_e : boolean := work.de0_cv_map_pkg.HAS_E;
	  -- Controlador de FLASH na janela de periferico 3 (0xB0000000), com a FLASH de duas portas e o chip de comandos
	  -- (apagar, gravar, proteger) atras dele: a atualizacao de programa em campo. Desligado, a FLASH e so de leitura.
	  has_flash_controller : boolean := false;
	  -- Bordas de espera de um apagar de setor do chip de FLASH, antes da varredura do setor.
	  flash_erase_latency   : natural := 2000;
	  -- Bordas de espera de uma gravacao de pagina do chip de FLASH, antes da varredura da pagina.
	  flash_program_latency : natural := 200;
	  -- Imagem de programa gravada na SDRAM no tempo zero (uma palavra de 32 bits por linha, em
	  -- hexadecimal, a partir de 0x40000000): o hospedeiro que carrega o chip pela porta de debug.
	  sdram_file : string := "";
	  -- Periodo, em picossegundos, do clock CLK_MEM do controlador da SDRAM (o do platform.yaml): base da conversao dos tempos do chip em ciclos.
	  sdram_tck_ps : natural := work.de0_cv_map_pkg.SDRAM_TCK_PS
  	);
	port (
    	-- Clock base do núcleo; um gerador de clock o divide por três.
    	i_clk     : in  std_logic;
    	-- Clock da SDRAM, conduzido pelo testbench sem relação fixa com i_clk.
    	i_clk_mem : in  std_logic;
		-- Reset do topo, ativo em '1'.
		i_rst   : in  std_logic := '0';
		-- Índice de palavra lido direto do modelo do chip de SDRAM, para o testbench.
		i_dbg_word_addr : in  std_logic_vector(23 downto 0) := (others => '0');
		-- Palavra do modelo do chip de SDRAM no índice de i_dbg_word_addr.
		o_dbg_word_data : out std_logic_vector(31 downto 0);
		-- Virtual JTAG da UART: clock TCK.
		i_uart_tck       : in  std_logic := '0';
		-- Virtual JTAG da UART: entrada de dados TDI.
		i_uart_tdi       : in  std_logic := '0';
		-- Virtual JTAG da UART: saída de dados TDO.
		o_uart_tdo       : out std_logic;
		-- Virtual JTAG da UART: registrador de instrução.
		i_uart_ir_in     : in  std_logic_vector(1 downto 0) := "00";
		-- Virtual JTAG da UART: estado Capture-DR.
		i_uart_state_cdr : in  std_logic := '0';
		-- Virtual JTAG da UART: estado Shift-DR.
		i_uart_state_sdr : in  std_logic := '0';
		-- Virtual JTAG da UART: estado Update-DR.
		i_uart_state_udr : in  std_logic := '0';
		-- Virtual JTAG da UART: estado Update-IR.
		i_uart_state_uir : in  std_logic := '0';
		-- Valor do registrador do display (periférico 5, 0xD0000000), cuja porta do hospedeiro fica parada aqui
		o_display_value  : out std_logic_vector(23 downto 0);
		-- Segmentos dos sete segmentos do display, 42 bits.
		o_display_hex    : out std_logic_vector(41 downto 0)
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

	-- Endereço de byte da busca de instrução do núcleo.
	signal if_addr : std_logic_vector(31 downto 0);
	-- Habilita de leitura da busca de instrução.
	signal if_rden : std_logic;
	-- Palavra lida da BOOT_MEMORY.
	signal boot_memory_data : std_logic_vector(31 downto 0);
	-- Palavra lida da FLASH pelo estágio IF.
	signal flash_data : std_logic_vector(31 downto 0);

	-- Endereço de byte da leitura de dado do estágio MEM na FLASH.
	signal flash_addr2 : std_logic_vector(31 downto 0);
	-- Habilita da leitura de dado do estágio MEM na FLASH.
	signal flash_rden2 : std_logic;
	-- Palavra lida da FLASH pelo estágio MEM.
	signal flash_data2 : std_logic_vector(31 downto 0) := (others => '0');

	-- RAM interna do núcleo: endereço.
	signal ram_addr : std_logic_vector(31 downto 0);
	-- RAM interna do núcleo: dado de escrita.
	signal ram_wdata : std_logic_vector(31 downto 0);
	-- Dado lido da RAM interna do núcleo; sem RAM interna fica em zero.
	signal ram_rdata : std_logic_vector(31 downto 0) := (others => '0');   -- sem RAM dentro do FPGA
	-- RAM interna do núcleo: habilita geral.
	signal ram_en : std_logic;
	-- RAM interna do núcleo: habilita de escrita.
	signal ram_wren : std_logic;
	-- RAM interna do núcleo: habilita de leitura.
	signal ram_rden : std_logic;
	-- RAM interna do núcleo: habilita de bytes.
	signal ram_byteena : std_logic_vector(3 downto 0);

	-- Barramento externo do núcleo para a SDRAM: endereço.
	signal sdram_addr    : std_logic_vector(31 downto 0);
	-- Barramento externo do núcleo para a SDRAM: dado de escrita.
	signal sdram_wdata   : std_logic_vector(31 downto 0);
	-- Barramento externo do núcleo para a SDRAM: dado lido.
	signal sdram_rdata   : std_logic_vector(31 downto 0);
	-- Barramento externo do núcleo para a SDRAM: habilita de bytes.
	signal sdram_byteena : std_logic_vector(3 downto 0);
	-- Barramento externo do núcleo para a SDRAM: habilita de leitura.
	signal sdram_rden    : std_logic;
	-- Barramento externo do núcleo para a SDRAM: habilita de escrita.
	signal sdram_wren    : std_logic;
	-- Barramento externo do núcleo: acesso concluído.
	signal sdram_ready   : std_logic;
	-- Avanço do pipeline do núcleo quando o acesso à memória conclui.
	signal mem_advance   : std_logic;

	-- Atrás do interconector: endereço de byte da SDRAM e das janelas de periféricos
	signal m_addr    : std_logic_vector(31 downto 0);
	-- Saída do interconector para a SDRAM: dado de escrita.
	signal m_wdata   : std_logic_vector(31 downto 0);
	-- Saída do interconector para a SDRAM: dado lido.
	signal m_rdata   : std_logic_vector(31 downto 0);
	-- Saída do interconector para a SDRAM: habilita de bytes.
	signal m_byteena : std_logic_vector(3 downto 0);
	-- Saída do interconector para a SDRAM: habilita de leitura.
	signal m_rden    : std_logic;
	-- Saída do interconector para a SDRAM: habilita de escrita.
	signal m_wren    : std_logic;
	-- Saída do interconector para a SDRAM: acesso concluído.
	signal m_ready   : std_logic;
	-- Janela de periféricos: endereço.
	signal p_addr    : std_logic_vector(PLIC_ADDR_WIDTH - 1 downto 0);
	-- Linhas de interrupção dos periféricos para o PLIC; uma ausente fica em zero.
	signal irq_lines : std_logic_vector(PLIC_N_SOURCES downto 1) := (others => '0');
	-- Janela de periféricos: dado de escrita.
	signal p_wdata   : std_logic_vector(31 downto 0);
	-- Janela de periféricos: habilita de bytes.
	signal p_byteena : std_logic_vector(3 downto 0);
	-- Janela de periféricos: escrita, leitura.
	signal p_we, p_re : std_logic_vector(7 downto 0);
	-- Janela de periféricos: dado lido.
	signal p_rdata   : std_logic_vector(8 * 32 - 1 downto 0) := (others => '0');
	-- As três linhas de interrupção de máquina do núcleo
	signal irq_timer, irq_software, irq_external : std_logic := '0';
	-- As três linhas de interrupção entram no núcleo por um registrador: o árbitro do PLIC e o comparador do mtime do CLINT
	-- ficam fora do caminho que decide a tomada da interrupção (um ciclo de latência a mais).
	signal irq_timer_q, irq_software_q, irq_external_q : std_logic := '0';
	-- mtime do CLINT, que o CSR time do núcleo espelha.
	signal clint_mtime : std_logic_vector(63 downto 0) := (others => '0');

	-- Clock do estágio IF, saída 0 do gerador de clock.
	signal pll_clk_if     : std_logic;
	-- Clock dos estágios ID, EX e MEM, saída 1 do gerador de clock.
	signal pll_clk_idexmem: std_logic;
	-- Clock do estágio WB, saída 2 do gerador de clock.
	signal pll_clk_wb     : std_logic;

	-- Contagem de refreshes do controlador da SDRAM, lida pela depuração.
	signal dbg_refreshes  : std_logic_vector(31 downto 0);
	-- Inicialização da SDRAM concluída com sucesso.
	signal dbg_init_ok    : std_logic;
	-- Inicialização da SDRAM em andamento.
	signal sdram_init     : std_logic;

	-- Busca de instrucao em SDRAM: cache de instrucoes no clock do IF
	signal ic_data   : std_logic_vector(31 downto 0);
	-- Cache de instruções: acesso concluído.
	signal ic_ready  : std_logic;
	-- Cache de instruções: seleção de região.
	signal ic_sel    : std_logic;
	-- Cache de instruções: pulso de invalidação.
	signal ic_inval  : std_logic;
	-- Porta de memória da cache de instruções: endereço.
	signal id_addr   : std_logic_vector(31 downto 0);
	-- Porta de memória da cache de instruções: habilita de leitura.
	signal id_rden   : std_logic;
	-- Porta de memória da cache de instruções: avanço para a próxima palavra da linha.
	signal id_adv    : std_logic;
	-- Porta de memória da cache de instruções: acesso concluído.
	signal id_ready  : std_logic;
	-- Porta de memória da cache de instruções: dado lido.
	signal id_rdata  : std_logic_vector(31 downto 0);
	-- Porta de memória da cache de instruções: pedido de linha de cache.
	signal id_line   : std_logic;
	-- Porta de memória da cache de instruções: linha larga lida de 96 bits.
	signal id_rdx    : std_logic_vector(95 downto 0);
	-- Eventos das caches e da FLASH para os contadores do Zihpm: falha da cache de instrucoes, falha da cache de
	-- dados e ciclo de espera do chip de FLASH.
	signal ic_miss, dc_miss, flash_busy : std_logic;
	-- Eventos externos para os contadores do Zihpm: falha da cache de instruções, falha da cache de dados e espera da
	-- FLASH.
	signal hpm_ext_events : std_logic_vector(2 downto 0);

	-- Roteador da cache de instruções: lado da SDRAM (porta de instruções do sdram_system)
	signal si_addr   : std_logic_vector(31 downto 0);
	-- Roteador de instruções, lado da SDRAM: dado de escrita.
	signal si_wdata  : std_logic_vector(31 downto 0);
	-- Roteador de instruções, lado da SDRAM: habilita de bytes.
	signal si_be     : std_logic_vector(3 downto 0);
	-- Roteador de instruções, lado da SDRAM: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço
	-- para a próxima palavra da linha, acesso concluído.
	signal si_rden, si_wren, si_line, si_adv, si_ready : std_logic;
	-- Roteador de instruções, lado da SDRAM: linha larga de escrita de 96 bits.
	signal si_wdx    : std_logic_vector(95 downto 0);
	-- Roteador de instruções, lado da SDRAM: dado lido.
	signal si_rdata  : std_logic_vector(31 downto 0);
	-- Roteador de instruções, lado da SDRAM: linha larga lida de 96 bits.
	signal si_rdx    : std_logic_vector(95 downto 0);

	-- Cache de dados: lado da memória
	signal dc_bypass : std_logic;
	-- Porta de memória da cache de dados: endereço, dado de escrita, dado lido.
	signal dd_addr, dd_wdata, dd_rdata : std_logic_vector(31 downto 0);
	-- Porta de memória da cache de dados: habilita de bytes.
	signal dd_be     : std_logic_vector(3 downto 0);
	-- Porta de memória da cache de dados: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço para
	-- a próxima palavra da linha, acesso concluído.
	signal dd_rden, dd_wren, dd_line, dd_adv, dd_ready : std_logic;
	-- Porta de memória da cache de dados: linha larga de escrita de 96 bits, linha larga lida de 96 bits.
	signal dd_wdx, dd_rdx : std_logic_vector(95 downto 0);
	-- Cache de dados com a invalidação concluída; Cache de dados ocupada com uma invalidação.
	signal dc_done, dc_busy : std_logic;

	-- Roteador da cache de dados: lado da SDRAM (porta de dados do sdram_system)
	signal sd_addr, sd_wdata, sd_rdata : std_logic_vector(31 downto 0);
	-- Roteador de dados, lado da SDRAM: habilita de bytes.
	signal sd_be     : std_logic_vector(3 downto 0);
	-- Roteador de dados, lado da SDRAM: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço para a
	-- próxima palavra da linha, acesso concluído.
	signal sd_rden, sd_wren, sd_line, sd_adv, sd_ready : std_logic;
	-- Roteador de dados, lado da SDRAM: linha larga de escrita de 96 bits, linha larga lida de 96 bits.
	signal sd_wdx, sd_rdx : std_logic_vector(95 downto 0);

	-- Lado da FLASH dos dois roteadores, o árbitro e o chip
	signal fa_addr, fa_rdata, fb_addr, fb_rdata, fc_addr, fc_rdata : std_logic_vector(31 downto 0);
	-- Roteador de instruções, lado da FLASH: habilita de leitura; Roteador de instruções, lado da FLASH: pedido de linha
	-- de cache; Roteador de instruções, lado da FLASH: avanço para a próxima palavra da linha; Roteador de instruções,
	-- lado da FLASH: acesso concluído; Roteador de dados, lado da FLASH: habilita de leitura; Roteador de dados, lado da
	-- FLASH: pedido de linha de cache; Roteador de dados, lado da FLASH: avanço para a próxima palavra da linha; Roteador
	-- de dados, lado da FLASH: acesso concluído.
	signal fa_rden, fa_line, fa_adv, fa_ready, fb_rden, fb_line, fb_adv, fb_ready : std_logic;
	-- Árbitro, lado do chip de FLASH: habilita de leitura, pedido de linha de cache, avanço para a próxima palavra da
	-- linha, acesso concluído.
	signal fc_rden, fc_line, fc_adv, fc_ready : std_logic;
	-- Roteador de instruções, lado da FLASH: linha larga lida de 96 bits; Roteador de dados, lado da FLASH: linha larga
	-- lida de 96 bits; Árbitro, lado do chip de FLASH: linha larga lida de 96 bits.
	signal fa_rdx, fb_rdx, fc_rdx : std_logic_vector(95 downto 0);
	-- Endereço de byte do pedido do árbitro ao chip de FLASH; Palavra lida do chip de FLASH pelo árbitro.
	signal flash_mem_addr, flash_mem_data : std_logic_vector(31 downto 0);

	-- Controlador de FLASH e chip de comandos (so com HAS_FLASH_CONTROLLER): comando, estado, buffer de pagina,
	-- porta B do armazenamento e invalidacao por regiao das duas caches.
	signal fl_cmd_valid, fl_busy, fl_wel, fl_refused : std_logic := '0';
	-- Controlador de FLASH: operação do comando.
	signal fl_cmd_op       : std_logic_vector(2 downto 0);
	-- Controlador de FLASH: endereço do comando.
	signal fl_cmd_addr     : std_logic_vector(31 downto 0);
	-- Controlador de FLASH: índice de palavra do buffer de página.
	signal fl_buf_idx      : std_logic_vector(5 downto 0);
	-- Controlador de FLASH: palavra do buffer de página.
	signal fl_buf_data     : std_logic_vector(31 downto 0);
	-- Controlador de FLASH: endereço da porta B do armazenamento, dado de escrita da porta B do armazenamento, dado lido
	-- da porta B do armazenamento.
	signal fl_b_addr, fl_b_wdata, fl_b_data : std_logic_vector(31 downto 0) := (others => '0');
	-- Controlador de FLASH: escrita na porta B do armazenamento.
	signal fl_b_we         : std_logic := '0';
	-- Invalidação por região das caches: pulso de validade.
	signal fl_inval_valid  : std_logic := '0';
	-- Invalidação por região das caches: primeiro endereço, último endereço.
	signal fl_inval_first, fl_inval_last : std_logic_vector(31 downto 0) := (others => '0');

begin

	u_pll : entity work.clk_gen_3way
    port map (
      i_clk    => i_clk,
      i_rst    => i_rst,
      o_clk0 => pll_clk_if,
      o_clk1 => pll_clk_idexmem,
      o_clk2 => pll_clk_wb
    );

	u_core : entity work.core
		generic map (has_m => has_m, has_zmmul => has_zmmul, has_zicsr => has_zicsr, has_zicntr => has_zicntr,
			has_zifencei => has_zifencei, has_zicclsm => has_zicclsm, has_e => has_e,
			has_zihpm => has_zihpm, hpm_counters => hpm_counters, hpm_width => hpm_width, has_zimop => has_zimop,
			has_zicond => has_zicond, has_zihintntl => has_zihintntl, has_zihintpause => has_zihintpause,
			has_interrupts => has_interrupts and (has_zicsr or has_zicntr or has_zihpm),
			has_sscofpmf => has_sscofpmf and has_zihpm and has_interrupts, time_external => has_interrupts,
			has_access_faults => has_access_faults and (has_zicsr or has_zicntr or has_zihpm),
			periph_slots => work.de0_cv_map_pkg.PERIPH_SLOTS)
		port map (
			o_trap       => core_trap,
			o_retire     => core_retire,
			o_trap_cause => core_trap_cause,
			o_trap_pc    => core_trap_pc,

			i_clk          => pll_clk_idexmem,
			i_rst 		=> i_rst,

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

			o_ext_addr    => sdram_addr,
			o_ext_wdata   => sdram_wdata,
			o_ext_byteena => sdram_byteena,
			o_ext_rden    => sdram_rden,
			o_ext_wren    => sdram_wren,
			i_ext_rdata   => sdram_rdata,
			i_ext_ready   => sdram_ready,
			o_mem_advance   => mem_advance,

			i_hpm_ext_events => hpm_ext_events,
			i_irq_software => irq_software_q,
			i_irq_timer    => irq_timer_q,
			i_mtime        => clint_mtime,
			i_irq_external => irq_external_q,
			i_ic_data  => ic_data,
			i_ic_ready => ic_ready,
			o_ic_sel   => ic_sel,
			o_ic_inval => ic_inval
	);

	u_icache : entity work.icache
		generic map (size_bits => icache_size_bits, rom_base_kib => ROM_BASE_KIB, rom_end_kib => ROM_END_KIB,
			sel_from_kib => ROM_BASE_KIB, check_addr => false)
		port map (
			i_clk => pll_clk_if, i_clk_cpu => pll_clk_idexmem, i_rst => i_rst,
			i_addr => if_addr, i_sel => ic_sel, o_ready => ic_ready, o_data => ic_data,
			i_invalidate => ic_inval, o_miss => ic_miss,
			i_inval_region => fl_inval_valid, i_inval_first => fl_inval_first, i_inval_last => fl_inval_last,
			o_d_addr => id_addr, o_d_rden => id_rden, o_d_advance => id_adv, i_d_ready => id_ready,
			i_d_rdata => id_rdata, o_d_line => id_line, i_d_rdata_x => id_rdx
	);

	u_router_i : entity work.mem_region_router
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_addr => id_addr, i_wdata => (others => '0'), i_byteena => (others => '0'),
			i_rden => id_rden, i_wren => '0', i_line => id_line, i_advance => id_adv,
			o_ready => id_ready, o_rdata => id_rdata, o_rdata_x => id_rdx,
			o_s_addr => si_addr, o_s_wdata => si_wdata, o_s_byteena => si_be, o_s_rden => si_rden,
			o_s_wren => si_wren, o_s_line => si_line, o_s_wdata_x => si_wdx, o_s_advance => si_adv,
			i_s_ready => si_ready, i_s_rdata => si_rdata, i_s_rdata_x => si_rdx,
			o_f_addr => fa_addr, o_f_rden => fa_rden, o_f_line => fa_line, o_f_advance => fa_adv,
			i_f_ready => fa_ready, i_f_rdata => fa_rdata, i_f_rdata_x => fa_rdx
	);

	-- Os últimos 4 KB da SDRAM guardam as palavras que o hospedeiro compartilha com o programa (tohost, fromhost,
	-- stdout): o hospedeiro as escreve atrás da cache, então nunca ficam guardadas nela
	dc_bypass <= '1' when m_addr(31 downto 12) = RAM_LAST_PAGE else '0';

	u_dcache : entity work.dcache
		generic map (size_bits => dcache_size_bits, write_through => true, rom_base_kib => ROM_BASE_KIB,
			rom_end_kib => ROM_END_KIB)
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
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

	u_router_d : entity work.mem_region_router
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
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

	u_flash_arbiter : entity work.flash_arbiter
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_a_addr => fa_addr, i_a_rden => fa_rden, i_a_line => fa_line, i_a_advance => fa_adv,
			o_a_ready => fa_ready, o_a_rdata => fa_rdata, o_a_rdata_x => fa_rdx,
			i_b_addr => fb_addr, i_b_rden => fb_rden, i_b_line => fb_line, i_b_advance => fb_adv,
			o_b_ready => fb_ready, o_b_rdata => fb_rdata, o_b_rdata_x => fb_rdx,
			o_addr => fc_addr, o_rden => fc_rden, o_line => fc_line, o_advance => fc_adv,
			i_ready => fc_ready, i_rdata => fc_rdata, i_rdata_x => fc_rdx
	);

	u_flash_chip : entity work.flash_chip
		generic map (first_latency => flash_first_latency, next_latency => flash_next_latency,
			size_bytes => ROM_STORAGE_BYTES)
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_addr => fc_addr, i_rden => fc_rden, i_line => fc_line, i_advance => fc_adv,
			o_ready => fc_ready, o_busy => flash_busy, o_rdata => fc_rdata, o_rdata_x => fc_rdx,
			o_mem_addr => flash_mem_addr, i_mem_data => flash_mem_data
	);

	g_plain : if not has_flash_controller generate
	-- O armazenamento atrás do chip: um vetor com leitura registrada, carregado da imagem do programa
	u_flash_storage : entity work.ROM_simulation
		generic map (rom_file => rom_file, size_bytes => 4 * 2 ** rom_addr_width)
		port map (
			i_addr => flash_mem_addr(31 downto 2),
			i_clk  => pll_clk_idexmem,
			i_re   => '1',
			o_data => flash_mem_data
	);
	end generate g_plain;

	-- Com o controlador o armazenamento tem duas portas: a A é lida pelo chip atrás das caches e a B é a que a porta
	-- de comandos do chip escreve (apagar, gravar), como na FLASH de duas portas da placa.
	g_update : if has_flash_controller generate
	u_flash_storage : entity work.flash_simulation
		generic map (size_bytes => 4 * 2 ** rom_addr_width, rom_file => rom_file)
		port map (
			i_clk_a => pll_clk_idexmem, i_address_a => flash_mem_addr(rom_addr_width + 1 downto 2),
			i_rden_a => '1', o_q_a => flash_mem_data,
			i_clk_b => pll_clk_idexmem, i_address_b => fl_b_addr(rom_addr_width + 1 downto 2),
			i_rden_b => '1', i_wren_b => fl_b_we, i_data_b => fl_b_wdata, o_q_b => fl_b_data
	);

	u_flash_cmd : entity work.flash_cmd_port
		generic map (
			size_bytes => 4 * 2 ** rom_addr_width, base_addr => (others => '0'),
			erase_latency => flash_erase_latency, program_latency => flash_program_latency
		)
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_cmd_valid => fl_cmd_valid, i_cmd_op => fl_cmd_op, i_cmd_addr => fl_cmd_addr,
			o_busy => fl_busy, o_wel => fl_wel, o_refused => fl_refused,
			o_buf_idx => fl_buf_idx, i_buf_data => fl_buf_data,
			o_mem_addr => fl_b_addr, o_mem_we => fl_b_we, o_mem_wdata => fl_b_wdata, i_mem_data => fl_b_data,
			o_inval_valid => fl_inval_valid, o_inval_first => fl_inval_first, o_inval_last => fl_inval_last
	);

	u_flash_ctrl : entity work.flash_controller
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_data_in => p_wdata, i_address => p_addr(2 downto 0),
			i_write => p_we(FLASH_CTRL_ID), i_read => p_re(FLASH_CTRL_ID),
			o_data_out => p_rdata(32 * FLASH_CTRL_ID + 31 downto 32 * FLASH_CTRL_ID),
			o_irq => irq_lines(IRQ_FLASH),
			o_cmd_valid => fl_cmd_valid, o_cmd_op => fl_cmd_op, o_cmd_addr => fl_cmd_addr,
			i_busy => fl_busy, i_wel => fl_wel, i_refused => fl_refused,
			i_buf_idx => fl_buf_idx, o_buf_data => fl_buf_data
	);
	end generate g_update;

	u_interconnect : entity work.ext_interconnect
		generic map (periph_addr_width => PLIC_ADDR_WIDTH)
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_addr => sdram_addr, i_wdata => sdram_wdata, i_byteena => sdram_byteena,
			i_rden => sdram_rden, i_wren => sdram_wren, i_mem_advance => mem_advance,
			o_ready => sdram_ready, o_rdata => sdram_rdata,
			o_m_addr => m_addr, o_m_wdata => m_wdata, o_m_byteena => m_byteena,
			o_m_rden => m_rden, o_m_wren => m_wren, i_m_ready => m_ready, i_m_rdata => m_rdata,
			o_p_addr => p_addr, o_p_wdata => p_wdata, o_p_byteena => p_byteena,
			o_p_we => p_we, o_p_re => p_re, i_p_rdata => p_rdata
		);

	u_uart : entity work.jtag_uart
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_addr => p_addr(7 downto 0), i_wdata => p_wdata, i_we => p_we(4), i_re => p_re(4),
			o_rdata => p_rdata(32 * 4 + 31 downto 32 * 4), o_irq => irq_lines(IRQ_UART_JTAG),
			i_tck => i_uart_tck, i_tdi => i_uart_tdi, o_tdo => o_uart_tdo, i_ir_in => i_uart_ir_in,
			i_state_cdr => i_uart_state_cdr, i_state_sdr => i_uart_state_sdr,
			i_state_udr => i_uart_state_udr, i_state_uir => i_uart_state_uir
		);

	-- O CLINT (msip, mtimecmp, mtime) e o PLIC (o controlador das linhas de interrupção externas), no domínio de
	-- clock do núcleo: as saídas deles são o MSIP, o MTIP e o MEIP do núcleo, sem sincronizador. A UART JTAG
	-- e o controlador de FLASH levantam as suas linhas (IRQ_UART_JTAG e IRQ_FLASH); as outras ficam em zero.
	g_irq : if has_interrupts generate
	process (pll_clk_idexmem)
	begin
		if rising_edge(pll_clk_idexmem) then
			irq_timer_q    <= irq_timer;
			irq_software_q <= irq_software;
			irq_external_q <= irq_external;
		end if;
	end process;

	u_clint : entity work.clint
		generic map (tick_cycles => clint_tick_cycles)
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_data_in => p_wdata, i_address => p_addr(13 downto 0), i_write => p_we(CLINT_ID),
			o_data_out => p_rdata(32 * CLINT_ID + 31 downto 32 * CLINT_ID),
			o_irq_timer => irq_timer, o_irq_software => irq_software, o_mtime => clint_mtime
		);

	u_plic : entity work.plic
		generic map (n_sources => PLIC_N_SOURCES, priority_bits => PLIC_PRIORITY_BITS, addr_width => PLIC_ADDR_WIDTH)
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_sources => irq_lines, i_data_in => p_wdata, i_address => p_addr,
			i_write => p_we(PLIC_ID), i_read => p_re(PLIC_ID),
			o_data_out => p_rdata(32 * PLIC_ID + 31 downto 32 * PLIC_ID),
			o_meip => irq_external
		);
	end generate g_irq;

	u_display : entity work.seg_display
		port map (
			i_clk => pll_clk_idexmem, i_rst => i_rst,
			i_address => p_addr(7 downto 0), i_data_in => p_wdata, i_write => p_we(5),
			o_rdata => p_rdata(32 * 5 + 31 downto 32 * 5),
			i_tck => '0', i_tdi => '0', i_ir_in => "00",
			i_state_cdr => '0', i_state_sdr => '0', i_state_udr => '0', i_state_uir => '0',
			o_value => o_display_value, o_fail => open, o_hex => o_display_hex
		);

	-- A SDRAM e o seu modelo de chip; as portas de depuração do modelo ficam sem uso aqui
	u_sdram : entity work.sdram_system
		generic map (tck_ps => sdram_tck_ps,
			init_cycles => work.sdram_pkg.cycles(work.sdram_pkg.T_INIT_PS, sdram_tck_ps),
			refresh_cycles => work.sdram_pkg.cycles(work.sdram_pkg.T_REFI_PS, sdram_tck_ps) * 9 / 10,
			init_file => sdram_file)
		port map (
			i_clk_mem => i_clk_mem, i_clk_cpu => pll_clk_idexmem,
			i_rst_mem => i_rst,   i_rst_cpu => i_rst,
			i_addr => sd_addr, i_wdata => sd_wdata, i_byteena => sd_be,
			i_rden => sd_rden, i_wren => sd_wren, i_mem_advance => sd_adv,
			o_ready => sd_ready, o_rdata => sd_rdata,
			i_line => sd_line, i_wdata_x => sd_wdx, o_rdata_x => sd_rdx,
			i_ins_addr => si_addr, i_ins_rden => si_rden, i_ins_advance => si_adv, o_ins_ready => si_ready,
			o_ins_rdata => si_rdata, i_ins_line => si_line, o_ins_rdata_x => si_rdx,
			o_init_done => sdram_init,
			i_dbg_word_addr => i_dbg_word_addr, o_dbg_word_data => o_dbg_word_data,
			i_dbg_flip => '0', i_dbg_flip_addr => (others => '0'), i_dbg_flip_bit => (others => '0'),
			o_dbg_refreshes => dbg_refreshes, o_dbg_init_ok => dbg_init_ok
	);

	u_boot_memory : entity work.ROM_simulation
		generic map (rom_file => boot_memory_file, size_bytes => 4 * 2 ** boot_memory_addr_width)
		port map (
			i_addr 	=> if_addr(31 downto 2),
			i_clk 	=> pll_clk_if,
			i_re 		=> if_rden,
			o_data	=> boot_memory_data
	);

end architecture;
