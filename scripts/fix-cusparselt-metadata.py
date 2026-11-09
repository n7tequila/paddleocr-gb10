#!/usr/bin/env python3
"""Repair *installed* cuSPARSELt 0.8.1 Wheel tag metadata ONLY.

For a verified manylinux2014_aarch64 wheel incorrectly tagged internally as
manylinux2014_sbsa. Modifies no libraries or bundled wheel. Optional workaround.
"""
import base64
import csv
from datetime import datetime, timezone
import hashlib
import io
from importlib.metadata import distribution
from pathlib import Path
import platform

if platform.system() != 'Linux' or platform.machine() != 'aarch64':
    raise SystemExit('Only intended for Linux/aarch64')
dist = distribution('nvidia-cusparselt-cu13')
if dist.version != '0.8.1':
    raise SystemExit(f'Refusing to change unexpected version {dist.version}')
info = Path(dist._path)
wheel = info / 'WHEEL'
record = info / 'RECORD'
old = wheel.read_text()
wrong = 'Tag: py3-none-manylinux2014_sbsa'
correct = 'Tag: py3-none-manylinux2014_aarch64'
if correct in old and wrong not in old:
    print('Already corrected'); raise SystemExit(0)
if old.count(wrong) != 1 or not record.is_file():
    raise SystemExit('Unexpected metadata format; no changes made')
rows = list(csv.reader(io.StringIO(record.read_text())))
indices = [i for i, row in enumerate(rows) if row and row[0].endswith('.dist-info/WHEEL')]
if len(indices) != 1:
    raise SystemExit('WHEEL entry missing/ambiguous; no changes made')
backup = info / ('WHEEL.backup.' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'))
backup.write_text(old)
new = old.replace(wrong, correct)
blob = new.encode()
wheel.write_bytes(blob)
digest = base64.urlsafe_b64encode(hashlib.sha256(blob).digest()).rstrip(b'=').decode()
rows[indices[0]][1:] = ['sha256=' + digest, str(len(blob))]
with record.open('w', newline='') as fh:
    csv.writer(fh).writerows(rows)
print('Patched:', wheel)
print('Backup:', backup)
