#!/usr/bin/env bash
# Check build-host tools; installation is confined to container root startup.
set -euo pipefail

available() {
    command -v "${CLANG_PATH:-clang}" >/dev/null 2>&1 || return 1
    python3 - <<'PY'
import ctypes
import ctypes.util
import glob
import os

paths = []
custom = os.environ.get("LIBCLANG_PATH")
if custom:
    paths.extend(glob.glob(os.path.join(custom, "libclang*.so*")))
    if os.path.isfile(custom):
        paths.append(custom)
found = ctypes.util.find_library("clang")
if found:
    paths.append(found)
for pattern in ("/usr/lib/llvm-*/lib/libclang.so*", "/usr/lib/*/libclang-*.so*", "/usr/lib64/libclang.so*", "/usr/local/lib/libclang.so*"):
    paths.extend(glob.glob(pattern))
for path in paths:
    try:
        ctypes.CDLL(path)
        raise SystemExit(0)
    except OSError:
        pass
raise SystemExit(1)
PY
}

if available; then
    exit 0
fi
if [[ "${1:-}" == "--install" ]]; then
    if [[ "$(id -u)" != 0 || ( ! -f /.dockerenv && ! -f /run/.containerenv ) ]]; then
        echo 'Rust build dependency installation must run as container root.' >&2
        exit 1
    fi
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends clang libclang-dev
    available
    exit 0
fi

# A new Dev Container installs these packages before project setup. Wait for
# that root-owned startup job; the editor and Cargo remain the normal user.
state=/tmp/rv32-rust-build-deps.state
if [[ "${1:-}" != --check ]]; then
    for ((attempt = 0; attempt < 300; ++attempt)); do
        if [[ ! -f "${state}" || "$(cat "${state}")" != preparing ]]; then
            break
        fi
        sleep 1
    done
fi
if available; then
    exit 0
fi
cat >&2 <<'MESSAGE'
Rust peripheral bindings need Clang and libclang in the build environment.
Rebuild the Dev Container using the matching SDK 0.9.1 infrastructure.
For a native host, install Clang/libclang or set CLANG_PATH and LIBCLANG_PATH.
MESSAGE
exit 1
