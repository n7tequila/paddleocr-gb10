# Reproduction guide and scope

The source build on 2026-11-09 was an **interactive recovery workflow** using the community `build.sh`, plus locally created repair scripts. It is not possible to assert byte-for-byte equivalence merely by rechecking out Paddle commit. This repository supplies a conservative, inspectable reconstruction.

## Pinned source

- Paddle source commit observed in successful Wheel: `6c839e963ed` (`PaddlePaddle/Paddle`)
- Original helper repository commit: `180f451cb17d3e0fa62453cff6ad2363ed2acbba`
- Helper MIT-licensed CUTLASS architecture generator patch invoked by this project, stored **in upstream Git** (downloaded at build time, not copied into this repo).
- Second comparison project `gaozhi-ustc/paddleocr-dgx` commit `f4782212daead5a1bd428f828c9cbc75787ae55e`: Docker-focused, CUDA 13.1; not executed here.

## Build phases

1. Confirm Linux aarch64, `nvcc 13.0`, Python 3.12, and `nvidia-smi` GB10 SM 12.1. Do not alter the host driver.
2. Create private workspace, venv and pip dependencies; locate `nvidia.cudnn` through `__path__` and verify cuDNN shared library.
3. Clone helper repository and Paddle source, checkout pinned commits. Refuse a mismatched existing checkout.
4. Apply upstream helper's CUTLASS sm_121 architecture generator patch; no `libtlfloat.a` injection. Apply guarded cleanup if a stale injection exists; patching warpctc/warprnnt is conditional and may require further future adaptation.
5. Configure CMake for `WITH_GPU=ON`, `WITH_ARM=ON`, `WITH_NCCL=OFF`, `WITH_DISTRIBUTE=OFF`, `WITH_TESTING=OFF`, `CUDA_ARCH_BIN=121`, and `-U__ARM_NEON -DEIGEN_DONT_VECTORIZE=1`.
6. `ninja -j4` with `pipefail`, preserve logs; rerun if interrupted.
7. Copy wheel, record source commit, SHA256; install into **separate venv**, then GPU sanity check.

## Precautions

- Use at least ~48 GiB `MemAvailable` before a build. This is a guardrail, not an exact build limit.
- No `sudo pip`, no installation into system Python, no automatic stopping of other services.
- The helper patch is reviewed/executed as a third-party script from a pinned commit. Review its source and repository license before executing.
- The pin is a Git revision, not a supply-chain signature. Check network/TLS authenticity and consider SHA256 for every downloaded dependency for stricter reproducibility.
- Model files are downloaded by PaddleX into its model cache on first test. Their licensing and exact downloaded hashes are not captured by this repository.
- `PIP_INDEX_URL` may be set to a domestic PyPI mirror by the operator; nothing hardcodes a proxy.
- This project has not yet verified a clean full re-build end-to-end after refactoring.

## Upgrades

Maintain three independent version tracks: (1) PaddlePaddle GPU Wheel / Python ABI / CUDA; (2) PaddleOCR + PaddleX Python packages; (3) OCR-VL and layout model weights. Create a new venv and retest before switching. Do not overwrite the last known-good Wheel or push binary artifacts into source control. Preserve the previous environment for rollback.
