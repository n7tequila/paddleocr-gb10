#!/usr/bin/env bash
set -Eeuo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${WORKSPACE:-$HOME/paddleocr-gb10-work}"
[[ $# -eq 1 && -f "$1" ]] || { echo "Usage: $0 /absolute/path/to/image.png"; exit 2; }
mkdir -p "$WORKSPACE/benchmarks"
AVAIL=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
if (( AVAIL < 33554432 )); then
  echo 'Less than 32 GiB available, aborting baseline benchmark. Do not risk Qwen co-residency without a monitored test.'
  exit 1
fi
export PADDLE_PDX_MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-BOS}"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
"$WORKSPACE/runtime-venv/bin/python" "$REPO/benchmarks/benchmark_vl.py" "$1" "$WORKSPACE/benchmarks"
