-- =============================================================================
-- Topo de simulação modular: os quatro modelos base do núcleo
--
-- Um único topo, configurado por genéricos, monta o núcleo com a ROM e a RAM cada uma dentro ou
-- fora do chip. O que está fora fica atrás de uma cache e de um modelo de chip simulado (flash_chip
-- para a ROM, ram_chip para a RAM), de tamanho configurável.
--
--   | Modelo               | ROM     | RAM     | Caches                  | rom_external | ram_external |
--   | integrated           | interna | interna | nenhuma                 | false        | false        |
--   | external-data        | interna | externa | cache de dados          | false        | true         |
--   | external-instruction | externa | interna | cache de instruções     | true         | false        |
--   | external             | externa | externa | de instruções e de dados | true         | true         |
--
-- O mapa vem dos genéricos, cujo valor padrão é o do pacote modular_map_pkg, gerado do platform.yaml da
-- plataforma, e é o mesmo do núcleo: a BOOT_ROM em [0, tamanho), a ROM logo depois
-- dela até rom_end_kib, a RAM em [ram_base_kib, ram_end_kib) e a janela externa a partir de
-- ext_base_kib. O que o projeto escolhe fica no config.yml da plataforma.
--
-- Com as duas memórias externas, um roteador por cache separa a ROM da RAM, e a ROM tem um árbitro
-- entre as duas caches. Com uma só externa, a cache fala direto com o chip.
--
-- Todos os tamanhos são genéricos em potência de dois (bytes para as memórias, bits para as
-- caches), verificados pelo log2_exact. Os valores padrão são os da simulação do ACT4: ROM e RAM
-- de 1 MB e caches de 4 kbit.
--
-- A porta de depuração lê uma palavra do chip de RAM externo, pelo índice a partir do seu início, sem
-- passar pelas caches: é como o testbench vê o HTIF tohost quando ele está no chip. Quando a RAM é
-- interna, o testbench observa as saídas o_ram_*, que são o barramento de dados da RAM do núcleo.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.modular_map_pkg.all;

entity modular_sim_top is
  generic (
    -- Imagem da BOOT_ROM, uma palavra de 32 bits por linha em hexadecimal.
    boot_rom_file       : string  := "default.hex";
    -- Imagem da ROM, a partir do seu início (interna, ou o armazenamento do chip de FLASH externo).
    rom_file            : string  := "default.hex";
    -- Imagem inicial da RAM (interna, ou o chip de RAM externo); vazio deixa tudo em zero.
    ram_file            : string  := "";
    -- A ROM é externa, atrás da cache de instruções.
    rom_external        : boolean := ROM_EXTERNAL;
    -- A RAM é externa, atrás da cache de dados.
    ram_external        : boolean := RAM_EXTERNAL;
    -- Tamanho da BOOT_ROM em bytes, uma potência de dois de pelo menos 1 KiB.
    boot_rom_size_bytes : positive := BOOT_ROM_SIZE_BYTES;
    -- Tamanho do armazenamento da ROM em bytes, uma potência de dois.
    rom_size_bytes      : positive := ROM_STORAGE_BYTES;
    -- Tamanho da RAM em bytes, uma potência de dois.
    ram_size_bytes      : positive := RAM_STORAGE_BYTES;
    -- Base RV32E (16 registradores) no núcleo; false é o RV32I (o perfil do platform.yaml por padrão).
    has_e               : boolean  := HAS_E;
    -- Fim exclusivo, em KiB, da ROM, que começa logo depois da BOOT_ROM.
    rom_end_kib         : natural  := ROM_END_KIB;
    -- Base, em KiB, da RAM.
    ram_base_kib        : natural  := RAM_BASE_KIB;
    -- Fim exclusivo, em KiB, da RAM.
    ram_end_kib         : natural  := RAM_END_KIB;
    -- Base, em KiB, da janela externa de periféricos e outros dispositivos.
    ext_base_kib        : natural  := EXT_BASE_KIB;
    -- Base, em KiB, da janela de periféricos.
    periph_base_kib     : natural  := PERIPH_BASE_KIB;
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
    has_zicsr           : boolean := HAS_ZICSR;
    -- Contadores da extensão Zicntr (implica Zicsr).
    has_zicntr          : boolean := HAS_ZICNTR;
    -- Contadores de eventos da extensão Zihpm (quatro, índices 3 a 6); exige Zicsr.
    has_zihpm           : boolean := HAS_ZIHPM;
    -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os índices a partir de 3.
    hpm_counters        : natural range 0 to 29 := 29;
    -- Largura, em bits, de cada contador de eventos do Zihpm.
    hpm_width           : natural range 0 to 64 := 64;
    -- Extensão Zimop no núcleo (mop.r.n e mop.rr.n escrevem zero em rd).
    has_zimop           : boolean := HAS_ZIMOP;
    -- Extensão Zicond no núcleo (czero.eqz e czero.nez).
    has_zicond          : boolean := HAS_ZICOND;
    -- Extensão M completa no núcleo.
    has_m               : boolean := HAS_M;
    -- Multiplicação sem divisão (Zmmul) no núcleo.
    has_zmmul           : boolean := HAS_ZMMUL;
    -- Zifencei no núcleo (FENCE.I invalida a cache de instruções); falso mantém o NOP.
    has_zifencei        : boolean := HAS_ZIFENCEI;
    -- Acesso desalinhado à memória principal executado em hardware (Zicclsm).
    has_zicclsm         : boolean := HAS_ZICCLSM
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



  -- Tamanho da BOOT_ROM em KiB: onde a ROM começa, o que a cache de instruções usa para reconhecê-la.
  constant BOOT_KIB : natural := boot_rom_size_bytes / 1024;

  -- Clocks dos estágios do núcleo.
  signal pll_clk_if      : std_logic;
  -- Clock dos estágios ID, EX e MEM, segunda fase do gerador de clock.
  signal pll_clk_idexmem : std_logic;
  -- Clock do estágio de escrita (WB), terceira fase do gerador de clock.
  signal pll_clk_wb      : std_logic;

  -- Sinais do núcleo: busca de instrução e FLASH interna.
  signal if_addr       : std_logic_vector(31 downto 0);
  -- Habilitação de leitura da busca de instrução ('1' = lê).
  signal if_rden       : std_logic;
  -- Palavra de instrução lida da BOOT_ROM.
  signal boot_rom_data : std_logic_vector(31 downto 0);
  -- Palavra de instrução lida da FLASH.
  signal flash_data    : std_logic_vector(31 downto 0) := (others => '0');
  -- Endereço da segunda porta da FLASH (estágio MEM).
  signal flash_addr2   : std_logic_vector(31 downto 0);
  -- Habilitação de leitura da segunda porta da FLASH ('1' = lê).
  signal flash_rden2   : std_logic;
  -- Palavra de dado lida da segunda porta da FLASH (estágio MEM).
  signal flash_data2   : std_logic_vector(31 downto 0) := (others => '0');

  -- Sinais do núcleo: RAM interna.
  signal ram_addr      : std_logic_vector(31 downto 0);
  -- Dado de escrita na RAM do núcleo.
  signal ram_wdata     : std_logic_vector(31 downto 0);
  -- Dado lido da RAM entregue ao núcleo.
  signal ram_rdata     : std_logic_vector(31 downto 0) := (others => '0');
  -- Habilitação geral da RAM do núcleo (estágio MEM).
  signal ram_en        : std_logic;
  -- Habilitação de escrita da RAM do núcleo ('1' = escreve).
  signal ram_wren      : std_logic;
  -- Habilitação de leitura da RAM do núcleo ('1' = lê).
  signal ram_rden      : std_logic;
  -- Habilitação de bytes da escrita na RAM do núcleo.
  signal ram_byteena   : std_logic_vector(3 downto 0);
  -- Leitura da RAM habilitada pelo núcleo e pelo enable geral ('1' = lê).
  signal ram_re_gated  : std_logic;
  -- Escrita na RAM habilitada pelo núcleo e pelo enable geral ('1' = escreve).
  signal ram_we_gated  : std_logic;

  -- Sinais do núcleo: barramento externo de dados.
  signal sdram_addr    : std_logic_vector(31 downto 0);
  -- Dado de escrita do barramento externo do núcleo.
  signal sdram_wdata   : std_logic_vector(31 downto 0);
  -- Habilitação de bytes da escrita no barramento externo.
  signal sdram_byteena : std_logic_vector(3 downto 0);
  -- Habilitação de leitura do barramento externo ('1' = lê).
  signal sdram_rden    : std_logic;
  -- Habilitação de escrita do barramento externo ('1' = escreve).
  signal sdram_wren    : std_logic;
  -- Dado lido do barramento externo devolvido ao núcleo.
  signal sdram_rdata   : std_logic_vector(31 downto 0) := (others => '0');
  -- Resposta do barramento externo pronta ('1' = pronta).
  signal sdram_ready   : std_logic := '1';
  -- Avanço do pipeline do núcleo liberado pela memória ('1' = avança).
  signal mem_advance   : std_logic;

  -- Sinais do núcleo: cache de instruções.
  signal ic_data       : std_logic_vector(31 downto 0) := (others => '0');
  -- Cache de instruções pronta com a palavra pedida ('1' = pronta).
  signal ic_ready      : std_logic := '1';
  -- Seleciona a cache de instruções para a região da ROM ('1' = selecionada).
  signal ic_sel        : std_logic;
  -- Invalidação da cache de instruções pelo FENCE.I ('1' = invalida).
  signal ic_inval      : std_logic;

  -- Eventos das caches e da FLASH para o Zihpm.
  signal ic_miss       : std_logic := '0';
  -- Pulso de falha (miss) na cache de dados, evento do Zihpm.
  signal dc_miss       : std_logic := '0';
  -- Chip de FLASH ocupado com um acesso, evento do Zihpm ('1' = ocupado).
  signal flash_busy    : std_logic := '0';
  -- Eventos externos do Zihpm: bit 0 falha de instrução, bit 1 falha de dados, bit 2 FLASH ocupada.
  signal hpm_ext_events : std_logic_vector(2 downto 0);

  -- Interconexão e cache de dados: lado do núcleo e lado da memória.
  signal m_addr        : std_logic_vector(31 downto 0);
  -- Interconexão do núcleo para a cache de dados: dado de escrita.
  signal m_wdata       : std_logic_vector(31 downto 0);
  -- Interconexão do núcleo para a cache de dados: habilitação de bytes da escrita.
  signal m_byteena     : std_logic_vector(3 downto 0);
  -- Interconexão do núcleo para a cache de dados: habilitação de leitura ('1' = lê).
  signal m_rden        : std_logic;
  -- Interconexão do núcleo para a cache de dados: habilitação de escrita ('1' = escreve).
  signal m_wren        : std_logic;
  -- Interconexão do núcleo para a cache de dados: acesso concluído ('1' = pronto).
  signal m_ready       : std_logic;
  -- Interconexão do núcleo para a cache de dados: dado lido.
  signal m_rdata       : std_logic_vector(31 downto 0);
  -- Cache de dados, lado da memória: endereço de byte do acesso.
  signal dd_addr       : std_logic_vector(31 downto 0);
  -- Cache de dados, lado da memória: dado de escrita.
  signal dd_wdata      : std_logic_vector(31 downto 0);
  -- Cache de dados, lado da memória: habilitação de bytes da escrita.
  signal dd_be         : std_logic_vector(3 downto 0);
  -- Cache de dados, lado da memória: habilitação de leitura ('1' = lê).
  signal dd_rden       : std_logic;
  -- Cache de dados, lado da memória: habilitação de escrita ('1' = escreve).
  signal dd_wren       : std_logic;
  -- Cache de dados, lado da memória: pedido de linha inteira de cache ('1' = acesso em linha).
  signal dd_line       : std_logic;
  -- Cache de dados, lado da memória: avanço para a próxima palavra da linha ('1' = avança).
  signal dd_adv        : std_logic;
  -- Cache de dados, lado da memória: acesso concluído ('1' = pronto).
  signal dd_ready      : std_logic;
  -- Cache de dados, lado da memória: dado lido.
  signal dd_rdata      : std_logic_vector(31 downto 0);
  -- Cache de dados, lado da memória: linha a escrever, barramento largo de 96 bits.
  signal dd_wdx        : std_logic_vector(95 downto 0);
  -- Cache de dados, lado da memória: linha lida, barramento largo de 96 bits.
  signal dd_rdx        : std_logic_vector(95 downto 0);
  -- Cache de dados concluiu o acesso pendente ('1' = concluído).
  signal dc_done       : std_logic;
  -- Cache de dados ocupada com um acesso ao chip ('1' = ocupada).
  signal dc_busy       : std_logic;

  -- Cache de instruções: lado da memória.
  signal id_addr       : std_logic_vector(31 downto 0);
  -- Cache de instruções, lado da memória: habilitação de leitura ('1' = lê).
  signal id_rden       : std_logic;
  -- Cache de instruções, lado da memória: avanço para a próxima palavra da linha ('1' = avança).
  signal id_adv        : std_logic;
  -- Cache de instruções, lado da memória: acesso concluído ('1' = pronto).
  signal id_ready      : std_logic;
  -- Cache de instruções, lado da memória: dado lido.
  signal id_rdata      : std_logic_vector(31 downto 0);
  -- Cache de instruções, lado da memória: pedido de linha inteira de cache ('1' = acesso em linha).
  signal id_line       : std_logic;
  -- Cache de instruções, lado da memória: linha lida, barramento largo de 96 bits.
  signal id_rdx        : std_logic_vector(95 downto 0);

  -- Roteadores por região (as duas memórias externas): lado do chip de RAM de cada um.
  signal si_addr       : std_logic_vector(31 downto 0);
  -- Roteador da ROM para o chip de RAM: dado de escrita.
  signal si_wdata      : std_logic_vector(31 downto 0);
  -- Roteador da ROM para o chip de RAM: habilitação de bytes da escrita.
  signal si_be         : std_logic_vector(3 downto 0);
  -- Roteador da ROM para o chip de RAM: habilitação de leitura ('1' = lê).
  signal si_rden       : std_logic;
  -- Roteador da ROM para o chip de RAM: habilitação de escrita ('1' = escreve).
  signal si_wren       : std_logic;
  -- Roteador da ROM para o chip de RAM: pedido de linha inteira de cache ('1' = acesso em linha).
  signal si_line       : std_logic;
  -- Roteador da ROM para o chip de RAM: avanço para a próxima palavra da linha ('1' = avança).
  signal si_adv        : std_logic;
  -- Roteador da ROM para o chip de RAM: acesso concluído ('1' = pronto).
  signal si_ready      : std_logic;
  -- Roteador da ROM para o chip de RAM: dado lido.
  signal si_rdata      : std_logic_vector(31 downto 0);
  -- Roteador da ROM para o chip de RAM: linha a escrever, barramento largo de 96 bits.
  signal si_wdx        : std_logic_vector(95 downto 0);
  -- Roteador da ROM para o chip de RAM: linha lida, barramento largo de 96 bits.
  signal si_rdx        : std_logic_vector(95 downto 0);
  -- Roteador de dados para o chip de RAM: endereço de byte do acesso.
  signal sd_addr       : std_logic_vector(31 downto 0);
  -- Roteador de dados para o chip de RAM: dado de escrita.
  signal sd_wdata      : std_logic_vector(31 downto 0);
  -- Roteador de dados para o chip de RAM: habilitação de bytes da escrita.
  signal sd_be         : std_logic_vector(3 downto 0);
  -- Roteador de dados para o chip de RAM: habilitação de leitura ('1' = lê).
  signal sd_rden       : std_logic;
  -- Roteador de dados para o chip de RAM: habilitação de escrita ('1' = escreve).
  signal sd_wren       : std_logic;
  -- Roteador de dados para o chip de RAM: pedido de linha inteira de cache ('1' = acesso em linha).
  signal sd_line       : std_logic;
  -- Roteador de dados para o chip de RAM: avanço para a próxima palavra da linha ('1' = avança).
  signal sd_adv        : std_logic;
  -- Roteador de dados para o chip de RAM: acesso concluído ('1' = pronto).
  signal sd_ready      : std_logic;
  -- Roteador de dados para o chip de RAM: dado lido.
  signal sd_rdata      : std_logic_vector(31 downto 0);
  -- Roteador de dados para o chip de RAM: linha a escrever, barramento largo de 96 bits.
  signal sd_wdx        : std_logic_vector(95 downto 0);
  -- Roteador de dados para o chip de RAM: linha lida, barramento largo de 96 bits.
  signal sd_rdx        : std_logic_vector(95 downto 0);

  -- Roteadores por região (as duas memórias externas): lado do chip de FLASH.
  -- Endereço e dado lido dos roteadores A, B e C do chip de FLASH.
  signal fa_addr, fa_rdata, fb_addr, fb_rdata, fc_addr, fc_rdata : std_logic_vector(31 downto 0);
  -- Roteador A para o chip de FLASH: leitura, pedido de linha, avanço e resposta pronta.
  signal fa_rden, fa_line, fa_adv, fa_ready : std_logic;
  -- Roteador B para o chip de FLASH: leitura, pedido de linha, avanço e resposta pronta.
  signal fb_rden, fb_line, fb_adv, fb_ready : std_logic;
  -- Roteador C para o chip de FLASH: leitura, pedido de linha, avanço e resposta pronta.
  signal fc_rden, fc_line, fc_adv, fc_ready : std_logic;
  -- Linhas lidas dos roteadores A, B e C, barramentos largos de 96 bits.
  signal fa_rdx, fb_rdx, fc_rdx : std_logic_vector(95 downto 0);
  -- Endereço de byte e dado lido do acesso ao chip de FLASH.
  signal flash_mem_addr, flash_mem_data : std_logic_vector(31 downto 0);

  -- Portas do chip de RAM externo: dados e instruções.
  signal rc_d_addr     : std_logic_vector(31 downto 0) := (others => '0');
  -- Porta de dados do chip de RAM externo: dado de escrita.
  signal rc_d_wdata    : std_logic_vector(31 downto 0) := (others => '0');
  -- Porta de dados do chip de RAM externo: habilitação de bytes da escrita.
  signal rc_d_be       : std_logic_vector(3 downto 0)  := (others => '0');
  -- Porta de dados do chip de RAM externo: habilitação de leitura ('1' = lê).
  signal rc_d_rden     : std_logic := '0';
  -- Porta de dados do chip de RAM externo: habilitação de escrita ('1' = escreve).
  signal rc_d_wren     : std_logic := '0';
  -- Porta de dados do chip de RAM externo: pedido de linha inteira de cache ('1' = acesso em linha).
  signal rc_d_line     : std_logic := '0';
  -- Porta de dados do chip de RAM externo: avanço para a próxima palavra da linha ('1' = avança).
  signal rc_d_adv      : std_logic := '0';
  -- Porta de dados do chip de RAM externo: linha a escrever, barramento largo de 96 bits.
  signal rc_d_wdx      : std_logic_vector(95 downto 0) := (others => '0');
  -- Porta de dados do chip de RAM externo: acesso concluído ('1' = pronto).
  signal rc_d_ready    : std_logic;
  -- Porta de dados do chip de RAM externo: dado lido.
  signal rc_d_rdata    : std_logic_vector(31 downto 0);
  -- Porta de dados do chip de RAM externo: linha lida, barramento largo de 96 bits.
  signal rc_d_rdx      : std_logic_vector(95 downto 0);
  -- Porta de instruções do chip de RAM externo: endereço de byte do acesso.
  signal rc_i_addr     : std_logic_vector(31 downto 0) := (others => '0');
  -- Porta de instruções do chip de RAM externo: habilitação de leitura ('1' = lê).
  signal rc_i_rden     : std_logic := '0';
  -- Porta de instruções do chip de RAM externo: pedido de linha inteira de cache ('1' = acesso em linha).
  signal rc_i_line     : std_logic := '0';
  -- Porta de instruções do chip de RAM externo: avanço para a próxima palavra da linha ('1' = avança).
  signal rc_i_adv      : std_logic := '0';
  -- Porta de instruções do chip de RAM externo: acesso concluído ('1' = pronto).
  signal rc_i_ready    : std_logic;
  -- Porta de instruções do chip de RAM externo: dado lido.
  signal rc_i_rdata    : std_logic_vector(31 downto 0);
  -- Porta de instruções do chip de RAM externo: linha lida, barramento largo de 96 bits.
  signal rc_i_rdx      : std_logic_vector(95 downto 0);

begin

  assert boot_rom_size_bytes mod 1024 = 0
    report "boot_rom_size_bytes deve ser múltiplo de 1 KiB"
    severity failure;

  o_ram_en      <= ram_en;
  o_ram_wren    <= ram_wren;
  o_ram_addr    <= ram_addr;
  o_ram_wdata   <= ram_wdata;
  o_ram_byteena <= ram_byteena;

  ram_re_gated <= ram_rden and ram_en;
  ram_we_gated <= ram_wren and ram_en;

  hpm_ext_events <= flash_busy & dc_miss & ic_miss;

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
      has_m        => has_m,
      has_zmmul    => has_zmmul,
      has_zicsr    => has_zicsr,
      has_zicntr   => has_zicntr,
      has_zifencei => has_zifencei,
      has_zicclsm  => has_zicclsm,
      has_e         => has_e,
      boot_rom_bits => log2_exact(boot_rom_size_bytes),
      rom_end_kib   => rom_end_kib,
      rom_external  => rom_external,
      ram_base_kib  => ram_base_kib,
      ram_end_kib   => ram_end_kib,
      ram_external  => ram_external,
      ext_base_kib  => ext_base_kib,
      periph_base_kib => periph_base_kib,
      has_zihpm    => has_zihpm,
      hpm_counters => hpm_counters,
      hpm_width    => hpm_width,
      has_zimop    => has_zimop,
      has_zicond   => has_zicond
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

  u_boot_rom : entity work.rom_simulation
    generic map (rom_file => boot_rom_file, size_bytes => boot_rom_size_bytes)
    port map (
      i_addr => if_addr(31 downto 2),
      i_clk  => pll_clk_if,
      i_re   => if_rden,
      o_data => boot_rom_data
    );

  -- ROM interna: a FLASH com duas portas, uma para instruções e outra para dados.
  g_rom_internal : if not rom_external generate
  begin
    u_flash : entity work.rom_simulation
      generic map (rom_file => rom_file, size_bytes => rom_size_bytes)
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
  end generate g_rom_internal;

  -- RAM interna do núcleo.
  g_ram_internal : if not ram_external generate
  begin
    u_ram : entity work.ram_simulation
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
  end generate g_ram_internal;

  -- Dados externos: a interconexão separa a janela de periféricos, a cache de dados fica entre o
  -- núcleo e a memória.
  g_data_external : if ram_external generate
  begin
    u_interconnect : entity work.ext_interconnect
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

    u_dcache : entity work.dcache
      generic map (
        size_bits     => dcache_size_bits,
        write_through => true,
        rom_base_kib  => BOOT_KIB,
        rom_end_kib   => rom_end_kib
      )
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
  g_instr_external : if rom_external generate
  begin
    u_icache : entity work.icache
      generic map (
        size_bits    => icache_size_bits,
        rom_base_kib => BOOT_KIB,
        rom_end_kib  => rom_end_kib
      )
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

  -- A RAM externa sozinha: a cache de dados fala direto com o chip de RAM.
  g_direct_data : if ram_external and not rom_external generate
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

  -- A ROM externa sozinha: a cache de instruções fala direto com o chip de FLASH.
  g_direct_instr : if rom_external and not ram_external generate
  begin
    fc_addr  <= id_addr;
    fc_rden  <= id_rden;
    fc_line  <= id_line;
    fc_adv   <= id_adv;
    id_ready <= fc_ready;
    id_rdata <= fc_rdata;
    id_rdx   <= fc_rdx;
  end generate g_direct_instr;

  -- As duas memórias externas: um roteador por cache separa a ROM do chip de RAM, e a ROM tem um
  -- árbitro entre as duas.
  g_routed : if rom_external and ram_external generate
  begin
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

  -- O chip de FLASH externo e o seu armazenamento, quando a ROM é externa.
  g_rom_chip : if rom_external generate
  begin
    u_flash_chip : entity work.flash_chip
      generic map (
        first_latency => flash_first_latency,
        next_latency  => flash_next_latency,
        size_bytes    => rom_size_bytes
      )
      port map (
        i_clk => pll_clk_idexmem, i_rst => i_rst,
        i_addr => fc_addr, i_rden => fc_rden, i_line => fc_line, i_advance => fc_adv,
        o_ready => fc_ready, o_busy => flash_busy, o_rdata => fc_rdata, o_rdata_x => fc_rdx,
        o_mem_addr => flash_mem_addr, i_mem_data => flash_mem_data
      );

    u_flash_storage : entity work.rom_simulation
      generic map (rom_file => rom_file, size_bytes => rom_size_bytes)
      port map (
        i_addr => flash_mem_addr(31 downto 2),
        i_clk  => pll_clk_idexmem,
        i_re   => '1',
        o_data => flash_mem_data
      );
  end generate g_rom_chip;

  -- O chip de RAM externo, quando algum lado é externo.
  g_ext_ram : if ram_external generate
  begin
    u_ext_ram : entity work.ram_chip
      generic map (
        init_file  => ram_file,
        latency    => ext_ram_latency,
        size_bytes => ram_size_bytes,
        base_kib   => ram_base_kib mod 65536
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

  g_no_ext_ram : if not ram_external generate
  begin
    o_dbg_word_data <= (others => '0');
  end generate g_no_ext_ram;

end architecture behaviour;
