#!/usr/bin/env bash
set -euo pipefail
cd /review/SDK
source scripts/env.sh
scripts/rv32-bench run --benchmarks smoke --backend build --jtag-hardware 'USB-Blaster [1-2]' --output /review/expanded-counter-check
scripts/rv32-project --project /review/expanded-counter-check/projects/smoke fpga --mode full > /review/expanded-counter.stdout 2> /review/expanded-counter.stderr
uv run --quiet --project .sdk python - <<'PY'
from pathlib import Path
from rv32_sdk.bench import parse_measurement
record = parse_measurement(Path('/review/expanded-counter.stdout').read_text())
assert not Path('/review/expanded-counter.stderr').read_bytes()
assert record['cycles'] == 48 and record['instructions'] == 16, record
print('Physical counter validation:', record, flush=True)
PY
bash .sdk/benchmarks/evidence/run_extended.sh /review/expanded-measurements
