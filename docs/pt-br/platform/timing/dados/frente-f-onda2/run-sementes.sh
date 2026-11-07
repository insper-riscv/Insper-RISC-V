#!/bin/bash
# uso (na PC1): run.sh <rotulo> <fonte> <freq MHz> <fase3 ps> [sementes]
# Compila a de0-cv em copias por semente (relogios de busca e nucleo na frequencia e a fase pedidas) e extrai metricas.
LABEL=$1; SRC=$2; FREQ=$3; PHASE=$4; SEEDS=${5:-"1 2 3 4 5"}
B=${TIMING_DIR:-/tmp/timing}
for s in $SEEDS; do
  d=$B/runs/$LABEL-s$s
  rm -rf $d; mkdir -p $d
  rsync -a --exclude .git --exclude output_files --exclude db --exclude incremental_db $SRC/ $d/
  p=$d/src/cyclone-v/de0-cv/pll/sdram_platform_pll.v
  sed -i 's/output_clock_frequency2("[0-9.]* MHz")/output_clock_frequency2("'$FREQ' MHz")/; s/output_clock_frequency3("[0-9.]* MHz")/output_clock_frequency3("'$FREQ' MHz")/; s/phase_shift3("[0-9]* ps")/phase_shift3("'$PHASE' ps")/' $p
  ( cd $d && quartus_sh -t src/cyclone-v/de0-cv/de0-cv_synth.tcl $s > $d/compile.log 2>&1
    cd src/cyclone-v/de0-cv
    quartus_sta -t $B/pares-de-dominios.tcl de0-cv 400 slow > $d/pares.txt 2>&1
    quartus_sta -t $B/pior-caminho-por-par.tcl de0-cv $d/detail > $d/detail.log 2>&1
    echo done > $d/DONE ) &
done
wait
