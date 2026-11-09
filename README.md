# PaddleOCR on NVIDIA GB10 (ARM64 / CUDA 13.0)

[中文文档](README.zh-CN.md) · [Troubleshooting](docs/troubleshooting.md) · [Reproduction](docs/reproduction.md) · [Benchmarks](docs/benchmarks.md)

**Community project; not affiliated with PaddlePaddle, NVIDIA, or the projects credited below.**

Run a self-built `paddlepaddle-gpu` Python 3.12 wheel with PaddleOCR 3.7.0 / PaddleX 3.7.2 and PaddleOCR-VL-1.6 on a GB10 (`aarch64`, `sm_121`, CUDA 13.0). The first reported validation was performed on a FusionXpark in November 2026.

## Verified result (9 Nov 2026)

| Component | Observed |
| --- | --- |
| Host | Ubuntu 24.04.5 / Linux aarch64, NVIDIA GB10 |
| Driver / CUDA | 580.178.04 / 13.0.88 |
| Compute capability | 12.1 (`sm_121`) |
| Python | 3.12.3 |
| PaddlePaddle source | `6c839e963ed`, 3.5.0.dev20261109 |
| PaddlePaddle wheel | 345 MB, `cp312-cp312-linux_aarch64` |
| PaddleOCR / PaddleX | 3.7.0 / 3.7.2 |
| Pipeline | `PaddleOCRVL(pipeline_version="v1.6", device="gpu:0")` |
| GPU sanity | `paddle.utils.run_check()` and GPU matrix multiplication **PASS** |
| VL result | 1 page parsed, JSON/Markdown output **PASS** |
| VL warm timings | 15.453s, 15.144s on a 1524×1368 news page |
| Memory during VL benchmark | process RSS peak 3,376.69 MiB; max `MemAvailable` drop 9,311.23 MiB |

**Important:** build and runtime scripts in this repository are a **reconstructed, cleaned-up reproduction path**, not an end-to-end re-run of the exact scripts on another machine. The results above describe the actual manually repaired host environment, not a promise that this repository's installer has been verified end-to-end. Preserve this distinction when reporting results.

## Quick start (GB10 host, not macOS)

```bash
# Ubuntu 24.04 / aarch64 / CUDA 13.0, build prerequisites
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-dev build-essential \
  cmake ninja-build patchelf swig libopenblas-dev liblapack-dev gfortran

git clone https://github.com/n7tequila/paddleocr-gb10.git
cd paddleocr-gb10

# Ensure 48+ GiB MemAvailable for source build. Stop large LLMs yourself.
JOBS=4 bash scripts/build-paddle.sh

# Then install the generated wheel into a separate runtime venv.
bash scripts/setup-runtime.sh

# Run a single locally cached demo/test image (models auto-download on first use).
bash scripts/test-vl.sh /path/to/image.png
```

`WORKSPACE` defaults to `$HOME/paddleocr-gb10-work` (build/source/venvs/wheels/results). The scripts never stop running containers. Set `WORKSPACE=/data/llm-docker/paddleocr-gb10-work` if you prefer the data disk. A build needs substantial free RAM; `ninja` supports incremental recovery after interruption.

**No automatic Docker Compose service is included in v0.1.0.** The real validation used a host Python venv, not a Dockerized OCR service. Docker is a planned follow-up after dual-model memory testing. Do not mistake this project for a production-ready appliance.

## Building details

The build script fetches the original GB10 helper project at a pinned commit (`180f451cb17d3e0fa62453cff6ad2363ed2acbba`, MIT licensed) to reuse its CUTLASS architecture patch, then checks out PaddlePaddle at the **observed successful source commit** `6c839e963ed`. It applies the architecture patch and a guarded cleanup of the erroneous TLFloat dependency. It **does not** execute or redistribute the original helper `build.sh` and does not inject `libtlfloat.a`. Other ARM64 upstream issues may require further local debugging. Refer to [reproduction details](docs/reproduction.md).

When built, the wheel lands in `$WORKSPACE/wheels` and a SHA-256 manifest is written there. The historically validated wheel SHA-256 was:

```text
a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb
```

That checksum is a **record of the original build**, not the expected hash of every new build; wheel timestamps and dependencies can change it. Binary wheel and model weights are **not** committed to Git.

## Common failures

- `GnuTLS recv error (-110)` while cloning → check your own Git proxy/network, retry. No third-party proxy is configured.
- Re-run stopped by pre-existing workspace → this project uses reusable directories and checks commits.
- `nvidia.cudnn.__file__ is None` → resolve cuDNN namespace package through `__path__`.
- `libtlfloat.a ... missing and no known rule` → SLEEF 3.6.1 produced `libsleef.a`, **not** `libtlfloat.a`; do not fabricate an empty archive. Remove the injected link rule after dependency inspection.
- Huge GCC Eigen `-Wdeprecated-enum-enum-conversion` output → a warning, not necessarily a build failure.
- `pip check` rejects `nvidia-cusparselt-cu13==0.8.1` on `manylinux2014_sbsa` metadata → see documented optional local-only workaround.

Complete timeline, exact errors, and commands: **[Troubleshooting](docs/troubleshooting.md)**.

## Benchmark interpretation

On the reference system the VL pipeline loaded in 15.670 s (cached) and processed the same page in 16.875 / 15.453 / 15.144 s. Process RSS was 3.30 GiB at peak; system `MemAvailable` dropped 9.09 GiB at most. Those figures **cannot be added** or treated as exclusive VRAM on GB10 unified memory. A Qwen3.8 vLLM instance previously used ~96,501 MiB GPU-reported memory and left ~18 GiB system-available RAM. **Co-residency has not yet been tested**, and OCR handwriting, formulas, child homework, accuracy, and concurrency remain unverified.

## Notes on kids' homework

The goal is educational parsing of photographed questions, handwritten essays, arithmetic, and formulas. The included demo benchmark is an **ordinary printed Chinese newspaper page**, not a handwriting accuracy benchmark. Do not automatically grade a child's answer from unverified OCR; retain original images, bounding boxes, and a human review path.

## Attribution and licensing

Original GB10 build guidance and architecture patch: [sarthaknimbalkar/dgx-spark-paddlepaddle-gpu](https://github.com/sarthaknimbalkar/dgx-spark-paddlepaddle-gpu) (MIT). Docker/service reference: [gaozhi-ustc/paddleocr-dgx](https://github.com/gaozhi-ustc/paddleocr-dgx) (referenced, not copied). PaddlePaddle: [PaddlePaddle/Paddle](https://github.com/PaddlePaddle/Paddle); PaddleOCR: [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR). This repository's **original scripts and docs** are MIT licensed. Dependencies, downloaded source and model weights retain their own licenses; inspect them before redistributing binaries. See [third-party notices](docs/third-party.md).

## Security / releases

Never commit private student images, model caches, auth tokens, virtualenvs, or compiled builds. Review source patches before running them. For a GitHub Release, upload the wheel as a separate asset only after verifying dependencies, licensing and provenance; see [Release guide](docs/releases.md).

## Publish from macOS

The existing GitHub repository can be populated using the provided macOS publisher. See [PUBLISHING.md](PUBLISHING.md). The publisher is **not** used on the GB10 host.
