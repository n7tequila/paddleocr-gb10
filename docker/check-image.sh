#!/usr/bin/env bash
set -Eeuo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${PADDLEOCR_IMAGE:-paddleocr-gb10:0.2.0}"
command -v docker >/dev/null || { echo 'Docker is missing' >&2; exit 1; }
# The check runs CUDA ops inside the container; it does not start the web service.
docker run --rm --gpus all --entrypoint python "$IMAGE" -c '
import importlib.metadata as m
import paddle
print("Paddle:",m.version("paddlepaddle-gpu"))
print("PaddleOCR:",m.version("paddleocr"))
print("PaddleX:",m.version("paddlex"))
assert paddle.is_compiled_with_cuda()
paddle.set_device("gpu:0")
x=paddle.ones([8,8]); print("CUDA tensor sum:",x.sum().numpy())
'
echo 'CUDA verification passed. Next run: docker/check-api.sh /path/to/image.png'
