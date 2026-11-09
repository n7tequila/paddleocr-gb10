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
