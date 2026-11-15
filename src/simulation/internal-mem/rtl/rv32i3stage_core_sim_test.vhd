-- =============================================================================
-- Topo de simulação da plataforma internal-mem
--
-- Monta o núcleo com as memórias simuladas (BOOT_MEMORY, FLASH e RAM) e a UART mapeada em
-- 0xC0000000, alimentados pelo gerador de clock de três fases. As larguras de endereço das
-- memórias e as extensões do núcleo são genéricos, para o testbench dimensionar a plataforma.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.internal_mem_map_pkg.all;
use work.config_pkg.addr_t;
use work.config_pkg.word_t;
use work.interconnect_pkg.all;

entity rv32i3stage_core_sim_test is
    generic (
        -- Imagem da BOOT_MEMORY, montada UMA vez por execução de testes (ver
        -- riscv_tools.boot_memory.build_boot_memory), e não por teste como o ROM_FILE
        -- (a imagem própria da FLASH; ver sim.parameters do config.yaml). Os dois têm
        -- "default.hex" como padrão para os chamadores que não os informam (por
        -- exemplo tests/python/tests.json).
        boot_memory_file       : string                := "default.hex";
        -- Imagem da FLASH, uma palavra de 32 bits por linha em hexadecimal.
        rom_file               : string                := "default.hex";
        -- Conteúdo inicial da RAM, no formato do ROM_FILE; vazio significa zero.
        ram_file               : string                := "";
        -- Largura do endereço de palavra do vetor interno de memória da BOOT_MEMORY, da
        -- FLASH e da RAM simuladas (profundidade 2**largura palavras). Os três valem 9
        -- (512 palavras) dentro dos modelos, pouco para um programa ou um endereço de
        -- tohost dimensionados para o hardware real. Expostos aqui para um testbench
        -- do pipeline completo ajustá-los ao mapa de memória dos seus testes sem editar
        -- este arquivo; o padrão 9/9/9 mantém os chamadores de tests.json
        -- (testes por instrução) como estão.
        boot_memory_addr_width : natural               := 9;
        -- Largura, em bits, do endereço de palavra da FLASH simulada (profundidade 2**largura).
        rom_addr_width         : natural               := 9;
        -- Largura, em bits, do endereço de palavra da RAM simulada (profundidade 2**largura).
        ram_addr_width         : natural               := 9;
        -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os indices a partir de 3.
        hpm_counters           : natural range 0 to 29 := 29;
        -- Largura, em bits, de cada contador de eventos do Zihpm.
        hpm_width              : natural range 0 to 64 := 64;
        -- A ROM fica fora do core (o modelo de memória do platform.yaml).
        rom_external           : boolean               := work.internal_mem_map_pkg.FLASH_ON_BUS;
        -- A RAM fica fora do core (o modelo de memória do platform.yaml).
        ram_external           : boolean               := work.internal_mem_map_pkg.RAM_ON_BUS;
        -- Existe cache de instruções (o modelo de memória do platform.yaml).
        has_icache             : boolean               := work.internal_mem_map_pkg.HAS_ICACHE;
        -- Existe cache de dados (o modelo de memória do platform.yaml).
        has_dcache             : boolean               := work.internal_mem_map_pkg.HAS_DCACHE;
        -- Tamanho da cache de instruções, em bits (o modelo de memória do platform.yaml).
        icache_size_bits       : positive              := work.internal_mem_map_pkg.ICACHE_SIZE_BITS;
        -- Tamanho da cache de dados, em bits (o modelo de memória do platform.yaml).
        dcache_size_bits       : positive              := work.internal_mem_map_pkg.DCACHE_SIZE_BITS
    );
    port (
        -- Clock base da simulação; o gerador de clock o divide por três.
        i_clk     : in    std_logic;
        -- Reset da simulação, ativo em '1'.
        i_rst     : in    std_logic := '0';
        -- Entrada serial da UART (repouso em '1').
        i_uart_rx : in    std_logic := '1';
        -- Saída serial da UART (repouso em '1').
        o_uart_tx : out   std_logic := '1'
    );
end entity rv32i3stage_core_sim_test;

architecture behaviour of rv32i3stage_core_sim_test is

    -- Exceção sinalizada pelo core sem Zicsr (um ciclo em '1'); com Zicsr fica em '0'.
    signal core_trap       : std_logic;
    -- Pulso de retirada de uma instrução em EX, contado pelo testbench para medir os ciclos por instrução.
    signal core_retire     : std_logic;
    -- Causa da exceção sinalizada, no formato do mcause.
    signal core_trap_cause : word_t;
    -- PC da instrução que gerou a exceção sinalizada.
    signal core_trap_pc    : word_t;

    -- IF stage: barramento UNICO compartilhado por BOOT_MEMORY e FLASH
    -- (ver rv32im_pipeline_core.vhd is_boot_memory_if/is_boot_memory_d) --
    -- ambas as ROM_simulation instancias abaixo recebem o MESMO
    -- if_addr/if_rden, cada uma devolvendo seu proprio dado.
    signal if_addr          : addr_t;
    -- Habilitação de leitura da busca de instrução ('1' = lê).
    signal if_rden          : std_logic;
    -- Palavra de instrução lida da BOOT_MEMORY.
    signal boot_memory_data : word_t;
    -- Palavra de instrução lida da FLASH.
    signal flash_data       : word_t;

    -- Estagio MEM: segunda porta da FLASH, so' para o copy-loop de
    -- .data em boot_memory.S (ver rv32im_pipeline_core.vhd flash_addr2).
    signal flash_addr2 : addr_t;
    -- Habilitação de leitura da segunda porta da FLASH ('1' = lê).
    signal flash_rden2 : std_logic;
    -- Palavra de dado lida da segunda porta da FLASH (estágio MEM).
    signal flash_data2 : word_t;

    -- Endereço de byte do acesso à RAM do núcleo.
    signal ram_addr         : addr_t;
    -- Dado de escrita na RAM do núcleo.
    signal ram_wdata        : word_t;
    -- Dado lido da RAM entregue ao núcleo.
    signal ram_rdata        : word_t;
    -- Dado lido diretamente da memória RAM, antes de chegar ao núcleo.
    signal ram_memory_rdata : word_t;
    -- Habilitação geral da RAM do núcleo (estágio MEM).
    signal ram_en           : std_logic;
    -- Leitura da RAM habilitada pelo núcleo e pelo enable geral ('1' = lê).
    signal ram_re_gated     : std_logic;
    -- Escrita na RAM habilitada pelo núcleo e pelo enable geral ('1' = escreve).
    signal ram_we_gated     : std_logic;
    -- Habilitação de escrita da RAM do núcleo ('1' = escreve).
    signal ram_wren         : std_logic;
    -- Habilitação de leitura da RAM do núcleo ('1' = lê).
    signal ram_rden         : std_logic;
    -- Habilitação de bytes da escrita na RAM do núcleo.
    signal ram_byteena      : std_logic_vector(3 downto 0);

    -- Clock do estágio de busca (IF), primeira fase do gerador de clock.
    signal pll_clk_if      : std_logic;
    -- Clock dos estágios ID, EX e MEM, segunda fase do gerador de clock.
    signal pll_clk_idexmem : std_logic;
    -- Clock do estágio de escrita (WB), terceira fase do gerador de clock.
    signal pll_clk_wb      : std_logic;
    -- Indica que o PLL travou ('1' = travado).
    signal pll_locked      : std_logic;

    -- Mesma UART memory-mapped do topo de hardware, em UART_BASE.
    signal uart_selected : std_logic;
    -- Escrita na UART ('1' = escreve; janela selecionada e escrita do núcleo).
    signal uart_write    : std_logic;
    -- Leitura da UART ('1' = lê; janela selecionada e leitura do núcleo).
    signal uart_read     : std_logic;
    -- Dado lido da UART.
    signal uart_rdata    : word_t;
    -- Leitura da UART atrasada um ciclo, que acompanha a resposta registrada.
    signal uart_read_d   : std_logic;
    -- Dado lido da UART registrado, devolvido ao núcleo no ciclo seguinte.
    signal uart_rdata_d  : word_t;

    -- Porta externa do core (enderecos com o bit 31 ou 30 em 1): aqui so' a UART responde.
    signal sdram_addr    : addr_t;
    -- Dado de escrita do barramento externo do núcleo.
    signal sdram_wdata   : word_t;
    -- Habilitação de bytes da escrita no barramento externo.
    signal sdram_byteena : std_logic_vector(3 downto 0);
    -- Habilitação de leitura do barramento externo ('1' = lê).
    signal sdram_rden    : std_logic;
    -- Habilitação de escrita do barramento externo ('1' = escreve).
    signal sdram_wren    : std_logic;
    -- Dado lido do barramento externo devolvido ao núcleo.
    signal sdram_rdata   : word_t;
    -- O acesso externo do núcleo não cai na janela da UART (nenhum escravo o atende): falha de acesso.
    signal ext_error     : std_logic;

begin

    -- A UART fica na janela de perifericos (UART_BASE), que o core atende pela porta externa.
    uart_selected <= '1'
                     when window_hit(sdram_addr, UART_BASE, PERIPH_MASKS(UART_INDEX)) else
                     '0';
    ext_error     <= (sdram_rden or sdram_wren) and not uart_selected;
    uart_write    <= sdram_wren and uart_selected;
    uart_read     <= sdram_rden and uart_selected;

    -- Sinais intermediarios para port maps (VHDL-93 nao aceita expressoes em port maps)
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

            i_clk => pll_clk_idexmem,
            i_rst => i_rst,

            ----------------------------------------------------------------------
            -- Interface de busca de instrucao -- barramento unico
            -- compartilhado por BOOT_MEMORY e FLASH (ver
            -- rv32im_pipeline_core.vhd)
            ----------------------------------------------------------------------
            o_if_addr          => if_addr,
            o_if_rden          => if_rden,
            i_boot_memory_data => boot_memory_data,
            i_flash_data       => flash_data,

            o_flash_addr2 => flash_addr2,
            o_flash_rden2 => flash_rden2,
            i_flash_data2 => flash_data2,

            ----------------------------------------------------------------------
            -- Interface com a RAM (leitura e escrita)
            ----------------------------------------------------------------------
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
            i_ext_error   => ext_error
        );

    u_uart_peripheral : entity work.uart
        generic map (
            data_width => 32,
            -- clk_gen_3way produz uma borda de pll_clk_idexmem a cada
            -- 30 ns com o i_clk de 10 ns usado pelo perfil de simulacao.
            -- Mantem 115200 baud nesse clock de 33,333 MHz; o topo de
            -- hardware usa o valor default para seu PLL de 50 MHz.
            baud_freq  => 16#240#,
            baud_limit => 16#2671#
        )
        port map (
            i_clk      => pll_clk_idexmem,
            i_rst      => i_rst,
            i_data_in  => sdram_wdata,
            i_address  => sdram_addr(3 downto 2),
            i_write    => uart_write,
            i_read     => uart_read,
            o_data_out => uart_rdata,
            o_irq      => open,
            i_uart_rx  => i_uart_rx,
            o_uart_tx  => o_uart_tx
        );

    p_uart_read_pipeline : process (i_rst, pll_clk_idexmem) is
    begin

        if i_rst = '1' then
            uart_read_d  <= '0';
            uart_rdata_d <= (others => '0');
        elsif rising_edge(pll_clk_idexmem) then
            uart_read_d <= uart_read;

            if uart_read = '1' then
                uart_rdata_d <= uart_rdata;
            end if;
        end if;

    end process p_uart_read_pipeline;

    -- O core recebe a resposta do acesso realizado no ciclo anterior.
    sdram_rdata <= uart_rdata_d;
    ram_rdata   <= ram_memory_rdata;

    -- BOOT_MEMORY e FLASH: duas instancias separadas da MESMA entidade
    -- ROM_simulation, cada uma com seu proprio arquivo/largura.
    -- BOOT_MEMORY: so' porta 1 (nunca tem .data proprio, addr2/clk2/re2
    -- ficam nos valores default). FLASH: porta 2 tambem usada, pelo
    -- estagio MEM (ver rv32im_pipeline_core.vhd flash_addr2 -- o
    -- copy-loop de .data em boot_memory.S le FLASH como dado).
    u_boot_memory : entity work.rom_simulation
        generic map (
            rom_file => boot_memory_file, size_bytes => 4 * 2 ** boot_memory_addr_width
        )
        port map (
            i_addr => if_addr(31 downto 2),
            i_clk  => pll_clk_if,
            i_re   => if_rden,
            o_data => boot_memory_data
        );

    u_flash : entity work.rom_simulation
        generic map (
            rom_file => rom_file, size_bytes => 4 * 2 ** rom_addr_width
        )
        port map (
            i_addr => if_addr(31 downto 2),
            i_clk  => pll_clk_if,
            i_re   => if_rden,
            o_data => flash_data,

            i_addr2 => flash_addr2(31 downto 2),
            i_clk2  => pll_clk_idexmem,
            i_re2   => flash_rden2,
            o_data2 => flash_data2
        );

    u_ram : entity work.ram_simulation
        generic map (
            size_bytes => 4 * 2 ** ram_addr_width, ram_file => ram_file
        )
        port map (
            i_addr     => ram_addr(31 downto 2),
            i_mask     => ram_byteena,
            i_clk      => pll_clk_idexmem,
            i_data_in  => ram_wdata,
            i_re_ram   => ram_re_gated,
            i_we_ram   => ram_we_gated,
            i_en_ram   => ram_en,
            o_data_out => ram_memory_rdata
        );

end architecture behaviour;
