// Propriedades do ext_interconnect, verificadas na netlist Verilog que o GHDL sintetiza do VHDL com a tabela padrão
// de janelas (oito janelas de 256 MiB em 0x80000000 | i << 28, 64 KiB de registradores cada, strict_periph ligado) e
// só a RAM (0x40000000 a 0x43FFFFFF) no barramento. O núcleo, a memória e os oito periféricos são entradas livres,
// presas ao contrato por suposições; as asserções são o que o interconector garante. Cinco registradores (dbg_*,
// adicionados a uma cópia da netlist) são expostos: o estado (0 livre, 1 pronto), a seleção do dado devolvido (0
// memória, 1 o dado guardado), o dado guardado, o dado lido no pulso e a marca de erro do acesso guardado. O dado de
// uma leitura vale no ciclo seguinte ao avanço, quando o núcleo o captura. Um acesso sem escravo (fora da memória e
// de toda janela, ou no padding de uma janela) termina com o error junto do ready e lê zero.
module props (input clk);
  (* anyseq *) wire rst, rden, wren, mem_advance, m_ready;
  (* anyseq *) wire [31:0] addr, wdata, m_rdata;
  (* anyseq *) wire [3:0] byteena;
  (* anyseq *) wire [255:0] p_rdata;
  wire ready, error, m_rden, m_wren, d_st, d_sel, d_err;
  wire [31:0] d_prq, d_pending;
  wire [31:0] rdata, m_addr, m_wdata, p_wdata;
  wire [3:0] m_be, p_be;
  wire [13:0] p_addr;
  wire [7:0] p_we, p_re;

  ext_interconnect dut (.i_clk(clk), .i_rst(rst), .i_addr(addr), .i_wdata(wdata), .i_byteena(byteena), .i_rden(rden),
    .i_wren(wren), .i_mem_advance(mem_advance), .o_ready(ready), .o_error(error), .o_rdata(rdata), .o_m_addr(m_addr),
    .o_m_wdata(m_wdata), .o_m_byteena(m_be), .o_m_rden(m_rden), .o_m_wren(m_wren), .i_m_ready(m_ready),
    .i_m_rdata(m_rdata), .o_p_addr(p_addr), .o_p_wdata(p_wdata), .o_p_byteena(p_be), .o_p_we(p_we), .o_p_re(p_re),
    .i_p_rdata(p_rdata), .dbg_st(d_st), .dbg_sel_wb(d_sel), .dbg_p_rdata_q(d_prq), .dbg_pending(d_pending),
    .dbg_err_q(d_err));

  // o modelo de decodificação: a janela acertada (bit 31), o índice dela e se o endereço cai nos registradores
  wire [2:0] id = addr[30:28];
  wire in_window = addr[31];
  wire in_regs = addr[27:16] == 12'd0;
  wire is_periph = in_window && in_regs;
  wire is_mem = addr[31:26] == 6'b010000;
  wire is_slow = !is_mem;
  wire active = rden || wren;
  wire [7:0] strobe = p_we | p_re;

  reg f_past_valid = 0;
  reg p_mem_done = 0, p_slow_done = 0;
  reg p_req = 0, p_adv = 0, p_ready = 0, p_rden = 0, p_wren = 0, p_slow = 0, p_start = 0, got = 0;
  reg [31:0] q_addr = 0, cap = 0, delivered = 0;
  reg cap_bad = 0;
  reg [7:0] p_strobe = 0;
  always @(posedge clk) begin
    f_past_valid <= 1;
    p_req <= active; p_adv <= mem_advance; p_ready <= ready; p_rden <= rden; p_wren <= wren; q_addr <= addr;
    p_mem_done <= f_past_valid && ready && mem_advance && rden && is_mem;
    p_slow_done <= f_past_valid && d_st && mem_advance && rden && is_slow;
    p_slow <= is_slow; p_strobe <= f_past_valid ? strobe : 8'd0;
    // o início de um acesso sem a memória: o interconector livre vê o pedido, e no ciclo seguinte está pronto
    p_start <= f_past_valid && !d_st && active && is_slow;
    // o dado do escravo selecionado (zero sem escravo) e a marca de erro, no ciclo em que o acesso é aceito
    if (!d_st && active && is_slow) begin
      cap_bad <= !is_periph;
      if (rden) cap <= is_periph ? p_rdata[32 * id +: 32] : 32'd0;
    end
    if (d_st && mem_advance && rden) delivered <= cap;
    if (rst) delivered <= 0;
  end

  // ---- o ambiente ----
  always @* if (!f_past_valid) assume (rst);
  always @* if (f_past_valid) assume (!rst);
  // o núcleo mantém o pedido e o endereço até avançar, e só avança com a resposta
  always @(posedge clk) if (f_past_valid && p_req && !p_adv)
    assume (rden == p_rden && wren == p_wren && addr == q_addr);
  always @* assume (!mem_advance || ready);
  always @* assume (!(rden && wren));
  // a memória só responde a um pedido dela
  always @* if (m_ready) assume (is_mem);

  always @(posedge clk) if (f_past_valid) begin
    // 1. Um só escravo por acesso: no máximo um bit de seleção, o da janela acertada pelo endereço.
    assert ((strobe & (strobe - 8'd1)) == 8'd0);
    if (strobe != 0) assert (strobe == (8'd1 << id) && p_we == (wren ? (8'd1 << id) : 8'd0) && p_re == (rden ? (8'd1 << id) : 8'd0));
    // 2. Memória e periférico se excluem: só o endereço da memória chega a ela, e o dela não chega a periférico.
    if (!is_mem) assert (!m_rden && !m_wren);
    else assert (strobe == 0 && m_rden == rden && m_wren == wren);
    // 3. O endereço, o dado e a máscara passam sem mudar.
    assert (m_addr == addr && m_wdata == wdata && m_be == byteena && p_wdata == wdata && p_be == byteena && p_addr == addr[15:2]);
    // 4. O pulso ao periférico dura um ciclo, só com o interconector livre e só numa janela e nos registradores;
    //    o acesso sem a memória termina no ciclo seguinte e a resposta dura até o avanço (nenhum acesso trava).
    if (strobe != 0) assert (!d_st && is_periph && active);
    if (p_start) assert (d_st && ready);
    if (p_ready && !p_adv && p_slow && d_st) assert (ready);
    // 5. Um acesso à memória é concluído quando a memória responde.
    if (is_mem && active) assert (ready == m_ready);
    // 6. O dado lido de um acesso sem a memória, no ciclo seguinte ao avanço, é o do escravo selecionado no pulso (zero
    //    sem escravo); o de uma leitura da memória vem direto dela, e a seleção volta à memória.
    if (!d_sel) assert (rdata == m_rdata);
    if (d_sel) assert (rdata == d_prq);
    if (p_slow_done) assert (d_sel && rdata == delivered);
    if (p_mem_done) assert (!d_sel);
    assert (d_prq == delivered);
    // O estado pronto vem de um pedido que continua na porta, e então guarda o dado lido no pulso.
    if (d_st) assert (p_req && !p_adv && is_slow);
    if (d_st && rden) assert (d_pending == cap);
    // 7. O error sobe junto com o ready de um acesso sem escravo (fora da memória e de toda janela, ou no padding de
    //    uma janela), só nele, e dura até o avanço; um acesso a escravo nunca o levanta.
    assert (error == (d_st && d_err));
    if (error) assert (ready);
    if (d_st) assert (d_err == cap_bad);
    if (d_st && is_periph) assert (!error);
    if (d_st && !is_periph) assert (error);
    if (d_st && cap_bad && rden) assert (d_pending == 32'd0);
    if (is_mem) assert (!error);
  end

`ifdef COVER
  always @(posedge clk) if (f_past_valid) begin
    cover (strobe != 0 && rden && id == 3'd4);
    cover (strobe != 0 && wren && id == 3'd5);
    cover (d_sel && ready);
    cover (!is_slow && m_ready && rden && !d_sel);
    cover (error && ready && rden);
    cover (error && ready && wren);
    cover (error && ready && in_window);
  end
`endif
endmodule
