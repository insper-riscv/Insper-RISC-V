#!/usr/bin/env bash
set -euo pipefail

_rv32_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${_rv32_script_dir}/env.sh"

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v uv >/dev/null || { echo "uv is required" >&2; exit 1; }

if git -C "${RV32_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "${RV32_ROOT}" submodule update --init --recursive
else
    echo "Archive checkout detected; using the bundled repository contents."
fi
uv sync --project "${RV32_TESTS_ROOT}"
"${RV32_ROOT}/scripts/rv32.sh" doctor

