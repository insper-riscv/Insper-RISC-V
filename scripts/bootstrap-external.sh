#!/usr/bin/env bash
set -euo pipefail

project_root="${1:-${RV32_PROJECT_ROOT:-/workspace}}"
manifest="${project_root}/rv32.toml"

if [[ ! -f "${manifest}" ]]; then
    echo "Missing ${manifest}" >&2
    exit 1
fi

python3 "${RV32_SDK_ROOT}/.sdk/rv32_sdk/source_check.py" "${RV32_SDK_ROOT}"

language="$({ python3 - "${manifest}" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as stream:
    print(tomllib.load(stream)["project"]["language"])
PY
} )"

if [[ "${language}" == "rust" ]]; then
    export RUSTUP_HOME="${RUSTUP_HOME:-/home/ubuntu/.rustup}"
    export CARGO_HOME="${CARGO_HOME:-/home/ubuntu/.cargo}"
    export PATH="${CARGO_HOME}/bin:${PATH}"

    if ! command -v rustup >/dev/null 2>&1; then
        echo "Installing the shared RV32 Rust toolchain (first Rust project only)..."
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
            | sh -s -- -y --profile minimal --default-toolchain 1.85.1
    fi
    rustup target add riscv32i-unknown-none-elf riscv32im-unknown-none-elf
    rustup component add rust-src
    # Bindgen runs on the development host, even when building bare-metal code.
    # Keep this installation confined to the intended disposable Dev Container.
    if python3 - "${manifest}" <<'PYTHON'
import sys
import tomllib
with open(sys.argv[1], "rb") as stream:
    enabled = tomllib.load(stream)["project"].get("generate_drivers", False)
raise SystemExit(0 if enabled else 1)
PYTHON
    then
        if ! command -v clang >/dev/null 2>&1 || ! /sbin/ldconfig -p 2>/dev/null | grep 'libclang\.so\|libclang-[0-9].*\.so' >/dev/null; then
            if [[ ! -f /.dockerenv ]]; then
                echo "Rust driver bindings need host clang and libclang; install them before setup." >&2
                exit 1
            fi
            echo "Installing Clang/libclang for Rust peripheral bindings..."
            sudo apt-get update -qq
            sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends clang libclang-dev
        fi
    fi
fi

bash "${RV32_SDK_ROOT}/scripts/install-vscode-extension.sh"

exec "${RV32_SDK_ROOT}/scripts/rv32-project" \
    --project "${project_root}" setup
