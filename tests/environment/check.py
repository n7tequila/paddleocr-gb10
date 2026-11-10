"""Run inside the existing image without GPU, network, or model inference."""
import importlib.metadata as metadata
import json
import platform
import subprocess
import sys

EXPECTED = {
    "paddlepaddle-gpu": "3.5.0.dev20261109+6c839e963ed",
    "paddleocr": "3.7.0",
    "paddlex": "3.7.2",
    "protobuf": "7.36.1",
    "sentencepiece": "0.2.3",
    "nvidia-cusparselt-cu13": "0.8.1",
}
observed = {name: metadata.version(name) for name in EXPECTED}
assert observed == EXPECTED, f"Package versions differ: {observed}"
assert platform.python_implementation() == "CPython" and sys.version_info[:2] == (3, 12)
assert platform.machine() == "aarch64", platform.machine()
try:
    metadata.version("paddlepaddle")
except metadata.PackageNotFoundError:
    pass
else:
    raise AssertionError("CPU paddlepaddle distribution is also installed")

import paddle
import google.protobuf.internal.builder
import sentencepiece

assert paddle.is_compiled_with_cuda(), "Paddle was replaced with a CPU build"
assert paddle.__file__.startswith("/opt/ocr-venv/"), paddle.__file__
wheel = metadata.distribution("nvidia-cusparselt-cu13").read_text("WHEEL") or ""
assert "manylinux2014_aarch64" in wheel and "manylinux2014_sbsa" not in wheel, wheel
check = subprocess.run([sys.executable, "-m", "pip", "check"], text=True, capture_output=True)
assert check.returncode == 0, f"pip check failed: {check.stdout} {check.stderr}"
print(json.dumps({"versions": observed, "paddle_path": paddle.__file__,
                  "architecture": platform.machine(), "python": platform.python_version(),
                  "cuda_build": paddle.version.cuda(), "cusparselt_tag": "manylinux2014_aarch64",
                  "pip_check": check.stdout.strip()}))
