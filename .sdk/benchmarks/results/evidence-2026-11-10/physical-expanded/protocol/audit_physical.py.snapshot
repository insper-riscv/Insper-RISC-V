"""Audit the copied physical dataset; reject failed or inconsistent repetitions."""
import csv
import hashlib
import json
import re
import statistics
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
report = json.loads((root / 'results.json').read_text())
if report['backend'] != 'fpga-fast' or report['cpu_hz_user_supplied'] != 50_000_000:
    raise ValueError('Unexpected physical protocol')
if report['jtag_hardware'] != 'USB-Blaster [1-2]' or report['official_embench_score']:
    raise ValueError('Unexpected board or unsupported score claim')
if report['embench_revision'] != '0466a18e4f6b47e19598d7c6ba72916d54b68f65':
    raise ValueError('Unexpected Embench source revision')
if hashlib.sha256((root / 'protocol/bench.py').read_bytes()).hexdigest() != report['runner_sha256']:
    raise ValueError('Runner hash mismatch')
groups = {}
for row in report['runs']:
    if row['status'] != 'passed':
        raise ValueError(f"Failed measurement: {row}")
    if not all(type(row[k]) is int and row[k] > 0 for k in ('cycles', 'instructions')):
        raise ValueError('Invalid counters')
    text = (root / Path(row['log']).name).read_text()
    records = re.findall(r'^RV32BENCH cycles=(\d+) instructions=(\d+) verified=([01])$', text, re.M)
    if records != [(str(row['cycles']), str(row['instructions']), '1')]:
        raise ValueError('Log/JSON mismatch or invalid verifier')
    if text.split('\nSTDERR:\n', 1)[1].strip():
        raise ValueError('Unexpected stderr')
    if abs(row['cpi'] - row['cycles'] / row['instructions']) > 1e-12:
        raise ValueError('CPI mismatch')
    if abs(row['seconds'] - row['cycles'] / 50_000_000) > 1e-12:
        raise ValueError('Time mismatch')
    elf = root / 'elf' / (row['benchmark'] + '.elf')
    if hashlib.sha256(elf.read_bytes()).hexdigest() != row['elf_sha256']:
        raise ValueError('ELF hash mismatch')
    groups.setdefault(row['benchmark'], []).append(row)
if len(groups) != 18 or len(report['runs']) != 54:
    raise ValueError('Incomplete suite subset')
summary = {'clock_hz_nominal': 50_000_000, 'official_embench_score': False,
           'physical_runs': len(report['runs']), 'workloads': {}}
for name, rows in groups.items():
    if sorted(r['repetition'] for r in rows) != [0, 1, 2]:
        raise ValueError('Missing or duplicate repetitions')
    for key in ('elf_sha256', 'source_sha256'):
        if len({r[key] for r in rows}) != 1:
            raise ValueError('Changed binary/source between repetitions')
    cycles = [r['cycles'] for r in rows]
    instructions = [r['instructions'] for r in rows]
    summary['workloads'][name] = dict(
        repetitions=3, verified=True,
        cycles_median=statistics.median(cycles), cycles_min=min(cycles), cycles_max=max(cycles),
        instructions_median=statistics.median(instructions),
        cpi_median=statistics.median(r['cpi'] for r in rows),
        milliseconds_at_nominal_clock=statistics.median(cycles) / 50_000,
        elf_sha256=rows[0]['elf_sha256'], source_sha256=rows[0]['source_sha256'])
(root / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
fields = ['benchmark', 'cycles_median', 'cycles_min', 'cycles_max', 'instructions_median', 'cpi_median', 'milliseconds_at_nominal_clock']
with (root / 'summary.csv').open('w', newline='') as f:
    writer = csv.DictWriter(f, fields, extrasaction='ignore')
    writer.writeheader()
    for name, data in summary['workloads'].items():
        writer.writerow(dict(benchmark=name, **data))
print(f"Audited {summary['physical_runs']} physical runs across {len(groups)} workloads")
