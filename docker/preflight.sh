#!/usr/bin/env bash
# Read-only validation before building or starting a GPU container.
set -Eeuo pipefail
BASE="${PADDLEOCR_BASE:-/data/llm-docker/paddleocr}"
echo '=== Host ==='
uname -m
free -h
nvidia-smi || true
echo '=== Qwen (read only) ==='
docker ps --format 'table {{.Names}}\t{{.Status}}' || true
echo '=== Required wheel ==='
ls -lh "$BASE"/wheels/paddlepaddle_gpu-*-cp312-cp312-linux_aarch64.whl
echo '=== Containers and port 8080 ==='
if command -v ss >/dev/null; then ss -ltnp | grep -E '(:8080[[:space:]]|Local Address)' || true; fi
echo '=== Model cache ==='
ls -ld "${PADDLEX_CACHE:-$HOME/.paddlex}" \
  "${PADDLEX_CACHE:-$HOME/.paddlex}/official_models/PP-DocLayoutV3" \
  "${PADDLEX_CACHE:-$HOME/.paddlex}/official_models/PaddleOCR-VL-1.6" || true
printf 'MemAvailable: '
awk '/MemAvailable:/ {printf "%.2f GiB\n", $2/1048576}' /proc/meminfo
echo 'Do not start duplicate PaddleX Serving while host port 8080 is occupied.'
