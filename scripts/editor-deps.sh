#!/usr/bin/env bash
# Language-server packages are installed only in the disposable Dev Container.
set -euo pipefail
state=/tmp/rv32-editor-deps.state

if command -v clangd >/dev/null 2>&1; then
    exit 0
fi

if [[ "${1:-}" == --install ]]; then
    if [[ "$(id -u)" != 0 || ( ! -f /.dockerenv && ! -f /run/.containerenv ) ]]; then
        echo 'Editor dependency installation requires container root.' >&2
        exit 1
    fi
    printf 'preparing\n' > "${state}"
    trap 'printf "failed\n" > "${state}"' ERR
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends clangd
    command -v clangd >/dev/null
    printf 'ready\n' > "${state}"
    exit 0
fi

for ((attempt = 0; attempt < 300; ++attempt)); do
    [[ -f "${state}" && "$(cat "${state}")" == preparing ]] || break
    sleep 1
done
if ! command -v clangd >/dev/null 2>&1; then
    echo 'clangd is missing. Rebuild the Dev Container; native hosts need clangd installed.' >&2
    exit 1
fi
