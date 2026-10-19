#!/usr/bin/env bash
# Source this file to configure a host shell, or let scripts/rv32.sh source it.

_rv32_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export RV32_ROOT="${RV32_ROOT:-$(cd -- "${_rv32_script_dir}/.." && pwd)}"
export RV32_TESTS_ROOT="${RV32_TESTS_ROOT:-${RV32_ROOT}/Tests}"
export RV32_LIVE_ROOT="${RV32_LIVE_ROOT:-${RV32_ROOT}/Live}"
export RV32_CONFIG="${RV32_CONFIG:-${RV32_LIVE_ROOT}/config.yaml}"
export RV32_PLATFORM="${RV32_PLATFORM:-${RV32_ROOT}/TopLevel/platforms/internal-mem/platform.yaml}"

if [[ -n "${RV32_TOOLCHAIN_ROOT:-}" ]]; then
    export RV32_GCC="${RV32_GCC:-${RV32_TOOLCHAIN_ROOT}/bin/riscv32-unknown-elf-gcc}"
    case ":${PATH}:" in
        *":${RV32_TOOLCHAIN_ROOT}/bin:"*) ;;
        *) export PATH="${RV32_TOOLCHAIN_ROOT}/bin:${PATH}" ;;
    esac
fi

if [[ -n "${QUARTUS_ROOTDIR:-}" ]]; then
    case ":${PATH}:" in
        *":${QUARTUS_ROOTDIR}/bin:"*) ;;
        *) export PATH="${QUARTUS_ROOTDIR}/bin:${PATH}" ;;
    esac
fi

unset _rv32_script_dir

