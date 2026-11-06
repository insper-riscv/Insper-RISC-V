# Caminhos por numero de niveis de logica: um por destino, por dominio de destino.
lassign $argv PROJECT NPATHS
project_open $PROJECT
create_timing_netlist -model slow
read_sdc
update_timing_netlist
set pre "pll_inst|altera_pll_i|general\\\[%s\\\].gpll~PLL_OUTPUT_COUNTER|divclk"
foreach {nome clk} {c3 3 c2 2 sdram 0} {
    set tc [get_clocks [format "pll_inst|altera_pll_i|general\[%s\].gpll~PLL_OUTPUT_COUNTER|divclk" $clk]]
    set paths [get_timing_paths -setup -npaths $NPATHS -nworst 1 -to_clock $tc]
    foreach_in_collection p $paths {
        puts [format "LV\t%s\t%s\t%s\t%s\t%s\t%s\t%s" $nome [get_path_info $p -num_logic_levels] [get_path_info $p -slack] [get_path_info $p -data_delay] [get_node_info -name [get_path_info $p -from]] [get_node_info -name [get_path_info $p -to]] [get_clock_info -name [get_path_info $p -from_clock]]]
    }
}
set tc [get_clocks DRAM_CLK_pin]
foreach_in_collection p [get_timing_paths -setup -npaths $NPATHS -nworst 1 -to_clock $tc] {
    puts [format "LV\tdram_clk\t%s\t%s\t%s\t%s\t%s\t%s" [get_path_info $p -num_logic_levels] [get_path_info $p -slack] [get_path_info $p -data_delay] [get_node_info -name [get_path_info $p -from]] [get_node_info -name [get_path_info $p -to]] [get_clock_info -name [get_path_info $p -from_clock]]]
}
delete_timing_netlist
project_close
