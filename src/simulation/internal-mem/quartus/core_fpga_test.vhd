-- =============================================================================
-- Topo de hardware da plataforma internal-mem para a DE0-CV
--
-- Monta o núcleo com a BOOT_MEMORY, a FLASH e a RAM dentro da FPGA, a UART mapeada em
-- 0xC0000000, o carregador da FLASH por JTAG e o PLL de três fases. Os LEDs mostram o
-- estado do PLL, do reset e do carregador. O reset do núcleo é a soma do PLL sem lock, do
-- botão físico (ativo em nível baixo) e do carregador da FLASH.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.internal_mem_map_pkg.all;

entity core_fpga_test is
	generic (
		-- Base RV32E (16 registradores) no core; false e o RV32I (o perfil da plataforma por padrao).
		HAS_E        : boolean := work.internal_mem_map_pkg.HAS_E;
		-- Extensao M completa no core.
		HAS_M        : boolean := work.internal_mem_map_pkg.HAS_M;
		-- Multiplicacao sem divisao (Zmmul) no core.
		HAS_ZMMUL    : boolean := work.internal_mem_map_pkg.HAS_ZMMUL;
		-- Zicsr no core (CSRs e traps do modo maquina).
		HAS_ZICSR    : boolean := work.internal_mem_map_pkg.HAS_ZICSR;
		-- Contadores cycle, time e instret (Zicntr).
		HAS_ZICNTR   : boolean := work.internal_mem_map_pkg.HAS_ZICNTR;
		-- Contadores de eventos do Zihpm.
		HAS_ZIHPM    : boolean := work.internal_mem_map_pkg.HAS_ZIHPM;
		-- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os indices a partir de 3.
		HPM_COUNTERS : natural range 0 to 29 := 29;
		-- Largura, em bits, de cada contador de eventos do Zihpm.
		HPM_WIDTH    : natural range 0 to 64 := 64;
		-- Extensao Zimop no core (mop.r.n e mop.rr.n escrevem zero em rd).
		HAS_ZIMOP    : boolean := work.internal_mem_map_pkg.HAS_ZIMOP;
		-- Extensao Zicond no core (czero.eqz e czero.nez).
		HAS_ZICOND   : boolean := work.internal_mem_map_pkg.HAS_ZICOND;
		-- Dicas ntl.* da extensao Zihintntl no core (executam como nop).
		HAS_ZIHINTNTL    : boolean := work.internal_mem_map_pkg.HAS_ZIHINTNTL;
		-- Dica pause da extensao Zihintpause no core (executa como nop).
		HAS_ZIHINTPAUSE    : boolean := work.internal_mem_map_pkg.HAS_ZIHINTPAUSE;
		-- Zifencei no core (FENCE.I).
		HAS_ZIFENCEI : boolean := work.internal_mem_map_pkg.HAS_ZIFENCEI;
		-- Acesso desalinhado executado em hardware (Zicclsm).
		HAS_ZICCLSM  : boolean := work.internal_mem_map_pkg.HAS_ZICCLSM;
		-- Interrupções de máquina do platform.yaml; este topo não tem CLINT, o genérico existe porque o gerador o passa a todos.
		HAS_INTERRUPTS : boolean := work.internal_mem_map_pkg.HAS_INTERRUPTS;
		-- Interrupção de estouro de contador (Sscofpmf); este topo não tem CLINT, o genérico existe porque o gerador o passa a todos.
		HAS_SSCOFPMF : boolean := work.internal_mem_map_pkg.HAS_SSCOFPMF
	);
	port (
		-- Clock de 50 MHz da placa, entrada do PLL.
		i_clock_50     : in  std_logic;
		-- Botão físico de reset da placa, ativo em nível baixo ('0' = pressionado).
		i_fpga_reset_n : in  std_logic := '1';
		-- Entrada serial da UART (repouso em '1').
		i_uart_rx      : in  std_logic := '1';
		-- Saída serial da UART (repouso em '1').
		o_uart_tx      : out std_logic := '1';
		-- LEDs vermelhos da placa: bit 0 pisca, bits 1 a 4 mostram o estado do PLL, do reset e do carregador da FLASH.
		o_ledr         : out std_logic_vector(9 downto 0) := (others => '0')
  	);
end entity;

architecture behaviour of core_fpga_test is

	-- IF stage: barramento unico compartilhado por BOOT_MEMORY e FLASH
	-- (ver rv32im_pipeline_core.vhd is_boot_memory_if/is_boot_memory_d)
	signal if_addr : std_logic_vector(31 downto 0);
	-- Habilitação de leitura da busca de instrução ('1' = lê).
	signal if_rden : std_logic;
	-- Palavra de instrução lida da BOOT_MEMORY.
	signal boot_memory_data : std_logic_vector(31 downto 0);
	-- Palavra de instrução lida da FLASH.
	signal flash_data : std_logic_vector(31 downto 0);

	-- Estagio MEM: leitura da FLASH como dado, para o copy-loop de .data
	-- em boot_memory.S (ver rv32im_pipeline_core.vhd flash_addr2). E' a porta B
	-- da unica copia da FLASH, que o carregador JTAG assume com o core parado.
	signal flash_addr2 : std_logic_vector(31 downto 0);
	-- Habilitação de leitura da segunda porta da FLASH ('1' = lê).
	signal flash_rden2 : std_logic;
	-- Palavra de dado lida da segunda porta da FLASH (estágio MEM).
	signal flash_data2 : std_logic_vector(31 downto 0);

	-- Carregador da FLASH: sinais entre a porta JTAG e o carregador.
	signal flash_cmd_tog    : std_logic;
	-- Código da operação pedida ao carregador da FLASH.
	signal flash_op         : std_logic_vector(3 downto 0);
	-- Endereço do comando enviado ao carregador da FLASH pelo JTAG.
	signal flash_cmd_addr   : std_logic_vector(23 downto 0);
	-- Dado do comando enviado ao carregador da FLASH pelo JTAG.
	signal flash_cmd_data   : std_logic_vector(31 downto 0);
	-- Toggle de conclusão do comando, do carregador para o JTAG.
	signal flash_done_tog   : std_logic;
	-- Endereço da resposta do carregador da FLASH.
	signal flash_rsp_addr   : std_logic_vector(23 downto 0);
	-- Dado da resposta do carregador da FLASH.
	signal flash_rsp_data   : std_logic_vector(31 downto 0);
	-- Status da resposta do carregador da FLASH.
	signal flash_rsp_status : std_logic_vector(7 downto 0);
	-- Core parado pelo carregador: entra no reset do core.
	signal flash_halt       : std_logic;
	-- Porta B da FLASH, ja' comutada entre o estagio MEM e o carregador.
	signal flash_address_b  : std_logic_vector(log2_exact(ROM_STORAGE_BYTES) - 3 downto 0);
	-- Habilitação de leitura da porta B da FLASH ('1' = lê).
	signal flash_rden_b     : std_logic;
	-- Habilitação de escrita da porta B da FLASH ('1' = escreve).
	signal flash_wren_b     : std_logic;
	-- Dado de escrita da porta B da FLASH, vindo do carregador.
	signal flash_data_b     : std_logic_vector(31 downto 0);

	-- RAM's In-System Memory Content Editor (JTAG) addresses it as a
	-- 0-based array relative to memory.ram_base (see
	-- riscv_tools.htif.word_offset's own docstring: "relative=True
	-- ... What mem_edit's JTAG primitives expect"), NOT the CPU's raw
	-- absolute address. Every previous memory-map round got this for
	-- free by accident (ram_base was always chosen as a power-of-two
	-- exactly matching RAM's own address width, so truncating the raw
	-- address to that width happened to equal subtracting ram_base) --
	-- broke silently the first time that stopped being true (ram_base
	-- = 0x11000 in that round, not aligned to RAM's 16-bit width), confirmed on
	-- real hardware: a debug LED wired directly to the tohost write
	-- (ram_addr = tohost_addr) lit up correctly, proving the CORE
	-- writes the right byte address -- but JTAG reads (computed
	-- RAM-relative, per mem_edit's own convention) always came back
	-- 0, since RAM's OWN address port was indexing by the untranslated
	-- raw address instead. GHDL sim never hit this: its own testbench
	-- (test_c_program.py) snoops the raw ram_addr bus directly rather
	-- than reading back RAM's internal array by JTAG-style 0-based
	-- index, so this class of bug is invisible to it by construction.
	constant RAM_BASE_WORD : unsigned(19 downto 0) := to_unsigned(RAM_BASE_KIB * 256, 20);
	-- Endereço de palavra da RAM relativo à base da RAM, como o JTAG o enxerga.
	signal ram_word_addr : unsigned(log2_exact(RAM_STORAGE_BYTES) - 3 downto 0);

	-- Endereço de byte do acesso à RAM do núcleo.
	signal ram_addr : std_logic_vector(31 downto 0);
	-- Dado de escrita na RAM do núcleo.
	signal ram_wdata : std_logic_vector(31 downto 0);
	-- Dado lido da RAM entregue ao núcleo.
	signal ram_rdata : std_logic_vector(31 downto 0);
	-- Habilitação geral da RAM do núcleo (estágio MEM).
	signal ram_en : std_logic;
	-- Habilitação de escrita da RAM do núcleo ('1' = escreve).
	signal ram_wren : std_logic;
	-- Habilitação de leitura da RAM do núcleo ('1' = lê).
	signal ram_rden : std_logic;
	-- Habilitação de bytes da escrita na RAM do núcleo.
	signal ram_byteena : std_logic_vector(3 downto 0);

	-- Clock do estágio de busca (IF), primeira fase do gerador de clock.
	signal pll_clk_if     : std_logic;
	-- Clock dos estágios ID, EX e MEM, segunda fase do gerador de clock.
	signal pll_clk_idexmem: std_logic;
	-- Indica que o PLL travou ('1' = travado).
	signal pll_locked     : std_logic;

	-- Mantém core em reset até o PLL estar travado, ou enquanto o
	-- botão físico de reset (i_fpga_reset_n, ativo em nível baixo) for
	-- pressionado o que permite reiniciar o core sem reconfigurar a FPGA
	-- (ex: depois de carregar um novo conteúdo de ROM via JTAG).
	signal core_reset : std_logic;

	-- Pulso de um ciclo de o_trap_take do core (exceção tomada, com ou sem Zicsr).
	signal core_trap : std_logic;
	-- Bandeira que segura o pulso até o próximo reset.
	signal trap_seen : std_logic := '0';

	-- UART memory-mapped em UART_BASE
	signal uart_selected : std_logic;
	-- Escrita na UART ('1' = escreve; janela selecionada e escrita do núcleo).
	signal uart_write    : std_logic;
	-- Leitura da UART ('1' = lê; janela selecionada e leitura do núcleo).
	signal uart_read     : std_logic;
	-- Dado lido da UART.
	signal uart_rdata    : std_logic_vector(31 downto 0);
	-- Leitura da UART atrasada um ciclo, que acompanha a resposta registrada.
	signal uart_read_d   : std_logic;
	-- Dado lido da UART registrado, devolvido ao núcleo no ciclo seguinte.
	signal uart_rdata_d  : std_logic_vector(31 downto 0);

	-- Porta externa do core, usada pela janela de periféricos.
	signal sdram_addr     : std_logic_vector(31 downto 0);
	-- Dado de escrita do barramento externo do núcleo.
	signal sdram_wdata    : std_logic_vector(31 downto 0);
	-- Dado lido do barramento externo devolvido ao núcleo.
	signal sdram_rdata    : std_logic_vector(31 downto 0);
	-- Habilitação de bytes da escrita no barramento externo.
	signal sdram_byteena  : std_logic_vector(3 downto 0);
	-- Habilitação de leitura do barramento externo ('1' = lê).
	signal sdram_rden     : std_logic;
	-- Habilitação de escrita do barramento externo ('1' = escreve).
	signal sdram_wren     : std_logic;



begin

	-- rst era amarrado em '0' antes -- nunca pulsado. gui_pll_auto_reset
	-- esta' "Off" nesta IP (ver pll.vhd), ou seja o PLL NAO tenta
	-- re-travar sozinho se perder o lock por qualquer motivo (ruido de
	-- alimentacao, etc.) -- fica preso ate a FPGA inteira ser
	-- reconfigurada, mesmo que o resto do sistema (JTAG TAP, que e' um
	-- bloco fixo independente desta logica) continue respondendo
	-- normalmente. Ligar ao botao fisico de reset da' um caminho de
	-- recuperacao mais barato que desligar a placa inteira -- se essa
	-- for mesmo a causa da instabilidade intermitente de JTAG vista em
	-- HARDWARE_PROGRAMMING.md/docs/DATA_HARVARD_BUG.md, apertar o botao
	-- deve bastar em vez de precisar de power-cycle completo.
	u_pll : entity work.pll
    port map (
      refclk   => i_clock_50,
      rst      => not i_fpga_reset_n,
      outclk_0 => pll_clk_if,
      outclk_1 => pll_clk_idexmem,
      outclk_2 => open,
      locked   => pll_locked
    );

	-- O carregador da FLASH segura o core em reset enquanto grava a imagem do
	-- proximo teste; liberado, o core reinicia pela BOOT_MEMORY.
	core_reset <= (not pll_locked) or (not i_fpga_reset_n) or flash_halt;


	-- Seleciona a janela de 256 MiB da UART (UART_BASE, do pacote gerado do platform.yaml).
	uart_selected <= '1'
		when sdram_addr(31 downto 28) = UART_BASE(31 downto 28)
		else '0';

	uart_write <= sdram_wren and uart_selected;
	uart_read  <= sdram_rden and uart_selected;

	-- Status LEDs -- ver README.md/docs para o mapa completo. Baratos
	-- o bastante pra deixar permanentes (nao so' debug de bring-up):
	-- dao um jeito de ver, so' olhando a placa, se o problema e' antes
	-- (PLL/reset) ou depois (logica do core/software) do reset, sem
	-- precisar de uma sessao JTAG.
	o_ledr(1) <= pll_locked;       -- '1' travado (deveria ficar sempre aceso)
	o_ledr(2) <= i_fpga_reset_n;     -- '1' botao de reset fisico solto
	o_ledr(3) <= not core_reset;   -- '1' core fora de reset, rodando
	o_ledr(4) <= flash_halt;       -- '1' core parado pelo carregador da FLASH
	o_ledr(5) <= trap_seen;        -- '1' core tomou uma exceção desde o último reset

	-- o_trap_take dura um ciclo de clock do core, invisível a olho nu: a bandeira o segura até o reset. O reset é
	-- assíncrono porque o botão também segura a PLL em reset e o clock do core pára, então um clear síncrono nunca o veria
	process (pll_clk_idexmem, core_reset)
	begin
		if core_reset = '1' then
			trap_seen <= '0';
		elsif rising_edge(pll_clk_idexmem) then
			if core_trap = '1' then
				trap_seen <= '1';
			end if;
		end if;
	end process;

	u_core : entity work.core
		generic map (
			has_m           => HAS_M,
			has_zmmul       => HAS_ZMMUL,
			has_zicsr       => HAS_ZICSR,
			has_zicntr      => HAS_ZICNTR,
			has_zihpm       => HAS_ZIHPM,
			hpm_counters    => HPM_COUNTERS,
			hpm_width       => HPM_WIDTH,
			has_zimop       => HAS_ZIMOP,
			has_zicond      => HAS_ZICOND,
			has_zihintntl   => HAS_ZIHINTNTL,
			has_zihintpause => HAS_ZIHINTPAUSE,
			has_zifencei    => HAS_ZIFENCEI,
			has_zicclsm     => HAS_ZICCLSM,
			has_e           => HAS_E,
			boot_memory_bits   => BOOT_MEMORY_BITS,
			rom_end_kib     => ROM_END_KIB,
			rom_external    => ROM_EXTERNAL,
			ram_base_kib    => RAM_BASE_KIB,
			ram_end_kib     => RAM_END_KIB,
			ram_external    => RAM_EXTERNAL,
			ext_base_kib    => EXT_BASE_KIB,
			periph_base_kib => PERIPH_BASE_KIB
		)
		port map (
			i_clk          => pll_clk_idexmem,
			i_rst        => core_reset,

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
			i_ext_ready   => '1',
			o_mem_advance   => open,

			o_trap_take     => core_trap
	);

	u_uart_peripheral : entity work.UART
		generic map (
			DATA_WIDTH => 32
		)
		port map (
			i_clk    => pll_clk_idexmem,
			i_rst    => core_reset,
			i_data_in  => sdram_wdata,
			i_address  => sdram_addr(3 downto 2),
			i_write    => uart_write,
			i_read     => uart_read,
			o_data_out => uart_rdata,
			o_irq      => open,
			i_uart_rx  => i_uart_rx,
			o_uart_tx  => o_uart_tx
		);

	UART_READ_PIPELINE : process (core_reset, pll_clk_idexmem)
	begin
		if core_reset = '1' then
			uart_read_d  <= '0';
			uart_rdata_d <= (others => '0');
		elsif rising_edge(pll_clk_idexmem) then
			uart_read_d <= uart_read;

			if uart_read = '1' then
				uart_rdata_d <= uart_rdata;
			end if;
		end if;
	end process;

	-- A UART responde no ciclo seguinte da porta externa; a RAM interna
	-- permanece dedicada à sua própria porta do core.
	sdram_rdata <= uart_rdata_d;

	-- BOOT_MEMORY: fixa, gravada uma unica vez (nunca reescrita via JTAG
	-- por teste -- ver config.yaml quartus.boot_memory_mif_target). So'
	-- precisa de porta unica agora -- nada mais le dado direto dela
	-- (ver rv32im_pipeline_core.vhd, estagio MEM so' fala com RAM).
	u_boot_memory : entity work.boot_memory
    generic map (size_bytes => BOOT_MEMORY_SIZE_BYTES)
    port map (
      i_address => if_addr(log2_exact(BOOT_MEMORY_SIZE_BYTES) - 1 downto 2),
      i_clk   => pll_clk_if,
      i_rden    => if_rden,
      i_wren    => '0',
      i_data    => (others => '0'),
      o_q       => boot_memory_data
    );

	-- FLASH: "firmware" desse teste, uma so' copia de duas portas, reescrita
	-- por teste pelo carregador JTAG (ver config.yaml quartus.rom_write_method)
	-- com o core parado. Porta A: busca de instrucao. Porta B: dado do
	-- estagio MEM (mesmo clock que a RAM) ou escrita do carregador.
	-- BOOT_MEMORY continua so' de porta unica.
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

	-- Carregador: dono da porta B com o core parado, e quem para o core.
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

	-- Instancia do Virtual JTAG e a porta JTAG do carregador.
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

	-- RAM-relative word address (see RAM_BASE_WORD's own comment above)
	ram_word_addr <= resize(unsigned(ram_addr(21 downto 2)) - RAM_BASE_WORD, ram_word_addr'length);

	u_ram : entity work.ram
	 generic map (size_bytes => RAM_STORAGE_BYTES)
	 port map (
		i_address => std_logic_vector(ram_word_addr),
		i_byteena => ram_byteena,
		i_clk   => pll_clk_idexmem,
		i_data    => ram_wdata,
		i_rden => ram_rden and ram_en,
		i_wren => ram_wren and ram_en,
		o_q    => ram_rdata
	 );

	 u_blink : entity work.Blinky
	 port map (
		i_clk => i_clock_50,
		o_led => o_ledr(0)
	 );

end architecture;
