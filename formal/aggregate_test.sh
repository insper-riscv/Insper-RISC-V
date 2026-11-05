#!/usr/bin/env bash
# Tests of formal/aggregate.sh over made-up results:  bash formal/aggregate_test.sh
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
failures=0

# row <id> <wanted> <verdict>: a line of a result file.
row() { printf '%s\t%s\t%s\t0\t10\tlabel of %s\n' "$1" "$2" "$3" "$1"; }

# check <name> <wanted exit code> <directory>: runs the aggregator and compares its exit code.
check() {
  local code=0
  bash "$here/aggregate.sh" "$3" > "$work/out.txt" 2>&1 || code=$?
  if [ "$code" = "$2" ]; then echo "ok    $1"; else echo "WRONG $1: exit $code, wanted $2"; cat "$work/out.txt"; failures=$((failures + 1)); fi
}

d="$work/agree"; mkdir "$d"
{ row p1 pass pass; row m1 fail fail; } > "$d/result-yices.tsv"
{ row p1 pass pass; row m1 fail fail; } > "$d/result-bitwuzla.tsv"
check "every engine agrees with what is wanted" 0 "$d"

d="$work/one-error"; mkdir "$d"
{ row p1 pass pass; row m1 fail fail; } > "$d/result-bitwuzla.tsv"
{ row p1 pass error; row m1 fail error; } > "$d/result-yices.tsv"
check "an engine with an error does not stop another from deciding" 0 "$d"

d="$work/skip"; mkdir "$d"
{ row p1 pass pass; row c1 pass pass; } > "$d/result-bitwuzla.tsv"
{ row p1 pass pass; row c1 pass skip; } > "$d/result-abc-bmc3.tsv"
check "a skip is not an answer, and the other engine decides" 0 "$d"

d="$work/disagree"; mkdir "$d"
{ row p1 pass pass; } > "$d/result-bitwuzla.tsv"
{ row p1 pass fail; } > "$d/result-yices.tsv"
check "one engine says pass and another says fail" 1 "$d"

d="$work/nobody"; mkdir "$d"
{ row p1 pass error; } > "$d/result-bitwuzla.tsv"
{ row p1 pass skip; } > "$d/result-abc-bmc3.tsv"
check "no engine answered a proof" 1 "$d"

d="$work/only-broken"; mkdir "$d"
{ row p1 pass error; row m1 fail error; } > "$d/result-yices.tsv"
check "the only engine is broken" 1 "$d"

d="$work/wanted-fail-passed"; mkdir "$d"
{ row m1 fail pass; } > "$d/result-bitwuzla.tsv"
{ row m1 fail pass; } > "$d/result-yices.tsv"
check "the engines agree on pass where fail is wanted" 1 "$d"

d="$work/missing-engine"; mkdir "$d"
{ row p1 pass pass; row p2 pass pass; } > "$d/result-bitwuzla.tsv"
{ row p1 pass pass; } > "$d/result-yices.tsv"
check "an engine that lacks a proof leaves it to the others" 0 "$d"

d="$work/empty"; mkdir "$d"
check "no result file at all" 1 "$d"

# The guard against warnings (warnings_in, ghdl_run and prove): every warning of GHDL, Yosys or SymbiYosys is an error.
guard_case() {  # <wanted: warn|clean> <log line> <what the line shows> [engine]
  local found
  printf '%s\n' "$2" > "$work/guard.log"
  found="$(FORMAL_ENGINE="${4:-bitwuzla}" bash -c 'engine=$FORMAL_ENGINE; source "$1"; warnings_in "$2"' _ "$here/common.sh" "$work/guard.log")"
  if { [ "$1" = warn ] && [ -n "$found" ]; } || { [ "$1" = clean ] && [ -z "$found" ]; }; then
    echo "ok    guard: $3"
  else
    echo "WRONG guard: $3 (wanted $1, found '$found')"
    failures=$((failures + 1))
  fi
}

guard_case warn  '/work/src/x.vhd:62:19:warning: unhandled attribute "altera_attribute" [-Wunhandled-attribute]' "a warning of GHDL"
guard_case warn  '/work/src/x.vhd:1:1:warning: library "ieee" is already loaded [-Wlibrary]' "a warning of GHDL about a library"
guard_case warn  'SBY 12:00:01 [mut_x] base: Warning: Wire ext_interconnect.\dbg_sel_wb is used but has no driver.' "a warning of Yosys in the log of SymbiYosys"
guard_case warn  'WARNING: something' "the word in capitals"
guard_case warn  'Warnings: 2 unique messages, 2 total' "a summary of Yosys with a count above zero"
guard_case clean 'Warnings: 0 unique messages, 0 total' "a summary of Yosys with a count of zero"
guard_case clean 'reading formal/no_warnings.sv' "a file name that contains the word"
guard_case clean 'assert property warning_free passed' "a property name that contains the word"
guard_case clean 'SBY 12:00:03 [safety] aig: Warning: Treating undriven bit props.\clk like $anyseq.' "an ABC message, in the abc-bmc3 engine" abc-bmc3
guard_case clean 'SBY 12:00:03 [safety] aig: Warning: Treating a total of 7 undriven bits in props like $anyseq.' "an ABC message with a count, in the abc-bmc3 engine" abc-bmc3
guard_case clean 'SBY 12:00:03 [safety] engine_0: Warning: The last 2 outputs are interpreted as constraints.' "an ABC message about constraints, in the abc-bmc3 engine" abc-bmc3
for e in yices bitwuzla boolector; do
  guard_case warn 'SBY 12:00:03 [safety] aig: Warning: Treating undriven bit props.\clk like $anyseq.' "the same ABC message in the $e engine" "$e"
done
guard_case warn  'SBY 12:00:03 [safety] base: Warning: Wire props.\x is used but has no driver.' "any other warning, in the abc-bmc3 engine" abc-bmc3
guard_case clean 'SBY 12:00:02 [safety] summary: engine_0 (smtbmc bitwuzla) returned pass' "an ordinary line"

# A warning injected into a real run must fail it: the tools are wrappers that call the real ones and add a warning.
# The wrappers need ghdl, yosys and sby, which the dev_tools image has; a machine without them skips this part.
inject_case() {  # <tool: ghdl|sby> <what the injection shows>
  local fake="$work/fake-$1" real code=0
  mkdir -p "$fake"
  real="$(command -v "$1")"
  if [ "$1" = ghdl ]; then
    printf '#!/bin/sh\n"%s" "$@" || exit $?\necho "x.vhd:3:4:warning: invented [-Winvented]" >&2\n' "$real" > "$fake/ghdl"
  else
    printf '#!/bin/sh\n"%s" "$@"; rc=$?\necho "Warning: invented"\nexit $rc\n' "$real" > "$fake/sby"
  fi
  chmod +x "$fake/$1"
  PATH="$fake:$PATH" FORMAL_ENGINE=bitwuzla FORMAL_TIMEOUT=120 bash "$here/interconnect.sh" > "$work/inject.txt" 2>&1 || code=$?
  if [ "$code" != 0 ] && grep -q 'warnings, which are errors' "$work/inject.txt"; then
    echo "ok    guard: a warning injected into $1 fails the run"
  else
    echo "WRONG guard: a warning injected into $1 did not fail the run (exit $code)"; tail -5 "$work/inject.txt"
    failures=$((failures + 1))
  fi
}
if command -v ghdl > /dev/null && command -v sby > /dev/null; then
  inject_case ghdl
  inject_case sby
else
  echo "skip  guard: ghdl or sby not installed, the injected-warning runs were skipped"
fi

[ "$failures" -eq 0 ] && echo "aggregate: all tests passed" || { echo "aggregate: $failures test(s) failed"; exit 1; }
