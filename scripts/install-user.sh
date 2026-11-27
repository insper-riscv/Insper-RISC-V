#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
sdk_root="$(cd -- "${script_dir}/.." && pwd)"
data_root="${XDG_DATA_HOME:-${HOME}/.local/share}"
cache_root="${XDG_CACHE_HOME:-${HOME}/.cache}"
bin_root="${HOME}/.local/bin"
quartus_root=""

usage() {
    cat <<'EOF'
Usage: bash scripts/install-user.sh [--quartus /path/to/altera/std25.1]

Registers this checkout as the current per-user RV32 SDK.  This is a one-time
machine setup; generated C and Rust projects then open without environment
variables or project-specific path configuration.
EOF
}

while (($#)); do
    case "$1" in
        --quartus)
            [[ $# -ge 2 ]] || { echo "--quartus needs a path" >&2; exit 2; }
            quartus_root="$(realpath "$2")"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

python3 "${sdk_root}/.sdk/rv32_sdk/source_check.py" "${sdk_root}"

install -d "${data_root}" "${cache_root}/rv32-cargo" \
    "${data_root}/rv32-rustup" "${bin_root}"

register_link() {
    local source="$1" target="$2"
    # An SDK or Quartus checkout already at its registration path is valid.
    if [[ "${source}" -ef "${target}" ]]; then
        return
    fi
    # Docker creates absent short-syntax bind sources as real directories.
    # Never let ln put a nested link inside one and report a false success.
    if [[ -d "${target}" && ! -L "${target}" ]]; then
        rmdir "${target}" 2>/dev/null || {
            echo "Cannot replace non-empty ${target}. Move it aside and rerun; its files were preserved." >&2
            return 1
        }
    elif [[ -e "${target}" && ! -L "${target}" ]]; then
        echo "Cannot replace existing file ${target}; its contents were preserved." >&2
        return 1
    fi
    ln -sfnT "${source}" "${target}"
}

register_link "${sdk_root}" "${data_root}/rv32-sdk"
if [[ ! -f "${data_root}/rv32-sdk/scripts/container-start.sh" ]]; then
    echo "Registered SDK is missing scripts/container-start.sh" >&2
    exit 1
fi

quartus_link="${data_root}/rv32-quartus"
if [[ -n "${quartus_root}" ]]; then
    register_link "${quartus_root}" "${quartus_link}"
elif [[ ! -e "${quartus_link}" ]]; then
    install -d "${quartus_link}"
fi

cat >"${bin_root}/rv32-new" <<'EOF'
#!/usr/bin/env bash
exec "${XDG_DATA_HOME:-${HOME}/.local/share}/rv32-sdk/scripts/rv32-new" "$@"
EOF

cat >"${bin_root}/rv32-project" <<'EOF'
#!/usr/bin/env bash
exec "${XDG_DATA_HOME:-${HOME}/.local/share}/rv32-sdk/scripts/rv32-project" "$@"
EOF

cat >"${bin_root}/rv32-drivers" <<'EOF'
#!/usr/bin/env bash
exec "${XDG_DATA_HOME:-${HOME}/.local/share}/rv32-sdk/scripts/rv32-drivers" "$@"
EOF

chmod +x "${bin_root}/rv32-drivers" "${bin_root}/rv32-new" "${bin_root}/rv32-project"

echo "RV32 SDK: ${data_root}/rv32-sdk -> ${sdk_root}"
echo "Quartus:  ${quartus_link}"
echo "Commands: ${bin_root}/rv32-new and ${bin_root}/rv32-project"
if [[ ":${PATH}:" != *":${bin_root}:"* ]]; then
    echo
    echo "Add this once to your shell profile:"
    echo "  export PATH=\"${bin_root}:\$PATH\""
fi

mkdir -p "${HOME}/.cache/rv32/sof"
