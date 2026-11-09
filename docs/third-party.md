# Third-party notices

The original scripts and documentation in this repository are MIT licensed. Upstream repositories and pretrained models retain their own independent licenses.

- `https://github.com/sarthaknimbalkar/dgx-spark-paddlepaddle-gpu` — MIT; this project fetches its `patch_arch_generators.py` at pinned Git commit during build; does not copy the upstream helper's build script.
- `https://github.com/gaozhi-ustc/paddleocr-dgx` — deployment architecture reference only, no files copied.
- `https://github.com/PaddlePaddle/Paddle` — third-party PaddlePaddle source, built separately.
- `https://github.com/PaddlePaddle/PaddleOCR` and `https://github.com/PaddlePaddle/PaddleX` — third-party runtime libraries.
- NVIDIA CUDA, cuDNN, cuSPARSELt packages — subject to their vendor licenses.
- PaddleOCR model weights — separately downloaded third-party assets; check usage and distribution rules before redistribution.

The original Wheel was created from pinned upstream Paddle source with local patches. Do not relicense Paddle/NVIDIA binary files under this repository's MIT license.
