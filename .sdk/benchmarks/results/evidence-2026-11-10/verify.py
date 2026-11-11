"""Verify the curated evidence package's file inventory and checksums."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'SHA256SUMS.json').read_text())
actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p.name != 'SHA256SUMS.json'}
assert set(manifest) == actual, 'Missing or unexpected files in evidence package'
for name, expected in manifest.items():
    path = (root / name).resolve()
    path.relative_to(root)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
print(f'Verified {len(manifest)} evidence files')
