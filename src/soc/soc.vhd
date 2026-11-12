-- =============================================================================
-- SoC independente de placa: núcleo, caches, interconector, CLINT, PLIC e periféricos
--
-- O SoC liga o núcleo às suas memórias e aos periféricos por contratos de interface e não
-- tem pino de placa, nome de família nem primitiva de fornecedor. Quem o instancia (o topo
-- de simulação ou o topo de uma placa) fornece os relógios, o reset e os backends de memória
-- das regiões que o núcleo alcança pela porta externa, e ele só liga o que recebe.
--
--   | Região        | Face do SoC                                   | Backend que o topo liga                  |
--   | BOOT_MEMORY   | o_if_addr, o_if_rden e i_boot_data            | bloco de memória do FPGA                  |
--   | ROM interna   | o_if_addr e o_rom_addr2 com i_rom_data(2)     | bloco de memória de duas portas           |
--   | ROM externa   | o_flash_* e i_flash_*                         | chip de FLASH (modelo ou dispositivo)     |
--   | RAM interna   | o_ram_* e i_ram_rdata                         | bloco de memória do FPGA                  |
--   | RAM externa   | o_ramd_* e o_rami_* com i_ramd_* e i_rami_*   | chip de RAM (modelo ou dispositivo)       |
--
--   rom_via_port = rom_external ou has_icache
--   ram_via_port = ram_external ou HAS_DCACHE (do config_pkg)
--
-- O núcleo recebe rom_via_port e ram_via_port nos seus genéricos rom_external e ram_external,
-- porque uma cache só existe do lado do protocolo da porta. A face de uma região que não é
-- alcançada pela porta fica parada (saídas em zero, entradas ignoradas).
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
-- Com a ROM e a RAM via porta, um roteador por mestre separa a ROM da RAM, e a ROM tem um árbitro entre
-- a busca e os dados. Com só a ROM via porta, o roteador dos dados leva o pedido à FLASH e responde zero
-- fora dela. Com só a RAM via porta, a cache de dados (ou a interconexão, sem ela) fala direto com o chip.
--
-- Os periféricos (chaves, botões, display, UART, temporizador, CLINT e PLIC) ficam na janela de
-- periféricos do núcleo. Os papéis de E/S têm a largura por generic (switches_width, keys_width e
-- display_digits), e um papel de largura zero é omitido. A polaridade dos pinos é um generic por papel,
-- resolvido por quem instancia o SoC; o periférico vê sempre o programa ativo em '1'.
--
-- O núcleo e o SoC leem a ISA (base, extensões, interrupções e a cache de dados) do config_pkg gerado do
-- platform.yaml da plataforma, sem genérico de ISA. O SoC confere em asserções que os genéricos do mapa, que
-- quem instancia lê do pacote do mapa, concordam com ele. Todos os tamanhos são genéricos
-- em potência de dois (bytes para
-- a BOOT_MEMORY, bits para as caches), verificados pelo log2_exact.
-- =============================================================================

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use work.utils_pkg.all;

entity soc is
    generic (
        -- Tamanho da BOOT_MEMORY em bytes, uma potência de dois de pelo menos 1 KiB.
        boot_memory_size_bytes : positive;
        -- Fim exclusivo, em KiB, da ROM, que começa logo depois da BOOT_MEMORY.
        rom_end_kib            : natural;
        -- Base, em KiB, da RAM.
        ram_base_kib           : natural;
        -- Fim exclusivo, em KiB, da RAM.
        ram_end_kib            : natural;
        -- Base, em KiB, da janela externa de periféricos e outros dispositivos.
        ext_base_kib           : natural;
        -- Base, em KiB, da janela de periféricos.
        periph_base_kib        : natural;
        -- A ROM é externa (um chip fora do núcleo, alcançado pela porta).
        rom_external           : boolean                       := false;
        -- A RAM é externa (um chip fora do núcleo, alcançado pela porta).
        ram_external           : boolean                       := false;
        -- Existe cache de instruções; sem ela, a ROM via porta é lida pela ponte de busca.
        has_icache             : boolean                       := false;
        -- Tamanho da cache de instruções em bits, uma potência de dois (4096 é 4 kbit).
        icache_size_bits       : positive                      := 4096;
        -- Tamanho da cache de dados em bits, uma potência de dois (4096 é 4 kbit).
        dcache_size_bits       : positive                      := 4096;
        -- Largura da janela de endereços das caches, em bits: a tag guarda os bits abaixo dela (26 é 64 MiB, 27 é 128
        -- MiB).
        cache_window_bits      : natural range 26 to 29        := 26;
        -- Quantidade de contadores de eventos do Zihpm (de 0 a 29), com os índices a partir de 3.
        hpm_counters           : natural range 0 to 29         := 29;
        -- Largura, em bits, de cada contador de eventos do Zihpm.
        hpm_width              : natural range 0 to 64         := 64;
        -- Quantidade de janelas de periférico do mapa, passada ao núcleo.
        periph_slots           : std_logic_vector(7 downto 0)  := (others => '1');
        -- Ciclos de clock do núcleo por incremento do mtime do CLINT.
        clint_tick_cycles      : positive                      := 1;
        -- Índice da janela de 256 MiB do CLINT (bits 30:28 do endereço); o do platform.yaml.
        clint_id               : natural range 0 to 7          := 6;
        -- Índice da janela de 256 MiB do PLIC, o controlador das interrupções externas.
        plic_id                : natural range 0 to 7          := 7;
        -- Número de fontes do PLIC; as linhas são as LINE_* abaixo, a partir da 1.
        plic_n_sources         : positive range 6 to 1023      := 6;
        -- Largura da prioridade e do limiar do PLIC, em bits.
        plic_priority_bits     : positive range 1 to 32        := 3;
        -- Largura do endereço de palavra da janela do PLIC (a janela tem 2**(plic_addr_width + 2) bytes).
        plic_addr_width        : positive range 20 to 26       := 20;
        -- As três linhas de interrupção entram no núcleo por um registrador (um ciclo de latência a mais), o que
        -- tira o árbitro do PLIC e o comparador do mtime do caminho que decide a tomada da interrupção.
        registered_irqs        : boolean                       := false;
        -- A cache de instruções escolhe a região pelo endereço registrado, sem a porta de seleção e sem conferir o
        -- endereço a cada consulta: tira a decodificação do PC do caminho até a cache (exige os dois clocks defasados).
        fast_icache_select     : boolean                       := false;
        -- A última página de 4 KiB da RAM (bits 31:12 em bypass_page) nunca é guardada na cache de dados: ali ficam as
        -- palavras que o hospedeiro compartilha com o programa.
        has_dcache_bypass      : boolean                       := false;
        -- Página de 4 KiB, bits 31:12 do endereço, que a cache de dados não guarda com has_dcache_bypass.
        bypass_page            : std_logic_vector(19 downto 0) := (others => '0');
        -- Controlador de FLASH da atualização de programa: comandos do chip (apagar, gravar, proteger) pela janela
        -- flash_ctrl_id, com a interrupção na linha LINE_FLASH e a invalidação das caches pela região gravada.
        has_flash_ctrl         : boolean                       := false;
        -- Índice da janela do controlador de FLASH.
        flash_ctrl_id          : natural range 0 to 7          := 3;
        -- Temporizador de uso geral, com a interrupção de overflow ligada ao PLIC.
        has_timer              : boolean                       := false;
        -- Índice da janela do temporizador.
        timer_id               : natural range 0 to 7          := 0;
        -- Papel das chaves, num bloco GPIO; omitido quando switches_width é zero.
        has_switches           : boolean                       := false;
        -- Índice da janela das chaves.
        switches_id            : natural range 0 to 7          := 1;
        -- Número de chaves (largura do papel); zero omite o papel.
        switches_width         : natural range 0 to 32         := 10;
        -- Chaves ativas em nível baixo no pino (o programa as vê ativas em '1').
        switches_active_low    : boolean                       := false;
        -- Papel dos botões, num bloco GPIO; omitido quando keys_width é zero.
        has_keys               : boolean                       := false;
        -- Índice da janela dos botões.
        keys_id                : natural range 0 to 7          := 2;
        -- Número de botões (largura do papel); zero omite o papel.
        keys_width             : natural range 0 to 32         := 4;
        -- Botões ativos em nível baixo no pino (o programa os vê ativos em '1').
        keys_active_low        : boolean                       := false;
        -- Papel do display de sete segmentos; omitido quando display_digits é zero.
        has_display            : boolean                       := false;
        -- Índice da janela do display.
        display_id             : natural range 0 to 7          := 5;
        -- Número de dígitos do display (largura do papel); zero omite o papel.
        display_digits         : natural range 0 to 8          := 6;
        -- Segmentos acesos em nível baixo no pino.
        display_active_low     : boolean                       := true;
        -- UART cuja outra ponta é o hospedeiro no JTAG.
        has_uart_jtag          : boolean                       := false;
        -- Índice da janela da UART via JTAG.
        uart_jtag_id           : natural range 0 to 7          := 4;
        -- UART cuja outra ponta são dois pinos (TX e RX) da placa.
        has_uart_pins          : boolean                       := false;
        -- Índice da janela da UART via pinos.
        uart_pins_id           : natural range 0 to 7          := 3;
        -- Polaridade do pino de transmissão do console em pinos: verdadeiro inverte o nível de o_uart_tx.
        uart_tx_invert         : boolean                       := false;
        -- Polaridade do pino de recepção do console em pinos: verdadeiro inverte o nível de i_uart_rx.
        uart_rx_invert         : boolean                       := false
    );
    port (
        -- Relógio do núcleo e das memórias de dados (estágios ID, EX e MEM).
        i_clk_core          : in    std_logic;
        -- Relógio das memórias de instrução (estágio IF), em fase com o do núcleo.
        i_clk_fetch         : in    std_logic;
        -- Reset, ativo em '1'.
        i_rst               : in    std_logic                     := '0';
        -- Pulso de retirada de instrução do núcleo, que o testbench conta para o CPI.
        o_retire            : out   std_logic;
        -- Endereço de palavra da busca de instrução, para a BOOT_MEMORY e a ROM interna.
        o_if_addr           : out   std_logic_vector(29 downto 0);
        -- Habilitação de leitura da busca de instrução ('1' = lê).
        o_if_rden           : out   std_logic;
        -- Palavra de instrução lida da BOOT_MEMORY.
        i_boot_data         : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Palavra de instrução lida da ROM interna.
        i_rom_data          : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Endereço de palavra da segunda porta da ROM interna (estágio MEM).
        o_rom_addr2         : out   std_logic_vector(29 downto 0);
        -- Habilitação de leitura da segunda porta da ROM interna ('1' = lê).
        o_rom_rden2         : out   std_logic;
        -- Palavra de dado lida da segunda porta da ROM interna.
        i_rom_data2         : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Habilita geral da RAM interna do núcleo (estágio MEM).
        o_ram_en            : out   std_logic;
        -- Habilita de escrita da RAM interna do núcleo.
        o_ram_wren          : out   std_logic;
        -- Habilita de leitura da RAM interna do núcleo.
        o_ram_rden          : out   std_logic;
        -- Endereço de byte do acesso à RAM interna do núcleo.
        o_ram_addr          : out   std_logic_vector(31 downto 0);
        -- Dado de escrita da RAM interna do núcleo.
        o_ram_wdata         : out   std_logic_vector(31 downto 0);
        -- Habilita de bytes da escrita na RAM interna do núcleo.
        o_ram_byteena       : out   std_logic_vector(3 downto 0);
        -- Dado lido da RAM interna do núcleo.
        i_ram_rdata         : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Chip de FLASH: endereço de byte do acesso.
        o_flash_addr        : out   std_logic_vector(31 downto 0);
        -- Chip de FLASH: habilitação de leitura ('1' = lê).
        o_flash_rden        : out   std_logic;
        -- Chip de FLASH: pedido de linha inteira de cache ('1' = acesso em linha).
        o_flash_line        : out   std_logic;
        -- Chip de FLASH: avanço para a próxima palavra da linha ('1' = avança).
        o_flash_advance     : out   std_logic;
        -- Chip de FLASH: acesso concluído ('1' = pronto).
        i_flash_ready       : in    std_logic                     := '0';
        -- Chip de FLASH: ocupado com um acesso, evento do Zihpm ('1' = ocupado).
        i_flash_busy        : in    std_logic                     := '0';
        -- Chip de FLASH: palavra lida.
        i_flash_rdata       : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Chip de FLASH: linha lida, barramento largo de 96 bits.
        i_flash_rdata_x     : in    std_logic_vector(95 downto 0) := (others => '0');
        -- Controlador de FLASH: pulso que entrega um comando ao chip.
        o_flash_cmd_valid   : out   std_logic;
        -- Controlador de FLASH: código do comando (001 habilitar escrita, 010 apagar, 011 gravar, 100 proteger, 101
        -- desproteger).
        o_flash_cmd_op      : out   std_logic_vector(2 downto 0);
        -- Controlador de FLASH: endereço de byte do comando.
        o_flash_cmd_addr    : out   std_logic_vector(31 downto 0);
        -- Controlador de FLASH: o chip executa um apagar ou uma gravação ('1' = ocupado).
        i_flash_cmd_busy    : in    std_logic                     := '0';
        -- Controlador de FLASH: o latch de escrita do chip está armado ('1').
        i_flash_cmd_wel     : in    std_logic                     := '0';
        -- Controlador de FLASH: o último apagar ou gravar foi recusado ('1').
        i_flash_cmd_refused : in    std_logic                     := '0';
        -- Controlador de FLASH: índice da palavra do buffer de página lida pela gravação do chip.
        i_flash_buf_idx     : in    std_logic_vector(5 downto 0)  := (others => '0');
        -- Controlador de FLASH: palavra do buffer de página, com leitura registrada.
        o_flash_buf_data    : out   std_logic_vector(31 downto 0);
        -- Região da FLASH regravada: pulso que derruba as linhas das caches de i_inval_first a i_inval_last (bytes).
        i_inval_valid       : in    std_logic                     := '0';
        -- Região da FLASH regravada: primeiro endereço de byte.
        i_inval_first       : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Região da FLASH regravada: último endereço de byte.
        i_inval_last        : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Chip de RAM, porta de dados: endereço de byte do acesso.
        o_ramd_addr         : out   std_logic_vector(31 downto 0);
        -- Chip de RAM, porta de dados: dado de escrita.
        o_ramd_wdata        : out   std_logic_vector(31 downto 0);
        -- Chip de RAM, porta de dados: habilitação de bytes da escrita.
        o_ramd_byteena      : out   std_logic_vector(3 downto 0);
        -- Chip de RAM, porta de dados: habilitação de leitura ('1' = lê).
        o_ramd_rden         : out   std_logic;
        -- Chip de RAM, porta de dados: habilitação de escrita ('1' = escreve).
        o_ramd_wren         : out   std_logic;
        -- Chip de RAM, porta de dados: pedido de linha inteira de cache ('1' = acesso em linha).
        o_ramd_line         : out   std_logic;
        -- Chip de RAM, porta de dados: avanço para a próxima palavra da linha ('1' = avança).
        o_ramd_advance      : out   std_logic;
        -- Chip de RAM, porta de dados: linha a escrever, barramento largo de 96 bits.
        o_ramd_wdata_x      : out   std_logic_vector(95 downto 0);
        -- Chip de RAM, porta de dados: acesso concluído ('1' = pronto).
        i_ramd_ready        : in    std_logic                     := '0';
        -- Chip de RAM, porta de dados: palavra lida.
        i_ramd_rdata        : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Chip de RAM, porta de dados: linha lida, barramento largo de 96 bits.
        i_ramd_rdata_x      : in    std_logic_vector(95 downto 0) := (others => '0');
        -- Chip de RAM, porta de instruções: endereço de byte do acesso.
        o_rami_addr         : out   std_logic_vector(31 downto 0);
        -- Chip de RAM, porta de instruções: habilitação de leitura ('1' = lê).
        o_rami_rden         : out   std_logic;
        -- Chip de RAM, porta de instruções: pedido de linha inteira de cache ('1' = acesso em linha).
        o_rami_line         : out   std_logic;
        -- Chip de RAM, porta de instruções: avanço para a próxima palavra da linha ('1' = avança).
        o_rami_advance      : out   std_logic;
        -- Chip de RAM, porta de instruções: acesso concluído ('1' = pronto).
        i_rami_ready        : in    std_logic                     := '0';
        -- Chip de RAM, porta de instruções: palavra lida.
        i_rami_rdata        : in    std_logic_vector(31 downto 0) := (others => '0');
        -- Chip de RAM, porta de instruções: linha lida, barramento largo de 96 bits.
        i_rami_rdata_x      : in    std_logic_vector(95 downto 0) := (others => '0');
        -- Chaves (pinos do GPIO), uma por bit do papel.
        io_switches         : inout std_logic_vector(switches_width - 1 downto 0);
        -- Botões (pinos do GPIO), um por bit do papel.
        io_keys             : inout std_logic_vector(keys_width - 1 downto 0);
        -- Segmentos dos displays, o dígito 0 nos bits 6:0 (polaridade de display_active_low).
        o_display_hex       : out   std_logic_vector(7 * display_digits - 1 downto 0);
        -- Valor do registrador do display, quatro bits por dígito.
        o_display_value     : out   std_logic_vector(4 * display_digits - 1 downto 0);
        -- Virtual JTAG do display (o hospedeiro lê e escreve o registrador): clock da cadeia.
        i_display_tck       : in    std_logic                     := '0';
        -- Virtual JTAG do display: dado vindo do hospedeiro.
        i_display_tdi       : in    std_logic                     := '0';
        -- Virtual JTAG do display: dado para o hospedeiro.
        o_display_tdo       : out   std_logic;
        -- Virtual JTAG do display: registrador de instrução.
        i_display_ir_in     : in    std_logic_vector(1 downto 0)  := "00";
        -- Virtual JTAG do display: estado Capture-DR.
        i_display_state_cdr : in    std_logic                     := '0';
        -- Virtual JTAG do display: estado Shift-DR.
        i_display_state_sdr : in    std_logic                     := '0';
        -- Virtual JTAG do display: estado Update-DR.
        i_display_state_udr : in    std_logic                     := '0';
        -- Virtual JTAG do display: estado Update-IR.
        i_display_state_uir : in    std_logic                     := '0';
        -- Bandeira de falha que o hospedeiro grava no display ('1' = houve falha).
        o_display_fail      : out   std_logic;
        -- Virtual JTAG da UART via JTAG: clock da cadeia.
        i_uart_tck          : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: dado vindo do hospedeiro.
        i_uart_tdi          : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: dado para o hospedeiro.
        o_uart_tdo          : out   std_logic;
        -- Virtual JTAG da UART via JTAG: registrador de instrução.
        i_uart_ir_in        : in    std_logic_vector(1 downto 0)  := "00";
        -- Virtual JTAG da UART via JTAG: estado Capture-DR.
        i_uart_state_cdr    : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: estado Shift-DR.
        i_uart_state_sdr    : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: estado Update-DR.
        i_uart_state_udr    : in    std_logic                     := '0';
        -- Virtual JTAG da UART via JTAG: estado Update-IR.
        i_uart_state_uir    : in    std_logic                     := '0';
        -- Linha serial de recepção da UART via pinos.
        i_uart_rx           : in    std_logic                     := '1';
        -- Linha serial de transmissão da UART via pinos.
        o_uart_tx           : out   std_logic
    );
end entity soc;

architecture behaviour of soc is

    -- Tamanho da BOOT_MEMORY em KiB: onde a ROM começa, o que a cache de instruções usa para reconhecê-la.
    constant BOOT_KIB : natural := boot_memory_size_bytes / 1024;

    -- Existe cache de dados no núcleo, do config_pkg; sem ela, a RAM via porta é acessada direto, palavra a palavra.
    constant HAS_DCACHE : boolean := work.config_pkg.HAS_DCACHE;
    -- Interrupções de máquina, do config_pkg: o CLINT e o controlador externo ficam na janela de periféricos e as
    -- três linhas chegam ao núcleo, que só as habilita com Zicsr.
    constant HAS_INTERRUPTS : boolean := work.config_pkg.HAS_INTERRUPTS;

    -- A ROM é alcançada pela porta do núcleo: está fora do chip ou atrás da cache de instruções.
    constant ROM_PORT : boolean := rom_external or has_icache;
    -- A RAM é alcançada pela porta do núcleo: está fora do chip ou atrás da cache de dados.
    constant RAM_PORT : boolean := ram_external or HAS_DCACHE;

    -- O papel de E/S existe: pedido pelo generic e com largura maior que zero.
    constant HAS_SWITCHES_ROLE : boolean := has_switches and switches_width > 0;
    -- O papel dos botões existe: pedido pelo generic e com largura maior que zero.
    constant HAS_KEYS_ROLE     : boolean := has_keys and keys_width > 0;
    -- O papel do display existe: pedido pelo generic e com pelo menos um dígito.
    constant HAS_DISPLAY_ROLE  : boolean := has_display and display_digits > 0;

    -- Há algum periférico na janela de periféricos: o CLINT e o PLIC, ou os do topo da placa.
    constant HAS_PERIPHERALS : boolean :=
        HAS_INTERRUPTS or HAS_SWITCHES_ROLE or HAS_KEYS_ROLE or HAS_DISPLAY_ROLE or has_uart_jtag or has_uart_pins
        or has_timer;

    -- Linhas do PLIC: o identificador da fonte de cada periférico, o mesmo em toda plataforma (as listas
    -- `interrupts.sources` dos platform.yaml repetem estes números, e `make check-irq-sources` os confere).
    -- UART serial pelos pinos.
    constant LINE_UART      : positive := 1;
    -- UART sobre JTAG.
    constant LINE_UART_JTAG : positive := 2;
    -- Chaves SW (GPIO).
    constant LINE_SWITCHES  : positive := 3;
    -- Botões KEY (GPIO).
    constant LINE_KEYS      : positive := 4;
    -- Temporizador de uso geral.
    constant LINE_TIMER     : positive := 5;
    -- Controlador de FLASH (só a plataforma de0-cv tem o chip).
    constant LINE_FLASH     : positive := 6;

    -- Início, em KiB, da seleção pelo endereço registrado da cache de instruções; -1 usa a porta de seleção.

    function ic_select_from (fast : boolean; start_kib : natural) return integer is
    begin

        if fast then
            return start_kib;
        end if;

        return -1;

    end function ic_select_from;

    -- Base, em KiB, do alias da FLASH que a cache de dados entrega ao roteador (0x20000000, bits 31:26 em "001000").
    constant FLASH_ALIAS_BASE_KIB : natural := 2 ** 19;
    -- Fim exclusivo, em KiB, do alias da FLASH (0x40000000), o dobro da base.
    constant FLASH_ALIAS_END_KIB  : natural := 2 * FLASH_ALIAS_BASE_KIB;

    -- Base da região da ROM, em KiB, nos endereços que o roteador dos dados vê: a cache de dados os
    -- troca pelos do alias da FLASH, e sem ela chegam os do mapa.
    constant D_ROM_BASE_KIB : natural := pick(HAS_DCACHE, FLASH_ALIAS_BASE_KIB, BOOT_KIB);
    -- Fim exclusivo da região da ROM, em KiB, nos endereços que o roteador dos dados vê.
    constant D_ROM_END_KIB  : natural := pick(HAS_DCACHE, FLASH_ALIAS_END_KIB, rom_end_kib);

    -- Bit da janela de um periférico: o do índice quando ele existe e zero quando não existe.

    function slot_vec (present : boolean; id : natural) return std_logic_vector is
    begin

        if present then
            return std_logic_vector(to_unsigned(2 ** id, 8));
        end if;

        return x"00";

    end function slot_vec;

    -- Janela do CLINT (existe com HAS_INTERRUPTS).
    constant SLOT_CLINT      : std_logic_vector(7 downto 0) := slot_vec(HAS_INTERRUPTS, clint_id);
    -- Janela do PLIC (existe com HAS_INTERRUPTS).
    constant SLOT_PLIC       : std_logic_vector(7 downto 0) := slot_vec(HAS_INTERRUPTS, plic_id);
    -- Janela do temporizador.
    constant SLOT_TIMER      : std_logic_vector(7 downto 0) := slot_vec(has_timer, timer_id);
    -- Janela das chaves.
    constant SLOT_SWITCHES   : std_logic_vector(7 downto 0) := slot_vec(HAS_SWITCHES_ROLE, switches_id);
    -- Janela dos botões.
    constant SLOT_KEYS       : std_logic_vector(7 downto 0) := slot_vec(HAS_KEYS_ROLE, keys_id);
    -- Janela do display.
    constant SLOT_DISPLAY    : std_logic_vector(7 downto 0) := slot_vec(HAS_DISPLAY_ROLE, display_id);
    -- Janela da UART via JTAG.
    constant SLOT_UART_JTAG  : std_logic_vector(7 downto 0) := slot_vec(has_uart_jtag, uart_jtag_id);
    -- Janela da UART via pinos.
    constant SLOT_UART_PINS  : std_logic_vector(7 downto 0) := slot_vec(has_uart_pins, uart_pins_id);
    -- Janela do controlador de FLASH.
    constant SLOT_FLASH_CTRL : std_logic_vector(7 downto 0) :=
        slot_vec(has_flash_ctrl, flash_ctrl_id);

    -- Janelas ocupadas pelos periféricos presentes, uma por bit.
    constant SLOTS_USED : std_logic_vector(7 downto 0) :=
        SLOT_CLINT or SLOT_PLIC or SLOT_TIMER or SLOT_SWITCHES or SLOT_KEYS or SLOT_DISPLAY or
        SLOT_UART_JTAG or SLOT_UART_PINS or SLOT_FLASH_CTRL;
    -- Soma das janelas dos presentes: é igual a SLOTS_USED só quando nenhum índice se repete.
    constant SLOTS_SUM  : natural                      :=
        to_integer(unsigned(SLOT_CLINT)) + to_integer(unsigned(SLOT_PLIC)) +
        to_integer(unsigned(SLOT_TIMER)) + to_integer(unsigned(SLOT_SWITCHES)) +
        to_integer(unsigned(SLOT_KEYS)) + to_integer(unsigned(SLOT_DISPLAY)) +
        to_integer(unsigned(SLOT_UART_JTAG)) + to_integer(unsigned(SLOT_UART_PINS)) +
        to_integer(unsigned(SLOT_FLASH_CTRL));

    -- Tamanho máximo, em KiB, de uma região que a janela das caches cobre.
    constant CACHE_WINDOW_KIB : natural := 2 ** (cache_window_bits - 10);

    -- Sinais do núcleo: busca de instrução e FLASH interna.
    signal if_addr     : std_logic_vector(31 downto 0);
    -- Habilitação de leitura da busca de instrução ('1' = lê).
    signal if_rden     : std_logic;
    -- Endereço da segunda porta da FLASH (estágio MEM).
    signal flash_addr2 : std_logic_vector(31 downto 0);
    -- Habilitação de leitura da segunda porta da FLASH ('1' = lê).
    signal flash_rden2 : std_logic;

    -- Sinais do núcleo: RAM interna.
    signal ram_addr    : std_logic_vector(31 downto 0);
    -- Dado de escrita na RAM do núcleo.
    signal ram_wdata   : std_logic_vector(31 downto 0);
    -- Habilitação geral da RAM do núcleo (estágio MEM).
    signal ram_en      : std_logic;
    -- Habilitação de escrita da RAM do núcleo ('1' = escreve).
    signal ram_wren    : std_logic;
    -- Habilitação de leitura da RAM do núcleo ('1' = lê).
    signal ram_rden    : std_logic;
    -- Habilitação de bytes da escrita na RAM do núcleo.
    signal ram_byteena : std_logic_vector(3 downto 0);

    -- Interrupções de máquina do núcleo: timer (MTIP) e software (MSIP) do CLINT, externa (MEIP) do controlador.
    signal irq_timer      : std_logic                                 := '0';
    -- Endereço de dado em uma página que a cache de dados não guarda (has_dcache_bypass).
    signal dc_bypass      : std_logic                                 := '0';
    -- mtime do CLINT, que o CSR time do núcleo espelha (zero sem CLINT).
    signal clint_mtime    : std_logic_vector(63 downto 0)             := (others => '0');
    -- Interrupção de software de máquina (MSIP), saída do CLINT.
    signal irq_software   : std_logic                                 := '0';
    -- As três linhas de interrupção como o núcleo as recebe (direto, ou por um registrador com registered_irqs).
    signal irq_timer_q    : std_logic                                 := '0';
    -- Interrupção de software de máquina (MSIP) como o núcleo a recebe.
    signal irq_software_q : std_logic                                 := '0';
    -- Interrupção externa de máquina (MEIP) como o núcleo a recebe.
    signal irq_external_q : std_logic                                 := '0';
    -- Interrupção externa de máquina (MEIP), saída do PLIC.
    signal irq_external   : std_logic                                 := '0';
    -- Linhas de interrupção dos periféricos para o PLIC; uma ausente fica em zero.
    signal irq_lines      : std_logic_vector(plic_n_sources downto 1) := (others => '0');

    -- Janela de periféricos: deslocamento de palavra dentro do periférico (a janela do PLIC é a maior).
    signal p_addr    : std_logic_vector(plic_addr_width - 1 downto 0);
    -- Janela de periféricos: dado de escrita.
    signal p_wdata   : std_logic_vector(31 downto 0);
    -- Janela de periféricos: habilita de bytes da escrita.
    signal p_byteena : std_logic_vector(3 downto 0);
    -- Janela de periféricos: pulso de escrita, um bit por periférico.
    signal p_we      : std_logic_vector(7 downto 0);
    -- Janela de periféricos: pulso de leitura, um bit por periférico.
    signal p_re      : std_logic_vector(7 downto 0);
    -- Janela de periféricos: dados lidos, 32 bits por periférico.
    signal p_rdata   : std_logic_vector(8 * 32 - 1 downto 0) := (others => '0');

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
    signal sdram_ready   : std_logic                     := '1';
    -- Avanço do pipeline do núcleo liberado pela memória ('1' = avança).
    signal mem_advance   : std_logic;

    -- Sinais do núcleo: cache de instruções.
    signal ic_data  : std_logic_vector(31 downto 0) := (others => '0');
    -- Cache de instruções pronta com a palavra pedida ('1' = pronta).
    signal ic_ready : std_logic                     := '1';
    -- Seleciona a cache de instruções para a região da ROM ('1' = selecionada).
    signal ic_sel   : std_logic;
    -- Invalidação da cache de instruções pelo FENCE.I ('1' = invalida).
    signal ic_inval : std_logic;
    -- Pedido de flush da cache de dados que o FENCE.I do núcleo faz antes de invalidar a cache de instruções.
    signal dc_flush : std_logic;

    -- Pulso de retirada de instrução do núcleo, que o testbench conta para o CPI.
    signal core_retire : std_logic;

    -- Eventos das caches e da FLASH para o Zihpm.
    signal ic_miss        : std_logic := '0';
    -- Pulso de falha (miss) na cache de dados, evento do Zihpm.
    signal dc_miss        : std_logic := '0';
    -- Chip de FLASH ocupado com um acesso, evento do Zihpm ('1' = ocupado).
    signal flash_busy     : std_logic;
    -- Eventos externos do Zihpm: bit 0 falha de instrução, bit 1 falha de dados, bit 2 FLASH ocupada.
    signal hpm_ext_events : std_logic_vector(2 downto 0);

    -- Interconexão e cache de dados: lado do núcleo e lado da memória.
    signal m_addr    : std_logic_vector(31 downto 0);
    -- Interconexão do núcleo para a cache de dados: dado de escrita.
    signal m_wdata   : std_logic_vector(31 downto 0);
    -- Interconexão do núcleo para a cache de dados: habilitação de bytes da escrita.
    signal m_byteena : std_logic_vector(3 downto 0);
    -- Interconexão do núcleo para a cache de dados: habilitação de leitura ('1' = lê).
    signal m_rden    : std_logic;
    -- Interconexão do núcleo para a cache de dados: habilitação de escrita ('1' = escreve).
    signal m_wren    : std_logic;
    -- Interconexão do núcleo para a cache de dados: acesso concluído ('1' = pronto).
    signal m_ready   : std_logic;
    -- Interconexão do núcleo para a cache de dados: dado lido.
    signal m_rdata   : std_logic_vector(31 downto 0);
    -- Cache de dados, lado da memória: endereço de byte do acesso.
    signal dd_addr   : std_logic_vector(31 downto 0);
    -- Cache de dados, lado da memória: dado de escrita.
    signal dd_wdata  : std_logic_vector(31 downto 0);
    -- Cache de dados, lado da memória: habilitação de bytes da escrita.
    signal dd_be     : std_logic_vector(3 downto 0);
    -- Cache de dados, lado da memória: habilitação de leitura ('1' = lê).
    signal dd_rden   : std_logic;
    -- Cache de dados, lado da memória: habilitação de escrita ('1' = escreve).
    signal dd_wren   : std_logic;
    -- Cache de dados, lado da memória: pedido de linha inteira de cache ('1' = acesso em linha).
    signal dd_line   : std_logic;
    -- Cache de dados, lado da memória: avanço para a próxima palavra da linha ('1' = avança).
    signal dd_adv    : std_logic;
    -- Cache de dados, lado da memória: acesso concluído ('1' = pronto).
    signal dd_ready  : std_logic;
    -- Cache de dados, lado da memória: dado lido.
    signal dd_rdata  : std_logic_vector(31 downto 0);
    -- Cache de dados, lado da memória: linha a escrever, barramento largo de 96 bits.
    signal dd_wdx    : std_logic_vector(95 downto 0);
    -- Cache de dados, lado da memória: linha lida, barramento largo de 96 bits.
    signal dd_rdx    : std_logic_vector(95 downto 0);
    -- Cache de dados concluiu o acesso pendente ('1' = concluído).
    signal dc_done   : std_logic;
    -- Cache de dados ocupada com um acesso ao chip ('1' = ocupada).
    signal dc_busy   : std_logic;

    -- Cache de instruções: lado da memória.
    signal id_addr  : std_logic_vector(31 downto 0);
    -- Cache de instruções, lado da memória: habilitação de leitura ('1' = lê).
    signal id_rden  : std_logic;
    -- Cache de instruções, lado da memória: avanço para a próxima palavra da linha ('1' = avança).
    signal id_adv   : std_logic;
    -- Cache de instruções, lado da memória: acesso concluído ('1' = pronto).
    signal id_ready : std_logic;
    -- Cache de instruções, lado da memória: dado lido.
    signal id_rdata : std_logic_vector(31 downto 0);
    -- Cache de instruções, lado da memória: pedido de linha inteira de cache ('1' = acesso em linha).
    signal id_line  : std_logic;
    -- Cache de instruções, lado da memória: linha lida, barramento largo de 96 bits.
    signal id_rdx   : std_logic_vector(95 downto 0);

    -- Roteadores por região (as duas memórias externas): lado do chip de RAM de cada um.
    signal si_addr  : std_logic_vector(31 downto 0);
    -- Roteador da ROM para o chip de RAM: dado de escrita.
    signal si_wdata : std_logic_vector(31 downto 0);
    -- Roteador da ROM para o chip de RAM: habilitação de bytes da escrita.
    signal si_be    : std_logic_vector(3 downto 0);
    -- Roteador da ROM para o chip de RAM: habilitação de leitura ('1' = lê).
    signal si_rden  : std_logic;
    -- Roteador da ROM para o chip de RAM: habilitação de escrita ('1' = escreve).
    signal si_wren  : std_logic;
    -- Roteador da ROM para o chip de RAM: pedido de linha inteira de cache ('1' = acesso em linha).
    signal si_line  : std_logic;
    -- Roteador da ROM para o chip de RAM: avanço para a próxima palavra da linha ('1' = avança).
    signal si_adv   : std_logic;
    -- Roteador da ROM para o chip de RAM: acesso concluído ('1' = pronto).
    signal si_ready : std_logic;
    -- Roteador da ROM para o chip de RAM: dado lido.
    signal si_rdata : std_logic_vector(31 downto 0);
    -- Roteador da ROM para o chip de RAM: linha a escrever, barramento largo de 96 bits.
    signal si_wdx   : std_logic_vector(95 downto 0);
    -- Roteador da ROM para o chip de RAM: linha lida, barramento largo de 96 bits.
    signal si_rdx   : std_logic_vector(95 downto 0);
    -- Roteador de dados para o chip de RAM: endereço de byte do acesso.
    signal sd_addr  : std_logic_vector(31 downto 0);
    -- Roteador de dados para o chip de RAM: dado de escrita.
    signal sd_wdata : std_logic_vector(31 downto 0);
    -- Roteador de dados para o chip de RAM: habilitação de bytes da escrita.
    signal sd_be    : std_logic_vector(3 downto 0);
    -- Roteador de dados para o chip de RAM: habilitação de leitura ('1' = lê).
    signal sd_rden  : std_logic;
    -- Roteador de dados para o chip de RAM: habilitação de escrita ('1' = escreve).
    signal sd_wren  : std_logic;
    -- Roteador de dados para o chip de RAM: pedido de linha inteira de cache ('1' = acesso em linha).
    signal sd_line  : std_logic;
    -- Roteador de dados para o chip de RAM: avanço para a próxima palavra da linha ('1' = avança).
    signal sd_adv   : std_logic;
    -- Roteador de dados para o chip de RAM: acesso concluído ('1' = pronto).
    signal sd_ready : std_logic;
    -- Roteador de dados para o chip de RAM: dado lido.
    signal sd_rdata : std_logic_vector(31 downto 0);
    -- Roteador de dados para o chip de RAM: linha a escrever, barramento largo de 96 bits.
    signal sd_wdx   : std_logic_vector(95 downto 0);
    -- Roteador de dados para o chip de RAM: linha lida, barramento largo de 96 bits.
    signal sd_rdx   : std_logic_vector(95 downto 0);

    -- Roteadores por região (as duas memórias externas): lado do chip de FLASH.
    -- Endereço e dado lido dos roteadores A, B e C do chip de FLASH.
    signal fa_addr  : std_logic_vector(31 downto 0);
    -- Roteador A, lado da FLASH: dado lido.
    signal fa_rdata : std_logic_vector(31 downto 0);
    -- Roteador B, lado da FLASH: endereço.
    signal fb_addr  : std_logic_vector(31 downto 0);
    -- Roteador B, lado da FLASH: dado lido.
    signal fb_rdata : std_logic_vector(31 downto 0);
    -- Roteador C, lado da FLASH: endereço.
    signal fc_addr  : std_logic_vector(31 downto 0);
    -- Roteador C, lado da FLASH: dado lido.
    signal fc_rdata : std_logic_vector(31 downto 0);
    -- Roteador A para o chip de FLASH: leitura, pedido de linha, avanço e resposta pronta.
    signal fa_rden  : std_logic;
    -- Roteador A, lado da FLASH: pedido de linha de cache.
    signal fa_line  : std_logic;
    -- Roteador A, lado da FLASH: avanço para a próxima palavra da linha.
    signal fa_adv   : std_logic;
    -- Roteador A, lado da FLASH: acesso concluído.
    signal fa_ready : std_logic;
    -- Roteador B para o chip de FLASH: leitura, pedido de linha, avanço e resposta pronta.
    signal fb_rden  : std_logic;
    -- Roteador B, lado da FLASH: pedido de linha de cache.
    signal fb_line  : std_logic;
    -- Roteador B, lado da FLASH: avanço para a próxima palavra da linha.
    signal fb_adv   : std_logic;
    -- Roteador B, lado da FLASH: acesso concluído.
    signal fb_ready : std_logic;
    -- Roteador C para o chip de FLASH: leitura, pedido de linha, avanço e resposta pronta.
    signal fc_rden  : std_logic;
    -- Roteador C, lado da FLASH: pedido de linha de cache.
    signal fc_line  : std_logic;
    -- Roteador C, lado da FLASH: avanço para a próxima palavra da linha.
    signal fc_adv   : std_logic;
    -- Roteador C, lado da FLASH: acesso concluído.
    signal fc_ready : std_logic;
    -- Linhas lidas dos roteadores A, B e C, barramentos largos de 96 bits.
    signal fa_rdx   : std_logic_vector(95 downto 0);
    -- Roteador B, lado da FLASH: linha larga lida de 96 bits.
    signal fb_rdx   : std_logic_vector(95 downto 0);
    -- Roteador C, lado da FLASH: linha larga lida de 96 bits.
    signal fc_rdx   : std_logic_vector(95 downto 0);

    -- Portas do chip de RAM externo: dados e instruções.
    signal rc_d_addr  : std_logic_vector(31 downto 0) := (others => '0');
    -- Porta de dados do chip de RAM externo: dado de escrita.
    signal rc_d_wdata : std_logic_vector(31 downto 0) := (others => '0');
    -- Porta de dados do chip de RAM externo: habilitação de bytes da escrita.
    signal rc_d_be    : std_logic_vector(3 downto 0)  := (others => '0');
    -- Porta de dados do chip de RAM externo: habilitação de leitura ('1' = lê).
    signal rc_d_rden  : std_logic                     := '0';
    -- Porta de dados do chip de RAM externo: habilitação de escrita ('1' = escreve).
    signal rc_d_wren  : std_logic                     := '0';
    -- Porta de dados do chip de RAM externo: pedido de linha inteira de cache ('1' = acesso em linha).
    signal rc_d_line  : std_logic                     := '0';
    -- Porta de dados do chip de RAM externo: avanço para a próxima palavra da linha ('1' = avança).
    signal rc_d_adv   : std_logic                     := '0';
    -- Porta de dados do chip de RAM externo: linha a escrever, barramento largo de 96 bits.
    signal rc_d_wdx   : std_logic_vector(95 downto 0) := (others => '0');
    -- Porta de dados do chip de RAM externo: acesso concluído ('1' = pronto).
    signal rc_d_ready : std_logic;
    -- Porta de dados do chip de RAM externo: dado lido.
    signal rc_d_rdata : std_logic_vector(31 downto 0);
    -- Porta de dados do chip de RAM externo: linha lida, barramento largo de 96 bits.
    signal rc_d_rdx   : std_logic_vector(95 downto 0);
    -- Porta de instruções do chip de RAM externo: endereço de byte do acesso.
    signal rc_i_addr  : std_logic_vector(31 downto 0) := (others => '0');
    -- Porta de instruções do chip de RAM externo: habilitação de leitura ('1' = lê).
    signal rc_i_rden  : std_logic                     := '0';
    -- Porta de instruções do chip de RAM externo: pedido de linha inteira de cache ('1' = acesso em linha).
    signal rc_i_line  : std_logic                     := '0';
    -- Porta de instruções do chip de RAM externo: avanço para a próxima palavra da linha ('1' = avança).
    signal rc_i_adv   : std_logic                     := '0';
    -- Porta de instruções do chip de RAM externo: acesso concluído ('1' = pronto).
    signal rc_i_ready : std_logic;
    -- Porta de instruções do chip de RAM externo: dado lido.
    signal rc_i_rdata : std_logic_vector(31 downto 0);
    -- Porta de instruções do chip de RAM externo: linha lida, barramento largo de 96 bits.
    signal rc_i_rdx   : std_logic_vector(95 downto 0);

begin

    assert boot_memory_size_bytes mod 1024 = 0
        report "boot_memory_size_bytes deve ser múltiplo de 1 KiB"
        severity failure;

    -- ---------------------------------------------------------------------------
    -- Validação dos generics: cada regra vale no RTL e em todo platform.yaml, e a
    -- mensagem traz o nome do generic e a causa.
    -- ---------------------------------------------------------------------------

    -- A BOOT_MEMORY é endereçada por bits do endereço, então o tamanho é potência de dois.
    assert is_power_of_two(boot_memory_size_bytes)
        report "boot_memory_size_bytes deve ser potência de dois, "
               & "o endereço da BOOT_MEMORY é um corte de bits"
        severity failure;

    -- O mapa é ordenado, sem sobreposição: BOOT_MEMORY, ROM, RAM, janela externa e janela de
    -- periféricos.
    assert rom_end_kib >= BOOT_KIB
        report "rom_end_kib deve ser no mínimo o tamanho da BOOT_MEMORY em KiB, "
               & "a ROM começa logo depois dela"
        severity failure;
    assert ram_base_kib >= rom_end_kib
        report "ram_base_kib deve ser no mínimo rom_end_kib, a RAM não pode sobrepor a ROM"
        severity failure;
    assert ram_end_kib > ram_base_kib
        report "ram_end_kib deve ser maior que ram_base_kib, a RAM precisa de ao menos 1 KiB"
        severity failure;
    assert ext_base_kib >= ram_end_kib
        report "ext_base_kib deve ser no mínimo ram_end_kib, a janela externa não pode sobrepor a RAM"
        severity failure;
    assert periph_base_kib >= ext_base_kib
        report "periph_base_kib deve ser no mínimo ext_base_kib, "
               & "a janela de periféricos vem depois da externa"
        severity failure;

    -- O núcleo lê o mapa do config_pkg da plataforma, e os genéricos do SoC (que o topo lê do pacote do mapa)
    -- têm de concordar com ele, senão o roteamento do SoC e a decodificação do núcleo divergem.
    assert shift_left(resize(to_unsigned(rom_end_kib, 32), work.config_pkg.ADDR_BITS + 1), 10) = work.config_pkg.ROM_END
        report "rom_end_kib difere de ROM_END do config_pkg"
        severity failure;
    assert shift_left(resize(to_unsigned(ram_base_kib, 32), work.config_pkg.ADDR_BITS + 1), 10) =
         work.config_pkg.RAM_BASE
        report "ram_base_kib difere de RAM_BASE do config_pkg"
        severity failure;
    assert shift_left(resize(to_unsigned(ram_end_kib, 32), work.config_pkg.ADDR_BITS + 1), 10) = work.config_pkg.RAM_END
        report "ram_end_kib difere de RAM_END do config_pkg"
        severity failure;
    assert shift_left(resize(to_unsigned(ext_base_kib, 32), work.config_pkg.ADDR_BITS + 1), 10) =
         work.config_pkg.EXT_BASE
        report "ext_base_kib difere de EXT_BASE do config_pkg"
        severity failure;
    assert shift_left(resize(to_unsigned(periph_base_kib, 32), work.config_pkg.ADDR_BITS + 1), 10) =
         work.config_pkg.PERIPH_BASE
        report "periph_base_kib difere de PERIPH_BASE do config_pkg"
        severity failure;
    assert log2_exact(boot_memory_size_bytes) = work.config_pkg.BOOT_MEMORY_BITS
        report "boot_memory_size_bytes difere de BOOT_MEMORY_BITS do config_pkg"
        severity failure;
    assert ROM_PORT = work.config_pkg.ROM_EXTERNAL and RAM_PORT = work.config_pkg.RAM_EXTERNAL
        report "rom_external, ram_external e as caches diferem de ROM_EXTERNAL e RAM_EXTERNAL do config_pkg"
        severity failure;
    -- As regiões alcançadas pelas caches ou pela ponte de busca cabem na janela de
    -- 2**cache_window_bits bytes.
    assert (not ROM_PORT) or rom_end_kib <= BOOT_KIB + CACHE_WINDOW_KIB
        report "cache_window_bits pequeno demais, "
               & "a ROM (rom_end_kib menos a BOOT_MEMORY) não cabe na janela das caches"
        severity failure;
    assert (not (RAM_PORT and HAS_DCACHE)) or ram_end_kib <= ram_base_kib + CACHE_WINDOW_KIB
        report "cache_window_bits pequeno demais, "
               & "a RAM (ram_base_kib até ram_end_kib) não cabe na janela da cache de dados"
        severity failure;

    -- Cada cache tem ao menos duas linhas de 128 bits e tamanho em potência de dois.
    assert (not has_icache) or (icache_size_bits >= 256 and is_power_of_two(icache_size_bits))
        report "icache_size_bits deve ser potência de dois de pelo menos 256 bits com has_icache"
        severity failure;
    assert (not HAS_DCACHE) or (dcache_size_bits >= 256 and is_power_of_two(dcache_size_bits))
        report "dcache_size_bits deve ser potência de dois de pelo menos 256 bits com HAS_DCACHE"
        severity failure;

    -- Opções que só existem dentro de uma cache não valem sem ela.
    assert HAS_DCACHE or (not has_dcache_bypass)
        report "has_dcache_bypass exige HAS_DCACHE, a página de desvio só existe na cache de dados"
        severity failure;
    assert has_icache or (not fast_icache_select)
        report "fast_icache_select exige has_icache, "
               & "a seleção pelo endereço registrado só existe na cache de instruções"
        severity failure;

    -- A polaridade dos pinos da UART só tem efeito no papel de pinos.
    assert has_uart_pins or (not (uart_tx_invert or uart_rx_invert))
        report "uart_tx_invert e uart_rx_invert exigem has_uart_pins, "
               & "a polaridade só vale para os pinos TX e RX"
        severity failure;

    -- Dois periféricos presentes não dividem a mesma janela de 256 MiB da janela de periféricos.
    assert to_integer(unsigned(SLOTS_USED)) = SLOTS_SUM
        report "clint_id, plic_id, timer_id, switches_id, keys_id, display_id, uart_jtag_id, "
               & "uart_pins_id e flash_ctrl_id: dois periféricos presentes usam o mesmo índice"
        severity failure;

    o_retire      <= core_retire;
    o_if_addr     <= if_addr(31 downto 2);
    o_if_rden     <= if_rden;
    o_rom_addr2   <= flash_addr2(31 downto 2);
    o_rom_rden2   <= flash_rden2;
    o_ram_en      <= ram_en;
    o_ram_wren    <= ram_wren;
    o_ram_rden    <= ram_rden;
    o_ram_addr    <= ram_addr;
    o_ram_wdata   <= ram_wdata;
    o_ram_byteena <= ram_byteena;

    -- As respostas dos chips chegam pelas portas do SoC.
    flash_busy <= i_flash_busy;
    fc_ready   <= i_flash_ready;
    fc_rdata   <= i_flash_rdata;
    fc_rdx     <= i_flash_rdata_x;
    rc_d_ready <= i_ramd_ready;
    rc_d_rdata <= i_ramd_rdata;
    rc_d_rdx   <= i_ramd_rdata_x;
    rc_i_ready <= i_rami_ready;
    rc_i_rdata <= i_rami_rdata;
    rc_i_rdx   <= i_rami_rdata_x;

    -- As requisições aos chips saem pelas portas do SoC.
    o_flash_addr    <= fc_addr;
    o_flash_rden    <= fc_rden;
    o_flash_line    <= fc_line;
    o_flash_advance <= fc_adv;
    o_ramd_addr     <= rc_d_addr;
    o_ramd_wdata    <= rc_d_wdata;
    o_ramd_byteena  <= rc_d_be;
    o_ramd_rden     <= rc_d_rden;
    o_ramd_wren     <= rc_d_wren;
    o_ramd_line     <= rc_d_line;
    o_ramd_advance  <= rc_d_adv;
    o_ramd_wdata_x  <= rc_d_wdx;
    o_rami_addr     <= rc_i_addr;
    o_rami_rden     <= rc_i_rden;
    o_rami_line     <= rc_i_line;
    o_rami_advance  <= rc_i_adv;

    hpm_ext_events <= flash_busy & dc_miss & ic_miss;

    gen_irq_direct : if not registered_irqs generate
    begin
        irq_timer_q    <= irq_timer;
        irq_software_q <= irq_software;
        irq_external_q <= irq_external;
    end generate gen_irq_direct;

    gen_irq_registered : if registered_irqs generate
    begin

        p_irq_registers : process (i_clk_core) is
        begin

            if rising_edge(i_clk_core) then
                irq_timer_q    <= irq_timer;
                irq_software_q <= irq_software;
                irq_external_q <= irq_external;
            end if;

        end process p_irq_registers;

    end generate gen_irq_registered;

    u_core : entity work.core
        generic map (
            hpm_counters  => hpm_counters,
            hpm_width     => hpm_width,
            time_external => HAS_INTERRUPTS,
            periph_slots  => periph_slots
        )
        port map (
            o_trap             => open,
            o_retire           => core_retire,
            o_trap_cause       => open,
            o_trap_pc          => open,
            i_clk              => i_clk_core,
            i_rst              => i_rst,
            o_if_addr          => if_addr,
            o_if_rden          => if_rden,
            i_boot_memory_data => i_boot_data,
            i_flash_data       => i_rom_data,
            o_flash_addr2      => flash_addr2,
            o_flash_rden2      => flash_rden2,
            i_flash_data2      => i_rom_data2,
            o_ram_addr         => ram_addr,
            o_ram_wdata        => ram_wdata,
            i_ram_rdata        => i_ram_rdata,
            o_ram_en           => ram_en,
            o_ram_wren         => ram_wren,
            o_ram_rden         => ram_rden,
            o_ram_byteena      => ram_byteena,
            o_ext_addr         => sdram_addr,
            o_ext_wdata        => sdram_wdata,
            o_ext_byteena      => sdram_byteena,
            o_ext_rden         => sdram_rden,
            o_ext_wren         => sdram_wren,
            i_ext_rdata        => sdram_rdata,
            i_ext_ready        => sdram_ready,
            o_mem_advance      => mem_advance,
            i_hpm_ext_events   => hpm_ext_events,
            i_irq_software     => irq_software_q,
            i_irq_timer        => irq_timer_q,
            i_mtime            => clint_mtime,
            i_irq_external     => irq_external_q,
            i_ic_data          => ic_data,
            i_ic_ready         => ic_ready,
            o_ic_sel           => ic_sel,
            o_ic_inval         => ic_inval,
            o_dc_flush         => dc_flush,
            i_dc_done          => dc_done
        );

    -- A interconexão separa a janela de periféricos e entrega o pedido de dados à cache de dados ou,
    -- sem ela, direto ao lado da memória. Existe quando há dados via porta ou interrupções (o CLINT
    -- e o controlador externo ficam na janela); sem dados via porta, o lado da memória responde zero.

    gen_data_port : if ROM_PORT or RAM_PORT or HAS_PERIPHERALS generate
    begin

        u_interconnect : entity work.ext_interconnect
            generic map (
                periph_addr_width => plic_addr_width
            )
            port map (
                i_clk         => i_clk_core,
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

    end generate gen_data_port;

    gen_no_data_port : if not (ROM_PORT or RAM_PORT) generate
    begin
        m_ready <= '1';
        m_rdata <= (others => '0');
    end generate gen_no_data_port;

    -- CLINT e controlador de interrupção externa, no domínio de clock do núcleo (sem sincronizador).

    gen_interrupts : if HAS_INTERRUPTS generate
    begin

        u_clint : entity work.clint
            generic map (
                tick_cycles => clint_tick_cycles
            )
            port map (
                i_clk          => i_clk_core,
                i_rst          => i_rst,
                i_data_in      => p_wdata,
                i_address      => p_addr(13 downto 0),
                i_write        => p_we(clint_id),
                o_data_out     => p_rdata(32 * clint_id + 31 downto 32 * clint_id),
                o_irq_timer    => irq_timer,
                o_irq_software => irq_software,
                o_mtime        => clint_mtime
            );

        u_plic : entity work.plic
            generic map (
                n_sources     => plic_n_sources,
                priority_bits => plic_priority_bits,
                addr_width    => plic_addr_width
            )
            port map (
                i_clk      => i_clk_core,
                i_rst      => i_rst,
                i_sources  => irq_lines,
                i_data_in  => p_wdata,
                i_address  => p_addr,
                i_write    => p_we(plic_id),
                i_read     => p_re(plic_id),
                o_data_out => p_rdata(32 * plic_id + 31 downto 32 * plic_id),
                o_meip     => irq_external
            );

    end generate gen_interrupts;

    -- Periféricos do topo da placa: chaves e botões (GPIO), display e as duas UART. Um periférico ausente deixa
    -- a saída em zero e o dado lido da janela em zero, como uma janela sem dispositivo.

    gen_switches : if HAS_SWITCHES_ROLE generate
    begin

        u_switches : entity work.gpio
            generic map (
                data_width => switches_width, active_low => switches_active_low
            )
            port map (
                i_clk        => i_clk_core,
                i_rst        => i_rst,
                i_data_in    => p_wdata(switches_width - 1 downto 0),
                i_address    => p_addr(3 downto 0),
                i_write      => p_we(switches_id),
                i_read       => p_re(switches_id),
                o_data_out   => p_rdata(32 * switches_id + switches_width - 1 downto 32 * switches_id),
                o_irq        => irq_lines(LINE_SWITCHES),
                io_gpio_pins => io_switches
            );

    end generate gen_switches;

    gen_keys : if HAS_KEYS_ROLE generate
    begin

        u_keys : entity work.gpio
            generic map (
                data_width => keys_width, active_low => keys_active_low
            )
            port map (
                i_clk        => i_clk_core,
                i_rst        => i_rst,
                i_data_in    => p_wdata(keys_width - 1 downto 0),
                i_address    => p_addr(3 downto 0),
                i_write      => p_we(keys_id),
                i_read       => p_re(keys_id),
                o_data_out   => p_rdata(32 * keys_id + keys_width - 1 downto 32 * keys_id),
                o_irq        => irq_lines(LINE_KEYS),
                io_gpio_pins => io_keys
            );

    end generate gen_keys;

    gen_display : if HAS_DISPLAY_ROLE generate
    begin

        u_display : entity work.seg_display
            generic map (
                digits => display_digits, active_low => display_active_low
            )
            port map (
                i_clk       => i_clk_core,
                i_rst       => i_rst,
                i_address   => p_addr(7 downto 0),
                i_data_in   => p_wdata,
                i_write     => p_we(display_id),
                o_rdata     => p_rdata(32 * display_id + 31 downto 32 * display_id),
                i_tck       => i_display_tck,
                i_tdi       => i_display_tdi,
                o_tdo       => o_display_tdo,
                i_ir_in     => i_display_ir_in,
                i_state_cdr => i_display_state_cdr,
                i_state_sdr => i_display_state_sdr,
                i_state_udr => i_display_state_udr,
                i_state_uir => i_display_state_uir,
                o_value     => o_display_value,
                o_fail      => o_display_fail,
                o_hex       => o_display_hex
            );

    end generate gen_display;

    -- O console é um só bloco de periférico; o backend ("jtag" ou "pinos") é a escolha da instância.

    gen_uart_jtag : if has_uart_jtag generate
    begin

        u_uart_jtag : entity work.console
            generic map (
                backend => "jtag"
            )
            port map (
                i_clk       => i_clk_core,
                i_rst       => i_rst,
                i_addr      => p_addr(7 downto 0),
                i_wdata     => p_wdata,
                i_we        => p_we(uart_jtag_id),
                i_re        => p_re(uart_jtag_id),
                o_rdata     => p_rdata(32 * uart_jtag_id + 31 downto 32 * uart_jtag_id),
                o_irq       => irq_lines(LINE_UART_JTAG),
                o_tx        => open,
                i_tck       => i_uart_tck,
                i_tdi       => i_uart_tdi,
                o_tdo       => o_uart_tdo,
                i_ir_in     => i_uart_ir_in,
                i_state_cdr => i_uart_state_cdr,
                i_state_sdr => i_uart_state_sdr,
                i_state_udr => i_uart_state_udr,
                i_state_uir => i_uart_state_uir
            );

    end generate gen_uart_jtag;

    gen_flash_ctrl : if has_flash_ctrl generate
    begin

        u_flash_ctrl : entity work.flash_controller
            port map (
                i_clk       => i_clk_core,
                i_rst       => i_rst,
                i_data_in   => p_wdata,
                i_address   => p_addr(2 downto 0),
                i_write     => p_we(flash_ctrl_id),
                i_read      => p_re(flash_ctrl_id),
                o_data_out  => p_rdata(32 * flash_ctrl_id + 31 downto 32 * flash_ctrl_id),
                o_irq       => irq_lines(LINE_FLASH),
                o_cmd_valid => o_flash_cmd_valid,
                o_cmd_op    => o_flash_cmd_op,
                o_cmd_addr  => o_flash_cmd_addr,
                i_busy      => i_flash_cmd_busy,
                i_wel       => i_flash_cmd_wel,
                i_refused   => i_flash_cmd_refused,
                i_buf_idx   => i_flash_buf_idx,
                o_buf_data  => o_flash_buf_data
            );

    end generate gen_flash_ctrl;

    gen_no_display : if not HAS_DISPLAY_ROLE generate
    begin
        o_display_tdo  <= '0';
        o_display_fail <= '0';
    end generate gen_no_display;

    gen_no_flash_ctrl : if not has_flash_ctrl generate
    begin
        o_flash_cmd_valid <= '0';
        o_flash_cmd_op    <= (others => '0');
        o_flash_cmd_addr  <= (others => '0');
        o_flash_buf_data  <= (others => '0');
    end generate gen_no_flash_ctrl;

    gen_timer : if has_timer generate
    begin

        u_timer : entity work.timer
            port map (
                i_clk      => i_clk_core,
                i_rst      => i_rst,
                i_data_in  => p_wdata,
                i_address  => p_addr(2 downto 0),
                i_write    => p_we(timer_id),
                i_read     => p_re(timer_id),
                o_data_out => p_rdata(32 * timer_id + 31 downto 32 * timer_id),
                o_irq      => irq_lines(LINE_TIMER),
                o_pwm      => open
            );

    end generate gen_timer;

    gen_uart_pins : if has_uart_pins generate
    begin

        u_uart_pins : entity work.console
            generic map (
                backend   => "pinos",
                tx_invert => uart_tx_invert,
                rx_invert => uart_rx_invert
            )
            port map (
                i_clk   => i_clk_core,
                i_rst   => i_rst,
                i_addr  => p_addr(7 downto 0),
                i_wdata => p_wdata,
                i_we    => p_we(uart_pins_id),
                i_re    => p_re(uart_pins_id),
                o_rdata => p_rdata(32 * uart_pins_id + 31 downto 32 * uart_pins_id),
                o_irq   => irq_lines(LINE_UART),
                i_rx    => i_uart_rx,
                o_tx    => o_uart_tx,
                o_tdo   => open
            );

    end generate gen_uart_pins;

    dc_bypass <= '1' when has_dcache_bypass and m_addr(31 downto 12) = bypass_page else '0';

    -- Com cache de dados, ela fica entre a interconexão e a memória.

    gen_dcache : if (ROM_PORT or RAM_PORT) and HAS_DCACHE generate
    begin

        u_dcache : entity work.dcache
            generic map (
                size_bits     => dcache_size_bits,
                window_bits   => cache_window_bits,
                write_through => true,
                rom_base_kib  => BOOT_KIB,
                rom_end_kib   => rom_end_kib
            )
            port map (
                i_clk          => i_clk_core,
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
                i_inval_region => i_inval_valid,
                i_inval_first  => i_inval_first,
                i_inval_last   => i_inval_last,
                o_flush_done   => dc_done,
                o_busy         => dc_busy,
                o_miss         => dc_miss,
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

    end generate gen_dcache;

    -- Sem cache de dados, o pedido da interconexão segue palavra a palavra, com os endereços do mapa.

    gen_no_dcache : if (ROM_PORT or RAM_PORT) and not HAS_DCACHE generate
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
    end generate gen_no_dcache;

    -- Instruções via porta, com cache: a cache de instruções entre o núcleo e a memória.

    gen_icache : if ROM_PORT and has_icache generate
    begin

        u_icache : entity work.icache
            generic map (
                size_bits    => icache_size_bits,
                window_bits  => cache_window_bits,
                rom_base_kib => BOOT_KIB,
                rom_end_kib  => rom_end_kib,
                sel_from_kib => ic_select_from(fast_icache_select, BOOT_KIB),
                check_addr   => not fast_icache_select
            )
            port map (
                i_clk          => i_clk_fetch,
                i_clk_cpu      => i_clk_core,
                i_rst          => i_rst,
                i_addr         => if_addr,
                i_sel          => ic_sel,
                o_ready        => ic_ready,
                o_data         => ic_data,
                i_invalidate   => ic_inval,
                i_inval_region => i_inval_valid,
                i_inval_first  => i_inval_first,
                i_inval_last   => i_inval_last,
                o_miss         => ic_miss,
                o_d_addr       => id_addr,
                o_d_rden       => id_rden,
                o_d_advance    => id_adv,
                i_d_ready      => id_ready,
                i_d_rdata      => id_rdata,
                o_d_line       => id_line,
                i_d_rdata_x    => id_rdx
            );

    end generate gen_icache;

    -- Instruções via porta, sem cache: a ponte de busca, que guarda só a linha corrente.

    gen_ifetch : if ROM_PORT and not has_icache generate
    begin

        u_ifetch : entity work.ifetch_bridge
            generic map (
                fetch_line   => true,
                window_bits  => cache_window_bits,
                rom_base_kib => BOOT_KIB,
                rom_end_kib  => rom_end_kib
            )
            port map (
                i_clk        => i_clk_core,
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

    end generate gen_ifetch;

    -- Sem a ROM via porta, a face do chip de FLASH fica parada.

    gen_flash_idle : if not ROM_PORT generate
    begin
        fc_addr <= (others => '0');
        fc_rden <= '0';
        fc_line <= '0';
        fc_adv  <= '0';
    end generate gen_flash_idle;

    -- Só a RAM via porta: o lado da memória dos dados fala direto com o chip de RAM.

    gen_direct_data : if RAM_PORT and not ROM_PORT generate
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
    end generate gen_direct_data;

    -- Só a ROM via porta: o roteador leva os dados da ROM à FLASH, e o que cai fora dela responde zero.

    gen_rom_only : if ROM_PORT and not RAM_PORT generate
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
    end generate gen_rom_only;

    -- A ROM via porta: o roteador dos dados e o árbitro entre a busca e os dados na FLASH.

    gen_rom_path : if ROM_PORT generate
    begin

        u_router_d : entity work.mem_region_router
            generic map (
                rom_base_kib => D_ROM_BASE_KIB,
                rom_end_kib  => D_ROM_END_KIB,
                hold_rdata   => not HAS_DCACHE
            )
            port map (
                i_clk       => i_clk_core,
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

        u_flash_arbiter : entity work.flash_arbiter
            port map (
                i_clk       => i_clk_core,
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

    end generate gen_rom_path;

    -- As duas memórias via porta: o roteador da busca separa a FLASH do chip de RAM, e o dos dados
    -- entrega o que não é da FLASH ao chip.

    gen_routed : if ROM_PORT and RAM_PORT generate
    begin

        u_router_i : entity work.mem_region_router
            port map (
                i_clk       => i_clk_core,
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
    end generate gen_routed;

end architecture behaviour;
