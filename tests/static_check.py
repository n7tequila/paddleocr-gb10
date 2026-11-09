#!/usr/bin/env python3
"""Source-distribution safety inspection (not a GPU integration test)."""
from pathlib import Path
from py_compile import compile
root=Path(__file__).resolve().parents[1]
for py in root.rglob('*.py'):
    compile(str(py), doraise=True)
for f in root.rglob('*'):
    if f.is_file() and (f.suffix.lower() in {'.whl','.safetensors','.pdparams','.pem','.key'} or f.stat().st_size>10_000_000):
        raise AssertionError(f'Forbidden artifact: {f}')
print('Python syntax + artifact safety: PASS')
