# paddleocr-gb10 Docker v0.2.0

**GB10 (ARM64 + CUDA 13.0) Docker packaging for the original official PaddleX Serving REST API.** No custom FastAPI routes. Model: PaddleOCR-VL-1.6.

The image `paddleocr-gb10:0.2.0` passed Docker GPU validation on GB10. Official PaddleX Serving started and `/layout-parsing` returned HTTP 200 for a real handwritten essay in 18.59 seconds. The source recipe now pins the Python versions captured from that image; a fresh rebuild with the new constraints is pending verification.

- [English installation, prerequisites and limitations](docs/docker-v0.2.0.md)
- [中文安装说明](README.docker.zh-CN.md)
- [Host and Docker Serving validation](docs/serving-validation-2026-11-10.md)
- [Docker release acceptance checklist](docs/release-0.2.0.md)
- [Automated test layers and resource safeguards](docs/testing.md)

## Image and deployment

The published GHCR image is `ghcr.io/n7tequila/paddleocr-gb10:0.2.0`. On 10 Nov 2026, anonymous token and manifest requests returned HTTP 200, and the OCI index advertised `linux/arm64`. A full remote pull and GPU retest are still pending. The image is linked from the [v0.2.0 Release](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0).

```bash
docker pull --platform linux/arm64 ghcr.io/n7tequila/paddleocr-gb10:0.2.0
test -e docker/.env || cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yaml up -d
bash docker/check-api.sh /path/to/test-image.png
```

The cache defaults to persistent `docker/model-cache` relative to the Compose file; set `PADDLEX_CACHE` in `docker/.env` to your own absolute path when using an existing cache. The model weights are not in the image and official tooling may download them on first use. NVIDIA Container Toolkit is required. The service uses GPU access and binds `127.0.0.1:8080` by default.

Compose checks PaddleX's official `GET /health` inside the container every 30 seconds. `starting` means the first successful check has not completed; failures during the 120-second startup grace period do not count toward the retry limit. `healthy` means `/health` returned HTTP 200; `unhealthy` means three counted checks failed consecutively. This check does not run OCR inference. Inspect status with `docker compose --env-file docker/.env -f docker/compose.yaml ps`; use the separate `/layout-parsing` request to validate inference.

The GHCR Compose path needs no local Wheel or Docker build context. For the optional local image path, set `PADDLEOCR_IMAGE=paddleocr-gb10:0.2.0` in `docker/.env`. To build locally on GB10 from the verified Wheel, run `bash docker/preflight.sh`, `bash docker/build-image.sh`, then `bash docker/check-image.sh`; see [full build steps](docs/docker-v0.2.0.md). The build helper refuses to overwrite an existing image unless explicitly requested. Set `PADDLEOCR_PUBLIC_PORT` to change the host port.

**Important:** On GB10 with Qwen3.8 already using ~93GiB unified memory, run one OCR process, avoid concurrent workloads until tested and observe system free RAM. Do not shut down or modify Qwen.

## Optional mirrors for mainland China

Default builds use upstream APT and PyPI. In `docker/build-image.sh`, uncomment:

```bash
# export APT_MIRROR="https://mirrors.aliyun.com/ubuntu-ports"
# export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
```

Alternatively pass these as environment variables to `bash docker/build-image.sh`. The APT URL is specifically the ARM64 **Ubuntu Ports** repository, not the x86 Ubuntu archive. The host Docker daemon registry mirror only affects the base image pull.
