#!/usr/bin/env python3
"""Guarded cleanup of the historical SLEEF TLFloat link injection.

Checks that the available SLEEF static archive doesn't have unresolved symbol
names mentioning TLFloat. If no archive exists yet, only remove a known injected
line before configure; source upgrades require manual review.
"""
import argparse
from pathlib import Path
import subprocess
import shutil

p = argparse.ArgumentParser()
p.add_argument('paddle_source', type=Path)
a = p.parse_args()
src = a.paddle_source.resolve()
cmake = src / 'cmake/external/sleef.cmake'
if not cmake.is_file():
    p.error(f'missing {cmake}')
text = cmake.read_text()
lines = text.splitlines(keepends=True)
matched = [line for line in lines if 'INTERFACE_LINK_LIBRARIES' in line and 'libtlfloat.a' in line]
if not matched:
    print('SLEEF: no injected TLFloat link found, no change needed')
    raise SystemExit(0)
if len(matched) != 1 or not matched[0].strip().startswith('set_property(TARGET sleef PROPERTY INTERFACE_LINK_LIBRARIES'):
    p.error('Unexpected TLFloat link lines: manual review required')
archive = src/'build/third_party/install/sleef/lib/libsleef.a'
if archive.is_file():
    out = subprocess.run(['nm', '-u', str(archive)], capture_output=True, text=True, check=True).stdout
    if any('tlfloat' in line.lower() for line in out.splitlines()):
        p.error('libsleef.a references TLFloat: cannot safely remove linkage')
else:
    print('SLEEF not yet compiled: removing *known helper-injected line* only; review if version changes')
backup = cmake.with_suffix(cmake.suffix+'.gb10-backup')
if not backup.exists():
    shutil.copy2(cmake, backup)
cmake.write_text(''.join(line for line in lines if line not in matched))
print(f'SLEEF: removed invalid helper-injected TLFloat link; backup: {backup}')
