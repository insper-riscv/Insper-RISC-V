// Topo mínimo da medição M.0.2: um PLL de 50 MHz para dois relógios (100 MHz e 50 MHz com fase), cada
// um alimentando um contador, para o sintetizador não podar o PLL. O módulo m0_pll vem de um dos dois
// arquivos m0_pll_*.v, escolhido pelo m0_map.tcl.
module m0_top #(
	parameter FAMILY = "Cyclone V"
) (
	input  wire       refclk,
	input  wire       rst,
	output wire [1:0] o_msb,
	output wire       o_locked
);

	wire clk_a;
	wire clk_b;
	reg [15:0] cnt_a = 16'd0;
	reg [15:0] cnt_b = 16'd0;

	m0_pll #(.FAMILY(FAMILY)) pll_inst (
		.refclk   (refclk),
		.rst      (rst),
		.outclk_0 (clk_a),
		.outclk_1 (clk_b),
		.locked   (o_locked)
	);

	always @(posedge clk_a) cnt_a <= cnt_a + 16'd1;
	always @(posedge clk_b) cnt_b <= cnt_b + 16'd1;

	assign o_msb = {cnt_b[15], cnt_a[15]};

endmodule
