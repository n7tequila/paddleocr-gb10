#!/usr/bin/env bash
# Compatibility entry point for the small, reported GPU check.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PADDLEOCR_ALLOW_GPU_TEST=1 exec bash "$ROOT/tests/run-tests.sh" gpu
