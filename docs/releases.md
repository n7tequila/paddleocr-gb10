# Release v0.1.0 — NVIDIA GB10 foundation

**Status:** community reproduction / experimental. Initial GPU Wheel and PaddleOCR-VL inference were validated on one FusionXpark on 9 Nov 2026. The cleaned-up scripts in this repository have not been re-run end-to-end on a fresh machine.

## Included

- Pinned versions and build instructions for Ubuntu 24.04 ARM64, NVIDIA GB10 (SM 12.1), CUDA 13.0, Python 3.12.
- Source-build workflow and guarded SLEEF/TLFloat fix; cuDNN namespace path workaround.
- Separate PaddleOCR 3.7.0 / PaddleX 3.7.2 runtime setup and PaddleOCR-VL-1.6 single-image test.
- Troubleshooting history, real GPU verification output, and a three-run performance/memory benchmark.
- macOS publishing script for an **already created and empty** GitHub repository.

## Excluded

No 345 MB GPU Wheel, model weights, source checkouts, virtual environments, cached model data, logs with user details, or student documents are included. Distribute GPU Wheel separately only after verifying licensing and dependencies.

## Historical successful binary

- Version: `paddlepaddle_gpu-3.5.0.dev20261109+6c839e963ed-cp312-cp312-linux_aarch64.whl`
- SHA256: `a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb`
- This checksum records the original successful user build; a rebuild need not match byte-for-byte.

See [troubleshooting](troubleshooting.md) and [reproduction status](reproduction.md).

## v0.2.0 — Docker and official PaddleX Serving

The [v0.2.0 GitHub Release](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0) is published and includes the community-built [CPython 3.12 / Linux aarch64 PaddlePaddle GPU Wheel](https://github.com/n7tequila/paddleocr-gb10/releases/download/v0.2.0/paddlepaddle_gpu-3.5.0.dev20261109%2B6c839e963ed-cp312-cp312-linux_aarch64.whl) plus [SHA256SUMS](https://github.com/n7tequila/paddleocr-gb10/releases/download/v0.2.0/SHA256SUMS). The published checksum matches `a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb`. This Wheel targets Python 3.12, CUDA 13.0 and NVIDIA GB10 / SM 12.1; it is not an official PaddlePaddle binary or a claim of support for all ARM64 GPUs. Compatible NVIDIA CUDA Python, cuDNN, cuBLAS and NCCL dependencies are required; see [Dockerfile](../docker/Dockerfile) and the [cuSPARSELt metadata workaround](troubleshooting.md).

The locally built `paddleocr-gb10:0.2.0` image passed GB10 GPU tensor validation. Official PaddleX Serving with PaddleOCR-VL-1.6 returned HTTP 200 from `POST /layout-parsing` for a real handwritten essay in 18.59 seconds. Qwen3.8 was loaded but idle during the coexistence check. Simultaneous high-load use, concurrency, long-running reliability and other ARM64 GPU platforms remain unverified.

**GHCR status on 10 Nov 2026:** `ghcr.io/n7tequila/paddleocr-gb10:0.2.0` is the intended public image address. Anonymous token access returned HTTP 401 and its GitHub Package page returned HTTP 404. Public pull and the remote manifest's `linux/arm64` platform were therefore not verified. The repository's Compose example uses this address for when it becomes public; set `PADDLEOCR_IMAGE=paddleocr-gb10:0.2.0` to use the locally validated image meanwhile. See the [Docker guide](docker-v0.2.0.md).
