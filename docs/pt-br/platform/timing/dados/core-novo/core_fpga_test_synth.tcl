load_package flow
set seed 5
if {$argc >= 1} { set seed [lindex $quartus(args) 0] }
cd [file dirname [file normalize [info script]]]
project_open core_fpga_test
set_global_assignment -name OPTIMIZATION_MODE "HIGH PERFORMANCE EFFORT"
set_global_assignment -name SEED $seed
execute_flow -compile
project_close -dont_export_assignments
