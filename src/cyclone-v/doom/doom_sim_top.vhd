-- ============================================================================
-- Topo de simulação da plataforma doom (SDRAM dividida em FLASH e RAM, vídeo e teclado)
-- ============================================================================
-- O núcleo, a BOOT_MEMORY (vetor VHDL), as caches de instruções e de dados e a
-- SDRAM (ponte, árbitro, controlador e modelo de chip do repositório Memory) em
-- clock próprio. O chip é um só e tem duas janelas do mesmo
-- controlador. A FLASH (as instruções, de FLASH_BASE_KIB a FLASH_END_KIB do
-- platform.yaml) começa em flash_chip_offset_bytes dentro do chip (o `offset` do
-- platform.yaml: no fim do chip na placa) e chega ao controlador pela porta de
-- instruções do sdram_system. A RAM (os dados, a partir de 0x40000000) começa em
-- ram_chip_offset_bytes dentro do chip, e chega pela porta de dados. As duas só
-- são alcançadas pelas caches, cujos pedidos de linha um roteador de região
-- envia à FLASH ou à RAM.
--
-- O núcleo só lê a FLASH: um store nela termina sem efeito no roteador (e é uma
-- falha de acesso no núcleo com AccessFaults), e a porta de instruções do chip
-- nunca escreve. Quem escreve a FLASH é a porta de depuração do chip, que no
-- teste é o sdram_file lido pelo modelo no tempo zero (a imagem do chip a
-- partir da palavra 0, com a FLASH e a RAM nos deslocamentos dos generics). A
-- busca de código que roda da RAM usa a mesma porta de instruções, atrás de um
-- segundo árbitro com a face da FLASH.
--
-- Além dos periféricos da de0-cv, a janela de periféricos tem o vídeo VGA
-- indexado (VIDEO, 0x80100000) e o teclado PS/2 (KBD, 0x80007000, com a
-- interrupção na linha IRQ_KBD do PLIC), como o topo gerado da placa os liga. O
-- vídeo recebe o clock de pixel i_pixel_clk, conduzido pelo testbench sem
-- relação fixa com i_clk, e a geometria do quadro e do modo pelos generics
-- video_*; as linhas do teclado são io_ps2_clk e io_ps2_dat, que o testbench
-- conduz como o dispositivo do conector.
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
use work.doom_map_pkg.all;
use work.config_pkg.addr_t;
use work.config_pkg.word_t;
use work.config_pkg.XLEN;
use work.config_pkg.ADDR_BITS;
use work.interconnect_pkg.all;

entity doom_sim_test is
    generic (
        -- Arquivo com a imagem da BOOT_MEMORY, uma palavra de 32 bits por linha em hexadecimal.
        boot_memory_file       : string                := "default.hex";
        -- Largura do endereço de palavra da BOOT_MEMORY.
        boot_memory_addr_width : natural               := 9;
        -- Largura do endereço de palavra da RAM interna; com a SDRAM como RAM não dimensiona nada.
        ram_addr_width         : natural               := 9;
        -- Interrupcoes de maquina: o CLINT e o controlador externo na janela de periféricos, e as tres linhas no core.
        has_interrupts         : boolean               := true;
        -- As memórias de instrução (BOOT_MEMORY e cache de instruções) leem, na borda do clock do núcleo, o endereço
        -- do PC do ciclo seguinte (o_if_addr_nx do núcleo), como o topo da placa com o clock de busca igual ao do núcleo.
        early_fetch            : boolean               := false;
        -- Ciclos de clock do core por incremento do mtime do CLINT.
        clint_tick_cycles      : positive              := work.doom_map_pkg.CLINT_TICK_CYCLES;
        -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os indices a partir de 3.
        hpm_counters           : natural range 0 to 29 := 29;
        -- Largura, em bits, de cada contador de eventos do Zihpm.
        hpm_width              : natural range 0 to 64 := 64;
        -- A ROM fica fora do core (o modelo de memória do platform.yaml).
        rom_external           : boolean               := work.doom_map_pkg.FLASH_ON_BUS;
        -- A RAM fica fora do core (o modelo de memória do platform.yaml).
        ram_external           : boolean               := work.doom_map_pkg.RAM_ON_BUS;
        -- Existe cache de instruções (o modelo de memória do platform.yaml).
        has_icache             : boolean               := work.doom_map_pkg.HAS_ICACHE;
        -- Existe cache de dados (o modelo de memória do platform.yaml).
        has_dcache             : boolean               := work.doom_map_pkg.HAS_DCACHE;
        -- Tamanho da cache de instruções, em bits (o modelo de memória do platform.yaml).
        icache_size_bits       : positive              := work.doom_map_pkg.ICACHE_SIZE_BITS;
        -- Tamanho da cache de dados, em bits (o modelo de memória do platform.yaml).
        dcache_size_bits       : positive              := work.doom_map_pkg.DCACHE_SIZE_BITS;
        -- Imagem de programa gravada na SDRAM no tempo zero (uma palavra de 32 bits por linha, em
        -- hexadecimal, a partir de 0x40000000): o hospedeiro que carrega o chip pela porta de debug.
        sdram_file             : string                := "";
        -- Deslocamento, em bytes, em que a base da FLASH fica dentro do chip de SDRAM (o `offset` da FLASH do
        -- platform.yaml): o padrão é o da placa, no fim do chip.
        flash_chip_offset_bytes : natural              := work.config_pkg.FLASH_CHIP_OFFSET;
        -- Deslocamento, em bytes, em que a RAM começa dentro do chip de SDRAM (o `offset` da RAM do platform.yaml).
        ram_chip_offset_bytes  : natural               := work.config_pkg.RAM_CHIP_OFFSET;
        -- Periodo, em picossegundos, do clock CLK_MEM do controlador da SDRAM (o do platform.yaml): base da conversao
        -- dos tempos do chip em ciclos.
        sdram_tck_ps           : natural               := work.doom_map_pkg.SDRAM_TCK_PS;
        -- Largura do framebuffer em pixels (a do platform.yaml, io.video.fb_width).
        video_fb_width         : positive              := 320;
        -- Altura do framebuffer em pixels (a do platform.yaml, io.video.fb_height).
        video_fb_height        : positive              := 200;
        -- Ampliação de cada pixel do framebuffer (a do plano de vídeo: a maior que cabe no modo).
        video_scale            : positive              := 2;
        -- Pixels visíveis por linha do modo (o 640x480 a 60 Hz da DE0-CV).
        video_h_visible        : positive              := 640;
        -- Pixels do pórtico frontal horizontal.
        video_h_front_porch    : natural               := 16;
        -- Pixels do pulso de sincronismo horizontal.
        video_h_sync           : positive              := 96;
        -- Pixels do pórtico traseiro horizontal.
        video_h_back_porch     : natural               := 48;
        -- Linhas visíveis por quadro do modo.
        video_v_visible        : positive              := 480;
        -- Linhas do pórtico frontal vertical.
        video_v_front_porch    : natural               := 10;
        -- Linhas do pulso de sincronismo vertical.
        video_v_sync           : positive              := 2;
        -- Linhas do pórtico traseiro vertical.
        video_v_back_porch     : natural               := 33;
        -- Ciclos que um nível das linhas PS/2 precisa durar para passar no filtro do teclado.
        kbd_filter_cycles      : positive              := 8;
        -- Ciclos sem borda de clock PS/2 que abortam um quadro do teclado.
        kbd_timeout_cycles     : positive              := 1000000
    );
    port (
        -- Clock base do núcleo; um gerador de clock o divide por três.
        i_clk            : in    std_logic;
        -- Clock da SDRAM, conduzido pelo testbench sem relação fixa com i_clk.
        i_clk_mem        : in    std_logic;
        -- Reset do topo, ativo em '1'.
        i_rst            : in    std_logic                     := '0';
        -- Índice de palavra lido direto do modelo do chip de SDRAM, para o testbench.
        i_dbg_word_addr  : in    std_logic_vector(23 downto 0) := (others => '0');
        -- Palavra do modelo do chip de SDRAM no índice de i_dbg_word_addr.
        o_dbg_word_data  : out   word_t;
        -- Virtual JTAG da UART: clock TCK.
        i_uart_tck       : in    std_logic                     := '0';
        -- Virtual JTAG da UART: entrada de dados TDI.
        i_uart_tdi       : in    std_logic                     := '0';
        -- Virtual JTAG da UART: saída de dados TDO.
        o_uart_tdo       : out   std_logic;
        -- Virtual JTAG da UART: registrador de instrução.
        i_uart_ir_in     : in    std_logic_vector(1 downto 0)  := "00";
        -- Virtual JTAG da UART: estado Capture-DR.
        i_uart_state_cdr : in    std_logic                     := '0';
        -- Virtual JTAG da UART: estado Shift-DR.
        i_uart_state_sdr : in    std_logic                     := '0';
        -- Virtual JTAG da UART: estado Update-DR.
        i_uart_state_udr : in    std_logic                     := '0';
        -- Virtual JTAG da UART: estado Update-IR.
        i_uart_state_uir : in    std_logic                     := '0';
        -- Valor do registrador do display (periférico 5, 0xD0000000), cuja porta do hospedeiro fica parada aqui
        o_display_value  : out   std_logic_vector(23 downto 0);
        -- Segmentos dos sete segmentos do display, 42 bits.
        o_display_hex    : out   std_logic_vector(41 downto 0);
        -- Clock de pixel do vídeo, assíncrono em relação a i_clk.
        i_pixel_clk      : in    std_logic                     := '0';
        -- Canal vermelho da saída VGA (4 bits, como o conversor resistivo da DE0-CV).
        o_vga_r          : out   std_logic_vector(3 downto 0);
        -- Canal verde da saída VGA.
        o_vga_g          : out   std_logic_vector(3 downto 0);
        -- Canal azul da saída VGA.
        o_vga_b          : out   std_logic_vector(3 downto 0);
        -- Sincronismo horizontal da saída VGA.
        o_vga_hs         : out   std_logic;
        -- Sincronismo vertical da saída VGA.
        o_vga_vs         : out   std_logic;
        -- O dispositivo PS/2 do testbench segura a linha de clock em baixo (open-drain, com pull-up no conector).
        i_ps2_dev_clk_low : in   std_logic                     := '0';
        -- O dispositivo PS/2 do testbench segura a linha de dados em baixo.
        i_ps2_dev_dat_low : in   std_logic                     := '0';
        -- Nível resolvido da linha de clock PS/2, como o dispositivo o vê.
        o_ps2_clk        : out   std_logic;
        -- Nível resolvido da linha de dados PS/2, como o dispositivo o vê.
        o_ps2_dat        : out   std_logic
    );
end entity doom_sim_test;

architecture behaviour of doom_sim_test is

    -- Tamanho do chip de SDRAM do modelo, em bytes (13 bits de linha, 2 de banco, 10 de coluna, 16 bits de dados).
    constant CHIP_BYTES : natural := 4 * 2 ** work.sdram_pkg.dram_word_addr_bits(13, 2, 10, 16);
    -- Tamanho da RAM, em bytes, do mapa do platform.yaml.
    constant RAM_BYTES  : natural := (RAM_END_KIB - RAM_BASE_KIB) * 1024;
    -- Tamanho da janela da FLASH, em bytes, do mapa do platform.yaml (da base ao fim da FLASH).
    constant FLASH_BYTES : natural := (FLASH_END_KIB - FLASH_BASE_KIB) * 1024;

    -- Endereço do chip de SDRAM de um endereço da FLASH do SoC: o deslocamento da FLASH no chip mais o endereço na FLASH.
    function flash_chip_addr (a : addr_t) return addr_t is
        -- Base da FLASH no mapa do SoC.
        constant BASE : unsigned(ADDR_BITS - 1 downto 0) := shift_left(to_unsigned(FLASH_BASE_KIB, ADDR_BITS), 10);
    begin

        return std_logic_vector(unsigned(a) - BASE + to_unsigned(flash_chip_offset_bytes, ADDR_BITS));

    end function flash_chip_addr;

    -- Endereço do chip de SDRAM de um endereço da RAM do SoC: o deslocamento da RAM no chip mais o endereço na RAM.
    function ram_chip_addr (a : addr_t) return addr_t is
        -- Base da RAM no mapa do SoC.
        constant BASE : unsigned(ADDR_BITS - 1 downto 0) := shift_left(to_unsigned(RAM_BASE_KIB, ADDR_BITS), 10);
    begin

        return std_logic_vector(unsigned(a) - BASE + to_unsigned(ram_chip_offset_bytes, ADDR_BITS));

    end function ram_chip_addr;

    -- Exceção sinalizada pelo core sem Zicsr (um ciclo em '1'); com Zicsr fica em '0'.
    signal core_trap       : std_logic;
    -- Pulso de retirada de uma instrução em EX, contado pelo testbench para medir os ciclos por instrução.
    signal core_retire     : std_logic;
    -- Causa da exceção sinalizada, no formato do mcause.
    signal core_trap_cause : word_t;
    -- PC da instrução que gerou a exceção sinalizada.
    signal core_trap_pc    : word_t;

    -- Endereço de byte da busca de instrução do núcleo.
    signal if_addr          : addr_t;
    -- Endereço de busca do PC do ciclo seguinte (o_if_addr_nx do núcleo).
    signal if_addr_nx       : addr_t;
    -- Endereço que as memórias de instrução leem: o do ciclo seguinte com early_fetch, ou o PC atual.
    signal if_addr_mem      : addr_t;
    -- Habilita de leitura da busca de instrução.
    signal if_rden          : std_logic;
    -- Palavra lida da BOOT_MEMORY.
    signal boot_memory_data : word_t;
    -- Palavra lida da FLASH pelo estágio IF.
    signal flash_data       : word_t;

    -- Endereço de byte da leitura de dado do estágio MEM na FLASH.
    signal flash_addr2 : addr_t;
    -- Habilita da leitura de dado do estágio MEM na FLASH.
    signal flash_rden2 : std_logic;
    -- Palavra lida da FLASH pelo estágio MEM.
    signal flash_data2 : word_t := (others => '0');

    -- RAM interna do núcleo: endereço.
    signal ram_addr    : addr_t;
    -- RAM interna do núcleo: dado de escrita.
    signal ram_wdata   : word_t;
    -- Dado lido da RAM interna do núcleo; sem RAM interna fica em zero.
    signal ram_rdata   : word_t := (others => '0');   -- sem RAM dentro do FPGA
    -- RAM interna do núcleo: habilita geral.
    signal ram_en      : std_logic;
    -- RAM interna do núcleo: habilita de escrita.
    signal ram_wren    : std_logic;
    -- RAM interna do núcleo: habilita de leitura.
    signal ram_rden    : std_logic;
    -- RAM interna do núcleo: habilita de bytes.
    signal ram_byteena : std_logic_vector(3 downto 0);

    -- Barramento externo do núcleo para a SDRAM: endereço.
    signal sdram_addr    : addr_t;
    -- Barramento externo do núcleo para a SDRAM: dado de escrita.
    signal sdram_wdata   : word_t;
    -- Barramento externo do núcleo para a SDRAM: dado lido.
    signal sdram_rdata   : word_t;
    -- Barramento externo do núcleo para a SDRAM: habilita de bytes.
    signal sdram_byteena : std_logic_vector(3 downto 0);
    -- Barramento externo do núcleo para a SDRAM: habilita de leitura.
    signal sdram_rden    : std_logic;
    -- Barramento externo do núcleo para a SDRAM: habilita de escrita.
    signal sdram_wren    : std_logic;
    -- Barramento externo do núcleo: acesso concluído.
    signal sdram_ready   : std_logic;
    -- O acesso externo do núcleo terminou sem escravo que o atenda (falha de acesso), junto com o ready.
    signal ext_error     : std_logic;
    -- Avanço do pipeline do núcleo quando o acesso à memória conclui.
    signal mem_advance   : std_logic;

    -- Atrás do interconector: endereço de byte da SDRAM e das janelas de periféricos
    signal m_addr         : addr_t;
    -- Saída do interconector para a SDRAM: dado de escrita.
    signal m_wdata        : word_t;
    -- Saída do interconector para a SDRAM: dado lido.
    signal m_rdata        : word_t;
    -- Saída do interconector para a SDRAM: habilita de bytes.
    signal m_byteena      : std_logic_vector(3 downto 0);
    -- Saída do interconector para a SDRAM: habilita de leitura.
    signal m_rden         : std_logic;
    -- Saída do interconector para a SDRAM: habilita de escrita.
    signal m_wren         : std_logic;
    -- Saída do interconector para a SDRAM: acesso concluído.
    signal m_ready        : std_logic;
    -- Janela de periféricos: endereço.
    signal p_addr         : std_logic_vector(PLIC_ADDR_WIDTH - 1 downto 0);
    -- Linhas de interrupção dos periféricos para o PLIC; uma ausente fica em zero.
    signal irq_lines      : std_logic_vector(PLIC_N_SOURCES downto 1) := (others => '0');
    -- Janela de periféricos: dado de escrita.
    signal p_wdata        : word_t;
    -- Janela de periféricos: habilita de bytes.
    signal p_byteena      : std_logic_vector(3 downto 0);
    -- Janela de periféricos: escrita, leitura.
    signal p_we, p_re     : std_logic_vector(PERIPH_COUNT - 1 downto 0);
    -- Janela de periféricos: dado lido.
    signal p_rdata        : std_logic_vector(PERIPH_COUNT * XLEN - 1 downto 0) := (others => '0');
    -- Linha de clock PS/2 do conector, resolvida entre o teclado, o dispositivo do testbench e o pull-up.
    signal ps2_clk        : std_logic;
    -- Linha de dados PS/2 do conector, resolvida entre o teclado, o dispositivo do testbench e o pull-up.
    signal ps2_dat        : std_logic;
    -- As três linhas de interrupção de máquina do núcleo
    signal irq_timer      : std_logic                                 := '0';
    -- Interrupção de software de máquina (MSIP), saída do CLINT.
    signal irq_software   : std_logic                                 := '0';
    -- Interrupção externa de máquina (MEIP), do controlador de interrupções.
    signal irq_external   : std_logic                                 := '0';
    -- As três linhas de interrupção entram no núcleo por um registrador: o árbitro do PLIC e o comparador do mtime do
    -- CLINT
    -- ficam fora do caminho que decide a tomada da interrupção (um ciclo de latência a mais).
    signal irq_timer_q    : std_logic                                 := '0';
    -- Interrupção de software de máquina (MSIP) como o núcleo a recebe.
    signal irq_software_q : std_logic                                 := '0';
    -- Interrupção externa de máquina (MEIP) como o núcleo a recebe.
    signal irq_external_q : std_logic                                 := '0';
    -- mtime do CLINT, que o CSR time do núcleo espelha.
    signal clint_mtime    : std_logic_vector(63 downto 0)             := (others => '0');

    -- Clock do estágio IF, saída 0 do gerador de clock.
    signal pll_clk_if      : std_logic;
    -- Clock dos estágios ID, EX e MEM, saída 1 do gerador de clock.
    signal pll_clk_idexmem : std_logic;
    -- Clock do estágio WB, saída 2 do gerador de clock.
    signal pll_clk_wb      : std_logic;

    -- Contagem de refreshes do controlador da SDRAM, lida pela depuração.
    signal dbg_refreshes : std_logic_vector(31 downto 0);
    -- Inicialização da SDRAM concluída com sucesso.
    signal dbg_init_ok   : std_logic;
    -- Inicialização da SDRAM em andamento.
    signal sdram_init    : std_logic;

    -- Busca de instrucao em SDRAM: cache de instrucoes no clock do IF
    signal ic_data        : word_t;
    -- Cache de instruções: acesso concluído.
    signal ic_ready       : std_logic;
    -- Cache de instruções: seleção de região.
    signal ic_sel         : std_logic;
    -- Cache de instruções: pulso de invalidação.
    signal ic_inval       : std_logic;
    -- Pedido de flush da cache de dados que o FENCE.I do núcleo faz antes de invalidar a cache de instruções.
    signal dc_flush       : std_logic;
    -- Porta de memória da cache de instruções: endereço.
    signal id_addr        : addr_t;
    -- Porta de memória da cache de instruções: habilita de leitura.
    signal id_rden        : std_logic;
    -- Porta de memória da cache de instruções: avanço para a próxima palavra da linha.
    signal id_adv         : std_logic;
    -- Porta de memória da cache de instruções: acesso concluído.
    signal id_ready       : std_logic;
    -- Porta de memória da cache de instruções: dado lido.
    signal id_rdata       : word_t;
    -- Porta de memória da cache de instruções: pedido de linha de cache.
    signal id_line        : std_logic;
    -- Porta de memória da cache de instruções: linha larga lida de 96 bits.
    signal id_rdx         : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Eventos das caches e da FLASH para os contadores do Zihpm: falha da cache de instrucoes, falha da cache de
    -- dados e ciclo de espera do chip de FLASH.
    signal ic_miss        : std_logic;
    -- Falha da cache de dados, evento dos contadores do Zihpm.
    signal dc_miss        : std_logic;
    -- Ciclo de espera do chip de FLASH, evento dos contadores do Zihpm.
    signal flash_busy     : std_logic;
    -- Eventos externos para os contadores do Zihpm: falha da cache de instruções, falha da cache de dados e espera da
    -- FLASH.
    signal hpm_ext_events : std_logic_vector(2 downto 0);

    -- Roteador da cache de instruções: lado da SDRAM (porta de instruções do sdram_system)
    signal si_addr  : addr_t;
    -- Roteador de instruções, lado da SDRAM: dado de escrita.
    signal si_wdata : word_t;
    -- Roteador de instruções, lado da SDRAM: habilita de bytes.
    signal si_be    : std_logic_vector(3 downto 0);
    -- Roteador de instruções, lado da SDRAM: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço
    -- para a próxima palavra da linha, acesso concluído.
    signal si_rden  : std_logic;
    -- Roteador de instruções, lado da SDRAM: habilita de escrita.
    signal si_wren  : std_logic;
    -- Roteador de instruções, lado da SDRAM: pedido de linha de cache.
    signal si_line  : std_logic;
    -- Roteador de instruções, lado da SDRAM: avanço para a próxima palavra da linha.
    signal si_adv   : std_logic;
    -- Roteador de instruções, lado da SDRAM: acesso concluído.
    signal si_ready : std_logic;
    -- Roteador de instruções, lado da SDRAM: linha larga de escrita de 96 bits.
    signal si_wdx   : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Roteador de instruções, lado da SDRAM: dado lido.
    signal si_rdata : word_t;
    -- Roteador de instruções, lado da SDRAM: linha larga lida de 96 bits.
    signal si_rdx   : std_logic_vector(3 * XLEN - 1 downto 0);

    -- Endereço de byte da RAM do SoC levado ao chip de SDRAM, na porta de instruções (execução a partir da RAM).
    signal si_chip_addr : addr_t;
    -- Endereço de byte da RAM do SoC levado ao chip de SDRAM, na porta de dados.
    signal sd_chip_addr : addr_t;
    -- Endereço de byte da FLASH do SoC levado ao chip de SDRAM.
    signal fl_chip_addr : addr_t;
    -- Porta de instruções do chip: endereço (FLASH em identidade ou RAM deslocada).
    signal ins_addr     : addr_t;
    -- Porta de instruções do chip: habilita de leitura.
    signal ins_rden     : std_logic;
    -- Porta de instruções do chip: pedido de linha.
    signal ins_line     : std_logic;
    -- Porta de instruções do chip: avanço para a próxima palavra da linha.
    signal ins_adv      : std_logic;
    -- Porta de instruções do chip: acesso concluído.
    signal ins_rdy      : std_logic;
    -- Porta de instruções do chip: palavra lida.
    signal ins_rdat     : word_t;
    -- Porta de instruções do chip: palavras 1 a 3 da linha lida.
    signal ins_rdx      : std_logic_vector(3 * XLEN - 1 downto 0);

    -- Cache de dados: lado da memória
    signal dc_bypass        : std_logic;
    -- Porta de memória da cache de dados: endereço, dado de escrita, dado lido.
    signal dd_addr          : addr_t;
    -- Porta de memória da cache de dados: dado de escrita.
    signal dd_wdata         : word_t;
    -- Porta de memória da cache de dados: dado lido.
    signal dd_rdata         : word_t;
    -- Porta de memória da cache de dados: habilita de bytes.
    signal dd_be            : std_logic_vector(3 downto 0);
    -- Porta de memória da cache de dados: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço
    -- para
    -- a próxima palavra da linha, acesso concluído.
    signal dd_rden          : std_logic;
    -- Porta de memória da cache de dados: habilita de escrita.
    signal dd_wren          : std_logic;
    -- Porta de memória da cache de dados: pedido de linha de cache.
    signal dd_line          : std_logic;
    -- Porta de memória da cache de dados: avanço para a próxima palavra da linha.
    signal dd_adv           : std_logic;
    -- Porta de memória da cache de dados: acesso concluído.
    signal dd_ready         : std_logic;
    -- Porta de memória da cache de dados: linha larga de escrita de 96 bits, linha larga lida de 96 bits.
    signal dd_wdx,  dd_rdx  : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Cache de dados com a invalidação concluída; Cache de dados ocupada com uma invalidação.
    signal dc_done, dc_busy : std_logic;

    -- Roteador da cache de dados: lado da SDRAM (porta de dados do sdram_system)
    signal sd_addr        : addr_t;
    -- Roteador de dados, lado da SDRAM: dado de escrita.
    signal sd_wdata       : word_t;
    -- Roteador de dados, lado da SDRAM: dado lido.
    signal sd_rdata       : word_t;
    -- Roteador de dados, lado da SDRAM: habilita de bytes.
    signal sd_be          : std_logic_vector(3 downto 0);
    -- Roteador de dados, lado da SDRAM: habilita de leitura, habilita de escrita, pedido de linha de cache, avanço para
    -- a
    -- próxima palavra da linha, acesso concluído.
    signal sd_rden        : std_logic;
    -- Roteador de dados, lado da SDRAM: habilita de escrita.
    signal sd_wren        : std_logic;
    -- Roteador de dados, lado da SDRAM: pedido de linha de cache.
    signal sd_line        : std_logic;
    -- Roteador de dados, lado da SDRAM: avanço para a próxima palavra da linha.
    signal sd_adv         : std_logic;
    -- Roteador de dados, lado da SDRAM: acesso concluído.
    signal sd_ready       : std_logic;
    -- Roteador de dados, lado da SDRAM: linha larga de escrita de 96 bits, linha larga lida de 96 bits.
    signal sd_wdx, sd_rdx : std_logic_vector(3 * XLEN - 1 downto 0);

    -- Lado da FLASH dos dois roteadores, o árbitro e o chip
    signal fa_addr                        : addr_t;
    -- Roteador A, lado da FLASH: dado lido.
    signal fa_rdata                       : word_t;
    -- Roteador B, lado da FLASH: endereço.
    signal fb_addr                        : addr_t;
    -- Roteador B, lado da FLASH: dado lido.
    signal fb_rdata                       : word_t;
    -- Roteador C, lado da FLASH: endereço.
    signal fc_addr                        : addr_t;
    -- Roteador C, lado da FLASH: dado lido.
    signal fc_rdata                       : word_t;
    -- Roteador de instruções, lado da FLASH: habilita de leitura; Roteador de instruções, lado da FLASH: pedido de
    -- linha
    -- de cache; Roteador de instruções, lado da FLASH: avanço para a próxima palavra da linha; Roteador de instruções,
    -- lado da FLASH: acesso concluído; Roteador de dados, lado da FLASH: habilita de leitura; Roteador de dados, lado
    -- da
    -- FLASH: pedido de linha de cache; Roteador de dados, lado da FLASH: avanço para a próxima palavra da linha;
    -- Roteador
    -- de dados, lado da FLASH: acesso concluído.
    signal fa_rden                        : std_logic;
    -- Roteador A, lado da FLASH: pedido de linha de cache.
    signal fa_line                        : std_logic;
    -- Roteador A, lado da FLASH: avanço para a próxima palavra da linha.
    signal fa_adv                         : std_logic;
    -- Roteador A, lado da FLASH: acesso concluído.
    signal fa_ready                       : std_logic;
    -- Roteador B, lado da FLASH: habilita de leitura.
    signal fb_rden                        : std_logic;
    -- Roteador B, lado da FLASH: pedido de linha de cache.
    signal fb_line                        : std_logic;
    -- Roteador B, lado da FLASH: avanço para a próxima palavra da linha.
    signal fb_adv                         : std_logic;
    -- Roteador B, lado da FLASH: acesso concluído.
    signal fb_ready                       : std_logic;
    -- Árbitro, lado do chip de FLASH: habilita de leitura, pedido de linha de cache, avanço para a próxima palavra da
    -- linha, acesso concluído.
    signal fc_rden                        : std_logic;
    -- Roteador C, lado da FLASH: pedido de linha de cache.
    signal fc_line                        : std_logic;
    -- Roteador C, lado da FLASH: avanço para a próxima palavra da linha.
    signal fc_adv                         : std_logic;
    -- Roteador C, lado da FLASH: acesso concluído.
    signal fc_ready                       : std_logic;
    -- Roteador de instruções, lado da FLASH: linha larga lida de 96 bits; Roteador de dados, lado da FLASH: linha larga
    -- lida de 96 bits; Árbitro, lado do chip de FLASH: linha larga lida de 96 bits.
    signal fa_rdx                         : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Roteador B, lado da FLASH: linha larga lida de 96 bits.
    signal fb_rdx                         : std_logic_vector(3 * XLEN - 1 downto 0);
    -- Roteador C, lado da FLASH: linha larga lida de 96 bits.
    signal fc_rdx                         : std_logic_vector(3 * XLEN - 1 downto 0);

begin

    if_addr_mem <= if_addr_nx when early_fetch else if_addr;

    -- A FLASH e a RAM cabem no chip. Elas só não se sobrepõem de verdade nos deslocamentos da placa; um teste com a imagem
    -- pequena aproxima a RAM da FLASH e usa só o começo das duas janelas.
    assert flash_chip_offset_bytes + FLASH_BYTES <= CHIP_BYTES
        report "a FLASH não cabe no chip de SDRAM"
        severity failure;
    assert ram_chip_offset_bytes + RAM_BYTES <= CHIP_BYTES
        report "a RAM não cabe no chip de SDRAM"
        severity failure;

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
            hpm_counters => hpm_counters, hpm_width => hpm_width, time_external => has_interrupts,
            early_addr => early_fetch
        )
        port map (
            o_trap       => core_trap,
            o_retire     => core_retire,
            o_trap_cause => core_trap_cause,
            o_trap_pc    => core_trap_pc,

            i_clk => pll_clk_idexmem,
            i_rst => i_rst,

            o_if_addr          => if_addr,
            o_if_addr_nx       => if_addr_nx,
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
            i_ext_error   => ext_error,
            o_mem_advance => mem_advance,

            i_hpm_ext_events => hpm_ext_events,
            i_irq_software   => irq_software_q,
            i_irq_timer      => irq_timer_q,
            i_mtime          => clint_mtime,
            i_irq_external   => irq_external_q,
            i_ic_data        => ic_data,
            i_ic_ready       => ic_ready,
            o_ic_sel         => ic_sel,
            o_ic_inval       => ic_inval,
            o_dc_flush       => dc_flush,
            i_dc_done        => dc_done
        );

    gen_ic_staggered : if not early_fetch generate
    begin

        u_icache : entity work.icache
            generic map (
                size_bits    => icache_size_bits, flash_base_kib => FLASH_BASE_KIB, flash_end_kib => FLASH_END_KIB,
                sel_from_kib => FLASH_BASE_KIB, check_addr => false
            )
            port map (
                i_clk          => pll_clk_if,
                i_clk_cpu      => pll_clk_idexmem,
                i_rst          => i_rst,
                i_addr         => if_addr_mem,
                i_sel          => ic_sel,
                o_ready        => ic_ready,
                o_data         => ic_data,
                i_invalidate   => ic_inval,
                o_miss         => ic_miss,
                i_inval_region => '0',
                i_inval_first  => (others => '0'),
                i_inval_last   => (others => '0'),
                o_d_addr       => id_addr,
                o_d_rden       => id_rden,
                o_d_advance    => id_adv,
                i_d_ready      => id_ready,
                i_d_rdata      => id_rdata,
                o_d_line       => id_line,
                i_d_rdata_x    => id_rdx
            );

    end generate gen_ic_staggered;

    gen_ic_aligned : if early_fetch generate
    begin

        u_icache_early : entity work.icache
            generic map (
                size_bits    => icache_size_bits, flash_base_kib => FLASH_BASE_KIB, flash_end_kib => FLASH_END_KIB,
                sel_from_kib => FLASH_BASE_KIB, check_addr => false
            )
            port map (
                i_clk          => pll_clk_idexmem,
                i_clk_cpu      => pll_clk_idexmem,
                i_rst          => i_rst,
                i_addr         => if_addr_mem,
                i_sel          => ic_sel,
                o_ready        => ic_ready,
                o_data         => ic_data,
                i_invalidate   => ic_inval,
                o_miss         => ic_miss,
                i_inval_region => '0',
                i_inval_first  => (others => '0'),
                i_inval_last   => (others => '0'),
                o_d_addr       => id_addr,
                o_d_rden       => id_rden,
                o_d_advance    => id_adv,
                i_d_ready      => id_ready,
                i_d_rdata      => id_rdata,
                o_d_line       => id_line,
                i_d_rdata_x    => id_rdx
            );

    end generate gen_ic_aligned;

    u_router_i : entity work.mem_region_router
        generic map (
            flash_window_kib => FLASH_END_KIB
        )
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => i_rst,
            i_addr      => id_addr,
            i_wdata     => (others => '0'),
            i_byteena   => (others => '0'),
            i_rden      => id_rden,
            i_wren      => '0',
            i_line      => id_line,
            i_advance   => id_adv,
            o_ready     => id_ready,
            o_rdata     => id_rdata,
            o_rdata_x   => id_rdx,
            o_s_addr    => si_addr,
            o_s_wdata   => si_wdata,
            o_s_byteena => si_be,
            o_s_rden    => si_rden,
            o_s_wren    => si_wren,
            o_s_line    => si_line,
            o_s_wdata_x => si_wdx,
            o_s_advance => si_adv,
            i_s_ready   => si_ready,
            i_s_rdata   => si_rdata,
            i_s_rdata_x => si_rdx,
            o_f_addr    => fa_addr,
            o_f_rden    => fa_rden,
            o_f_line    => fa_line,
            o_f_advance => fa_adv,
            i_f_ready   => fa_ready,
            i_f_rdata   => fa_rdata,
            i_f_rdata_x => fa_rdx
        );

    -- Os últimos 4 KB da SDRAM guardam as palavras que o hospedeiro compartilha com o programa (tohost, fromhost,
    -- stdout): o hospedeiro as escreve atrás da cache, então nunca ficam guardadas nela
    dc_bypass <= '1' when m_addr(31 downto 12) = RAM_LAST_PAGE else '0';

    u_dcache : entity work.dcache
        generic map (
            size_bits   => dcache_size_bits, write_through => true, flash_base_kib => FLASH_BASE_KIB,
            flash_end_kib => FLASH_END_KIB
        )
        port map (
            i_clk          => pll_clk_idexmem,
            i_rst          => i_rst,
            i_addr         => m_addr,
            i_wdata        => m_wdata,
            i_byteena      => m_byteena,
            i_rden         => m_rden,
            i_wren         => m_wren,
            i_mem_advance  => mem_advance,
            o_ready        => m_ready,
            o_rdata        => m_rdata,
            i_flush        => dc_flush,
            i_invalidate   => '1',
            o_flush_done   => dc_done,
            o_busy         => dc_busy,
            o_miss         => dc_miss,
            i_inval_region => '0',
            i_inval_first  => (others => '0'),
            i_inval_last   => (others => '0'),
            i_bypass       => dc_bypass,
            o_d_addr       => dd_addr,
            o_d_wdata      => dd_wdata,
            o_d_byteena    => dd_be,
            o_d_rden       => dd_rden,
            o_d_wren       => dd_wren,
            o_d_advance    => dd_adv,
            i_d_ready      => dd_ready,
            i_d_rdata      => dd_rdata,
            o_d_line       => dd_line,
            o_d_wdata_x    => dd_wdx,
            i_d_rdata_x    => dd_rdx
        );

    u_router_d : entity work.mem_region_router
        generic map (
            flash_window_kib => FLASH_END_KIB
        )
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => i_rst,
            i_addr      => dd_addr,
            i_wdata     => dd_wdata,
            i_byteena   => dd_be,
            i_rden      => dd_rden,
            i_wren      => dd_wren,
            i_line      => dd_line,
            i_wdata_x   => dd_wdx,
            i_advance   => dd_adv,
            o_ready     => dd_ready,
            o_rdata     => dd_rdata,
            o_rdata_x   => dd_rdx,
            o_s_addr    => sd_addr,
            o_s_wdata   => sd_wdata,
            o_s_byteena => sd_be,
            o_s_rden    => sd_rden,
            o_s_wren    => sd_wren,
            o_s_line    => sd_line,
            o_s_wdata_x => sd_wdx,
            o_s_advance => sd_adv,
            i_s_ready   => sd_ready,
            i_s_rdata   => sd_rdata,
            i_s_rdata_x => sd_rdx,
            o_f_addr    => fb_addr,
            o_f_rden    => fb_rden,
            o_f_line    => fb_line,
            o_f_advance => fb_adv,
            i_f_ready   => fb_ready,
            i_f_rdata   => fb_rdata,
            i_f_rdata_x => fb_rdx
        );

    -- Espera da FLASH para o Zihpm: um pedido da face FLASH ainda sem resposta da SDRAM.
    flash_busy     <= fc_rden and not fc_ready;
    hpm_ext_events <= flash_busy & dc_miss & ic_miss;

    -- Os endereços do núcleo para o chip: a RAM começa em ram_chip_offset_bytes dentro dele, e a FLASH em
    -- flash_chip_offset_bytes.
    sd_chip_addr <= ram_chip_addr(sd_addr);
    si_chip_addr <= ram_chip_addr(si_addr);
    fl_chip_addr <= flash_chip_addr(fc_addr);

    u_flash_arbiter : entity work.flash_arbiter
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => i_rst,
            i_a_addr    => fa_addr,
            i_a_rden    => fa_rden,
            i_a_line    => fa_line,
            i_a_advance => fa_adv,
            o_a_ready   => fa_ready,
            o_a_rdata   => fa_rdata,
            o_a_rdata_x => fa_rdx,
            i_b_addr    => fb_addr,
            i_b_rden    => fb_rden,
            i_b_line    => fb_line,
            i_b_advance => fb_adv,
            o_b_ready   => fb_ready,
            o_b_rdata   => fb_rdata,
            o_b_rdata_x => fb_rdx,
            o_addr      => fc_addr,
            o_rden      => fc_rden,
            o_line      => fc_line,
            o_advance   => fc_adv,
            i_ready     => fc_ready,
            i_rdata     => fc_rdata,
            i_rdata_x   => fc_rdx
        );

    -- A face da FLASH (busca e leitura de dados) e a da RAM (busca de código que roda da RAM) dividem a porta de
    -- instruções do chip.

    u_ins_arbiter : entity work.flash_arbiter
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => i_rst,
            i_a_addr    => fl_chip_addr,
            i_a_rden    => fc_rden,
            i_a_line    => fc_line,
            i_a_advance => fc_adv,
            o_a_ready   => fc_ready,
            o_a_rdata   => fc_rdata,
            o_a_rdata_x => fc_rdx,
            i_b_addr    => si_chip_addr,
            i_b_rden    => si_rden,
            i_b_line    => si_line,
            i_b_advance => si_adv,
            o_b_ready   => si_ready,
            o_b_rdata   => si_rdata,
            o_b_rdata_x => si_rdx,
            o_addr      => ins_addr,
            o_rden      => ins_rden,
            o_line      => ins_line,
            o_advance   => ins_adv,
            i_ready     => ins_rdy,
            i_rdata     => ins_rdat,
            i_rdata_x   => ins_rdx
        );

    u_interconnect : entity work.ext_interconnect
        generic map (
            periph_count      => PERIPH_COUNT,
            periph_bases      => addr_array_t(PERIPH_BASES),
            periph_masks      => addr_array_t(PERIPH_MASKS),
            periph_sizes      => window_sizes(addr_array_t(PERIPH_MASKS)),
            strict_periph     => STRICT_PERIPH,
            periph_addr_width => PLIC_ADDR_WIDTH,
            flash_on_bus      => FLASH_ON_BUS,
            flash_base        => addr_from(to_unsigned(FLASH_BASE_KIB, ADDR_BITS) sll 10),
            flash_last        => addr_from((to_unsigned(FLASH_END_KIB, ADDR_BITS) sll 10) - 1),
            ram_on_bus        => RAM_ON_BUS,
            ram_base          => addr_from(to_unsigned(RAM_BASE_KIB, ADDR_BITS) sll 10),
            ram_last          => addr_from((to_unsigned(RAM_END_KIB, ADDR_BITS) sll 10) - 1)
        )
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
            o_error       => ext_error,
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
            i_rst       => i_rst,
            i_addr      => p_addr(7 downto 0),
            i_wdata     => p_wdata,
            i_we        => p_we(UART_INDEX),
            i_re        => p_re(UART_INDEX),
            o_rdata     => p_rdata(XLEN * UART_INDEX + XLEN - 1 downto XLEN * UART_INDEX),
            o_irq       => irq_lines(IRQ_UART_JTAG),
            i_tck       => i_uart_tck,
            i_tdi       => i_uart_tdi,
            o_tdo       => o_uart_tdo,
            i_ir_in     => i_uart_ir_in,
            i_state_cdr => i_uart_state_cdr,
            i_state_sdr => i_uart_state_sdr,
            i_state_udr => i_uart_state_udr,
            i_state_uir => i_uart_state_uir
        );

    -- O CLINT (msip, mtimecmp, mtime) e o PLIC (o controlador das linhas de interrupção externas), no domínio de
    -- clock do núcleo: as saídas deles são o MSIP, o MTIP e o MEIP do núcleo, sem sincronizador. A UART JTAG
    -- levanta a sua linha (IRQ_UART_JTAG); as outras ficam em zero.

    g_irq : if has_interrupts generate

        process (pll_clk_idexmem) is
        begin

            if rising_edge(pll_clk_idexmem) then
                irq_timer_q    <= irq_timer;
                irq_software_q <= irq_software;
                irq_external_q <= irq_external;
            end if;

        end process;

        u_clint : entity work.clint
            generic map (
                tick_cycles => clint_tick_cycles
            )
            port map (
                i_clk          => pll_clk_idexmem,
                i_rst          => i_rst,
                i_data_in      => p_wdata,
                i_address      => p_addr(13 downto 0),
                i_write        => p_we(CLINT_INDEX),
                o_data_out     => p_rdata(XLEN * CLINT_INDEX + XLEN - 1 downto XLEN * CLINT_INDEX),
                o_irq_timer    => irq_timer,
                o_irq_software => irq_software,
                o_mtime        => clint_mtime
            );

        u_plic : entity work.plic
            generic map (
                n_sources => PLIC_N_SOURCES, priority_bits => PLIC_PRIORITY_BITS, addr_width => PLIC_ADDR_WIDTH
            )
            port map (
                i_clk      => pll_clk_idexmem,
                i_rst      => i_rst,
                i_sources  => irq_lines,
                i_data_in  => p_wdata,
                i_address  => p_addr,
                i_write    => p_we(PLIC_INDEX),
                i_read     => p_re(PLIC_INDEX),
                o_data_out => p_rdata(XLEN * PLIC_INDEX + XLEN - 1 downto XLEN * PLIC_INDEX),
                o_meip     => irq_external
            );

    end generate g_irq;

    u_display : entity work.seg_display
        port map (
            i_clk       => pll_clk_idexmem,
            i_rst       => i_rst,
            i_address   => p_addr(7 downto 0),
            i_data_in   => p_wdata,
            i_write     => p_we(DISPLAY_INDEX),
            o_rdata     => p_rdata(XLEN * DISPLAY_INDEX + XLEN - 1 downto XLEN * DISPLAY_INDEX),
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

    -- O vídeo VGA indexado (256 KiB de janela: registradores, paleta e framebuffer) com a geometria e o modo do
    -- topo gerado da placa; o clock de pixel é assíncrono em relação ao do núcleo.
    u_video : entity work.video
        generic map (
            fb_width        => video_fb_width,
            fb_height       => video_fb_height,
            channel_bits    => 4,
            pixel_format    => "indexed",
            scale           => video_scale,
            h_visible       => video_h_visible,
            h_front_porch   => video_h_front_porch,
            h_sync          => video_h_sync,
            h_back_porch    => video_h_back_porch,
            h_sync_positive => false,
            v_visible       => video_v_visible,
            v_front_porch   => video_v_front_porch,
            v_sync          => video_v_sync,
            v_back_porch    => video_v_back_porch,
            v_sync_positive => false
        )
        port map (
            i_clk         => pll_clk_idexmem,
            i_pixel_clk   => i_pixel_clk,
            i_rst         => i_rst,
            i_data_in     => p_wdata,
            i_address     => p_addr(15 downto 0),
            i_byteena     => p_byteena,
            i_write       => p_we(VIDEO_INDEX),
            o_data_out    => p_rdata(XLEN * VIDEO_INDEX + XLEN - 1 downto XLEN * VIDEO_INDEX),
            o_vga_r       => o_vga_r,
            o_vga_g       => o_vga_g,
            o_vga_b       => o_vga_b,
            o_vga_hs      => o_vga_hs,
            o_vga_vs      => o_vga_vs,
            o_vga_blank_n => open,
            o_vga_sync_n  => open
        );

    -- O teclado PS/2 no canal 0 do conector, com a interrupção na linha do PLIC. As linhas são open-drain com pull-up
    -- no conector ('H'), e o dispositivo do testbench as segura em baixo.
    ps2_clk <= '0' when i_ps2_dev_clk_low = '1' else 'Z';
    ps2_dat <= '0' when i_ps2_dev_dat_low = '1' else 'Z';
    ps2_clk <= 'H';
    ps2_dat <= 'H';
    o_ps2_clk <= to_x01(ps2_clk);
    o_ps2_dat <= to_x01(ps2_dat);

    u_keyboard : entity work.ps2_keyboard
        generic map (
            filter_cycles  => kbd_filter_cycles,
            timeout_cycles => kbd_timeout_cycles
        )
        port map (
            i_clk      => pll_clk_idexmem,
            i_rst      => i_rst,
            i_data_in  => p_wdata,
            i_address  => p_addr(1 downto 0),
            i_write    => p_we(KBD_INDEX),
            i_read     => p_re(KBD_INDEX),
            o_data_out => p_rdata(XLEN * KBD_INDEX + XLEN - 1 downto XLEN * KBD_INDEX),
            o_irq      => irq_lines(IRQ_KBD),
            io_ps2_clk => ps2_clk,
            io_ps2_dat => ps2_dat
        );

    -- A SDRAM e o seu modelo de chip; as portas de depuração do modelo ficam sem uso aqui
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
            i_rst_cpu       => i_rst,
            i_addr          => sd_chip_addr,
            i_wdata         => sd_wdata,
            i_byteena       => sd_be,
            i_rden          => sd_rden,
            i_wren          => sd_wren,
            i_mem_advance   => sd_adv,
            o_ready         => sd_ready,
            o_rdata         => sd_rdata,
            i_line          => sd_line,
            i_wdata_x       => sd_wdx,
            o_rdata_x       => sd_rdx,
            i_ins_addr      => ins_addr,
            i_ins_rden      => ins_rden,
            i_ins_advance   => ins_adv,
            o_ins_ready     => ins_rdy,
            o_ins_rdata     => ins_rdat,
            i_ins_line      => ins_line,
            o_ins_rdata_x   => ins_rdx,
            o_init_done     => sdram_init,
            i_dbg_word_addr => i_dbg_word_addr,
            o_dbg_word_data => o_dbg_word_data,
            i_dbg_flip      => '0',
            i_dbg_flip_addr => (others => '0'),
            i_dbg_flip_bit  => (others => '0'),
            o_dbg_refreshes => dbg_refreshes,
            o_dbg_init_ok   => dbg_init_ok
        );

    gen_boot_staggered : if not early_fetch generate
    begin

        u_boot_memory : entity work.rom_simulation
            generic map (
                rom_file => boot_memory_file, size_bytes => 4 * 2 ** boot_memory_addr_width
            )
            port map (
                i_addr => if_addr_mem(31 downto 2),
                i_clk  => pll_clk_if,
                i_re   => if_rden,
                o_data => boot_memory_data
            );

    end generate gen_boot_staggered;

    gen_boot_aligned : if early_fetch generate
    begin

        u_boot_memory_early : entity work.rom_simulation
            generic map (
                rom_file => boot_memory_file, size_bytes => 4 * 2 ** boot_memory_addr_width
            )
            port map (
                i_addr => if_addr_mem(31 downto 2),
                i_clk  => pll_clk_idexmem,
                i_re   => if_rden,
                o_data => boot_memory_data
            );

    end generate gen_boot_aligned;

end architecture behaviour;
