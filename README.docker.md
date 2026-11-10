# paddleocr-gb10 Docker v0.2.0

**GB10 (ARM64 + CUDA 13.0) Docker packaging for the original official PaddleX Serving REST API.** No custom FastAPI routes. Model: PaddleOCR-VL-1.6.

The image `paddleocr-gb10:0.2.0` passed Docker GPU validation on GB10. Official PaddleX Serving started and `/layout-parsing` returned HTTP 200 for a real handwritten essay in 18.59 seconds. The source recipe now pins the Python versions captured from that image; a fresh rebuild with the new constraints is pending verification.

- [English installation, prerequisites and limitations](docs/docker-v0.2.0.md)
- [中文安装说明](README.docker.zh-CN.md)
- [Host and Docker Serving validation](docs/serving-validation-2026-11-10.md)
- [Docker release acceptance checklist](docs/release-0.2.0.md)

## Image and deployment

The intended GHCR image is `ghcr.io/n7tequila/paddleocr-gb10:0.2.0`. As of 10 Nov 2026 its anonymous token request returned HTTP 401 and its Package page returned HTTP 404, so public pull and remote `linux/arm64` architecture remain unverified. Once public access is enabled:

```bash
docker pull --platform linux/arm64 ghcr.io/n7tequila/paddleocr-gb10:0.2.0
cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yaml up -d
bash docker/check-api.sh /path/to/test-image.png
```

The cache defaults to persistent `docker/model-cache` relative to the Compose file; set `PADDLEX_CACHE` in `docker/.env` to your own absolute path when using an existing cache. The model weights are not in the image and official tooling may download them on first use. NVIDIA Container Toolkit is required. The service uses GPU access and binds `127.0.0.1:8004` by default.

For the already validated local image while GHCR is unavailable, set `PADDLEOCR_IMAGE=paddleocr-gb10:0.2.0` in `docker/.env`. To build locally on GB10 from the verified Wheel, run `bash docker/preflight.sh`, `bash docker/build-image.sh`, then `bash docker/check-image.sh`; see [full build steps](docs/docker-v0.2.0.md). The build helper refuses to overwrite an existing image unless explicitly requested.

**Important:** On GB10 with Qwen3.8 already using ~93GiB unified memory, run one OCR process, avoid concurrent workloads until tested and observe system free RAM. Do not shut down or modify Qwen.

## Optional mirrors for mainland China

Default builds use upstream APT and PyPI. In `docker/build-image.sh`, uncomment:

```bash
# export APT_MIRROR="https://mirrors.aliyun.com/ubuntu-ports"
# export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
```

Alternatively pass these as environment variables to `bash docker/build-image.sh`. The APT URL is specifically the ARM64 **Ubuntu Ports** repository, not the x86 Ubuntu archive. The host Docker daemon registry mirror only affects the base image pull.
