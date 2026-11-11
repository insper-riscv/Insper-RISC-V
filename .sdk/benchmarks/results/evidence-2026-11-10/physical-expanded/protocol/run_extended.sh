#!/usr/bin/env bash
# Only run after programming the matching SDK bitstream and checking the
# authorized cable/chip identity. This script does not program the hardware.
set -euo pipefail
sdk_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
source "${sdk_root}/scripts/env.sh"
output="${1:?Usage: run_extended.sh NEW_OUTPUT_DIRECTORY}"
hardware="${2:-USB-Blaster [1-2]}"
# cubic is deliberately recorded as a build failure: it does not fit this FLASH.
"${sdk_root}/scripts/rv32-bench" run --backend fpga-fast \
  --jtag-hardware "${hardware}" --cpu-hz 50000000 --repeats 3 --timeout 180 \
  --benchmarks aha-mont64 crc32 edn huffbench matmult-int minver nbody \
  nettle-aes nettle-sha256 nsichneu picojpeg qrduino sglib-combined slre st \
  statemate ud wikisort --output "${output}"
