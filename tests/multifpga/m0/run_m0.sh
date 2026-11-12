#!/usr/bin/env bash
# Roda a matriz das medições M.0.2 e M.0.6 (quartus_map) e guarda os resultados em <pasta de saída>/<caso>-<família>/ (minúsculas e hífens).
# Uso: run_m0.sh <pasta de saída> [família ...]   (sem famílias, roda as quatro)
# Cada síntese espera o flock /tmp/quartus-<host>.lock, de modo que só uma roda por máquina.
set -euo pipefail

aqui="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
saida="$(realpath -m "${1:?uso: run_m0.sh <pasta de saída> [família ...]}")"
shift || true
host="$(hostname -s)"

# Dispositivo representativo de cada família (o de uma placa do laboratório).
declare -A dispositivo=(
  ["Cyclone V"]="5CEBA4F23C7"          # DE0-CV
  ["Cyclone IV E"]="EP4CE115F29C7"     # DE2-115
  ["MAX 10"]="10M50DAF484C7G"          # DE10-Lite
  ["Cyclone 10 LP"]="10CL016YU256C8G"  # MKR Vidor 4000
)
familias=("$@")
[ "${#familias[@]}" -gt 0 ] || familias=("Cyclone V" "Cyclone IV E" "MAX 10" "Cyclone 10 LP")

for familia in "${familias[@]}"; do
  for caso in pll_altera_pll pll_altpll vjtag; do
    pasta="$saida/$(echo "${caso}-${familia}" | tr "A-Z _" "a-z--")"
    rm -rf "$pasta"
    mkdir -p "$pasta"
    flock "/tmp/quartus-${host}.lock" \
      quartus_sh -t "$aqui/m0_map.tcl" "$caso" "$familia" "${dispositivo[$familia]}" "$pasta" \
      >"$pasta/quartus_sh.log" 2>&1 || true
    if grep -q "PASSA" "$pasta/resultado.txt" 2>/dev/null; then
      (cd "$pasta" && quartus_cdb -t "$aqui/m0_atoms.tcl" >atomos.log 2>&1 || true)
      case "$caso" in pll_*) (cd "$pasta" && quartus_sta -t "$aqui/m0_clocks.tcl" >relogios.log 2>&1 || true) ;; esac
    fi
    echo "$(cat "$pasta/resultado.txt" 2>/dev/null || echo "RESULTADO $caso \"$familia\" ${dispositivo[$familia]} SEM-RESULTADO")"
  done
done
