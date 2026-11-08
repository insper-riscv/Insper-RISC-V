# Relatorio completo do pior caminho de cada par de relogios (modelo lento).
lassign $argv PROJECT OUT
project_open $PROJECT
create_timing_netlist -model slow
read_sdc
update_timing_netlist
foreach pair {{3 3} {2 3} {3 2} {2 2}} {
    lassign $pair f t
    set fc [get_clocks [format "pll_inst|altera_pll_i|general\[%s\].gpll~PLL_OUTPUT_COUNTER|divclk" $f]]
    set tc [get_clocks [format "pll_inst|altera_pll_i|general\[%s\].gpll~PLL_OUTPUT_COUNTER|divclk" $t]]
    report_timing -setup -npaths 3 -detail full_path -from_clock $fc -to_clock $tc -file ${OUT}-$f-$t.rpt
}
delete_timing_netlist
project_close
