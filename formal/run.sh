#!/usr/bin/env bash
# Formal verification of the repository: every make target named formal* of each submodule, with the
# engine chosen by FORMAL_ENGINE (yices, bitwuzla, boolector or abc-bmc3; default bitwuzla). The targets of
# the submodules are found and run by `make formal`, so this script is the entry point the tree rules ask
# for and adds nothing of its own.
set -euo pipefail
cd "$(dirname "$0")/.."
exec make formal FORMAL_ENGINE="${FORMAL_ENGINE:-bitwuzla}"
