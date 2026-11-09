# Incident log / 完整排障复盘（2026-11-09）

This document records **observed events**, not a generic list of hypothetical errors. The initial successful workflow was interactive and had local edits; the repository installer is a later reconstruction. All private logs, model weights and personal images are intentionally excluded.

## Environment

- FusionXpark NVIDIA GB10 (`aarch64` / compute capability 12.1), 20 ARM CPU cores; Ubuntu 24.04.5; NVIDIA Linux kernel `7.0.0-1025-nvidia`.
- NVIDIA driver `580.178.04`, toolkit `nvcc 13.0.88`, runtime API 13.0; Docker 29.6.2, NVIDIA Container Toolkit 1.20.1; Python 3.12.3; GCC 13.3; CMake 3.28.3.
- Original workspace `/data/llm-docker/paddleocr/`; original references `sarthaknimbalkar/dgx-spark-paddlepaddle-gpu` commit `180f451cb17d3e0fa62453cff6ad2363ed2acbba` and `gaozhi-ustc/paddleocr-dgx` commit `f4782212daead5a1bd428f828c9cbc75787ae55e`.
- When Qwen3.8 was running: system `MemAvailable` ~18 GiB, vLLM GPU process **96,501 MiB**; before benchmark with Qwen stopped: 118.35 GiB available.

## 1. Git TLS interruption and rerun guard

Observed clone failure:

```text
fatal: unable to access 'https://github.com/sarthaknimbalkar/dgx-spark-paddlepaddle-gpu.git/':
GnuTLS recv error (-110): The TLS connection was non-properly terminated.
```

Then re-running the bootstrap exited because `/data/llm-docker/paddleocr` already existed. **Cause:** interrupted network request + overly strict one-time initialization guard. **Resolution:** use the user's already configured local network proxy, retry official GitHub URL, and make source bootstrap idempotent. No third-party proxy is used by this project.

## 2. cuDNN Python namespace `__file__ == None`

Observed during step `[1/7] build venv + deps`:

```text
TypeError: expected str, bytes or os.PathLike object, not NoneType
```

The original helper used `os.path.dirname(nvidia.cudnn.__file__)`. Namespace packages may have `__file__ is None`. **Resolution:** inspect `nvidia.cudnn.__path__` and verify `<package>/lib/libcudnn.so.9`; do not blindly assume `__file__` is a file. The new build script implements this detection and also checks the cuDNN path before CMake.

## 3. SLEEF / TLFloat erroneous dependency (central fix)

Observed after CMake success:

```text
ninja: error: 'third_party/install/sleef/lib/libtlfloat.a',
needed by 'paddle/phi/libphi_core.so', missing and no known rule to make it
```

The original helper *injected* this CMake line into `cmake/external/sleef.cmake`:

```cmake
set_property(TARGET sleef PROPERTY INTERFACE_LINK_LIBRARIES "${SLEEF_LIB_DIR}/libtlfloat.a")
```

Initial recovery tried to find/copy `libtlfloat.a`; none existed. Next, `ninja -C build -j4 extern_sleef` **succeeded**: SLEEF 3.6.1 completed 160 build steps, installed `libsleef.a`, `libsleefgnuabi.a`, and headers, **but did not produce** `libtlfloat.a`. The previously proposed recovery by copying that library was therefore invalid for this source combination.

**Successful recovery:** check `nm -u` for unresolved TLFloat symbols in `libsleef.a` before changing linkage; remove exactly the injected `INTERFACE_LINK_LIBRARIES` reference; regenerate build with `cmake -S Paddle -B Paddle/build`; run incremental `ninja -C build -j4`. Do not `touch libtlfloat.a` or create an empty static archive. The reconstructed build script does **not inject** this dependency, and `patches/fix_tlfloat_link.py` performs a guarded removal if present.

Note: the observed success is specific to the pinned Paddle commit + linked SLEEF configuration; if a future version genuinely requires TLFloat, **build the actual dependency** instead of removing it.

## 4. Large Eigen warning flood during actual build

```text
warning: bitwise operation between different enumeration types ...
[-Wdeprecated-enum-enum-conversion]
```

GCC 13.3 emitted repetitive warnings from Eigen C++ tensor templates while compiling `slice.cc`. No `FAILED:` or fatal diagnostic was present in the submitted excerpt. **Resolution:** treat warnings as non-fatal, inspect the true exit status, and avoid suppressing meaningful errors prematurely.

## 5. Ctrl+C during Ninja

The build was interrupted manually with Ctrl+C while progressing. **Resolution:** preserve CMake/Ninja cache and rerun `ninja -C "$BUILD" -j4` with `set -o pipefail`; compiled targets are reused. Do **not** clean or run the original unpatched helper again. Subsequent incremental build completed successfully.

## 6. Wheel built + GPU verified

Actual artifact:

```text
paddlepaddle_gpu-3.5.0.dev20261109+6c839e963ed-cp312-cp312-linux_aarch64.whl
SHA256 a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb
size ~345 MB
```

`paddle.device.is_compiled_with_cuda() == True`; CUDA compute capability 12.1, driver/runtime API 13.0; GPU matmul succeeded; `paddle.utils.run_check()` printed `PaddlePaddle works well on 1 GPU.`

## 7. Runtime resolver: NumPy too new

Runtime installed `paddleocr==3.7.0`, `paddlex==3.7.2` and custom PaddlePaddle Wheel. Default `pip install --force-reinstall` of the local Wheel reinstalled transitive dependencies and upgraded NumPy to **2.5.4**, conflicting with:

```text
paddlex 3.7.2 requires numpy<2.4,>=1.24
```

**Resolution:** restore `numpy==2.3.5` and install the already-built PaddlePaddle Wheel with `--no-deps` once compatible dependencies have been prepared. The new runtime script pins NumPy and verifies `pip check`.

## 8. `nvidia-cusparselt-cu13` metadata mismatch

`pip check` initially showed:

```text
nvidia-cusparselt-cu13 0.8.1 is not supported on this platform
```

Package metadata from runtime venv:

```text
Wheel-Version: 1.0
Root-Is-Purelib: true
Tag: py3-none-manylinux2014_sbsa
```

The built PaddlePaddle required **exactly** `nvidia-cusparselt-cu13==0.8.1; platform_system == "Linux"`, so a straightforward upgrade to `0.8.1.post1` would not satisfy that pin. The original operator corrected the local installed WHEEL tag to `manylinux2014_aarch64` and updated its `RECORD` hash/size. Subsequently `pip check` returned `No broken requirements found`, and GPU matmul still passed. This is a **local metadata workaround**, not an NVIDIA library patch or proof that every sparse-kernel path works.

An optional, opt-in, reversible helper is provided at `scripts/fix-cusparselt-metadata.py`; it refuses unexpected tags/versions and writes a backup. Do not treat metadata modification as generally safe for unrelated machines.

## 9. VL-1.6 first actual inference

Called `PaddleOCRVL(pipeline_version="v1.6", device="gpu:0", use_doc_orientation_classify=False, use_doc_unwarping=False)` using `paddle_dynamic` backend. `PP-DocLayoutV3` and `PaddleOCR-VL-1.6-0.9B` auto-downloaded; model weights loaded successfully and produced 1 parsed page with Markdown and JSON output.

First run wall time: **54.64 s**, initialization **36.92 s** (model download was already completed during init; test image downloaded subsequently). A benign Paddle tensor construction warning was visible.

## 10. Repeat benchmark

One cached local 1524×1368 newspaper image; single process, three serial runs:

| Metric | Observed |
| --- | ---: |
| Baseline MemAvailable | 118.35 GiB |
| Model initialization | 15.670 s |
| Run 1 | 16.875 s |
| Run 2 | 15.453 s |
| Run 3 | 15.144 s |
| Peak Python RSS | 3,376.69 MiB |
| Maximum MemAvailable drop | 9,311.23 MiB = ~9.09 GiB |

The output contained **31 parsed blocks**, including some empty text blocks and merged paragraphs; 27 nonempty text blocks and one image block were identified in a manual review. This is *not* a character-accuracy benchmark because the original newspaper source image was not independently ground-truthed. See [benchmarks](benchmarks.md).

## 11. Docker build and official Serving

The GB10 Docker image `paddleocr-gb10:0.2.0` was built using the local PaddlePaddle GPU Wheel. The build needed the same cuSPARSELt 0.8.1 metadata fix as the host: its installed WHEEL tag used `manylinux2014_sbsa` on ARM64. `docker/fix-cusparselt-wheel-tag.py` changes the installed tag to `manylinux2014_aarch64` and updates the corresponding RECORD hash and size. It does not patch NVIDIA binary libraries. The Dockerfile restores protobuf 7.36.1 and httpx 0.28.1 after installing the custom Paddle Wheel with `--no-deps`; it installs CUDA Python runtime requirements explicitly and runs `pip check`.

The `--no-deps` Wheel install prevents pip from replacing the custom ARM64 GPU build, but also leaves its dependencies unresolved. During Docker preparation, `pip check` exposed missing runtime dependencies. The fix is to install the Wheel's compatible protobuf, httpx and CUDA package versions explicitly, retaining NumPy 2.3.5 and PaddleOCR/PaddleX 3.7.0/3.7.2. The Dockerfile checks `google.protobuf.internal.builder`, runs `pip check`, then imports CUDA-enabled Paddle. Avoid a general `pip install --upgrade` here: it previously raised NumPy beyond PaddleX's `<2.4` bound.

The existing image then passed Docker GPU validation (compute capability 12.1). Official PaddleX Serving started; its `/layout-parsing` endpoint returned HTTP 200 for a real handwritten essay in 18.59 seconds. The validated image's `pip freeze` was captured as `docker/requirements-verified.txt`. This constraints file and updated build context packaging have **not yet been tested by a fresh build**. If a rebuild fails, keep the first pip or Docker error and compare it with the package versions in that file before changing any pinned CUDA dependency.

## Open work / not yet validated

- This clean-room installation flow on a different empty GB10 host.
- Fresh image rebuild using the new exact dependency constraints; multi-request throughput, concurrency and long-running service stability.
- Simultaneous Qwen3.8 generation plus OCR runtime safety and repeated-request memory metrics.
- Chinese child handwriting, formulas, vertical arithmetic, essays, and homework question-answer linking.
- Compatibility after future upstream API / CUDA / driver updates.
