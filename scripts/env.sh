#!/usr/bin/env bash
# Source this file to configure a host shell, or let scripts/rv32.sh source it.

_rv32_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# The invoked SDK determines the root, even when another SDK was exported earlier.
export RV32_SDK_ROOT="$(cd -- "${_rv32_script_dir}/.." && pwd)"
export RV32_ROOT="${RV32_SDK_ROOT}"

case ":${PATH}:" in
    *":${RV32_SDK_ROOT}/scripts:"*) ;;
    *) export PATH="${RV32_SDK_ROOT}/scripts:${PATH}" ;;
esac

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

# The published dev image installs GHDL here. Compose may replace its PATH.
if [[ -d /opt/ghdl/bin ]]; then
    case ":${PATH}:" in
        *":/opt/ghdl/bin:"*) ;;
        *) export PATH="/opt/ghdl/bin:${PATH}" ;;
    esac
fi

unset _rv32_script_dir
