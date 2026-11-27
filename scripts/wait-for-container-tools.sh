#!/usr/bin/env bash
# Wait for the root startup job; never install packages as the editor user.
set -euo pipefail

state="${1:?Missing dependency state file}"
label="${2:-container tools}"
limit="${RV32_DEPS_WAIT_SECONDS:-1800}"
if ! [[ "${limit}" =~ ^[1-9][0-9]{0,3}$ ]] || ((limit > 3600)); then
    echo 'RV32_DEPS_WAIT_SECONDS must be an integer between 1 and 3600.' >&2
    exit 1
fi

for ((elapsed = 0; elapsed < limit; ++elapsed)); do
    # Older/native environments have no startup job; the caller checks tools.
    [[ -f "${state}" ]] || exit 0
    status="$(cat "${state}")"
    case "${status}" in
        ready) exit 0 ;;
        failed)
            echo "RV32: ${label} installation failed. Inspect the container startup logs." >&2
            exit 1
            ;;
        preparing|"")
            if ((elapsed % 60 == 0)); then
                echo "RV32: Waiting for ${label} installation (${elapsed}s)."
            fi
            sleep 1
            ;;
        *)
            echo "RV32: Unexpected ${label} setup state: ${status}" >&2
            exit 1
            ;;
    esac
done

echo "RV32: ${label} installation is still running after ${limit}s. Wait for startup to finish and rerun bootstrap-external.sh; rebuilding restarts the installation." >&2
exit 1
