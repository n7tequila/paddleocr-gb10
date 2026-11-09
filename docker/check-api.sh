#!/usr/bin/env bash
# Uses the official JSON + base64 API, not a custom endpoint.
set -Eeuo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${1:-${PADDLEOCR_SAMPLE:-$HOME/.paddlex/predict_input/paddleocr_vl_demo.png}}"
URL="${PADDLEOCR_API_URL:-http://127.0.0.1:8004/layout-parsing}"
[[ -f "$IMAGE" ]] || { echo "Image not found: $IMAGE" >&2; exit 1; }
python3 "$REPO/docker/test-official-api.py" --url "$URL" --image "$IMAGE" \
  --output "${PADDLEOCR_RESULT:-$REPO/docker/api-smoke-result.json}"
