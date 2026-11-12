# Shared by formal/interconnect.sh (sourced, never run). A warning of GHDL, Yosys or SymbiYosys is an error: the
# code, the proof or the netlist is fixed, the warning is never silenced (no -Wno-* option, no list of ignored
# warnings). The script that sources it sets engine.

# The only warnings accepted, and only from the abc-bmc3 engine: the three messages of ABC about the undriven clock
# of the property module, the undriven bits and the outputs read as constraints.
abc_notes='aig: Warning: Treating undriven bit props\.\\clk like \$anyseq\.$|aig: Warning: Treating a total of [0-9]+ undriven bits in props like \$anyseq\.$|engine_0: Warning: The last ([0-9]+ outputs are|output is) interpreted as (a )?constraints?\.$'

# warnings_in <log> [label]: prints every warning of a tool log as <label>:<line>: <text> (the label is the log by
# default), and nothing when there is none. A warning is a diagnostic: the word "warning" or "warnings", in any case,
# as a whole word, which is how GHDL (file:line:col:warning: text), Yosys (Warning: text) and SymbiYosys (the same,
# after its time and the tag of the proof) write it. A name that only contains the word (no_warnings.sv, a property
# called warning_free) is not a whole word, and the summary of Yosys with a count of zero ("Warnings: 0 unique
# messages, 0 total") reports that there is none.
warnings_in() {
  local ignore='^$^'
  # Only the log of the abc-bmc3 engine (never GHDL's output) may carry these ABC messages, which come from the way ABC
  # reads the netlist and cannot be removed from the design; any other message, in any engine, still fails.
  [ "$engine" = abc-bmc3 ] && [ "${2:-}" != ghdl ] && ignore="$abc_notes"
  ignore="$ignore" awk -v label="${2:-$1}" '
    BEGIN { ignore = ENVIRON["ignore"] }
    { l = tolower($0) }
    l ~ /(^|[^a-z0-9_.\/-])warnings?($|[^a-z0-9_.\/-])/ && l !~ /warnings: 0 unique messages, 0 total/ && $0 !~ ignore { printf "%s:%d: %s\n", label, FNR, $0 }
  ' "$1"
}

# ghdl_run <ghdl arguments>: runs ghdl. Errors reach the terminal, and a warning is an error: it reaches the terminal
# as it came (file:line:col:warning: text) and ghdl_run fails.
ghdl_run() {
  local err rc=0 w
  err="$(mktemp)"
  ghdl "$@" 2> "$err" || rc=$?
  cat "$err" >&2
  w="$(warnings_in "$err" ghdl)"
  rm -f "$err"
  if [ -n "$w" ]; then
    echo "formal: ghdl has warnings, which are errors (the file and line are in the text of each):" >&2
    echo "$w" >&2
    return 1
  fi
  return "$rc"
}
