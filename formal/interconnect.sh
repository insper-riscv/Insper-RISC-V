#!/usr/bin/env bash
# Formal verification of the external interconnect with SymbiYosys. Needs
# ghdl, yosys, sby and the engine chosen by FORMAL_ENGINE (all in the ci-vhdl image). Run from the root of the
# repository:  FORMAL_ENGINE=bitwuzla bash formal/interconnect.sh
#
# FORMAL_ENGINE is one of yices, bitwuzla (the default), boolector and abc-bmc3. The first three are SMT solvers
# of the smtbmc engine; abc-bmc3 is the bounded model checker of ABC, which has no induction and no cover, so it
# skips those proofs. FORMAL_TIMEOUT (seconds, 900 by default) bounds each proof.
#
# Besides the report, the run writes build/formal/result-<engine>.tsv, one line per proof with the columns
# id, wanted (pass or fail), verdict (pass, fail, error or skip), sby exit code, milliseconds and the label, which
# formal/aggregate.sh joins across engines.
# A warning of GHDL, Yosys or SymbiYosys is an error (formal/common.sh): it is fixed, never silenced.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="$root/build/formal"
rm -rf "$out"; mkdir -p "$out"; cd "$out"

engine="${FORMAL_ENGINE:-bitwuzla}"
case "$engine" in
  yices|bitwuzla|boolector|abc-bmc3) ;;
  *) echo "FORMAL_ENGINE must be yices, bitwuzla, boolector or abc-bmc3, not '$engine'" >&2; exit 2 ;;
esac
timeout_s="${FORMAL_TIMEOUT:-900}"
results="$out/result-$engine.tsv"; : > "$results"
# shellcheck source=formal/common.sh
source "$root/formal/common.sh"

fail=0
# expect <label> <wanted: PASS|FAIL> <result: PASS|FAIL|SKIP|ERROR ...>. An ERROR (the tool did not reach a verdict)
# never matches, not even a wanted FAIL; a SKIP is a proof this engine does not do and is not a failure. The id,
# the exit code and the time of the proof come from the files prove left for its tag.
expect() {
  local tag verdict rc ms
  tag="$(cat "$out/.last")"
  IFS=$'\t' read -r verdict rc ms < "$out/$tag.res"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$tag" "${2,,}" "$verdict" "$rc" "$ms" "$1" >> "$results"
  case "$3" in
    SKIP*) printf '  skip  %-62s %s\n' "$1" "${3#SKIP }" ;;
    ERROR*) printf '  ERROR %-62s %s\n' "$1" "${3#ERROR }"; fail=1 ;;
    "$2") printf '  ok    %-62s %s (%s ms)\n' "$1" "$3" "$ms" ;;
    *) printf '  WRONG %-62s wanted %s, got %s\n' "$1" "$2" "$3"; fail=1 ;;
  esac
}

# expose <netlist> <signal[:high bit]>...: adds the wires of the last module (the top, GHDL writes it last) as
# the outputs dbg_<signal>. The logic is the same; the proof states the invariants over these registers.
expose() {
  local v="$1"; shift
  local ports="" assigns="" s w nm width src
  for s in "$@"; do
    nm="${s%%:*}"; w=""; width=1
    if [ "$s" != "$nm" ]; then w="[${s#*:}:0] "; width=$(( ${s#*:} + 1 )); fi
    ports+=",
   output ${w}dbg_$nm"
    # a signal the netlist no longer has (GHDL drops what nothing reads) is exposed as 0, never left without a driver
    # (GHDL puts a (* src=... *) attribute before the declaration, so the keyword is not always the first field)
    if awk -v nm="$nm;" '/^module / { n = 0 } $NF == nm { for (i = 1; i < NF; i++) if ($i == "reg" || $i == "wire") n = 1 } END { exit !n }' "$v"; then src="$nm"; else src="${width}'b0"; fi
    assigns+="  assign dbg_$nm = $src;
"
  done
  awk -v ports="$ports" -v assigns="$assigns" '
    { line[NR] = $0 }
    /^module / { m = NR }
    /^endmodule/ { e = NR }
    END {
      done = 0
      for (i = 1; i <= NR; i++) {
        l = line[i]
        if (i >= m && !done && l ~ /\);[ \t]*$/) { sub(/\);[ \t]*$/, ports ");", l); done = 1 }
        if (i == e) printf "%s", assigns
        print l
      }
    }' "$v" > "$v.tmp" && mv "$v.tmp" "$v"
  grep -q "dbg_${1%%:*}" "$v" || true
}

# prove <netlist> <props> <mode: prove|bmc|cover> <depth> <defines> <tag>  ->  PASS, FAIL, SKIP or ERROR
# PASS is sby exit code 0, FAIL is 2 (a counterexample or a goal that cannot be covered) and any other code
# (4 unknown, 8 timeout, 16 error, 124 the FORMAL_TIMEOUT) is ERROR: the tool did not reach a verdict. The
# abc-bmc3 engine only checks bounded properties of designs with registers, so it answers SKIP for a proof by
# induction, for a cover and for a combinational design.
# The verdict, the exit code and the milliseconds go to <tag>.res, and the tag to .last, for expect.
prove() {
  echo "$6" > "$out/.last"
  local engine_lines script_lines options_lines="" rc=0 verdict began ended
  case "$engine" in
    abc-bmc3)
      if [ "$3" != bmc ]; then
        printf 'SKIP\t-\t0\n' > "$6.res"; echo "SKIP abc-bmc3 has no $3"; return
      fi
      engine_lines="abc bmc3"
      options_lines="aigsmt none"
      script_lines=$'techmap\nopt -fast\nsetundef -anyseq' ;;
    *) engine_lines="smtbmc $engine"; script_lines="" ;;
  esac
  cat > "$6.sby" <<EOS
[options]
mode $3
depth $4
$options_lines
[engines]
$engine_lines
[script]
read_verilog -formal -sv $5 $1 $2
prep -top props
$script_lines
[files]
$1
$2
EOS
  began=$(date +%s%N)
  timeout "$timeout_s" sby -f "$6.sby" > "$6.log" 2>&1 || rc=$?
  ended=$(date +%s%N)
  local found
  # ABC refuses a design without registers (the trap unit is combinational): that is a proof this engine does
  # not do, not a failure of the tool.
  if [ "$engine" = abc-bmc3 ] && [ "$rc" = 16 ] && grep -q 'Does not work for combinational networks' "$6.log"; then
    printf 'skip\t%s\t0\n' "$rc" > "$6.res"; echo "SKIP abc-bmc3 does not work for a combinational design"; return
  fi
  # A warning is an error, whatever the exit code was: no verdict is reached
  found="$(warnings_in "$6.log" "$out/$6.log")"
  if [ -n "$found" ]; then
    echo "formal: the log of the proof has warnings, which are errors:" >&2
    echo "$found" >&2
    printf 'error\t%s\t%s\n' "$rc" "$(( (ended - began) / 1000000 ))" > "$6.res"
    echo "ERROR warning in the log of the proof, first at $(echo "$found" | head -n 1 | cut -c1-200)"; return
  fi
  case "$rc" in
    0) verdict=PASS ;;
    2) verdict=FAIL ;;
    *) verdict=ERROR ;;
  esac
  printf '%s\t%s\t%s\n' "${verdict,,}" "$rc" "$(( (ended - began) / 1000000 ))" > "$6.res"
  case "$verdict" in
    ERROR) echo "ERROR sby exited with code $rc, not a verdict (see $6.log)" ;;
    *) echo "$verdict" ;;
  esac
}


# netlist <vhdl> <name>: the Verilog netlist GHDL synthesizes for the interconnect, with the state exposed.
netlist() {
  local work="$out/work_$2"; mkdir -p "$work"
  ghdl_run -a --std=08 --workdir="$work" "$1"
  ghdl_run --synth --std=08 --workdir="$work" --out=verilog ext_interconnect > "$2.v"
  expose "$2.v" st sel_wb p_rdata_q:31 pending:31
  grep -q dbg_st "$2.v" || { echo "the netlist has no register named st: the exposure did not apply"; exit 1; }
}

ic="$root/src/interconnect/ext_interconnect.vhd"; props="$root/formal/ext_interconnect_props.sv"

echo "ext_interconnect"
netlist "$ic" ext
expect "one slave per access, memory and peripheral apart, one pulse, no hang, the data of the selected slave (induction)" PASS "$(prove ext.v "$props" prove 4 '' ext_safety)"
expect "cover: a read and a write of peripherals, a delivered peripheral read and a memory read are reachable" PASS "$(prove ext.v "$props" cover 12 '-DCOVER' ext_cover)"

# Mutants of the VHDL: each defect must make a proof fail.
mutant() {  # <file> <props> <entity> <defines> <name> <sed expression> [bmc depth]
  local copy="$out/mut_$5.vhd"
  sed "$6" "$1" > "$copy"
  cmp -s "$1" "$copy" && { echo "mutant $5: the edit did not change the file"; exit 1; }
  netlist "$copy" "mut_$5"
  expect "mutant $5 is caught" FAIL "$(prove "mut_$5.v" "$2" bmc "${7:-10}" "$4" "mut_$5")"
}
mutant "$ic" "$props" ext_interconnect '' slot_off_by_one  "s/id        <= to_integer(unsigned(i_addr(30 downto 28)));/id        <= to_integer(unsigned(i_addr(31 downto 29)));/"
mutant "$ic" "$props" ext_interconnect '' pulse_not_gated  "s/pulse <= '1' when st = ST_IDLE and is_periph = '1' and active = '1' else '0';/pulse <= '1' when is_periph = '1' and active = '1' else '0';/"
mutant "$ic" "$props" ext_interconnect '' memory_sees_periph "s/o_m_rden    <= i_rden and not is_periph;/o_m_rden    <= i_rden;/"
mutant "$ic" "$props" ext_interconnect '' ready_always     "s/'1' when st = ST_DONE else/'1' when true else/"
mutant "$ic" "$props" ext_interconnect '' slot_zero_data   "s/pending <= i_p_rdata(32 \* id + 31 downto 32 \* id);/pending <= i_p_rdata(31 downto 0);/"
mutant "$ic" "$props" ext_interconnect '' select_kept      "s/sel_wb <= '0';/null;/"
mutant "$ic" "$props" ext_interconnect '' write_reads      "s/o_p_we(id) <= i_wren;/o_p_we(id) <= i_rden;/"
mutant "$ic" "$props" ext_interconnect '' address_dropped  "s/o_p_addr    <= i_addr(periph_addr_width + 1 downto 2);/o_p_addr    <= i_addr(periph_addr_width + 2 downto 3);/"

[ "$fail" -eq 0 ] && echo "formal: all expectations met" || { echo "formal: FAILED (logs in build/formal)"; exit 1; }
