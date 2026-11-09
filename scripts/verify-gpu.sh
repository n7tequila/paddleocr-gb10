#!/usr/bin/env bash
set -Eeuo pipefail
WORKSPACE="${WORKSPACE:-$HOME/paddleocr-gb10-work}"
"$WORKSPACE/runtime-venv/bin/python" - <<'PYCODE'
import paddle
print('Paddle:', paddle.__version__)
print('CUDA:', paddle.device.is_compiled_with_cuda())
assert paddle.device.is_compiled_with_cuda()
paddle.set_device('gpu:0')
y=paddle.matmul(paddle.ones([128,128]), paddle.ones([128,128]))
assert float(y[0,0]) == 128.0
print('Matmul device:', y.place)
paddle.utils.run_check()
print('GPU verification PASS')
PYCODE
