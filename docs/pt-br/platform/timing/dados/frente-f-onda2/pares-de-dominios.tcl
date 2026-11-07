lassign $argv PROJECT NPATHS MODEL
project_open $PROJECT
create_timing_netlist -model $MODEL
read_sdc
update_timing_netlist
foreach pair {{general[3] general[3]} {general[2] general[2]} {general[3] general[2]} {general[2] general[3]}} {
    lassign $pair f t
    set fc [get_clocks [format "pll_inst|altera_pll_i|%s.gpll~PLL_OUTPUT_COUNTER|divclk" $f]]
    set tc [get_clocks [format "pll_inst|altera_pll_i|%s.gpll~PLL_OUTPUT_COUNTER|divclk" $t]]
    set paths [get_timing_paths -setup -npaths $NPATHS -from_clock $fc -to_clock $tc]
    foreach_in_collection p $paths {
        puts [format "PATH\t%s\t%s\t%s\t%s\t%s\t%s" [get_clock_info -name $tc] \
            [get_path_info $p -slack] [get_path_info $p -data_delay] \
            [get_node_info -name [get_path_info $p -from]] \
            [get_node_info -name [get_path_info $p -to]] \
            [get_clock_info -name [get_path_info $p -from_clock]]]
    }
}
delete_timing_netlist
project_close
