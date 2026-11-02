-- =============================================================================
-- Topo de simulação modular: os quatro modelos base do núcleo
--
-- Um único topo, configurado por genéricos, monta o núcleo com a memória de instruções e a de
-- dados dentro ou fora do chip. O que está fora fica atrás de uma cache e de um modelo de chip
-- simulado (ram_chip, e flash_chip quando a FLASH também é externa), de tamanho configurável.
--
--   | Modelo               | Instruções                          | Dados                              | instr_external | data_external |
--   | integrated           | internas                            | internos                           | false          | false         |
--   | external-data        | internas                            | externos, atrás da cache de dados  | false          | true          |
--   | external-instruction | externas, atrás da cache de instruções | internos                        | true           | false         |
--   | external             | externas, atrás da cache de instruções | externos, atrás da cache de dados | true         | true          |
--
-- Mapa A (ext_flash falso, o padrão): BOOT_ROM em 0x00000000, FLASH interna em 0x00000800, RAM
-- interna em 0x00008000 e o chip externo em 0x40000000. As instruções externas são buscadas nesse
-- chip, pela cache de instruções, e os dados externos também, pela cache de dados.
--
-- Mapa B (ext_flash verdadeiro, exige os dois lados externos): só a BOOT_ROM é interna. A FLASH
-- externa fica em 0x20000000 e o chip de RAM em 0x40000000, os dois atrás das caches e de um
-- roteador por região, como na plataforma da placa, só que com o chip de RAM simulado no lugar do
-- controlador e do chip da SDRAM.
--
-- Todos os tamanhos são genéricos em potência de dois (bytes para as memórias, bits para as
-- caches), verificados pelo log2_exact. Os valores padrão são os da simulação do ACT4: FLASH e RAM
-- de 1 MB e caches de 4 kbit.
--
-- A porta de depuração lê uma palavra do chip externo, pelo índice a partir do seu início, sem
-- passar pelas caches: é como o testbench vê o HTIF tohost quando ele está no chip. Quando a RAM é
-- interna, o testbench observa as saídas o_ram_*, que são o barramento de dados da RAM do núcleo.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;

entity modular_sim_top is
  generic (
    -- Imagem da BOOT_ROM, uma palavra de 32 bits por linha em hexadecimal.
    boot_rom_file       : string  := "default.hex";
    -- Imagem da FLASH (interna no mapa A, o chip de FLASH externo no mapa B).
    rom_file            : string  := "default.hex";
    -- Imagem inicial da RAM interna; vazio deixa tudo em zero.
    ram_file            : string  := "";
    -- Imagem inicial do chip de RAM externo, a partir de 0x40000000; vazio deixa tudo em zero.
    ext_ram_file        : string  := "";
    -- A memória de instruções é externa, atrás da cache de instruções.
    instr_external      : boolean := false;
    -- A memória de dados é externa, atrás da cache de dados.
    data_external       : boolean := false;
    -- Mapa B: a FLASH é um chip externo em 0x20000000 e não há RAM interna.
    ext_flash           : boolean := false;
    -- Tamanho da BOOT_ROM em bytes, uma potência de dois.
    boot_rom_size_bytes : positive := 2048;
    -- Tamanho da FLASH em bytes, uma potência de dois (interna no mapa A, o chip no mapa B).
    flash_size_bytes    : positive := 1048576;
    -- Tamanho da RAM interna em bytes, uma potência de dois.
    ram_size_bytes      : positive := 1048576;
    -- Tamanho do chip de RAM externo em bytes, uma potência de dois.
    ext_ram_size_bytes  : positive := 1048576;
    -- Tamanho da cache de instruções em bits, uma potência de dois (4096 é 4 kbit).
    icache_size_bits    : positive := 4096;
    -- Tamanho da cache de dados em bits, uma potência de dois (4096 é 4 kbit).
    dcache_size_bits    : positive := 4096;
    -- Bordas até a primeira palavra do chip de FLASH e entre as palavras de uma linha.
    flash_first_latency : natural := 24;
    -- Bordas entre as palavras seguintes da mesma linha do chip de FLASH.
    flash_next_latency  : natural := 4;
    -- Bordas entre o pedido e a conclusão de um acesso ao chip de RAM externo.
    ext_ram_latency     : natural := 8;
    -- Zicsr no núcleo (instruções CSR reais); falso mantém o comportamento de NOP.
    has_zicsr           : boolean := false;
    -- Contadores da extensão Zicntr (implica Zicsr).
    has_zicntr          : boolean := false;
    -- Contadores de eventos da extensão Zihpm (quatro, índices 3 a 6); exige Zicsr.
    has_zihpm           : boolean := false;
    -- Extensão M completa no núcleo.
    has_m               : boolean := true;
    -- Multiplicação sem divisão (Zmmul) no núcleo.
    has_zmmul           : boolean := false;
    -- Zifencei no núcleo (FENCE.I invalida a cache de instruções); falso mantém o NOP.
    has_zifencei        : boolean := false;
    -- Acesso desalinhado à memória principal executado em hardware (Zicclsm).
    has_zicclsm         : boolean := true
  );
  port (
    -- Clock base; um gerador o divide por três para os estágios do núcleo.
    i_clk           : in  std_logic;
    -- Reset, ativo em '1'.
    i_rst           : in  std_logic := '0';
    -- Índice da palavra do chip de RAM externo que a porta de depuração lê.
    i_dbg_word_addr : in  std_logic_vector(23 downto 0) := (others => '0');
    -- Palavra do chip de RAM externo no índice de i_dbg_word_addr.
    o_dbg_word_data : out std_logic_vector(31 downto 0);
    -- Habilita geral da RAM interna do núcleo (estágio MEM).
    o_ram_en        : out std_logic;
    -- Habilita de escrita da RAM interna do núcleo.
    o_ram_wren      : out std_logic;
    -- Endereço de byte do acesso à RAM interna do núcleo.
    o_ram_addr      : out std_logic_vector(31 downto 0);
    -- Dado de escrita da RAM interna do núcleo.
    o_ram_wdata     : out std_logic_vector(31 downto 0);
    -- Habilita de bytes da escrita na RAM interna do núcleo.
    o_ram_byteena   : out std_logic_vector(3 downto 0)
  );
end entity modular_sim_top;

architecture behaviour of modular_sim_top is

  -- Quantidade de contadores de eventos do Zihpm: quatro com a extensão, nenhum sem ela.
  function hpm_count (present : boolean) return natural is
  begin
    if present then
      return 4;
    end if;
    return 0;
  end function hpm_count;

  -- Há algum lado externo, então há um chip de RAM externo.
  constant HAS_EXTERNAL : boolean := instr_external or data_external;

  -- Clocks dos estágios do núcleo.
  signal pll_clk_if      : std_logic;
  signal pll_clk_idexmem : std_logic;
  signal pll_clk_wb      : std_logic;

  -- Sinais do núcleo: busca de instrução e FLASH interna.
  signal if_addr       : std_logic_vector(31 downto 0);
  signal if_rden       : std_logic;
  signal boot_rom_data : std_logic_vector(31 downto 0);
  signal flash_data    : std_logic_vector(31 downto 0) := (others => '0');
  signal flash_addr2   : std_logic_vector(31 downto 0);
  signal flash_rden2   : std_logic;
  signal flash_data2   : std_logic_vector(31 downto 0) := (others => '0');

  -- Sinais do núcleo: RAM interna.
  signal ram_addr      : std_logic_vector(31 downto 0);
  signal ram_wdata     : std_logic_vector(31 downto 0);
  signal ram_rdata     : std_logic_vector(31 downto 0) := (others => '0');
  signal ram_en        : std_logic;
  signal ram_wren      : std_logic;
  signal ram_rden      : std_logic;
  signal ram_byteena   : std_logic_vector(3 downto 0);
  signal ram_re_gated  : std_logic;
  signal ram_we_gated  : std_logic;

  -- Sinais do núcleo: barramento externo de dados.
  signal sdram_addr    : std_logic_vector(31 downto 0);
  signal sdram_wdata   : std_logic_vector(31 downto 0);
  signal sdram_byteena : std_logic_vector(3 downto 0);
  signal sdram_rden    : std_logic;
  signal sdram_wren    : std_logic;
  signal sdram_rdata   : std_logic_vector(31 downto 0) := (others => '0');
  signal sdram_ready   : std_logic := '1';
  signal mem_advance   : std_logic;

  -- Sinais do núcleo: cache de instruções.
  signal ic_data       : std_logic_vector(31 downto 0) := (others => '0');
  signal ic_ready      : std_logic := '1';
  signal ic_sel        : std_logic;
  signal ic_inval      : std_logic;

  -- Eventos das caches e da FLASH para o Zihpm.
  signal ic_miss       : std_logic := '0';
  signal dc_miss       : std_logic := '0';
  signal flash_busy    : std_logic := '0';
  signal hpm_ext_events : std_logic_vector(2 downto 0);

  -- Interconexão e cache de dados: lado do núcleo e lado da memória.
  signal m_addr        : std_logic_vector(31 downto 0);
  signal m_wdata       : std_logic_vector(31 downto 0);
  signal m_byteena     : std_logic_vector(3 downto 0);
  signal m_rden        : std_logic;
  signal m_wren        : std_logic;
  signal m_ready       : std_logic;
  signal m_rdata       : std_logic_vector(31 downto 0);
  signal dd_addr       : std_logic_vector(31 downto 0);
  signal dd_wdata      : std_logic_vector(31 downto 0);
  signal dd_be         : std_logic_vector(3 downto 0);
  signal dd_rden       : std_logic;
  signal dd_wren       : std_logic;
  signal dd_line       : std_logic;
  signal dd_adv        : std_logic;
  signal dd_ready      : std_logic;
  signal dd_rdata      : std_logic_vector(31 downto 0);
  signal dd_wdx        : std_logic_vector(95 downto 0);
  signal dd_rdx        : std_logic_vector(95 downto 0);
  signal dc_done       : std_logic;
  signal dc_busy       : std_logic;

  -- Cache de instruções: lado da memória.
  signal id_addr       : std_logic_vector(31 downto 0);
  signal id_rden       : std_logic;
  signal id_adv        : std_logic;
  signal id_ready      : std_logic;
  signal id_rdata      : std_logic_vector(31 downto 0);
  signal id_line       : std_logic;
  signal id_rdx        : std_logic_vector(95 downto 0);

  -- Roteadores por região (mapa B): lado do chip de RAM de cada um.
  signal si_addr       : std_logic_vector(31 downto 0);
  signal si_wdata      : std_logic_vector(31 downto 0);
  signal si_be         : std_logic_vector(3 downto 0);
  signal si_rden       : std_logic;
  signal si_wren       : std_logic;
  signal si_line       : std_logic;
  signal si_adv        : std_logic;
  signal si_ready      : std_logic;
  signal si_rdata      : std_logic_vector(31 downto 0);
  signal si_wdx        : std_logic_vector(95 downto 0);
  signal si_rdx        : std_logic_vector(95 downto 0);
  signal sd_addr       : std_logic_vector(31 downto 0);
  signal sd_wdata      : std_logic_vector(31 downto 0);
  signal sd_be         : std_logic_vector(3 downto 0);
  signal sd_rden       : std_logic;
  signal sd_wren       : std_logic;
  signal sd_line       : std_logic;
  signal sd_adv        : std_logic;
  signal sd_ready      : std_logic;
  signal sd_rdata      : std_logic_vector(31 downto 0);
  signal sd_wdx        : std_logic_vector(95 downto 0);
  signal sd_rdx        : std_logic_vector(95 downto 0);

  -- Roteadores por região (mapa B): lado do chip de FLASH.
  signal fa_addr, fa_rdata, fb_addr, fb_rdata, fc_addr, fc_rdata : std_logic_vector(31 downto 0);
  signal fa_rden, fa_line, fa_adv, fa_ready : std_logic;
  signal fb_rden, fb_line, fb_adv, fb_ready : std_logic;
  signal fc_rden, fc_line, fc_adv, fc_ready : std_logic;
  signal fa_rdx, fb_rdx, fc_rdx : std_logic_vector(95 downto 0);
  signal flash_mem_addr, flash_mem_data : std_logic_vector(31 downto 0);

  -- Portas do chip de RAM externo: dados e instruções.
  signal rc_d_addr     : std_logic_vector(31 downto 0) := (others => '0');
  signal rc_d_wdata    : std_logic_vector(31 downto 0) := (others => '0');
  signal rc_d_be       : std_logic_vector(3 downto 0)  := (others => '0');
  signal rc_d_rden     : std_logic := '0';
  signal rc_d_wren     : std_logic := '0';
  signal rc_d_line     : std_logic := '0';
  signal rc_d_adv      : std_logic := '0';
  signal rc_d_wdx      : std_logic_vector(95 downto 0) := (others => '0');
  signal rc_d_ready    : std_logic;
  signal rc_d_rdata    : std_logic_vector(31 downto 0);
  signal rc_d_rdx      : std_logic_vector(95 downto 0);
  signal rc_i_addr     : std_logic_vector(31 downto 0) := (others => '0');
  signal rc_i_rden     : std_logic := '0';
  signal rc_i_line     : std_logic := '0';
  signal rc_i_adv      : std_logic := '0';
  signal rc_i_ready    : std_logic;
  signal rc_i_rdata    : std_logic_vector(31 downto 0);
  signal rc_i_rdx      : std_logic_vector(95 downto 0);

begin

  assert not ext_flash or (instr_external and data_external)
    report "ext_flash (mapa B) exige instr_external e data_external"
    severity failure;

  o_ram_en      <= ram_en;
  o_ram_wren    <= ram_wren;
  o_ram_addr    <= ram_addr;
  o_ram_wdata   <= ram_wdata;
  o_ram_byteena <= ram_byteena;

  ram_re_gated <= ram_rden and ram_en;
  ram_we_gated <= ram_wren and ram_en;

  hpm_ext_events <= flash_busy & dc_miss & ic_miss;

  pll_inst : entity work.clk_gen_3way
    port map (
      clk_in => i_clk,
      reset  => i_rst,
      clk0   => pll_clk_if,
      clk1   => pll_clk_idexmem,
      clk2   => pll_clk_wb
    );

  core_inst : entity work.core
    generic map (
      has_m        => has_m,
      has_zmmul    => has_zmmul,
      has_zicsr    => has_zicsr,
      has_zicntr   => has_zicntr,
      has_zifencei => has_zifencei,
      has_zicclsm  => has_zicclsm,
      ext_flash    => ext_flash,
      hpm_counters => hpm_count(has_zihpm)
    )
    port map (
      o_trap           => open,
      o_retire         => open,
      o_trap_cause     => open,
      o_trap_pc        => open,
      i_clk            => pll_clk_idexmem,
      i_rst            => i_rst,
      o_if_addr        => if_addr,
      o_if_rden        => if_rden,
      i_boot_rom_data  => boot_rom_data,
      i_flash_data     => flash_data,
      o_flash_addr2    => flash_addr2,
      o_flash_rden2    => flash_rden2,
      i_flash_data2    => flash_data2,
      o_ram_addr       => ram_addr,
      o_ram_wdata      => ram_wdata,
      i_ram_rdata      => ram_rdata,
      o_ram_en         => ram_en,
      o_ram_wren       => ram_wren,
      o_ram_rden       => ram_rden,
      o_ram_byteena    => ram_byteena,
      o_sdram_addr     => sdram_addr,
      o_sdram_wdata    => sdram_wdata,
      o_sdram_byteena  => sdram_byteena,
      o_sdram_rden     => sdram_rden,
      o_sdram_wren     => sdram_wren,
      i_sdram_rdata    => sdram_rdata,
      i_sdram_ready    => sdram_ready,
      o_mem_advance    => mem_advance,
      i_hpm_ext_events => hpm_ext_events,
      i_ic_data        => ic_data,
      i_ic_ready       => ic_ready,
      o_ic_sel         => ic_sel,
      o_ic_inval       => ic_inval
    );

  boot_rom_inst : entity work.rom_simulation
    generic map (rom_file => boot_rom_file, size_bytes => boot_rom_size_bytes)
    port map (
      i_addr => if_addr(31 downto 2),
      i_clk  => pll_clk_if,
      i_re   => if_rden,
      o_data => boot_rom_data
    );

  -- Mapa A: a FLASH e a RAM internas do núcleo.
  g_internal : if not ext_flash generate
  begin
    flash_inst : entity work.rom_simulation
      generic map (rom_file => rom_file, size_bytes => flash_size_bytes)
      port map (
        i_addr  => if_addr(31 downto 2),
        i_clk   => pll_clk_if,
        i_re    => if_rden,
        o_data  => flash_data,
        i_addr2 => flash_addr2(31 downto 2),
        i_clk2  => pll_clk_idexmem,
        i_re2   => flash_rden2,
        o_data2 => flash_data2
      );

    ram_inst : entity work.ram_simulation
      generic map (size_bytes => ram_size_bytes, ram_file => ram_file)
      port map (
        i_addr     => ram_addr(31 downto 2),
        i_mask     => ram_byteena,
        i_clk      => pll_clk_idexmem,
        i_data_in  => ram_wdata,
        i_re_ram   => ram_re_gated,
        i_we_ram   => ram_we_gated,
        i_en_ram   => ram_en,
        o_data_out => ram_rdata
      );
  end generate g_internal;

  -- Dados externos: a interconexão separa a janela de periféricos, a cache de dados fica entre o
  -- núcleo e a memória.
  g_data_external : if data_external generate
  begin
    interconnect_inst : entity work.ext_interconnect
      port map (
        i_clk         => pll_clk_idexmem,
        i_rst         => i_rst,
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
        o_p_addr      => open,
        o_p_wdata     => open,
        o_p_byteena   => open,
        o_p_we        => open,
        o_p_re        => open,
        i_p_rdata     => (others => '0')
      );

    dcache_inst : entity work.dcache
      generic map (size_bits => dcache_size_bits, write_through => true)
      port map (
        i_clk         => pll_clk_idexmem,
        i_rst         => i_rst,
        i_addr        => m_addr,
        i_wdata       => m_wdata,
        i_byteena     => m_byteena,
        i_rden        => m_rden,
        i_wren        => m_wren,
        i_mem_advance => mem_advance,
        o_ready       => m_ready,
        o_rdata       => m_rdata,
        i_flush       => ic_inval,
        i_invalidate  => '1',
        o_flush_done  => dc_done,
        o_busy        => dc_busy,
        o_miss        => dc_miss,
        i_bypass      => '0',
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
  end generate g_data_external;

  -- Instruções externas: a cache de instruções entre o núcleo e a memória.
  g_instr_external : if instr_external generate
  begin
    icache_inst : entity work.icache
      generic map (size_bits => icache_size_bits)
      port map (
        i_clk        => pll_clk_if,
        i_clk_cpu    => pll_clk_idexmem,
        i_rst        => i_rst,
        i_addr       => if_addr,
        i_sel        => ic_sel,
        o_ready      => ic_ready,
        o_data       => ic_data,
        i_invalidate => ic_inval,
        o_miss       => ic_miss,
        o_d_addr     => id_addr,
        o_d_rden     => id_rden,
        o_d_advance  => id_adv,
        i_d_ready    => id_ready,
        i_d_rdata    => id_rdata,
        o_d_line     => id_line,
        i_d_rdata_x  => id_rdx
      );
  end generate g_instr_external;

  -- Mapa A: as caches falam direto com o chip de RAM externo.
  g_direct : if not ext_flash generate
  begin
    g_direct_data : if data_external generate
    begin
      rc_d_addr  <= dd_addr;
      rc_d_wdata <= dd_wdata;
      rc_d_be    <= dd_be;
      rc_d_rden  <= dd_rden;
      rc_d_wren  <= dd_wren;
      rc_d_line  <= dd_line;
      rc_d_adv   <= dd_adv;
      rc_d_wdx   <= dd_wdx;
      dd_ready   <= rc_d_ready;
      dd_rdata   <= rc_d_rdata;
      dd_rdx     <= rc_d_rdx;
    end generate g_direct_data;

    g_direct_instr : if instr_external generate
    begin
      rc_i_addr <= id_addr;
      rc_i_rden <= id_rden;
      rc_i_line <= id_line;
      rc_i_adv  <= id_adv;
      id_ready  <= rc_i_ready;
      id_rdata  <= rc_i_rdata;
      id_rdx    <= rc_i_rdx;
    end generate g_direct_instr;
  end generate g_direct;

  -- Mapa B: um roteador por cache separa a FLASH externa do chip de RAM, e a FLASH tem um árbitro
  -- e o chip com o seu armazenamento.
  g_routed : if ext_flash generate
  begin
    router_i_inst : entity work.mem_region_router
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

    router_d_inst : entity work.mem_region_router
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

    flash_arbiter_inst : entity work.flash_arbiter
      port map (
        i_clk => pll_clk_idexmem, i_rst => i_rst,
        i_a_addr => fa_addr, i_a_rden => fa_rden, i_a_line => fa_line, i_a_advance => fa_adv,
        o_a_ready => fa_ready, o_a_rdata => fa_rdata, o_a_rdata_x => fa_rdx,
        i_b_addr => fb_addr, i_b_rden => fb_rden, i_b_line => fb_line, i_b_advance => fb_adv,
        o_b_ready => fb_ready, o_b_rdata => fb_rdata, o_b_rdata_x => fb_rdx,
        o_addr => fc_addr, o_rden => fc_rden, o_line => fc_line, o_advance => fc_adv,
        i_ready => fc_ready, i_rdata => fc_rdata, i_rdata_x => fc_rdx
      );

    flash_chip_inst : entity work.flash_chip
      generic map (
        first_latency => flash_first_latency,
        next_latency  => flash_next_latency,
        size_bytes    => flash_size_bytes
      )
      port map (
        i_clk => pll_clk_idexmem, i_rst => i_rst,
        i_addr => fc_addr, i_rden => fc_rden, i_line => fc_line, i_advance => fc_adv,
        o_ready => fc_ready, o_busy => flash_busy, o_rdata => fc_rdata, o_rdata_x => fc_rdx,
        o_mem_addr => flash_mem_addr, i_mem_data => flash_mem_data
      );

    flash_storage_inst : entity work.rom_simulation
      generic map (rom_file => rom_file, size_bytes => flash_size_bytes)
      port map (
        i_addr => flash_mem_addr(31 downto 2),
        i_clk  => pll_clk_idexmem,
        i_re   => '1',
        o_data => flash_mem_data
      );

    rc_d_addr  <= sd_addr;
    rc_d_wdata <= sd_wdata;
    rc_d_be    <= sd_be;
    rc_d_rden  <= sd_rden;
    rc_d_wren  <= sd_wren;
    rc_d_line  <= sd_line;
    rc_d_adv   <= sd_adv;
    rc_d_wdx   <= sd_wdx;
    sd_ready   <= rc_d_ready;
    sd_rdata   <= rc_d_rdata;
    sd_rdx     <= rc_d_rdx;

    rc_i_addr <= si_addr;
    rc_i_rden <= si_rden;
    rc_i_line <= si_line;
    rc_i_adv  <= si_adv;
    si_ready  <= rc_i_ready;
    si_rdata  <= rc_i_rdata;
    si_rdx    <= rc_i_rdx;
  end generate g_routed;

  -- O chip de RAM externo, quando algum lado é externo.
  g_ext_ram : if HAS_EXTERNAL generate
  begin
    ext_ram_inst : entity work.ram_chip
      generic map (
        init_file  => ext_ram_file,
        latency    => ext_ram_latency,
        size_bytes => ext_ram_size_bytes
      )
      port map (
        i_clk           => pll_clk_idexmem,
        i_rst           => i_rst,
        i_addr          => rc_d_addr,
        i_wdata         => rc_d_wdata,
        i_byteena       => rc_d_be,
        i_rden          => rc_d_rden,
        i_wren          => rc_d_wren,
        i_mem_advance   => rc_d_adv,
        o_ready         => rc_d_ready,
        o_rdata         => rc_d_rdata,
        i_line          => rc_d_line,
        i_wdata_x       => rc_d_wdx,
        i_byteena_x     => (others => '1'),
        o_rdata_x       => rc_d_rdx,
        i_ins_addr      => rc_i_addr,
        i_ins_rden      => rc_i_rden,
        i_ins_advance   => rc_i_adv,
        o_ins_ready     => rc_i_ready,
        o_ins_rdata     => rc_i_rdata,
        i_ins_line      => rc_i_line,
        o_ins_rdata_x   => rc_i_rdx,
        o_init_done     => open,
        i_dbg_word_addr => i_dbg_word_addr,
        o_dbg_word_data => o_dbg_word_data
      );
  end generate g_ext_ram;

  g_no_ext_ram : if not HAS_EXTERNAL generate
  begin
    o_dbg_word_data <= (others => '0');
  end generate g_no_ext_ram;

end architecture behaviour;
