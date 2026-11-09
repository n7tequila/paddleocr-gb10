#!/usr/bin/env python3
"""Fix NVIDIA cuSPARSELt 0.8.1 installed wheel metadata on ARM64.

Only changes an unsupported manylinux2014_sbsa wheel tag to
manylinux2014_aarch64. Does not modify binary libraries.
"""
import base64
import csv
import hashlib
import io
import platform
import sys
import sysconfig
from pathlib import Path

PACKAGE = "nvidia-cusparselt-cu13"
VERSION = "0.8.1"

if platform.machine() != "aarch64":
    raise SystemExit("ERROR: This fix is only for Linux aarch64")

site = Path(sysconfig.get_paths()["purelib"])
matches = list(site.glob("nvidia_cusparselt_cu13-0.8.1.dist-info"))

if len(matches) != 1:
    raise SystemExit(
        "ERROR: Expected exactly one cuSPARSELt dist-info; found "
        + str(len(matches))
    )

dist = matches[0]
wheel = dist / "WHEEL"
record = dist / "RECORD"

if not wheel.is_file() or not record.is_file():
    raise SystemExit("ERROR: Missing WHEEL or RECORD metadata")

original = wheel.read_bytes()
text = original.decode("utf-8")

old = "manylinux2014_sbsa"
new = "manylinux2014_aarch64"

tag_lines = [
    line for line in text.splitlines()
    if line.startswith("Tag: ")
]

if not tag_lines:
    raise SystemExit("ERROR: WHEEL has no Tag metadata")

if all(old not in line for line in tag_lines):
    if all(new in line for line in tag_lines):
        print("cuSPARSELt tag already compatible")
        sys.exit(0)
    raise SystemExit(
        "ERROR: Unexpected wheel tags: " + repr(tag_lines)
    )

if any(old not in line for line in tag_lines):
    raise SystemExit("ERROR: Mixed wheel tags; refusing to modify")

updated = text.replace(old, new).encode("utf-8")

rows = list(csv.reader(
    io.StringIO(record.read_text(encoding="utf-8"), newline="")
))

wheel_record_path = dist.name + "/WHEEL"
count = 0

for row in rows:
    if row and row[0] == wheel_record_path:
        digest = base64.urlsafe_b64encode(
            hashlib.sha256(updated).digest()
        ).rstrip(b"=").decode("ascii")

        row[1] = "sha256=" + digest
        row[2] = str(len(updated))
        count += 1

if count != 1:
    raise SystemExit(
        "ERROR: WHEEL entry not found exactly once in RECORD"
    )

buffer = io.StringIO(newline="")
writer = csv.writer(buffer, lineterminator="\n")
writer.writerows(rows)

wheel.write_bytes(updated)
record.write_text(buffer.getvalue(), encoding="utf-8")

print("Fixed:", wheel)
print("Tag:", old, "->", new)
print("RECORD SHA256 and size updated")
