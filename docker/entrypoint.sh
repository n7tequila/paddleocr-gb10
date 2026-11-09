#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "${1:-}" != "" ]]; then
  exec "$@"
fi
: "${PADDLEOCR_PIPELINE:=PaddleOCR-VL-1.6}"
: "${PADDLEOCR_DEVICE:=gpu:0}"
: "${PADDLEOCR_HOST:=0.0.0.0}"
: "${PADDLEOCR_PORT:=8080}"
echo "Starting ORIGINAL PaddleX Serving: pipeline=$PADDLEOCR_PIPELINE device=$PADDLEOCR_DEVICE bind=$PADDLEOCR_HOST:$PADDLEOCR_PORT"
echo 'Endpoints and JSON request/response are maintained by PaddleX, not by this project.'
exec paddlex --serve --pipeline "$PADDLEOCR_PIPELINE" --device "$PADDLEOCR_DEVICE" --host "$PADDLEOCR_HOST" --port "$PADDLEOCR_PORT"
