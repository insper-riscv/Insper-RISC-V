#!/usr/bin/env bash
# Root startup replaces the image's sleep command. Editor commands use ubuntu.
set -euo pipefail
state=/tmp/rv32-rust-build-deps.state
printf 'preparing\n' > "${state}"
trap 'printf "failed\n" > "${state}"' ERR

sdk_root="${RV32_SDK_ROOT:-/opt/rv32-sdk}"
project_root="${RV32_PROJECT_ROOT:-/workspace}"
if python3 - "${project_root}/rv32.toml" <<'PY'
import sys
import tomllib
with open(sys.argv[1], "rb") as stream:
    project = tomllib.load(stream)["project"]
raise SystemExit(0 if project.get("language") == "rust" and project.get("generate_drivers", False) else 1)
PY
then
    bash "${sdk_root}/scripts/rust-build-deps.sh" --install
fi
printf 'ready\n' > "${state}"
exec sleep infinity
