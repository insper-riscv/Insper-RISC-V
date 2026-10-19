#!/usr/bin/env bash
set -euo pipefail

_rv32_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${_rv32_script_dir}/env.sh"

if [[ "${1:-}" == "setup" ]]; then
    exec python3 "${RV32_ROOT}/scripts/live_c.py" setup
fi

exec uv run --project "${RV32_TESTS_ROOT}" \
    python "${RV32_ROOT}/scripts/live_c.py" "$@"

