# paddleocr-gb10 Docker v0.2.0

**GB10 (ARM64 + CUDA 13.0) Docker packaging for the original official PaddleX Serving REST API.** No custom FastAPI routes. Model: PaddleOCR-VL-1.6.

The image `paddleocr-gb10:0.2.0` passed Docker GPU validation on GB10. Official PaddleX Serving started and `/layout-parsing` returned HTTP 200 for a real handwritten essay in 18.59 seconds. The source recipe now pins the Python versions captured from that image; a fresh rebuild with the new constraints is pending verification.

- [English installation, prerequisites and limitations](docs/docker-v0.2.0.md)
- [中文安装说明](README.docker.zh-CN.md)
- [Host Serving validation](docs/serving-validation-2026-11-10.md)
- [Docker release acceptance checklist](docs/release-0.2.0.md)

```bash
cd /data/llm-docker/paddleocr-gb10
bash docker/preflight.sh
bash docker/build-image.sh
bash docker/check-image.sh
cp docker/.env.example docker/.env
# Edit the PADDLEX_CACHE absolute path in docker/.env before launch.
docker compose --env-file docker/.env -f docker/compose.yaml up -d
bash docker/check-api.sh /path/to/test-image.png
```

**Important:** On GB10 with Qwen3.8 already using ~93GiB unified memory, run one OCR process, avoid concurrent workloads until tested and observe system free RAM. Do not shut down or modify Qwen.

## Optional mirrors for mainland China

Default builds use upstream APT and PyPI. In `docker/build-image.sh`, uncomment:

```bash
# export APT_MIRROR="https://mirrors.aliyun.com/ubuntu-ports"
# export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
```

Alternatively pass these as environment variables to `bash docker/build-image.sh`. The APT URL is specifically the ARM64 **Ubuntu Ports** repository, not the x86 Ubuntu archive. The host Docker daemon registry mirror only affects the base image pull.
