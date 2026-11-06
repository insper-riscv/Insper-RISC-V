-- ============================================================================
-- Topo de simulação da plataforma modelo
-- ============================================================================
-- Liga o núcleo (perfil rv32i) à BOOT_MEMORY, à ROM e à RAM de simulação, todas
-- dentro do chip, e, quando has_uart é verdadeiro, a uma UART sobre JTAG na
-- janela de periféricos do núcleo. O mapa vem dos genéricos, cujo valor padrão
-- é o do pacote template_map_pkg, gerado do platform.yaml.
--
-- O topo só conecta: o gerador de clock, o núcleo, as memórias e a UART são
-- entidades dos outros repositórios e do próprio diretório da plataforma.
-- ============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;
use work.template_map_pkg.all;

entity template_sim_top is
    generic(
        -- Imagem da BOOT_MEMORY, uma palavra de 32 bits por linha em hexadecimal
        boot_memory_file       : string   := "default.hex";
        -- Imagem da ROM, a partir do seu início
        rom_file            : string   := "default.hex";
        -- Imagem inicial da RAM; vazio deixa tudo em zero
        ram_file            : string   := "";
        -- Tamanho da BOOT_MEMORY em bytes, uma potência de dois
        boot_memory_size_bytes : positive := BOOT_MEMORY_SIZE_BYTES;
        -- Tamanho do armazenamento da ROM em bytes, uma potência de dois
        rom_size_bytes      : positive := ROM_STORAGE_BYTES;
        -- Tamanho da RAM em bytes, uma potência de dois
        ram_size_bytes      : positive := RAM_STORAGE_BYTES;
        -- Instancia a UART sobre JTAG na janela de periféricos
        has_uart            : boolean  := false;
        -- Base RV32E (16 registradores) no núcleo; falso é o RV32I do perfil
        has_e               : boolean  := HAS_E;
        -- Extensão M (multiplicação e divisão) no núcleo
        has_m               : boolean  := HAS_M;
        -- Extensão Zmmul (só multiplicação) no núcleo
        has_zmmul           : boolean  := HAS_ZMMUL;
        -- Extensão Zicsr (instruções CSR) no núcleo
        has_zicsr           : boolean  := HAS_ZICSR;
        -- Contadores da extensão Zicntr (implica Zicsr)
        has_zicntr          : boolean  := HAS_ZICNTR;
        -- Contadores de eventos da extensão Zihpm (exige Zicsr)
        has_zihpm           : boolean  := HAS_ZIHPM;
        -- Extensão Zimop (mop.r.n e mop.rr.n escrevem zero em rd)
        has_zimop           : boolean  := HAS_ZIMOP;
        -- Extensão Zicond (czero.eqz e czero.nez)
        has_zicond          : boolean  := HAS_ZICOND;
        -- Extensão Zihintntl (dicas de não temporalidade)
        has_zihintntl       : boolean  := HAS_ZIHINTNTL;
        -- Extensão Zihintpause (a instrução pause)
        has_zihintpause     : boolean  := HAS_ZIHINTPAUSE;
        -- Extensão Zifencei (fence.i)
        has_zifencei        : boolean  := HAS_ZIFENCEI;
        -- Extensão Zicclsm (acessos desalinhados)
        has_zicclsm         : boolean  := HAS_ZICCLSM
    );
    port(
        -- Clock base; o gerador o divide por três para os estágios do núcleo
        i_clk       : in  std_logic;
        -- Reset, ativo em '1'
        i_rst       : in  std_logic := '0';
        -- Clock da cadeia JTAG da UART
        i_uart_tck  : in  std_logic := '0';
        -- Dado serial do hospedeiro para a UART
        i_uart_tdi  : in  std_logic := '0';
        -- Dado serial da UART para o hospedeiro
        o_uart_tdo  : out std_logic;
        -- Registrador de instrução do Virtual JTAG da UART
        i_uart_ir   : in  std_logic_vector(1 downto 0) := "00";
        -- Estado Capture-DR da cadeia virtual da UART
        i_uart_cdr  : in  std_logic := '0';
        -- Estado Shift-DR da cadeia virtual da UART
        i_uart_sdr  : in  std_logic := '0';
        -- Estado Update-DR da cadeia virtual da UART
        i_uart_udr  : in  std_logic := '0';
        -- Estado Update-IR da cadeia virtual da UART
        i_uart_uir  : in  std_logic := '0'
    );
end entity template_sim_top;

architecture behaviour of template_sim_top is

    -- Clock do estágio de busca, primeira fase do gerador
    signal pll_clk_if      : std_logic;
    -- Clock dos estágios ID, EX e MEM, segunda fase do gerador
    signal pll_clk_idexmem : std_logic;
    -- Clock do estágio de escrita (WB), terceira fase do gerador
    signal pll_clk_wb      : std_logic;

    -- Endereço de byte da busca de instrução
    signal if_addr         : std_logic_vector(31 downto 0);
    -- Habilitação de leitura da busca de instrução
    signal if_rden         : std_logic;
    -- Palavra lida da BOOT_MEMORY
    signal boot_memory_data   : std_logic_vector(31 downto 0);
    -- Palavra de instrução lida da ROM
    signal rom_data        : std_logic_vector(31 downto 0);
    -- Endereço de byte da segunda porta da ROM (estágio MEM)
    signal rom_addr2       : std_logic_vector(31 downto 0);
    -- Habilitação de leitura da segunda porta da ROM
    signal rom_rden2       : std_logic;
    -- Palavra de dado lida da segunda porta da ROM
    signal rom_data2       : std_logic_vector(31 downto 0);

    -- Endereço de byte do acesso à RAM
    signal ram_addr        : std_logic_vector(31 downto 0);
    -- Dado de escrita na RAM
    signal ram_wdata       : std_logic_vector(31 downto 0);
    -- Dado lido da RAM
    signal ram_rdata       : std_logic_vector(31 downto 0);
    -- Habilitação geral da RAM
    signal ram_en          : std_logic;
    -- Habilitação de escrita da RAM do núcleo
    signal ram_wren        : std_logic;
    -- Habilitação de leitura da RAM do núcleo
    signal ram_rden        : std_logic;
    -- Habilitação de bytes da escrita na RAM
    signal ram_byteena     : std_logic_vector(3 downto 0);
    -- Leitura da RAM habilitada pelo núcleo e pelo habilita geral
    signal ram_re_gated    : std_logic;
    -- Escrita na RAM habilitada pelo núcleo e pelo habilita geral
    signal ram_we_gated    : std_logic;

    -- Endereço de byte do barramento externo do núcleo
    signal ext_addr        : std_logic_vector(31 downto 0);
    -- Dado de escrita do barramento externo
    signal ext_wdata       : std_logic_vector(31 downto 0);
    -- Habilitação de bytes da escrita no barramento externo
    signal ext_byteena     : std_logic_vector(3 downto 0);
    -- Habilitação de leitura do barramento externo
    signal ext_rden        : std_logic;
    -- Habilitação de escrita do barramento externo
    signal ext_wren        : std_logic;
    -- Dado entregue ao núcleo pelo barramento externo
    signal ext_rdata       : std_logic_vector(31 downto 0) := (others => '0');

    -- O acesso do núcleo cai na janela da UART
    signal uart_selected   : std_logic;
    -- Dado lido da UART
    signal uart_rdata      : std_logic_vector(31 downto 0);
    -- Dado lido da UART, guardado para o ciclo seguinte ao acesso
    signal uart_rdata_q    : std_logic_vector(31 downto 0) := (others => '0');

begin

    ram_re_gated <= ram_rden and ram_en;
    ram_we_gated <= ram_wren and ram_en;

    u_clock : entity work.clk_gen_3way
        port map(
            i_clk  => i_clk,
            i_rst  => i_rst,
            o_clk0 => pll_clk_if,
            o_clk1 => pll_clk_idexmem,
            o_clk2 => pll_clk_wb
        );

    u_core : entity work.core
        generic map(
            has_e           => has_e,
            has_m           => has_m,
            has_zmmul       => has_zmmul,
            has_zicsr       => has_zicsr,
            has_zicntr      => has_zicntr,
            has_zihpm       => has_zihpm,
            has_zifencei    => has_zifencei,
            has_zicclsm     => has_zicclsm,
            has_zimop       => has_zimop,
            has_zicond      => has_zicond,
            has_zihintntl   => has_zihintntl,
            has_zihintpause => has_zihintpause,
            boot_memory_bits   => log2_exact(boot_memory_size_bytes),
            rom_end_kib     => ROM_END_KIB,
            rom_external    => ROM_EXTERNAL,
            ram_base_kib    => RAM_BASE_KIB,
            ram_end_kib     => RAM_END_KIB,
            ram_external    => RAM_EXTERNAL,
            ext_base_kib    => EXT_BASE_KIB,
            periph_base_kib => PERIPH_BASE_KIB
        )
        port map(
            o_trap          => open,
            o_retire        => open,
            o_trap_cause    => open,
            o_trap_pc       => open,
            i_clk           => pll_clk_idexmem,
            i_rst           => i_rst,
            o_if_addr       => if_addr,
            o_if_rden       => if_rden,
            i_boot_memory_data => boot_memory_data,
            i_flash_data    => rom_data,
            o_flash_addr2   => rom_addr2,
            o_flash_rden2   => rom_rden2,
            i_flash_data2   => rom_data2,
            o_ram_addr      => ram_addr,
            o_ram_wdata     => ram_wdata,
            i_ram_rdata     => ram_rdata,
            o_ram_en        => ram_en,
            o_ram_wren      => ram_wren,
            o_ram_rden      => ram_rden,
            o_ram_byteena   => ram_byteena,
            o_sdram_addr    => ext_addr,
            o_sdram_wdata   => ext_wdata,
            o_sdram_byteena => ext_byteena,
            o_sdram_rden    => ext_rden,
            o_sdram_wren    => ext_wren,
            i_sdram_rdata   => ext_rdata
        );

    u_boot_memory : entity work.rom_simulation
        generic map(rom_file => boot_memory_file, size_bytes => boot_memory_size_bytes)
        port map(
            i_addr => if_addr(31 downto 2),
            i_clk  => pll_clk_if,
            i_re   => if_rden,
            o_data => boot_memory_data
        );

    -- A ROM tem duas portas: instruções e dados de somente leitura
    u_rom : entity work.rom_simulation
        generic map(rom_file => rom_file, size_bytes => rom_size_bytes)
        port map(
            i_addr  => if_addr(31 downto 2),
            i_clk   => pll_clk_if,
            i_re    => if_rden,
            o_data  => rom_data,
            i_addr2 => rom_addr2(31 downto 2),
            i_clk2  => pll_clk_idexmem,
            i_re2   => rom_rden2,
            o_data2 => rom_data2
        );

    u_ram : entity work.ram_simulation
        generic map(size_bytes => ram_size_bytes, ram_file => ram_file)
        port map(
            i_addr     => ram_addr(31 downto 2),
            i_mask     => ram_byteena,
            i_clk      => pll_clk_idexmem,
            i_data_in  => ram_wdata,
            i_re_ram   => ram_re_gated,
            i_we_ram   => ram_we_gated,
            i_en_ram   => ram_en,
            o_data_out => ram_rdata
        );

    -- Sem UART, o barramento externo não tem dispositivo e o topo não o usa
    g_no_uart : if not has_uart generate
    begin
        uart_selected <= '0';
        uart_rdata    <= (others => '0');
        o_uart_tdo    <= '0';
    end generate g_no_uart;

    -- Com UART, ela responde na janela de periféricos cuja base é UART_BASE
    g_uart : if has_uart generate
    begin
        uart_selected <= '1' when ext_addr(31 downto 28) = UART_BASE(31 downto 28) else '0';

        u_uart : entity work.jtag_uart
            port map(
                i_clk       => pll_clk_idexmem,
                i_rst       => i_rst,
                i_addr      => ext_addr(9 downto 2),
                i_wdata     => ext_wdata,
                i_we        => ext_wren and uart_selected,
                i_re        => ext_rden and uart_selected,
                o_rdata     => uart_rdata,
                i_tck       => i_uart_tck,
                i_tdi       => i_uart_tdi,
                o_tdo       => o_uart_tdo,
                i_ir_in     => i_uart_ir,
                i_state_cdr => i_uart_cdr,
                i_state_sdr => i_uart_sdr,
                i_state_udr => i_uart_udr,
                i_state_uir => i_uart_uir
            );
    end generate g_uart;

    -- O núcleo lê o dado do barramento externo no ciclo seguinte ao pedido
    p_uart_read : process(pll_clk_idexmem, i_rst)
    begin
        if i_rst = '1' then
            uart_rdata_q <= (others => '0');
        elsif rising_edge(pll_clk_idexmem) then
            if ext_rden = '1' and uart_selected = '1' then
                uart_rdata_q <= uart_rdata;
            end if;
        end if;
    end process p_uart_read;

    ext_rdata <= uart_rdata_q;

end architecture behaviour;
