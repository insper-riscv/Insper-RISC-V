// Propriedades do ext_interconnect, verificadas na netlist Verilog que o GHDL sintetiza do VHDL. O núcleo, a memória
// e os oito periféricos são entradas livres, presas ao contrato por suposições; as asserções são o que o
// interconector garante. Quatro registradores (dbg_*, adicionados a uma cópia da netlist) são expostos: o estado
// (0 livre, 1 pronto), a seleção do dado devolvido (0 memória, 1 o periférico lido), o dado do periférico
// guardado e o dado lido no pulso. O dado de uma leitura vale no ciclo seguinte ao avanço, quando o núcleo o captura.
module props (input clk);
  (* anyseq *) wire rst, rden, wren, mem_advance, m_ready;
  (* anyseq *) wire [31:0] addr, wdata, m_rdata;
  (* anyseq *) wire [3:0] byteena;
  (* anyseq *) wire [255:0] p_rdata;
  wire ready, m_rden, m_wren, d_st, d_sel;
  wire [31:0] d_prq, d_pending;
  wire [31:0] rdata, m_addr, m_wdata, p_wdata;
  wire [3:0] m_be, p_be;
  wire [13:0] p_addr;
  wire [7:0] p_we, p_re;

  ext_interconnect dut (.i_clk(clk), .i_rst(rst), .i_addr(addr), .i_wdata(wdata), .i_byteena(byteena), .i_rden(rden),
    .i_wren(wren), .i_mem_advance(mem_advance), .o_ready(ready), .o_rdata(rdata), .o_m_addr(m_addr), .o_m_wdata(m_wdata),
    .o_m_byteena(m_be), .o_m_rden(m_rden), .o_m_wren(m_wren), .i_m_ready(m_ready), .i_m_rdata(m_rdata), .o_p_addr(p_addr),
    .o_p_wdata(p_wdata), .o_p_byteena(p_be), .o_p_we(p_we), .o_p_re(p_re), .i_p_rdata(p_rdata),
    .dbg_st(d_st), .dbg_sel_wb(d_sel), .dbg_p_rdata_q(d_prq), .dbg_pending(d_pending));

  wire is_periph = addr[31];
  wire active = rden || wren;
  wire [2:0] id = addr[30:28];
  wire [7:0] strobe = p_we | p_re;

  reg f_past_valid = 0;
  reg p_mem_done = 0, p_per_done = 0;
  reg p_req = 0, p_adv = 0, p_ready = 0, p_rden = 0, p_wren = 0, p_periph = 0, got = 0;
  reg [31:0] q_addr = 0, cap = 0, delivered = 0;
  reg [7:0] p_strobe = 0;
  always @(posedge clk) begin
    f_past_valid <= 1;
    p_req <= active; p_adv <= mem_advance; p_ready <= ready; p_rden <= rden; p_wren <= wren; q_addr <= addr;
    p_mem_done <= f_past_valid && ready && mem_advance && rden && !is_periph;
    p_per_done <= f_past_valid && d_st && mem_advance && rden && is_periph;
    p_periph <= is_periph; p_strobe <= f_past_valid ? strobe : 8'd0;
    // o dado do periférico selecionado, no ciclo do pulso de leitura, e o dado entregue quando a leitura avança
    if (strobe != 0 && rden) cap <= p_rdata[32 * id +: 32];
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
  always @* if (m_ready) assume (!is_periph);

  always @(posedge clk) if (f_past_valid) begin
    // 1. Um só escravo por acesso: no máximo um bit de seleção, o do campo de identificação do endereço.
    assert ((strobe & (strobe - 8'd1)) == 8'd0);
    if (strobe != 0) assert (strobe == (8'd1 << id) && p_we == (wren ? (8'd1 << id) : 8'd0) && p_re == (rden ? (8'd1 << id) : 8'd0));
    // 2. Memória e periférico se excluem: o endereço de periférico não chega à memória, e o de memória não chega a periférico.
    if (is_periph) assert (!m_rden && !m_wren);
    else assert (strobe == 0 && m_rden == rden && m_wren == wren);
    // 3. O endereço, o dado e a máscara passam sem mudar.
    assert (m_addr == addr && m_wdata == wdata && m_be == byteena && p_wdata == wdata && p_be == byteena && p_addr == addr[15:2]);
    // 4. O pulso ao periférico dura um ciclo e só com o interconector livre; o acesso termina no ciclo seguinte e a
    //    resposta dura até o avanço (nenhum acesso trava).
    if (strobe != 0) assert (!d_st && is_periph && active);
    if (p_strobe != 0 && !p_adv) assert (ready && d_st);
    if (p_ready && !p_adv && p_periph && d_st) assert (ready);
    // 5. Um acesso à memória é concluído quando a memória responde.
    if (!is_periph && active) assert (ready == m_ready);
    // 6. O dado lido de um periférico, no ciclo seguinte ao avanço, é o do escravo selecionado no pulso; o de uma leitura
    //    da memória vem direto dela, e a seleção volta à memória.
    if (!d_sel) assert (rdata == m_rdata);
    if (d_sel) assert (rdata == d_prq);
    if (p_per_done) assert (d_sel && rdata == delivered);
    if (p_mem_done) assert (!d_sel);
    assert (d_prq == delivered);
    // O estado pronto vem de um pedido que continua na porta, e então guarda o dado lido no pulso.
    if (d_st) assert (p_req && !p_adv && is_periph);
    if (d_st && rden) assert (d_pending == cap);
  end

`ifdef COVER
  always @(posedge clk) if (f_past_valid) begin
    cover (strobe != 0 && rden && id == 3'd4);
    cover (strobe != 0 && wren && id == 3'd5);
    cover (d_sel && ready);
    cover (!is_periph && m_ready && rden && !d_sel);
  end
`endif
endmodule
