#!/usr/bin/env bash
set -Eeuo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_BASE="${PADDLEOCR_BASE:-/data/llm-docker/paddleocr}"
WHEEL_DIR="${PADDLE_WHEEL_DIR:-$PROJECT_BASE/wheels}"
IMAGE="${PADDLEOCR_IMAGE:-paddleocr-gb10:0.2.0}"

# Optional mirrors for mainland China:
# export APT_MIRROR="https://mirrors.aliyun.com/ubuntu-ports"
# export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

APT_MIRROR="${APT_MIRROR:-}"
PIP_INDEX_URL="${PIP_INDEX_URL:-}"

EXPECTED_SHA256="a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb"

[[ "$(uname -m)" == "aarch64" ]] || {
    echo "ERROR: Requires ARM64 host."
    exit 1
}

command -v docker >/dev/null || {
    echo "ERROR: Docker not found."
    exit 1
}

mapfile -t wheels < <(
    find "$WHEEL_DIR" -maxdepth 1 -type f \
      -name 'paddlepaddle_gpu-*-cp312-cp312-linux_aarch64.whl' |
    sort
)

if (( ${#wheels[@]} != 1 )); then
    echo "ERROR: Expected exactly one PaddlePaddle GPU wheel."
    printf '%s\n' "${wheels[@]}"
    exit 1
fi

WHEEL="${wheels[0]}"
SHA="$(sha256sum "$WHEEL" | awk '{print $1}')"

if [[ "${ALLOW_UNVERIFIED_WHEEL:-0}" != "1" &&
      "$SHA" != "$EXPECTED_SHA256" ]]; then
    echo "ERROR: Wheel SHA256 mismatch."
    echo "Actual:   $SHA"
    echo "Expected: $EXPECTED_SHA256"
    exit 1
fi

if docker image inspect "$IMAGE" >/dev/null 2>&1 &&
   [[ "${REBUILD_EXISTING_IMAGE:-0}" != "1" ]]; then
    echo "ERROR: Image already exists: $IMAGE"
    echo "Set REBUILD_EXISTING_IMAGE=1 to rebuild."
    exit 1
fi

CTX="$(mktemp -d "${TMPDIR:-/tmp}/paddleocr-gb10-build.XXXXXX")"
trap 'rm -rf "$CTX"' EXIT

mkdir -p "$CTX/docker/.build"

# Required Docker build files.
cp "$REPO/docker/Dockerfile" "$CTX/docker/"
cp "$REPO/docker/entrypoint.sh" "$CTX/docker/"
cp "$REPO/docker/requirements-verified.txt" "$CTX/docker/"
cp "$REPO/docker/.dockerignore" "$CTX/.dockerignore"

# Copy only the metadata repair used by the Dockerfile.
cp "$REPO/docker/fix-cusparselt-wheel-tag.py" "$CTX/docker/"

# Copy only the verified wheel, never the whole runtime directory.
cp "$WHEEL" "$CTX/docker/.build/$(basename "$WHEEL")"

echo "=== Docker build ==="
echo "Image: $IMAGE"
echo "Wheel: $WHEEL"
echo "SHA256: $SHA"
echo "Context: $CTX"

echo
echo "=== Build context files ==="
find "$CTX/docker" -maxdepth 1 -type f -printf '%f\n' | sort

# Verify every local Dockerfile COPY source is packed in the build context.
for required in requirements-verified.txt fix-cusparselt-wheel-tag.py entrypoint.sh; do
    test -f "$CTX/docker/$required" || {
        echo "ERROR: Missing Docker build input: $required" >&2
        exit 1
    }
done

docker build \
    --platform linux/arm64 \
    --progress=plain \
    --build-arg "PADDLE_WHEEL=$(basename "$WHEEL")" \
    --build-arg "PADDLE_WHEEL_SHA256=$SHA" \
    --build-arg "APT_MIRROR=$APT_MIRROR" \
    --build-arg "PIP_INDEX_URL=$PIP_INDEX_URL" \
    -t "$IMAGE" \
    -f "$CTX/docker/Dockerfile" \
    "$CTX"

echo
echo "SUCCESS: Built $IMAGE"
echo "Next: bash docker/check-image.sh"
