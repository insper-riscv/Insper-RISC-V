# Compila o projeto external-data em linha de comando, com modo de otimização e semente fixos para o resultado
# ser reproduzível. Rode de qualquer pasta, pelo Quartus:
#
#   quartus_sh -t src/cyclone-v/external-data/external-data_synth.tcl [semente] [map]
#
# O primeiro argumento é a semente do posicionamento (padrão 5). Com `map` no segundo argumento só a
# síntese roda (quartus_map), que basta para conferir que os caminhos e as entidades resolvem. As
# atribuições feitas aqui não são gravadas no .qsf versionado.
#
# Para programar a placa logo depois, encadeie o programador no MESMO shell (um quartus_pgm em outro
# processo-pai falha com "Can't scan JTAG chain"):
#
#   quartus_sh -t src/cyclone-v/external-data/external-data_synth.tcl && src/cyclone-v/external-data/external-data_program.sh

load_package flow

set project "external-data"
set seed 5
set only_map 0

if {$argc >= 1} {
    set seed [lindex $quartus(args) 0]
}
if {$argc >= 2} {
    set only_map [string equal [lindex $quartus(args) 1] "map"]
}
if {![string is integer -strict $seed] || $seed < 1} {
    puts "Erro: a semente deve ser um inteiro positivo, recebi '$seed'."
    exit 2
}

cd [file dirname [file normalize [info script]]]

project_open $project
set_global_assignment -name OPTIMIZATION_MODE "HIGH PERFORMANCE EFFORT"
set_global_assignment -name SEED $seed

if {$only_map} {
    execute_module -tool map
} else {
    execute_flow -compile
}

project_close -dont_export_assignments
