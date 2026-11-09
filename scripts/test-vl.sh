#!/usr/bin/env bash
set -Eeuo pipefail
WORKSPACE="${WORKSPACE:-$HOME/paddleocr-gb10-work}"
[[ $# -eq 1 && -f "$1" ]] || { echo "Usage: $0 /absolute/path/to/image.png"; exit 2; }
mkdir -p "$WORKSPACE/results"
export PADDLE_PDX_MODEL_SOURCE="${PADDLE_PDX_MODEL_SOURCE:-BOS}"
export PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True
"$WORKSPACE/runtime-venv/bin/python" - "$1" "$WORKSPACE/results" <<'PYCODE'
import sys,time
from pathlib import Path
from paddleocr import PaddleOCRVL
input_path, output = sys.argv[1], Path(sys.argv[2]); output.mkdir(exist_ok=True,parents=True)
t0=time.monotonic()
pipeline=PaddleOCRVL(pipeline_version='v1.6',device='gpu:0',use_doc_orientation_classify=False,use_doc_unwarping=False)
print(f'Initialized in {time.monotonic()-t0:.3f}s',flush=True)
num=0
for res in pipeline.predict(input_path):
    res.save_to_json(save_path=str(output))
    res.save_to_markdown(save_path=str(output))
    num += 1
print(f'Pages: {num}; elapsed: {time.monotonic()-t0:.3f}s; saved to: {output}', flush=True)
assert num > 0
PYCODE
