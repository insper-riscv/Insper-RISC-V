-- =============================================================================
-- Topo de simulação modular: as memórias e as caches do núcleo em qualquer combinação
--
-- Um único topo, configurado por genéricos, monta o núcleo com quatro escolhas independentes: a ROM
-- e a RAM dentro ou fora do chip (rom_external e ram_external) e a cache de instruções e a de dados
-- (has_icache e has_dcache). Uma memória que o núcleo alcança pela porta (externa, ou interna atrás de
-- uma cache) fica num modelo de chip simulado (flash_chip para a ROM, ram_chip para a RAM), de tamanho
-- configurável; a que não é alcançada pela porta é o vetor do próprio núcleo.
--
--   rom_via_port = rom_external ou has_icache
--   ram_via_port = ram_external ou has_dcache
--
-- O núcleo recebe rom_via_port e ram_via_port nos seus genéricos rom_external e ram_external, porque
-- uma cache só existe do lado do protocolo da porta. A posição física (interna ou externa) não muda a
-- simulação além disso: o chip simulado faz o papel da memória em qualquer das duas.
--
--   | Lado da ROM                  | Busca de instrução                | Dado da ROM                   |
--   | interna, sem cache           | FLASH interna do núcleo           | segunda porta da FLASH interna |
--   | via porta, sem cache         | ponte de busca (ifetch_bridge)    | roteador, árbitro e chip      |
--   | via porta, com cache         | cache de instruções               | roteador, árbitro e chip      |
--
--   | Lado da RAM                  | Acesso a dados                    |
--   | interna, sem cache           | RAM interna do núcleo             |
--   | via porta, sem cache         | interconexão direto ao chip       |
--   | via porta, com cache         | interconexão, cache de dados e chip |
--
-- Os quatro modelos originais continuam valendo: sem has_icache e has_dcache informados, a cache
-- existe quando a memória é externa (o padrão de has_icache é rom_external ou HAS_ICACHE do pacote, o de
-- has_dcache é ram_external ou HAS_DCACHE).
--
-- O mapa vem dos genéricos, cujo valor padrão é o do pacote modular_map_pkg, gerado do platform.yaml da
-- plataforma, e é o mesmo do núcleo: a BOOT_MEMORY em [0, tamanho), a ROM logo depois
-- dela até rom_end_kib, a RAM em [ram_base_kib, ram_end_kib) e a janela externa a partir de
-- ext_base_kib. O que o projeto escolhe fica no platform.yaml da plataforma.
--
-- Com a ROM e a RAM via porta, um roteador por mestre separa a ROM da RAM, e a ROM tem um árbitro entre
-- a busca e os dados. Com só a ROM via porta, o roteador dos dados leva o pedido à FLASH e responde zero
-- fora dela. Com só a RAM via porta, a cache de dados (ou a interconexão, sem ela) fala direto com o chip.
--
-- Todos os tamanhos são genéricos em potência de dois (bytes para as memórias, bits para as
-- caches), verificados pelo log2_exact. Os valores padrão são os da simulação do ACT4: ROM e RAM
-- de 1 MB e caches de 4 kbit.
--
-- A porta de depuração lê uma palavra do chip de RAM, pelo índice a partir do seu início, sem
-- passar pelas caches: é como o testbench vê o HTIF tohost quando ele está no chip. Quando a RAM é
-- do núcleo, o testbench observa as saídas o_ram_*, que são o barramento de dados da RAM do núcleo; quando
-- é via porta, observa o barramento externo do núcleo (sdram_*).
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.modular_map_pkg.all;

entity modular_sim_top is
  generic (
    -- Imagem da BOOT_MEMORY, uma palavra de 32 bits por linha em hexadecimal.
    boot_memory_file       : string  := "default.hex";
    -- Imagem da ROM, a partir do seu início (interna, ou o armazenamento do chip de FLASH externo).
    rom_file            : string  := "default.hex";
    -- Imagem inicial da RAM (interna, ou o chip de RAM externo); vazio deixa tudo em zero.
    ram_file            : string  := "";
    -- A ROM é externa (um chip fora do núcleo, alcançado pela porta).
    rom_external        : boolean := ROM_EXTERNAL;
    -- A RAM é externa (um chip fora do núcleo, alcançado pela porta).
    ram_external        : boolean := RAM_EXTERNAL;
    -- Tamanho da BOOT_MEMORY em bytes, uma potência de dois de pelo menos 1 KiB.
    boot_memory_size_bytes : positive := BOOT_MEMORY_SIZE_BYTES;
    -- Tamanho do armazenamento da ROM em bytes, uma potência de dois.
    rom_size_bytes      : positive := ROM_STORAGE_BYTES;
    -- Tamanho da RAM em bytes, uma potência de dois.
    ram_size_bytes      : positive := RAM_STORAGE_BYTES;
    -- Base RV32E (16 registradores) no núcleo; false é o RV32I (o perfil do platform.yaml por padrão).
    has_e               : boolean  := HAS_E;
    -- Fim exclusivo, em KiB, da ROM, que começa logo depois da BOOT_MEMORY.
    rom_end_kib         : natural  := ROM_END_KIB;
    -- Base, em KiB, da RAM.
    ram_base_kib        : natural  := RAM_BASE_KIB;
    -- Fim exclusivo, em KiB, da RAM.
    ram_end_kib         : natural  := RAM_END_KIB;
    -- Base, em KiB, da janela externa de periféricos e outros dispositivos.
    ext_base_kib        : natural  := EXT_BASE_KIB;
    -- Base, em KiB, da janela de periféricos.
    periph_base_kib     : natural  := PERIPH_BASE_KIB;
    -- Existe cache de instruções; sem ela, a ROM via porta é lida pela ponte de busca. Por padrão, a
    -- cache existe quando a ROM é externa ou o pacote a liga.
    has_icache          : boolean := rom_external or HAS_ICACHE;
    -- Existe cache de dados; sem ela, a RAM via porta é acessada direto, palavra a palavra. Por
    -- padrão, a cache existe quando a RAM é externa ou o pacote a liga.
    has_dcache          : boolean := ram_external or HAS_DCACHE;
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
    -- Dicas ntl.* da extensão Zihintntl no núcleo (executam como nop).
    has_zihintntl       : boolean := HAS_ZIHINTNTL;
    -- Dica pause da extensão Zihintpause no núcleo (executa como nop).
    has_zihintpause     : boolean := HAS_ZIHINTPAUSE;
    -- Extensão M completa no núcleo.
    has_m               : boolean := HAS_M;
    -- Multiplicação sem divisão (Zmmul) no núcleo.
    has_zmmul           : boolean := HAS_ZMMUL;
    -- Zifencei no núcleo (FENCE.I invalida a cache de instruções); falso mantém o NOP.
    has_zifencei        : boolean := HAS_ZIFENCEI;
    -- Acesso desalinhado à memória principal executado em hardware (Zicclsm).
    has_zicclsm         : boolean := HAS_ZICCLSM;
    -- Interrupções de máquina: o CLINT e o controlador externo ficam na janela de periféricos e as
    -- três linhas chegam ao núcleo, que só as habilita com Zicsr.
    has_interrupts      : boolean := HAS_INTERRUPTS;
    -- Ciclos de clock do núcleo por incremento do mtime do CLINT.
    clint_tick_cycles   : positive := 1;
    -- Índice da janela de 256 MiB do CLINT (bits 30:28 do endereço); o do platform.yaml.
    clint_id            : natural range 0 to 7 := 6;
    -- Índice da janela de 256 MiB do controlador de interrupção externa.
    ext_irq_id          : natural range 0 to 7 := 7;
    -- Chaves SW da placa, num bloco GPIO de 10 pinos (plataformas da FPGA).
    has_switches        : boolean := false;
    -- Índice da janela das chaves.
    switches_id         : natural range 0 to 7 := 1;
    -- Botões KEY da placa, num bloco GPIO de 4 pinos (plataformas da FPGA).
    has_keys            : boolean := false;
    -- Índice da janela dos botões.
    keys_id             : natural range 0 to 7 := 2;
    -- Displays de 7 segmentos HEX0 a HEX5 (plataformas da FPGA).
    has_display         : boolean := false;
    -- Índice da janela do display.
    display_id          : natural range 0 to 7 := 5;
    -- UART cuja outra ponta é o hospedeiro no JTAG.
    has_uart_jtag       : boolean := false;
    -- Índice da janela da UART via JTAG.
    uart_jtag_id        : natural range 0 to 7 := 4;
    -- UART cuja outra ponta são dois pinos (TX e RX) da placa.
    has_uart_pins       : boolean := false;
    -- Índice da janela da UART via pinos.
    uart_pins_id        : natural range 0 to 7 := 3
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
    o_ram_byteena   : out std_logic_vector(3 downto 0);
    -- Chaves SW (10 pinos do GPIO); o testbench as conduz.
    io_sw           : inout std_logic_vector(9 downto 0);
    -- Botões KEY (4 pinos do GPIO); o testbench os conduz.
    io_key          : inout std_logic_vector(3 downto 0);
    -- Segmentos dos displays, HEX0 nos bits 6:0 e HEX5 nos bits 41:36 (nível baixo).
    o_display_hex   : out std_logic_vector(41 downto 0);
    -- Valor de 24 bits do registrador do display.
    o_display_value : out std_logic_vector(23 downto 0);
    -- Virtual JTAG da UART via JTAG: clock da cadeia.
    i_uart_tck      : in  std_logic := '0';
    -- Virtual JTAG da UART via JTAG: dado vindo do hospedeiro.
    i_uart_tdi      : in  std_logic := '0';
    -- Virtual JTAG da UART via JTAG: dado para o hospedeiro.
    o_uart_tdo      : out std_logic;
    -- Virtual JTAG da UART via JTAG: registrador de instrução.
    i_uart_ir_in    : in  std_logic_vector(1 downto 0) := "00";
    -- Virtual JTAG da UART via JTAG: estado Capture-DR.
    i_uart_state_cdr : in std_logic := '0';
    -- Virtual JTAG da UART via JTAG: estado Shift-DR.
    i_uart_state_sdr : in std_logic := '0';
    -- Virtual JTAG da UART via JTAG: estado Update-DR.
    i_uart_state_udr : in std_logic := '0';
    -- Virtual JTAG da UART via JTAG: estado Update-IR.
    i_uart_state_uir : in std_logic := '0';
    -- Linha serial de recepção da UART via pinos.
    i_uart_rx       : in  std_logic := '1';
    -- Linha serial de transmissão da UART via pinos.
    o_uart_tx       : out std_logic
  );
end entity modular_sim_top;

architecture behaviour of modular_sim_top is



  -- Tamanho da BOOT_MEMORY em KiB: onde a ROM começa, o que a cache de instruções usa para reconhecê-la.
  constant BOOT_KIB : natural := boot_memory_size_bytes / 1024;

  -- A ROM é alcançada pela porta do núcleo: está fora do chip ou atrás da cache de instruções.
  constant ROM_PORT : boolean := rom_external or has_icache;
  -- A RAM é alcançada pela porta do núcleo: está fora do chip ou atrás da cache de dados.
  constant RAM_PORT : boolean := ram_external or has_dcache;

  -- Há algum periférico na janela de periféricos: o CLINT e o controlador externo, ou os do topo da placa.
  constant HAS_PERIPHERALS : boolean :=
    has_interrupts or has_switches or has_keys or has_display or has_uart_jtag or has_uart_pins;

  -- Escolhe entre dois valores naturais conforme a condição.
  function pick(cond : boolean; a : natural; b : natural) return natural is
  begin
    if cond then
      return a;
    end if;
    return b;
  end function pick;

  -- Base da região da ROM, em KiB, nos endereços que o roteador dos dados vê: a cache de dados os
  -- troca pelos da região da FLASH (0x20000000), e sem ela chegam os do mapa.
  constant D_ROM_BASE_KIB : natural := pick(has_dcache, 524288, BOOT_KIB);
  -- Fim exclusivo da região da ROM, em KiB, nos endereços que o roteador dos dados vê.
  constant D_ROM_END_KIB  : natural := pick(has_dcache, 1048576, rom_end_kib);

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
  -- Palavra de instrução lida da BOOT_MEMORY.
  signal boot_memory_data : std_logic_vector(31 downto 0);
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

  -- Interrupções de máquina do núcleo: timer (MTIP) e software (MSIP) do CLINT, externa (MEIP) do controlador.
  signal irq_timer     : std_logic := '0';
  -- Interrupção de software de máquina (MSIP), saída do CLINT.
  signal irq_software  : std_logic := '0';
  -- Interrupção externa de máquina (MEIP), saída do controlador de interrupção externa.
  signal irq_external  : std_logic := '0';

  -- Janela de periféricos: deslocamento de palavra dentro do periférico (64 KiB por janela).
  signal p_addr        : std_logic_vector(13 downto 0);
  -- Janela de periféricos: dado de escrita.
  signal p_wdata       : std_logic_vector(31 downto 0);
  -- Janela de periféricos: habilita de bytes da escrita.
  signal p_byteena     : std_logic_vector(3 downto 0);
  -- Janela de periféricos: pulso de escrita, um bit por periférico.
  signal p_we          : std_logic_vector(7 downto 0);
  -- Janela de periféricos: pulso de leitura, um bit por periférico.
  signal p_re          : std_logic_vector(7 downto 0);
  -- Janela de periféricos: dados lidos, 32 bits por periférico.
  signal p_rdata       : std_logic_vector(8 * 32 - 1 downto 0) := (others => '0');

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

  -- Pulso de retirada de instrução do núcleo, que o testbench conta para o CPI.
  signal core_retire   : std_logic;

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

  assert boot_memory_size_bytes mod 1024 = 0
    report "boot_memory_size_bytes deve ser múltiplo de 1 KiB"
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
      boot_memory_bits => log2_exact(boot_memory_size_bytes),
      rom_end_kib   => rom_end_kib,
      rom_external  => ROM_PORT,
      ram_base_kib  => ram_base_kib,
      ram_end_kib   => ram_end_kib,
      ram_external  => RAM_PORT,
      ext_base_kib  => ext_base_kib,
      periph_base_kib => periph_base_kib,
      has_zihpm    => has_zihpm,
      hpm_counters => hpm_counters,
      hpm_width    => hpm_width,
      has_zimop    => has_zimop,
      has_zicond   => has_zicond,
      has_zihintntl   => has_zihintntl,
      has_zihintpause => has_zihintpause,
      has_interrupts  => has_interrupts and has_zicsr
    )
    port map (
      o_trap           => open,
      o_retire         => core_retire,
      o_trap_cause     => open,
      o_trap_pc        => open,
      i_clk            => pll_clk_idexmem,
      i_rst            => i_rst,
      o_if_addr        => if_addr,
      o_if_rden        => if_rden,
      i_boot_memory_data  => boot_memory_data,
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
      i_irq_software   => irq_software,
      i_irq_timer      => irq_timer,
      i_irq_external   => irq_external,
      i_ic_data        => ic_data,
      i_ic_ready       => ic_ready,
      o_ic_sel         => ic_sel,
      o_ic_inval       => ic_inval
    );

  u_boot_memory : entity work.rom_simulation
    generic map (rom_file => boot_memory_file, size_bytes => boot_memory_size_bytes)
    port map (
      i_addr => if_addr(31 downto 2),
      i_clk  => pll_clk_if,
      i_re   => if_rden,
      o_data => boot_memory_data
    );

  -- ROM do núcleo: a FLASH com duas portas, uma para instruções e outra para dados.
  g_rom_internal : if not ROM_PORT generate
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

  -- RAM do núcleo.
  g_ram_internal : if not RAM_PORT generate
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

  -- A interconexão separa a janela de periféricos e entrega o pedido de dados à cache de dados ou,
  -- sem ela, direto ao lado da memória. Existe quando há dados via porta ou interrupções (o CLINT
  -- e o controlador externo ficam na janela); sem dados via porta, o lado da memória responde zero.
  g_data_port : if ROM_PORT or RAM_PORT or HAS_PERIPHERALS generate
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
        o_p_addr      => p_addr,
        o_p_wdata     => p_wdata,
        o_p_byteena   => p_byteena,
        o_p_we        => p_we,
        o_p_re        => p_re,
        i_p_rdata     => p_rdata
      );
  end generate g_data_port;

  g_no_data_port : if not (ROM_PORT or RAM_PORT) generate
  begin
    m_ready <= '1';
    m_rdata <= (others => '0');
  end generate g_no_data_port;

  -- CLINT e controlador de interrupção externa, no domínio de clock do núcleo (sem sincronizador).
  g_interrupts : if has_interrupts generate
  begin
    u_clint : entity work.clint
      generic map (tick_cycles => clint_tick_cycles)
      port map (
        i_clk          => pll_clk_idexmem,
        i_rst          => i_rst,
        i_data_in      => p_wdata,
        i_address      => p_addr,
        i_write        => p_we(clint_id),
        i_read         => p_re(clint_id),
        o_data_out     => p_rdata(32 * clint_id + 31 downto 32 * clint_id),
        o_irq_timer    => irq_timer,
        o_irq_software => irq_software
      );

    -- Nenhum periférico do topo gera linha de interrupção ainda: as linhas ficam em zero.
    u_ext_irq : entity work.ext_irq_controller
      port map (
        i_clk          => pll_clk_idexmem,
        i_rst          => i_rst,
        i_irq_lines    => (others => '0'),
        i_data_in      => p_wdata,
        i_address      => p_addr(1 downto 0),
        i_write        => p_we(ext_irq_id),
        i_read         => p_re(ext_irq_id),
        o_data_out     => p_rdata(32 * ext_irq_id + 31 downto 32 * ext_irq_id),
        o_irq_external => irq_external
      );
  end generate g_interrupts;

  -- Periféricos do topo da placa: chaves e botões (GPIO), display e as duas UART. Um periférico ausente deixa
  -- a saída em zero e o dado lido da janela em zero, como uma janela sem dispositivo.
  g_switches : if has_switches generate
  begin
    u_switches : entity work.gpio
      generic map (data_width => 10)
      port map (
        i_clk        => pll_clk_idexmem,
        i_rst        => i_rst,
        i_data_in    => p_wdata(9 downto 0),
        i_address    => p_addr(3 downto 0),
        i_write      => p_we(switches_id),
        i_read       => p_re(switches_id),
        o_data_out   => p_rdata(32 * switches_id + 9 downto 32 * switches_id),
        o_irq        => open,
        io_gpio_pins => io_sw
      );
  end generate g_switches;

  g_keys : if has_keys generate
  begin
    u_keys : entity work.gpio
      generic map (data_width => 4)
      port map (
        i_clk        => pll_clk_idexmem,
        i_rst        => i_rst,
        i_data_in    => p_wdata(3 downto 0),
        i_address    => p_addr(3 downto 0),
        i_write      => p_we(keys_id),
        i_read       => p_re(keys_id),
        o_data_out   => p_rdata(32 * keys_id + 3 downto 32 * keys_id),
        o_irq        => open,
        io_gpio_pins => io_key
      );
  end generate g_keys;

  g_display : if has_display generate
  begin
    u_display : entity work.seg_display
      port map (
        i_clk       => pll_clk_idexmem,
        i_rst       => i_rst,
        i_addr      => p_addr(7 downto 0),
        i_wdata     => p_wdata,
        i_we        => p_we(display_id),
        i_re        => p_re(display_id),
        o_rdata     => p_rdata(32 * display_id + 31 downto 32 * display_id),
        i_tck       => '0',
        i_tdi       => '0',
        o_tdo       => open,
        i_ir_in     => "00",
        i_state_cdr => '0',
        i_state_sdr => '0',
        i_state_udr => '0',
        i_state_uir => '0',
        o_value     => o_display_value,
        o_fail      => open,
        o_hex       => o_display_hex
      );
  end generate g_display;

  g_uart_jtag : if has_uart_jtag generate
  begin
    u_uart_jtag : entity work.jtag_uart
      port map (
        i_clk       => pll_clk_idexmem,
        i_rst       => i_rst,
        i_addr      => p_addr(7 downto 0),
        i_wdata     => p_wdata,
        i_we        => p_we(uart_jtag_id),
        i_re        => p_re(uart_jtag_id),
        o_rdata     => p_rdata(32 * uart_jtag_id + 31 downto 32 * uart_jtag_id),
        i_tck       => i_uart_tck,
        i_tdi       => i_uart_tdi,
        o_tdo       => o_uart_tdo,
        i_ir_in     => i_uart_ir_in,
        i_state_cdr => i_uart_state_cdr,
        i_state_sdr => i_uart_state_sdr,
        i_state_udr => i_uart_state_udr,
        i_state_uir => i_uart_state_uir
      );
  end generate g_uart_jtag;

  g_uart_pins : if has_uart_pins generate
  begin
    u_uart_pins : entity work.uart
      port map (
        i_clk      => pll_clk_idexmem,
        i_rst      => i_rst,
        i_data_in  => p_wdata,
        i_address  => p_addr(1 downto 0),
        i_write    => p_we(uart_pins_id),
        i_read     => p_re(uart_pins_id),
        o_data_out => p_rdata(32 * uart_pins_id + 31 downto 32 * uart_pins_id),
        o_irq      => open,
        i_uart_rx  => i_uart_rx,
        o_uart_tx  => o_uart_tx
      );
  end generate g_uart_pins;

  -- Com cache de dados, ela fica entre a interconexão e a memória.
  g_dcache : if (ROM_PORT or RAM_PORT) and has_dcache generate
  begin
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
  end generate g_dcache;

  -- Sem cache de dados, o pedido da interconexão segue palavra a palavra, com os endereços do mapa.
  g_no_dcache : if (ROM_PORT or RAM_PORT) and not has_dcache generate
  begin
    dd_addr  <= m_addr;
    dd_wdata <= m_wdata;
    dd_be    <= m_byteena;
    dd_rden  <= m_rden;
    dd_wren  <= m_wren;
    dd_line  <= '0';
    dd_adv   <= mem_advance;
    dd_wdx   <= (others => '0');
    m_ready  <= dd_ready;
    m_rdata  <= dd_rdata;
  end generate g_no_dcache;

  -- Instruções via porta, com cache: a cache de instruções entre o núcleo e a memória.
  g_icache : if ROM_PORT and has_icache generate
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
  end generate g_icache;

  -- Instruções via porta, sem cache: a ponte de busca, que guarda só a linha corrente.
  g_ifetch : if ROM_PORT and not has_icache generate
  begin
    u_ifetch : entity work.ifetch_bridge
      generic map (
        fetch_line   => true,
        rom_base_kib => BOOT_KIB,
        rom_end_kib  => rom_end_kib
      )
      port map (
        i_clk        => pll_clk_idexmem,
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
  end generate g_ifetch;

  -- Só a RAM via porta: o lado da memória dos dados fala direto com o chip de RAM.
  g_direct_data : if RAM_PORT and not ROM_PORT generate
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

  -- Só a ROM via porta: o roteador leva os dados da ROM à FLASH, e o que cai fora dela responde zero.
  g_rom_only : if ROM_PORT and not RAM_PORT generate
  begin
    sd_ready <= '1';
    sd_rdata <= (others => '0');
    sd_rdx   <= (others => '0');
    fa_addr  <= id_addr;
    fa_rden  <= id_rden;
    fa_line  <= id_line;
    fa_adv   <= id_adv;
    id_ready <= fa_ready;
    id_rdata <= fa_rdata;
    id_rdx   <= fa_rdx;
  end generate g_rom_only;

  -- A ROM via porta: o roteador dos dados e o árbitro entre a busca e os dados na FLASH.
  g_rom_path : if ROM_PORT generate
  begin
    u_router_d : entity work.mem_region_router
      generic map (
        rom_base_kib => D_ROM_BASE_KIB,
        rom_end_kib  => D_ROM_END_KIB,
        hold_rdata   => not has_dcache
      )
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
  end generate g_rom_path;

  -- As duas memórias via porta: o roteador da busca separa a FLASH do chip de RAM, e o dos dados
  -- entrega o que não é da FLASH ao chip.
  g_routed : if ROM_PORT and RAM_PORT generate
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

  -- O chip de FLASH e o seu armazenamento, quando a ROM é alcançada pela porta.
  g_rom_chip : if ROM_PORT generate
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

  -- O chip de RAM, quando a RAM é alcançada pela porta.
  g_ext_ram : if RAM_PORT generate
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

  g_no_ext_ram : if not RAM_PORT generate
  begin
    o_dbg_word_data <= (others => '0');
  end generate g_no_ext_ram;

end architecture behaviour;
