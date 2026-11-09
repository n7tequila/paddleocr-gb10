# Experimental GB10 / arm64 image. Uses the user's validated local PaddlePaddle GPU wheel.
# No custom REST API: runs official PaddleX Serving.
ARG CUDA_IMAGE=nvidia/cuda:13.0.2-cudnn-runtime-ubuntu24.04
FROM ${CUDA_IMAGE}
ARG PADDLE_WHEEL
ARG PADDLE_WHEEL_SHA256
# Optional build-time mirrors; empty = upstream defaults.
# China examples (configure in docker/build-image.sh, not here):
# APT_MIRROR=https://mirrors.aliyun.com/ubuntu-ports
# PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=""
ARG PIP_INDEX_URL=""
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PADDLEX_HOME=/root/.paddlex \
    CUDA_VISIBLE_DEVICES=0 \
    PADDLEOCR_PIPELINE=PaddleOCR-VL-1.6 \
    PADDLEOCR_DEVICE=gpu:0 \
    PADDLEOCR_HOST=0.0.0.0 \
    PADDLEOCR_PORT=8080
# Ubuntu 24.04 arm64 typically uses Deb822 ubuntu.sources.
# Only replace Ubuntu Ports addresses; never change NVIDIA's own repositories.
RUN if [ -n "$APT_MIRROR" ]; then \
      set -eu; \
      for file in /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list; do \
        if [ -f "$file" ]; then \
          sed -i -E "s#https?://(ports\.ubuntu\.com/ubuntu-ports|[^ /]+/ubuntu-ports)(/)?#${APT_MIRROR%/}/#g" "$file"; \
        fi; \
      done; \
      echo "APT mirror enabled: $APT_MIRROR"; \
    fi
RUN if [ -n "$PIP_INDEX_URL" ]; then \
      mkdir -p /etc/pip && printf '[global]\nindex-url = %s\n' "$PIP_INDEX_URL" > /etc/pip.conf && \
      echo "PyPI mirror enabled: $PIP_INDEX_URL"; \
    fi
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-dev \
    ca-certificates libgomp1 libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/ocr-venv
ENV PATH=/opt/ocr-venv/bin:$PATH
RUN python -m pip install --upgrade 'pip==26.3' 'setuptools==80.10.2' 'wheel==0.48.0'
# All Python package versions were captured from the validated 0.2.0 image.
# PIP_CONSTRAINT also applies to the official paddlex --install serving command.
COPY docker/requirements-verified.txt /opt/requirements-verified.txt
ENV PIP_CONSTRAINT=/opt/requirements-verified.txt
# Pip installs PaddleOCR / PaddleX first. The GB10 wheel is then installed WITHOUT
# dependency resolution, to prevent pip replacing it with a generic CPU/GPU wheel.
RUN python -m pip install 'numpy==2.3.5' 'paddleocr[doc-parser]==3.7.0' 'paddlex==3.7.2'
# pip requires the original PEP-427 wheel filename; the build helper copies it here.
COPY docker/.build/ /tmp/wheelhouse/
RUN test -n "$PADDLE_WHEEL" && test -n "$PADDLE_WHEEL_SHA256" && \
    echo "$PADDLE_WHEEL_SHA256  /tmp/wheelhouse/$PADDLE_WHEEL" | sha256sum -c - && \
    python -m pip install --no-deps "/tmp/wheelhouse/$PADDLE_WHEEL"
# The CLI is official; this may install extra serving dependencies. Do not expose
# this stage as a public, general-purpose Docker build service.
RUN paddlex --install serving
# PaddlePaddle GPU wheel is installed with --no-deps.
# Explicitly restore its required protobuf runtime dependency.
RUN python -m pip install 'protobuf==7.36.1' && \
    python -c "from google.protobuf.internal import builder; print('protobuf OK')"

# Restore the HTTP client required by PaddlePaddle.
# The custom ARM64 GPU wheel was installed with --no-deps.
RUN python -m pip install 'httpx==0.28.1'

# Verify the complete installed dependency graph before importing Paddle.
# GB10 PaddlePaddle GPU wheel runtime dependencies
# Exact versions match the installed packages in the verified Docker image.
# Keep --no-deps for installing the custom PaddlePaddle wheel itself.
RUN python -m pip install \
    'cuda-python==13.0.3' \
    'cuda-toolkit[cudart,cufft,cufile,cupti,curand,cusolver,cusparse,nvjitlink,nvrtc,nvtx]==13.0.2' \
    'networkx==3.7' \
    'nvidia-cublas==13.1.1.3' \
    'nvidia-cudnn-cu13==9.20.0.48' \
    'nvidia-cusparselt-cu13==0.8.1' \
    'nvidia-nccl-cu13==2.31.2' \
    'opt_einsum==3.3.0'

# Fix NVIDIA cuSPARSELt SBSA wheel metadata on GB10 ARM64.
COPY docker/fix-cusparselt-wheel-tag.py /tmp/fix-cusparselt-wheel-tag.py
RUN python /tmp/fix-cusparselt-wheel-tag.py

RUN python -m pip check

# Reassert pinned top-level runtime and preserve the custom PaddlePaddle wheel.
RUN python - <<'PYCODE'
import paddle, importlib.metadata as m
assert paddle.is_compiled_with_cuda(), 'Not a CUDA-enabled PaddlePaddle wheel'
for package, version in [('paddleocr','3.7.0'),('paddlex','3.7.2')]:
    assert m.version(package)==version, (package,m.version(package))
print('Paddle:',paddle.__version__)
PYCODE
COPY docker/entrypoint.sh /usr/local/bin/paddleocr-gb10-entrypoint
RUN chmod +x /usr/local/bin/paddleocr-gb10-entrypoint && \
    rm -rf /tmp/wheel /tmp/wheelhouse
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/paddleocr-gb10-entrypoint"]
