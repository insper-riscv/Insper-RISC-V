#!/usr/bin/env bash
# Install the SDK's bundled VSIX into the Dev Container's workspace extension host.
set -euo pipefail
sdk_root="${RV32_SDK_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
vsix="${sdk_root}/share/rv32-development.vsix"
if [[ ! -f "${vsix}" ]]; then
    echo "Missing bundled extension: ${vsix}; obtain the complete SDK package." >&2
    exit 1
fi
agent="${VSCODE_AGENT_FOLDER:-${HOME}/.vscode-server}"
# postCreate and postAttach can overlap; serialize this installer only.
mkdir -p "${agent}"
exec 9>"${agent}/.rv32-extension-install.lock"
flock --exclusive --timeout 120 9
for server in "${agent}"/bin/*/bin/code-server \
              "${agent}"/bin/*/*/bin/code-server \
              /vscode/vscode-server/bin/*/*/bin/code-server; do
    if [[ -x "${server}" ]]; then
        expected="$(python3 - "${vsix}" <<'PYVSIX'
import json, sys, zipfile
with zipfile.ZipFile(sys.argv[1]) as package:
    print(json.loads(package.read("extension/package.json"))["version"])
PYVSIX
)"
        installed="$("${server}" --server-data-dir "${agent}" --extensions-dir "${agent}/extensions" --list-extensions --show-versions 9>&- 2>/dev/null || true)"
        while IFS= read -r extension; do
            if [[ "${extension}" == "insper-riscv.rv32-development@${expected}" ]]; then
                exit 0
            fi
        done <<< "${installed}"
        "${server}" --server-data-dir "${agent}" \
            --extensions-dir "${agent}/extensions" \
            --install-extension "${vsix}" --force \
            --do-not-include-pack-dependencies 9>&-
        exit 0
    fi
done
echo "VS Code server is not available; install ${vsix} in the container window."
