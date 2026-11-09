#!/usr/bin/env bash
# Candidate reproduction script: NOT YET end-to-end validated on a clean GB10.
set -Eeuo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${WORKSPACE:-$HOME/paddleocr-gb10-work}"
CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-13.0}"
JOBS="${JOBS:-4}"
PADDLE_COMMIT="${PADDLE_COMMIT:-6c839e963ed}"
HELPER_COMMIT="180f451cb17d3e0fa62453cff6ad2363ed2acbba"
BUILD="$WORKSPACE/build"
PADDLE="$WORKSPACE/sources/Paddle"
HELPER="$WORKSPACE/sources/dgx-spark-paddlepaddle-gpu"
VENV="$WORKSPACE/build-venv"
WHEEL_DIR="$WORKSPACE/wheels"
mkdir -p "$BUILD" "$WORKSPACE/sources" "$WHEEL_DIR" "$WORKSPACE/logs"
LOG="$WORKSPACE/logs/build-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$LOG") 2>&1
printf 'Build log: %s\n' "$LOG"
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || { echo 'Linux aarch64 required'; exit 1; }
[[ -x "$CUDA_HOME/bin/nvcc" ]] || { echo "CUDA nvcc missing: $CUDA_HOME/bin/nvcc"; exit 1; }
"$CUDA_HOME/bin/nvcc" --version | grep -q 'release 13\.0' || { echo 'This build route was validated with CUDA 13.0, refusing another release'; exit 1; }
for bin in cmake ninja git python3 gcc g++ nm; do command -v "$bin" >/dev/null || { echo "Missing build tool: $bin"; exit 1; }; done
[[ "$JOBS" =~ ^[1-9][0-9]*$ ]] || { echo 'JOBS must be positive integer'; exit 1; }
AVAILABLE_KB=$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)
if (( AVAILABLE_KB < 50000000 )); then
    echo 'Less than ~48 GiB MemAvailable. Stop LLM manually and rerun.'
    free -h
    exit 1
fi
python3 -m venv "$VENV"
PY="$VENV/bin/python"
"$PY" -m pip install -U pip setuptools wheel
"$PY" -m pip install patchelf 'protobuf>=3.20' 'numpy==2.3.5' 'nvidia-cudnn-cu13==9.20.0.48'
CUDNN=$("$PY" - <<'PYCODE'
from pathlib import Path
import nvidia.cudnn
found = [Path(x) for x in nvidia.cudnn.__path__ if (Path(x)/'lib/libcudnn.so.9').is_file()]
if len(found) != 1:
    raise SystemExit(f'Expected one cuDNN location, found {found}')
print(found[0])
PYCODE
)
ln -sfn "$CUDNN/lib/libcudnn.so.9" "$CUDNN/lib/libcudnn.so"
export PATH="$VENV/bin:$CUDA_HOME/bin:$PATH"
export CUDA_HOME CUDA_TOOLKIT_ROOT_DIR="$CUDA_HOME"
get_repo() {
 local url="$1" dest="$2" commit="$3"
 if [[ ! -d "$dest/.git" ]]; then
   [[ ! -e "$dest" ]] || { echo "Non-Git directory exists: $dest"; exit 1; }
   git clone --filter=blob:none "$url" "$dest"
 fi
 git -C "$dest" fetch origin "$commit" --depth=1 || git -C "$dest" fetch origin
 git -C "$dest" checkout --detach "$commit"
 [[ "$(git -C "$dest" rev-parse HEAD)" == "$commit"* ]] || { echo "Commit mismatch: $dest"; exit 1; }
}
get_repo https://github.com/sarthaknimbalkar/dgx-spark-paddlepaddle-gpu.git "$HELPER" "$HELPER_COMMIT"
get_repo https://github.com/PaddlePaddle/Paddle.git "$PADDLE" "$PADDLE_COMMIT"
"$PY" -m pip install -r "$PADDLE/python/requirements.txt"
# Original MIT-licensed helper architecture fix, deliberately NOT using its build.sh.
"$PY" "$HELPER/patch_arch_generators.py" "$PADDLE"
"$PY" "$REPO/patches/fix_tlfloat_link.py" "$PADDLE"
cd "$PADDLE"
# Legacy warp libraries were patched in the original manual workflow. These files
# may or may not exist at this stage; avoid silent broad source rewrites.
for lib in warpctc warprnnt; do
  f="third_party/$lib/CMakeLists.txt"
  if [[ -f "$f" ]]; then
    "$PY" - "$f" <<'PYCODE'
from pathlib import Path
import sys
p=Path(sys.argv[1]); t=p.read_text()
for target in [
    'set(CUDA_NVCC_FLAGS "${NVCC_FLAGS_EXTRA} --std=c++11")',
    'set(CUDA_NVCC_FLAGS "${NVCC_FLAGS_EXTRA} -Xcompiler -fopenmp")',
    'set(CUDA_NVCC_FLAGS "${NVCC_FLAGS_EXTRA}")',
]:
    if target in t:
        t=t.replace(target, target.replace('${NVCC_FLAGS_EXTRA}', '-gencode arch=compute_90,code=sm_90'))
p.write_text(t)
PYCODE
  fi
done
cmake -S "$PADDLE" -B "$PADDLE/build" -GNinja \
  -DWITH_GPU=ON -DWITH_ARM=ON -DWITH_AVX=OFF \
  -DCUDA_ARCH_NAME=Manual -DCUDA_ARCH_BIN=121 \
  '-DCMAKE_CUDA_FLAGS=-U__ARM_NEON -DEIGEN_DONT_VECTORIZE=1' \
  -DPY_VERSION=3.12 -DPYTHON_EXECUTABLE="$PY" \
  -DWITH_TESTING=OFF -DWITH_DISTRIBUTE=OFF -DWITH_NCCL=OFF \
  -DCUDNN_ROOT="$CUDNN"
# SLEEF may be an ExternalProject. Build it first and verify no missing TLFloat link.
ninja -C "$PADDLE/build" -j"$JOBS" extern_sleef
"$PY" "$REPO/patches/fix_tlfloat_link.py" "$PADDLE"
# If a link line was removed after configure, reconfigure to regenerate build.ninja.
cmake -S "$PADDLE" -B "$PADDLE/build"
ninja -C "$PADDLE/build" -j"$JOBS"
shopt -s nullglob
files=("$PADDLE"/build/python/dist/paddlepaddle_gpu-*.whl)
(( ${#files[@]} == 1 )) || { echo "Expected one Paddle GPU Wheel, found ${#files[@]}"; exit 1; }
cp -v "${files[0]}" "$WHEEL_DIR/"
git -C "$PADDLE" rev-parse HEAD > "$WHEEL_DIR/paddle-source-commit.txt"
(cd "$WHEEL_DIR" && sha256sum ./*.whl > SHA256SUMS)
printf '\nSUCCESS: Wheel copied to %s\n' "$WHEEL_DIR"
