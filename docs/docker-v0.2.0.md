# Docker + OFFICIAL PaddleX REST API (GB10, v0.2.0)

**Status:** The existing `paddleocr-gb10:0.2.0` image passed Docker GPU validation on GB10. Official PaddleX Serving started and `/layout-parsing` returned HTTP 200 for a real handwritten essay in 18.59 seconds. The new package constraints were captured from that image; a fresh rebuild of this updated recipe remains to be tested.

**Distribution status (10 Nov 2026):** [v0.2.0 Release](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0), its [Wheel](https://github.com/n7tequila/paddleocr-gb10/releases/download/v0.2.0/paddlepaddle_gpu-3.5.0.dev20261109%2B6c839e963ed-cp312-cp312-linux_aarch64.whl), and [SHA256SUMS](https://github.com/n7tequila/paddleocr-gb10/releases/download/v0.2.0/SHA256SUMS) are published. Anonymous GHCR token and OCI index requests returned HTTP 200; the index advertises `linux/arm64`. A full pull and GPU/API retest of the remote image remain outstanding. Compose pulls the GHCR tag by default without a local Wheel or Docker build context.

This project does **not** implement another API or change the official PaddleX request/response. The container entrypoint is simply `paddlex --serve --pipeline PaddleOCR-VL-1.6 --device gpu:0 --host 0.0.0.0 --port 8080`. Upstream docs: https://paddlepaddle.github.io/PaddleX/3.7/en/pipeline_usage/tutorials/ocr_pipelines/PaddleOCR-VL.html

## Validated configuration

- Ubuntu 24.04 ARM64 (`aarch64`), NVIDIA GB10 SM 12.1, CUDA 13, driver 580.178.04
- Host-built `paddlepaddle_gpu-3.5.0.dev20261109+6c839e963ed-cp312-cp312-linux_aarch64.whl`; historical SHA256 `a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb`
- PaddleOCR 3.7.0, PaddleX 3.7.2, `PaddleOCR-VL-1.6`, official `paddle_dynamic` inference
- Successful host `/layout-parsing`: HTTP 200, 16.97s, one page, official `logId/errorCode/errorMsg/result.layoutParsingResults` shape
- Successful Docker `/layout-parsing`: HTTP 200, 18.59s, real handwritten essay; Docker GPU compute capability 12.1
- Qwen3.8 resident + OCR inference: three rounds, minimum MemAvailable 10.20GiB, memory PSI 0.00%. **Qwen generating at same time remains untested.**

## Deploy the published image

On a GB10 host with Docker, NVIDIA Container Toolkit and GPU access, run from the repository root:

```bash
test -e docker/.env || cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yaml config
docker compose --env-file docker/.env -f docker/compose.yaml up -d
docker compose --env-file docker/.env -f docker/compose.yaml logs --tail=80 paddleocr
bash docker/check-api.sh /path/to/image.png
```

The default host address is `127.0.0.1:8080`; set `PADDLEOCR_PUBLIC_PORT` in `docker/.env` if it is busy. If an older `docker/.env` exists, set its `PADDLEOCR_IMAGE` to the GHCR tag. `PADDLEX_CACHE` defaults to persistent `docker/model-cache`, mapped to `/root/.paddlex`; model weights are downloaded on first start. Compose marks the container healthy after PaddleX starts listening on its internal port, with a 10-minute startup grace period for model loading. This TCP check does not validate OCR inference; use the `/layout-parsing` request below for that. This path pulls GHCR directly and requires no Wheel download or image build.

## Optional local build on FusionXpark

Use a checkout of this repository **on the GB10 host** (not macOS). The build script obtains the GPU wheel from the already-working host environment and verifies its checksum:

```bash
# From this repository's root on GB10:
bash docker/preflight.sh
bash docker/build-image.sh
bash docker/check-image.sh
```

If the checkout directory is different, `cd` into it; scripts derive their own location. Set `PADDLEOCR_BASE=/data/llm-docker/paddleocr` if the existing runtime is stored elsewhere. Docker build may require several GB free disk and network access. **Image build does not stop Qwen or run PaddleOCR inference.** If the base image cannot be pulled, resolve Docker registry access yourself; do not disable TLS verification.

The build uses `nvidia/cuda:13.0.2-cudnn-runtime-ubuntu24.04`, Ubuntu 24.04 Python 3.12, and the SHA256-checked local PaddlePaddle GPU 3.5.0 development Wheel. It installs PaddleOCR 3.7.0, PaddleX 3.7.2 and NumPy 2.3.5, then installs the local Wheel with `--no-deps`. Official `paddlex --install serving` adds Serving dependencies. `docker/requirements-verified.txt` constrains installed Python packages to versions captured from the validated image, including setuptools 80.10.2, wheel 0.48.0, protobuf 7.36.1, httpx 0.28.1 and CUDA Python packages; pip 26.3 is pinned directly in the Dockerfile. The build repairs only the installed cuSPARSELt 0.8.1 ARM64 WHEEL tag and its RECORD checksum, runs `pip check`, and confirms CUDA Paddle plus the PaddleOCR/PaddleX versions.

`docker/build-image.sh` creates a temporary context containing the Dockerfile, entrypoint, constraints file, cuSPARSELt repair script and only the verified Paddle Wheel. It refuses to overwrite an existing image tag unless `REBUILD_EXISTING_IMAGE=1` is set. Rebuilding the current tag is **not required** to use the validated image and has not been done during this cleanup.

To deploy a locally built image, set `PADDLEOCR_IMAGE=paddleocr-gb10:0.2.0` in `docker/.env`, then use the Compose and API commands above.

Run Compose commands with `--env-file docker/.env` as shown to avoid ambiguity in env variable resolution. `PADDLEX_CACHE` may be a user-selected absolute directory or the default `docker/model-cache`, where official tooling can download model weights. `paddlex --install serving` is run *at Docker build time*, not on each container startup. Docker Compose selects `linux/arm64` and the GHCR image by default; a full pull and service check of that remote image remain outstanding.

## Limitations and decisions

- **Never modify Qwen** to accommodate Docker packaging; it is an independent container.
- Host port binds to `127.0.0.1:8080` by default. To allow LAN clients, explicitly set `PADDLEOCR_BIND=0.0.0.0`, configure firewall and add a reverse proxy/authentication. Official Serving does not constitute an authenticated internet-facing gateway.
- `gpus: all` requires NVIDIA Container Toolkit / compatible Docker Compose.
- The image uses `nvidia/cuda:13.0.2-cudnn-runtime-ubuntu24.04`. The existing image passed GB10 GPU validation; the new dependency constraints need a fresh build test. The base image is pinned by tag, not digest, and APT packages may change upstream.
- The original host and Docker build needed the `nvidia-cusparselt-cu13==0.8.1` metadata workaround (`manylinux2014_sbsa` vs `_aarch64`). The included script changes installed WHEEL metadata and RECORD only; binary libraries stay untouched.
- The PaddlePaddle GPU Wheel is **not embedded in Git or the model cache**. It is available as the v0.2.0 Release attachment linked above, or can be built locally. The build helper's default Wheel location is host-specific; set `PADDLE_WHEEL_DIR` to the directory containing your verified Wheel.
- Do not run multiple workers or parallel requests by default. Container memory limits are intentionally unset for GB10 unified RAM; monitor real `MemAvailable` and PSI under dual-model load. No automatic OOM safeguard is implemented here.
- The startup command exposes original PaddleX endpoints including `POST /layout-parsing`; it does not supply a custom `/v1/ocr/parse` endpoint.

## API request

```bash
python3 docker/test-official-api.py \
  --url http://127.0.0.1:8080/layout-parsing \
  --image /path/to/image.png \
  --output /tmp/paddle-response.json
```

The request sends JSON with Base64 `file`, `fileType: 1`, and flags `visualize`, `useDocOrientationClassify`, `useDocUnwarping`. The test allows 300 seconds and asserts successful official `errorCode=0` and first-page `prunedResult` and `markdown` fields. Check Compose logs and `ps` during first-start model download, then use a successful request as the readiness check. A direct curl example is in the [main README](../README.md). Do not confuse `/layout-parsing` with the PP-OCR `/ocr` pipeline; only PaddleOCR-VL-1.6 is shipped.

## Image inspection and troubleshooting

```bash
docker compose --env-file docker/.env -f docker/compose.yaml ps
docker compose --env-file docker/.env -f docker/compose.yaml logs --tail=100
docker run --rm --gpus all --entrypoint python paddleocr-gb10:0.2.0 \
    -c 'import paddle; print(paddle.__version__, paddle.is_compiled_with_cuda()); paddle.set_device("gpu:0"); print(paddle.ones([2,2]).sum().numpy())'
```

If `docker/build-image.sh` fails, retain the **first actual error**, not only final pip summary. Fix packages or packaging compatibilities **inside the Docker context**, not by modifying the validated host virtualenv. See also `docs/troubleshooting.md` and `docs/reproduction.md`.

## Optional domestic APT/PyPI mirrors

Mirror defaults remain disabled for reproducible upstream builds. To enable Chinese mirrors, uncomment the two `export` examples near the top of `docker/build-image.sh`:

```bash
# export APT_MIRROR="https://mirrors.aliyun.com/ubuntu-ports"
# export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
```

`APT_MIRROR` rewrites only Ubuntu Ports entries inside the image, retaining NVIDIA repositories. `PIP_INDEX_URL` writes `/etc/pip.conf` inside the image before pip and PaddleX Serving installation. Docker Hub / CUDA base image pulls still depend on the host Docker daemon mirror/proxy.
