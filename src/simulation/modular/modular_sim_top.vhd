-- =============================================================================
-- Topo de simulação modular: as memórias e as caches do núcleo em qualquer combinação
--
-- O topo só conecta. O SoC (a entidade soc: núcleo, caches, interconector, CLINT, PLIC e periféricos)
-- fica independente de placa e de modelo de chip, e este topo lhe acrescenta o gerador de relógio e
-- os modelos de simulação dos backends de memória:
--
--   | Região        | Modelo de simulação neste topo                              |
--   | BOOT_MEMORY   | rom_simulation                                              |
--   | ROM interna   | rom_simulation de duas portas                               |
--   | ROM externa   | flash_chip sobre um rom_simulation de armazenamento         |
--   | RAM interna   | ram_simulation                                              |
--   | RAM externa   | ram_chip                                                    |
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
-- O mapa vem dos genéricos, cujo valor padrão é o do pacote modular_map_pkg, gerado do platform.yaml da
-- plataforma: a BOOT_MEMORY em [0, tamanho), a ROM logo depois dela até rom_end_kib, a RAM em
-- [ram_base_kib, ram_end_kib) e a janela externa a partir de ext_base_kib. O que o projeto escolhe fica
-- no platform.yaml da plataforma.
--
-- Todos os tamanhos são genéricos em potência de dois (bytes para as memórias, bits para as
-- caches). Os valores padrão são os da simulação do ACT4: ROM e RAM de 1 MB e caches de 4 kbit.
--
-- Os papéis de E/S têm a largura por generic: switches_width, keys_width e display_digits (zero omite o
-- papel). A polaridade dos pinos é resolvida aqui, por generic: o SoC e os periféricos veem o programa
-- ativo em '1'.
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
        boot_memory_file       : string                   := "default.hex";
        -- Imagem da ROM, a partir do seu início (interna, ou o armazenamento do chip de FLASH externo).
        rom_file               : string                   := "default.hex";
        -- Imagem inicial da RAM (interna, ou o chip de RAM externo); vazio deixa tudo em zero.
        ram_file               : string                   := "";
        -- A ROM é externa (um chip fora do núcleo, alcançado pela porta).
        rom_external           : boolean                  := ROM_EXTERNAL;
        -- A RAM é externa (um chip fora do núcleo, alcançado pela porta).
        ram_external           : boolean                  := RAM_EXTERNAL;
        -- Tamanho da BOOT_MEMORY em bytes, uma potência de dois de pelo menos 1 KiB.
        boot_memory_size_bytes : positive                 := BOOT_MEMORY_SIZE_BYTES;
        -- Tamanho do armazenamento da ROM em bytes, uma potência de dois.
        rom_size_bytes         : positive                 := ROM_STORAGE_BYTES;
        -- Tamanho da RAM em bytes, uma potência de dois.
        ram_size_bytes         : positive                 := RAM_STORAGE_BYTES;
        -- Fim exclusivo, em KiB, da ROM, que começa logo depois da BOOT_MEMORY.
        rom_end_kib            : natural                  := ROM_END_KIB;
        -- Base, em KiB, da RAM.
        ram_base_kib           : natural                  := RAM_BASE_KIB;
        -- Fim exclusivo, em KiB, da RAM.
        ram_end_kib            : natural                  := RAM_END_KIB;
        -- Base, em KiB, da janela externa de periféricos e outros dispositivos.
        ext_base_kib           : natural                  := EXT_BASE_KIB;
        -- Base, em KiB, da janela de periféricos.
        periph_base_kib        : natural                  := PERIPH_BASE_KIB;
        -- Existe cache de instruções; sem ela, a ROM via porta é lida pela ponte de busca. Por padrão, a
        -- cache existe quando a ROM é externa ou o pacote a liga.
        has_icache             : boolean                  := rom_external or HAS_ICACHE;
        -- Existe cache de dados; sem ela, a RAM via porta é acessada direto, palavra a palavra. Por
        -- padrão, a cache existe quando a RAM é externa ou o pacote a liga.
        has_dcache             : boolean                  := ram_external or HAS_DCACHE;
        -- Tamanho da cache de instruções em bits, uma potência de dois (4096 é 4 kbit).
        icache_size_bits       : positive                 := 4096;
        -- Tamanho da cache de dados em bits, uma potência de dois (4096 é 4 kbit).
        dcache_size_bits       : positive                 := 4096;
        -- Largura da janela de endereços das caches, em bits: a tag guarda os bits abaixo dela (26 é 64 MiB, 27 é 128
        -- MiB).
        cache_window_bits      : natural range 26 to 29   := 26;
        -- Bordas até a primeira palavra do chip de FLASH e entre as palavras de uma linha.
        flash_first_latency    : natural                  := 24;
        -- Bordas entre as palavras seguintes da mesma linha do chip de FLASH.
        flash_next_latency     : natural                  := 4;
        -- Bordas entre o pedido e a conclusão de um acesso ao chip de RAM externo.
        ext_ram_latency        : natural                  := 8;
        -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os índices a partir de 3.
        hpm_counters           : natural range 0 to 29    := 29;
        -- Largura, em bits, de cada contador de eventos do Zihpm.
        hpm_width              : natural range 0 to 64    := 64;
        -- Ciclos de clock do núcleo por incremento do mtime do CLINT.
        clint_tick_cycles      : positive                 := 1;
        -- Índice da janela de 256 MiB do CLINT (bits 30:28 do endereço); o do platform.yaml.
        clint_id               : natural range 0 to 7     := 6;
        -- Índice da janela de 256 MiB do PLIC, o controlador das interrupções externas.
        plic_id                : natural range 0 to 7     := 7;
        -- Número de fontes do PLIC; as linhas são as LINE_* abaixo, a partir da 1.
        plic_n_sources         : positive range 6 to 1023 := 6;
        -- Largura da prioridade e do limiar do PLIC, em bits.
        plic_priority_bits     : positive range 1 to 32   := 3;
        -- Largura do endereço de palavra da janela do PLIC (a janela tem 2**(plic_addr_width + 2) bytes).
        plic_addr_width        : positive range 20 to 26  := 20;
        -- Temporizador de uso geral, com a interrupção de overflow ligada ao PLIC.
        has_timer              : boolean                  := false;
        -- Índice da janela do temporizador.
        timer_id               : natural range 0 to 7     := 0;
        -- Chaves SW da placa, num bloco GPIO (plataformas da FPGA).
        has_switches           : boolean                  := false;
        -- Índice da janela das chaves.
        switches_id            : natural range 0 to 7     := 1;
        -- Número de chaves; zero omite o papel.
        switches_width         : natural range 0 to 32    := 10;
        -- Chaves ativas em nível baixo no pino.
        switches_active_low    : boolean                  := false;
        -- Botões KEY da placa, num bloco GPIO (plataformas da FPGA).
        has_keys               : boolean                  := false;
        -- Índice da janela dos botões.
        keys_id                : natural range 0 to 7     := 2;
        -- Número de botões; zero omite o papel.
        keys_width             : natural range 0 to 32    := 4;
        -- Botões ativos em nível baixo no pino.
        keys_active_low        : boolean                  := false;
        -- Displays de 7 segmentos (plataformas da FPGA).
        has_display            : boolean                  := false;
        -- Índice da janela do display.
        display_id             : natural range 0 to 7     := 5;
        -- Número de dígitos do display; zero omite o papel.
        display_digits         : natural range 0 to 8     := 6;
        -- Segmentos acesos em nível baixo no pino.
        display_active_low     : boolean                  := true;
        -- UART cuja outra ponta é o hospedeiro no JTAG.
        has_uart_jtag          : boolean                  := false;
        -- Índice da janela da UART via JTAG.
        uart_jtag_id           : natural range 0 to 7     := 4;
        -- UART cuja outra ponta são dois pinos (TX e RX) da placa.
        has_uart_pins          : boolean                  := false;
        -- Índice da janela da UART via pinos.
        uart_pins_id           : natural range 0 to 7     := 3;
        -- Polaridade do pino de transmissão do console em pinos.
        uart_tx_invert         : boolean                  := false;
        -- Polaridade do pino de recepção do console em pinos.
        uart_rx_invert         : boolean                  := false
    );
    port (
        -- Clock base; um gerador o divide por três para os estágios do núcleo.
        i_clk            : in    std_logic;
        -- Reset, ativo em '1'.
        i_rst            : in    std_logic                     := '0';
        -- Índice da palavra do chip de RAM externo que a porta de depuração lê.
        i_dbg_word_addr  : in    std_logic_vector(23 downto 0) := (others => '0');
        -- Palavra do chip de RAM externo no índice de i_dbg_word_addr.
        o_dbg_word_data  : out   std_logic_vector(31 downto 0);
        -- Habilita geral da RAM interna do núcleo (estágio MEM).
        o_ram_en         : out   std_logic;
        -- Habilita de escrita da RAM interna do núcleo.
        o_ram_wren       : out   std_logic;
        -- Endereço de byte do acesso à RAM interna do núcleo.
        o_ram_addr       : out   std_logic_vector(31 downto 0);
        -- Dado de escrita da RAM interna do núcleo.
        o_ram_wdata      : out   std_logic_vector(31 downto 0);
        -- Habilita de bytes da escrita na RAM interna do núcleo.
        o_ram_byteena    : out   std_logic_vector(3 downto 0);
        -- Chaves SW (pinos do GPIO); o testbench as conduz.
        io_sw            : inout std_logic_vector(switches_width - 1 downto 0);
        -- Botões KEY (pinos do GPIO); o testbench os conduz.
        io_key           : inout std_logic_vector(keys_width - 1 downto 0);
        -- Segmentos dos displays, o dígito 0 nos bits 6:0 (polaridade de display_active_low).
        o_display_hex    : out   std_logic_vector(7 * display_digits - 1 downto 0);
        -- Valor do registrador do display, quatro bits por dígito.
        o_display_value  : out   std_logic_vector(4 * display_digits - 1 downto 0);
        -- Virtual JTAG da UART via JTAG: clock da cadeia.
        i_uart_tck       : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: dado vindo do hospedeiro.
        i_uart_tdi       : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: dado para o hospedeiro.
        o_uart_tdo       : out   std_logic;
        -- Virtual JTAG da UART via JTAG: registrador de instrução.
        i_uart_ir_in     : in    std_logic_vector(1 downto 0)  := "00";
        -- Virtual JTAG da UART via JTAG: estado Capture-DR.
        i_uart_state_cdr : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: estado Shift-DR.
        i_uart_state_sdr : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: estado Update-DR.
        i_uart_state_udr : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: estado Update-IR.
        i_uart_state_uir : in    std_logic                     := '0';
        -- Linha serial de recepção da UART via pinos.
        i_uart_rx        : in    std_logic                     := '1';
        -- Linha serial de transmissão da UART via pinos.
        o_uart_tx        : out   std_logic
    );
end entity modular_sim_top;

architecture behaviour of modular_sim_top is

    -- A ROM é alcançada pela porta do núcleo: está fora do chip ou atrás da cache de instruções.
    constant ROM_PORT : boolean := rom_external or has_icache;
    -- A RAM é alcançada pela porta do núcleo: está fora do chip ou atrás da cache de dados.
    constant RAM_PORT : boolean := ram_external or has_dcache;

    -- Clock da busca de instrução, primeira fase do gerador de clock.
    signal pll_clk_if      : std_logic;
    -- Clock dos estágios ID, EX e MEM, segunda fase do gerador de clock.
    signal pll_clk_idexmem : std_logic;
    -- Clock do estágio de escrita (WB), terceira fase do gerador de clock, que o SoC não usa.
    signal pll_clk_wb      : std_logic;

    -- Busca de instrução: endereço de palavra e habilitação, para a BOOT_MEMORY e a FLASH interna.
    signal if_addr          : std_logic_vector(29 downto 0);
    -- Habilitação de leitura da busca de instrução ('1' = lê).
    signal if_rden          : std_logic;
    -- Palavra de instrução lida da BOOT_MEMORY.
    signal boot_memory_data : std_logic_vector(31 downto 0);
    -- Palavra de instrução lida da FLASH interna.
    signal flash_data       : std_logic_vector(31 downto 0) := (others => '0');
    -- Endereço de palavra da segunda porta da FLASH interna (estágio MEM).
    signal flash_addr2      : std_logic_vector(29 downto 0);
    -- Habilitação de leitura da segunda porta da FLASH interna ('1' = lê).
    signal flash_rden2      : std_logic;
    -- Palavra de dado lida da segunda porta da FLASH interna (estágio MEM).
    signal flash_data2      : std_logic_vector(31 downto 0) := (others => '0');

    -- RAM interna do núcleo.
    signal ram_addr     : std_logic_vector(31 downto 0);
    -- Dado de escrita na RAM do núcleo.
    signal ram_wdata    : std_logic_vector(31 downto 0);
    -- Dado lido da RAM entregue ao núcleo.
    signal ram_rdata    : std_logic_vector(31 downto 0) := (others => '0');
    -- Habilitação geral da RAM do núcleo (estágio MEM).
    signal ram_en       : std_logic;
    -- Habilitação de escrita da RAM do núcleo ('1' = escreve).
    signal ram_wren     : std_logic;
    -- Habilitação de leitura da RAM do núcleo ('1' = lê).
    signal ram_rden     : std_logic;
    -- Habilitação de bytes da escrita na RAM do núcleo.
    signal ram_byteena  : std_logic_vector(3 downto 0);
    -- Leitura da RAM habilitada pelo núcleo e pelo enable geral ('1' = lê).
    signal ram_re_gated : std_logic;
    -- Escrita na RAM habilitada pelo núcleo e pelo enable geral ('1' = escreve).
    signal ram_we_gated : std_logic;

    -- Chip de FLASH: endereço de byte do acesso.
    signal fc_addr                        : std_logic_vector(31 downto 0);
    -- Chip de FLASH: habilitação de leitura ('1' = lê).
    signal fc_rden                        : std_logic;
    -- Chip de FLASH: pedido de linha inteira de cache ('1' = acesso em linha).
    signal fc_line                        : std_logic;
    -- Chip de FLASH: avanço para a próxima palavra da linha ('1' = avança).
    signal fc_adv                         : std_logic;
    -- Chip de FLASH: acesso concluído ('1' = pronto).
    signal fc_ready                       : std_logic                     := '0';
    -- Chip de FLASH: ocupado com um acesso ('1' = ocupado).
    signal fc_busy                        : std_logic                     := '0';
    -- Chip de FLASH: palavra lida.
    signal fc_rdata                       : std_logic_vector(31 downto 0) := (others => '0');
    -- Chip de FLASH: linha lida, barramento largo de 96 bits.
    signal fc_rdx                         : std_logic_vector(95 downto 0) := (others => '0');
    -- Endereço de byte e dado lido do armazenamento do chip de FLASH.
    signal flash_mem_addr, flash_mem_data : std_logic_vector(31 downto 0);

    -- Chip de RAM, porta de dados: endereço de byte do acesso.
    signal rc_d_addr  : std_logic_vector(31 downto 0);
    -- Chip de RAM, porta de dados: dado de escrita.
    signal rc_d_wdata : std_logic_vector(31 downto 0);
    -- Chip de RAM, porta de dados: habilitação de bytes da escrita.
    signal rc_d_be    : std_logic_vector(3 downto 0);
    -- Chip de RAM, porta de dados: habilitação de leitura ('1' = lê).
    signal rc_d_rden  : std_logic;
    -- Chip de RAM, porta de dados: habilitação de escrita ('1' = escreve).
    signal rc_d_wren  : std_logic;
    -- Chip de RAM, porta de dados: pedido de linha inteira de cache ('1' = acesso em linha).
    signal rc_d_line  : std_logic;
    -- Chip de RAM, porta de dados: avanço para a próxima palavra da linha ('1' = avança).
    signal rc_d_adv   : std_logic;
    -- Chip de RAM, porta de dados: linha a escrever, barramento largo de 96 bits.
    signal rc_d_wdx   : std_logic_vector(95 downto 0);
    -- Chip de RAM, porta de dados: acesso concluído ('1' = pronto).
    signal rc_d_ready : std_logic                     := '0';
    -- Chip de RAM, porta de dados: palavra lida.
    signal rc_d_rdata : std_logic_vector(31 downto 0) := (others => '0');
    -- Chip de RAM, porta de dados: linha lida, barramento largo de 96 bits.
    signal rc_d_rdx   : std_logic_vector(95 downto 0) := (others => '0');
    -- Chip de RAM, porta de instruções: endereço de byte do acesso.
    signal rc_i_addr  : std_logic_vector(31 downto 0);
    -- Chip de RAM, porta de instruções: habilitação de leitura ('1' = lê).
    signal rc_i_rden  : std_logic;
    -- Chip de RAM, porta de instruções: pedido de linha inteira de cache ('1' = acesso em linha).
    signal rc_i_line  : std_logic;
    -- Chip de RAM, porta de instruções: avanço para a próxima palavra da linha ('1' = avança).
    signal rc_i_adv   : std_logic;
    -- Chip de RAM, porta de instruções: acesso concluído ('1' = pronto).
    signal rc_i_ready : std_logic                     := '0';
    -- Chip de RAM, porta de instruções: palavra lida.
    signal rc_i_rdata : std_logic_vector(31 downto 0) := (others => '0');
    -- Chip de RAM, porta de instruções: linha lida, barramento largo de 96 bits.
    signal rc_i_rdx   : std_logic_vector(95 downto 0) := (others => '0');

begin

    -- O SoC lê a cache de dados do config_pkg; a que este topo supõe (RAM_PORT, o modelo do chip) tem de ser a mesma.
    assert has_dcache = work.config_pkg.HAS_DCACHE
        report "has_dcache difere de HAS_DCACHE do config_pkg"
        severity failure;

    ram_re_gated <= ram_rden and ram_en;
    ram_we_gated <= ram_wren and ram_en;

    u_pll : entity work.clk_gen_3way
        port map (
            i_clk  => i_clk,
            i_rst  => i_rst,
            o_clk0 => pll_clk_if,
            o_clk1 => pll_clk_idexmem,
            o_clk2 => pll_clk_wb
        );

    u_soc : entity work.soc
        generic map (
            boot_memory_size_bytes => boot_memory_size_bytes,
            rom_end_kib            => rom_end_kib,
            ram_base_kib           => ram_base_kib,
            ram_end_kib            => ram_end_kib,
            ext_base_kib           => ext_base_kib,
            periph_base_kib        => periph_base_kib,
            rom_external           => rom_external,
            ram_external           => ram_external,
            has_icache             => has_icache,
            icache_size_bits       => icache_size_bits,
            dcache_size_bits       => dcache_size_bits,
            cache_window_bits      => cache_window_bits,
            hpm_counters           => hpm_counters,
            hpm_width              => hpm_width,
            periph_slots          => PERIPH_SLOTS,
            clint_tick_cycles      => clint_tick_cycles,
            clint_id               => clint_id,
            plic_id                => plic_id,
            plic_n_sources         => plic_n_sources,
            plic_priority_bits     => plic_priority_bits,
            plic_addr_width        => plic_addr_width,
            has_timer              => has_timer,
            timer_id               => timer_id,
            has_switches           => has_switches,
            switches_id            => switches_id,
            switches_width         => switches_width,
            switches_active_low    => switches_active_low,
            has_keys               => has_keys,
            keys_id                => keys_id,
            keys_width             => keys_width,
            keys_active_low        => keys_active_low,
            has_display            => has_display,
            display_id             => display_id,
            display_digits         => display_digits,
            display_active_low     => display_active_low,
            has_uart_jtag          => has_uart_jtag,
            uart_jtag_id           => uart_jtag_id,
            has_uart_pins          => has_uart_pins,
            uart_pins_id           => uart_pins_id,
            uart_tx_invert         => uart_tx_invert,
            uart_rx_invert         => uart_rx_invert
        )
        port map (
            i_clk_core       => pll_clk_idexmem,
            i_clk_fetch      => pll_clk_if,
            i_rst            => i_rst,
            o_retire         => open,
            o_if_addr        => if_addr,
            o_if_rden        => if_rden,
            i_boot_data      => boot_memory_data,
            i_rom_data       => flash_data,
            o_rom_addr2      => flash_addr2,
            o_rom_rden2      => flash_rden2,
            i_rom_data2      => flash_data2,
            o_ram_en         => ram_en,
            o_ram_wren       => ram_wren,
            o_ram_rden       => ram_rden,
            o_ram_addr       => ram_addr,
            o_ram_wdata      => ram_wdata,
            o_ram_byteena    => ram_byteena,
            i_ram_rdata      => ram_rdata,
            o_flash_addr     => fc_addr,
            o_flash_rden     => fc_rden,
            o_flash_line     => fc_line,
            o_flash_advance  => fc_adv,
            i_flash_ready    => fc_ready,
            i_flash_busy     => fc_busy,
            i_flash_rdata    => fc_rdata,
            i_flash_rdata_x  => fc_rdx,
            o_ramd_addr      => rc_d_addr,
            o_ramd_wdata     => rc_d_wdata,
            o_ramd_byteena   => rc_d_be,
            o_ramd_rden      => rc_d_rden,
            o_ramd_wren      => rc_d_wren,
            o_ramd_line      => rc_d_line,
            o_ramd_advance   => rc_d_adv,
            o_ramd_wdata_x   => rc_d_wdx,
            i_ramd_ready     => rc_d_ready,
            i_ramd_rdata     => rc_d_rdata,
            i_ramd_rdata_x   => rc_d_rdx,
            o_rami_addr      => rc_i_addr,
            o_rami_rden      => rc_i_rden,
            o_rami_line      => rc_i_line,
            o_rami_advance   => rc_i_adv,
            i_rami_ready     => rc_i_ready,
            i_rami_rdata     => rc_i_rdata,
            i_rami_rdata_x   => rc_i_rdx,
            io_switches      => io_sw,
            io_keys          => io_key,
            o_display_hex    => o_display_hex,
            o_display_value  => o_display_value,
            i_uart_tck       => i_uart_tck,
            i_uart_tdi       => i_uart_tdi,
            o_uart_tdo       => o_uart_tdo,
            i_uart_ir_in     => i_uart_ir_in,
            i_uart_state_cdr => i_uart_state_cdr,
            i_uart_state_sdr => i_uart_state_sdr,
            i_uart_state_udr => i_uart_state_udr,
            i_uart_state_uir => i_uart_state_uir,
            i_uart_rx        => i_uart_rx,
            o_uart_tx        => o_uart_tx
        );

    o_ram_en      <= ram_en;
    o_ram_wren    <= ram_wren;
    o_ram_addr    <= ram_addr;
    o_ram_wdata   <= ram_wdata;
    o_ram_byteena <= ram_byteena;

    u_boot_memory : entity work.rom_simulation
        generic map (
            rom_file => boot_memory_file, size_bytes => boot_memory_size_bytes
        )
        port map (
            i_addr => if_addr,
            i_clk  => pll_clk_if,
            i_re   => if_rden,
            o_data => boot_memory_data
        );

    -- ROM do núcleo: a FLASH com duas portas, uma para instruções e outra para dados.

    gen_rom_internal : if not ROM_PORT generate
    begin

        u_flash : entity work.rom_simulation
            generic map (
                rom_file => rom_file, size_bytes => rom_size_bytes
            )
            port map (
                i_addr  => if_addr,
                i_clk   => pll_clk_if,
                i_re    => if_rden,
                o_data  => flash_data,
                i_addr2 => flash_addr2,
                i_clk2  => pll_clk_idexmem,
                i_re2   => flash_rden2,
                o_data2 => flash_data2
            );

    end generate gen_rom_internal;

    -- RAM do núcleo.

    gen_ram_internal : if not RAM_PORT generate
    begin

        u_ram : entity work.ram_simulation
            generic map (
                size_bytes => ram_size_bytes, ram_file => ram_file
            )
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

    end generate gen_ram_internal;

    -- O chip de FLASH e o seu armazenamento, quando a ROM é alcançada pela porta.

    gen_rom_chip : if ROM_PORT generate
    begin

        u_flash_chip : entity work.flash_chip
            generic map (
                first_latency => flash_first_latency,
                next_latency  => flash_next_latency,
                size_bytes    => rom_size_bytes
            )
            port map (
                i_clk      => pll_clk_idexmem,
                i_rst      => i_rst,
                i_addr     => fc_addr,
                i_rden     => fc_rden,
                i_line     => fc_line,
                i_advance  => fc_adv,
                o_ready    => fc_ready,
                o_busy     => fc_busy,
                o_rdata    => fc_rdata,
                o_rdata_x  => fc_rdx,
                o_mem_addr => flash_mem_addr,
                i_mem_data => flash_mem_data
            );

        u_flash_storage : entity work.rom_simulation
            generic map (
                rom_file => rom_file, size_bytes => rom_size_bytes
            )
            port map (
                i_addr => flash_mem_addr(31 downto 2),
                i_clk  => pll_clk_idexmem,
                i_re   => '1',
                o_data => flash_mem_data
            );

    end generate gen_rom_chip;

    -- O chip de RAM, quando a RAM é alcançada pela porta.

    gen_ext_ram : if RAM_PORT generate
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

    end generate gen_ext_ram;

    gen_no_ext_ram : if not RAM_PORT generate
    begin
        o_dbg_word_data <= (others => '0');
    end generate gen_no_ext_ram;

end architecture behaviour;
