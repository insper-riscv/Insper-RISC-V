# Lista os relógios que o derive_pll_clocks cria no netlist pós-síntese (create_timing_netlist -post_map, sem fitter) de
# um projeto m0 já sintetizado e os alvos (nós de relógio) de cada um. Rode na pasta de trabalho do m0_map.tcl:
#
#   quartus_sta -t m0_clocks.tcl
#
# Escreve "RELOGIO <nome> <alvo>" em relogios.txt.

load_package sta
project_open m0
create_timing_netlist -post_map
create_clock -name refclk -period 20.000 [get_ports refclk]
derive_pll_clocks -create_base_clocks
set fd [open relogios.txt w]
foreach_in_collection c [get_clocks *] {
    set nome [get_clock_info -name $c]
    set alvos [get_clock_info -targets $c]
    set lista {}
    foreach_in_collection a $alvos { lappend lista [get_node_info -name $a] }
    puts $fd "RELOGIO $nome $lista"
}
close $fd
delete_timing_netlist
project_close
