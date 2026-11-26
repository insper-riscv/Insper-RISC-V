# SPDX-License-Identifier: Apache-2.0
# Fixed observer protocol; inputs are argument data, never evaluated as Tcl.
package require ::quartus::jtag
if {[llength $argv] != 4} {
    error "Usage: hardware_scan.tcl cable device configure|read markers"
}
lassign $argv cable device operation markers
if {$operation ni {configure read}} { error "Invalid operation" }
if {![regexp {^[0-9a-fA-F]{16}$} $markers]} { error "Invalid marker word" }
open_device -hardware_name $cable -device_name $device
device_lock -timeout 10000
try {
    if {$operation eq "configure"} {
        device_virtual_ir_shift -instance_index 4 -ir_value 0 -no_captured_ir_value
        device_virtual_dr_shift -instance_index 4 -length 64 -dr_value $markers -value_in_hex
        puts "CONFIGURED"
    } else {
        device_virtual_ir_shift -instance_index 4 -ir_value 1 -no_captured_ir_value
        # First capture may precede propagation of done through the two FFs.
        set zeros [string repeat 0 112]
        device_virtual_dr_shift -instance_index 4 -length 448 -dr_value $zeros -value_in_hex
        set result [device_virtual_dr_shift -instance_index 4 -length 448 -dr_value $zeros -value_in_hex]
        puts "METRICS=$result"
    }
} finally {
    device_unlock
    close_device
}
