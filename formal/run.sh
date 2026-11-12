#!/usr/bin/env bash
# Formal verification of the repository: its own proofs (formal/interconnect.sh), with the engine chosen by
# FORMAL_ENGINE (yices, bitwuzla, boolector or abc-bmc3; default bitwuzla). The proofs of the submodules run
# in the CI of each one. This script is the entry point the tree rules ask for.
set -euo pipefail
cd "$(dirname "$0")/.."
exec make formal FORMAL_ENGINE="${FORMAL_ENGINE:-bitwuzla}"
