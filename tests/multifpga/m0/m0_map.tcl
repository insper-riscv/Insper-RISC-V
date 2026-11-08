# Síntese (só quartus_map) de um caso mínimo da trilha M.0 numa família, numa pasta de trabalho descartável.
#
#   quartus_sh -t m0_map.tcl <caso> <família> <dispositivo> <pasta de trabalho>
#
# Casos: pll_altera_pll, pll_altpll (M.0.2) e vjtag (M.0.6). Escreve em <pasta de trabalho>/resultado.txt a linha
# "RESULTADO <caso> <família> <dispositivo> PASSA|FALHA". Os átomos do netlist pós-síntese saem do m0_atoms.tcl. Nunca
# programa placa nem roda fitter.

load_package flow

if {$argc != 4} {
    puts "Erro: uso: m0_map.tcl <caso> <família> <dispositivo> <pasta de trabalho>"
    exit 2
}
lassign $quartus(args) caso familia dispositivo trabalho
set aqui [file dirname [file normalize [info script]]]

file mkdir $trabalho
cd $trabalho
set projeto "m0"
project_new $projeto -overwrite
set_global_assignment -name FAMILY $familia
set_global_assignment -name DEVICE $dispositivo
set_global_assignment -name TOP_LEVEL_ENTITY [expr {$caso eq "vjtag" ? "m0_vjtag_top" : "m0_top"}]

switch -- $caso {
    pll_altera_pll {
        set_global_assignment -name VERILOG_FILE [file join $aqui pll m0_top.v]
        set_global_assignment -name VERILOG_FILE [file join $aqui pll m0_pll_altera_pll.v]
        set_parameter -name FAMILY $familia
    }
    pll_altpll {
        set_global_assignment -name VERILOG_FILE [file join $aqui pll m0_top.v]
        set_global_assignment -name VERILOG_FILE [file join $aqui pll m0_pll_altpll.v]
        set_parameter -name FAMILY $familia
    }
    vjtag {
        set_global_assignment -name VHDL_FILE [file join $aqui .. .. vhdl m0_vjtag_top.vhd]
    }
    default {
        puts "Erro: caso desconhecido '$caso'."
        exit 2
    }
}

set linhas {}
if {[catch {execute_module -tool map} msg]} {
    lappend linhas "RESULTADO $caso \"$familia\" $dispositivo FALHA"
    lappend linhas "MENSAGEM $msg"
} else {
    lappend linhas "RESULTADO $caso \"$familia\" $dispositivo PASSA"
}
set fd [open resultado.txt w]
puts $fd [join $linhas "\n"]
close $fd
project_close
