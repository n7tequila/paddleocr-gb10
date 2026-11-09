#!/usr/bin/env bash
# Self-contained runtime venv (host GB10). No models launched.
set -Eeuo pipefail
WORKSPACE="${WORKSPACE:-$HOME/paddleocr-gb10-work}"
VENV="$WORKSPACE/runtime-venv"
mkdir -p "$WORKSPACE/logs"
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || { echo 'Linux aarch64 required'; exit 1; }
shopt -s nullglob
wheels=("$WORKSPACE"/wheels/paddlepaddle_gpu-*.whl)
(( ${#wheels[@]} == 1 )) || { echo "Place exactly one built wheel under $WORKSPACE/wheels"; exit 1; }
python3 -m venv "$VENV"
PY="$VENV/bin/python"
"$PY" -m pip install -U pip setuptools wheel
"$PY" -m pip install 'paddleocr[doc-parser]==3.7.0' 'paddlex==3.7.2' 'numpy==2.3.5'
# Install wheel runtime deps separately, then install local build without a full
# force-reinstall. The exact dependency versions are metadata of the local wheel.
"$PY" -m pip install "${wheels[0]}" || {
  echo 'Initial local Wheel install failed. Inspect dependency resolver output.' >&2
  exit 1
}
"$PY" -m pip install --no-deps 'numpy==2.3.5'
"$PY" -m pip install --no-deps --force-reinstall "${wheels[0]}"
"$PY" -m pip check || echo 'pip check has issues: read docs/troubleshooting.md (cuSPARSELt metadata).'
"$PY" - <<'PYCODE'
import paddle, paddleocr
print('Paddle', paddle.__version__)
print('PaddleOCR', paddleocr.__version__)
print('CUDA compiled', paddle.device.is_compiled_with_cuda())
paddle.set_device('gpu:0')
x=paddle.ones([32,32]); y=paddle.matmul(x,x)
assert float(y[0,0]) == 32.0
print('GPU matmul PASS')
PYCODE
"$PY" -m pip freeze > "$WORKSPACE/runtime-requirements.lock"
echo "Runtime ready: $VENV"
