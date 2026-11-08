# Lista os átomos de PLL, de buffer de relógio e de Virtual JTAG do netlist pós-síntese (quartus_map) de um projeto m0
# já sintetizado, sem rodar fitter. Rode na pasta de trabalho do m0_map.tcl:
#
#   quartus_cdb -t m0_atoms.tcl
#
# Escreve "ATOMO <tipo> <nome>" em atomos.txt.

load_package atoms
project_open m0
read_atom_netlist -type map
set fd [open atomos.txt w]
foreach_in_collection a [get_atom_nodes] {
    set tipo [get_atom_node_info -key TYPE -node $a]
    if {[regexp -nocase {pll|clkctrl|clkbuf|jtag} $tipo]} {
        puts $fd "ATOMO $tipo [get_atom_node_info -key NAME -node $a]"
    }
}
close $fd
project_close
