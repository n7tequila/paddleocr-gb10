# Automated tests (v0.2.1 development)

Run each layer independently from the repository root:

```bash
bash tests/run-tests.sh static
bash tests/run-tests.sh environment
PADDLEOCR_ALLOW_GPU_TEST=1 bash tests/run-tests.sh gpu
bash tests/run-tests.sh api
PADDLEOCR_ALLOW_STABILITY_TEST=1 bash tests/run-tests.sh stability
bash tests/run-tests.sh release
bash tests/run-tests.sh all
```

`all` runs only static, environment, and metadata-only release checks. CI runs static checks and unit tests on GitHub-hosted runners. The GB10 with Qwen3.8 is **not** registered as a public repository self-hosted runner. No command builds an image, installs dependencies, restarts a service, or stops Qwen. Missing local images are reported as SKIP; the harness never pulls one. A failed check returns exit code 1; SKIP is recorded separately and does not count as a pass.

| Layer | What it does | GPU / inference |
| --- | --- | --- |
| `static` | Shell and Python syntax, Compose, references, ignore rules, README paths, diff whitespace | No / no |
| `environment` | Existing image package versions, Python/ARM64, `pip check`, CUDA build, cuSPARSELt tag | No / no |
| `gpu` | One 8×8 CUDA matrix calculation | Tiny GPU / no model |
| `api` | Official `/health` and one `/layout-parsing` request with the synthetic fixture | Running service / one OCR request |
| `stability` | Docker health status, three serial OCR requests, three malformed requests, final health | Running service / three OCR requests |
| `release` | Anonymous GHCR Manifest and GitHub Release metadata | No / no image download |

The image layer defaults to existing `paddleocr-gb10:0.2.0`; override with `PADDLEOCR_IMAGE`. API tests default to the current Compose address `http://127.0.0.1:8080`. Set `PADDLEOCR_API_URL` to use another host port, or supply the full `/layout-parsing` URL. The API fixture is [synthetic text](../tests/fixtures/README.md) and expects one page with nonempty Markdown; it does not require exact transcription.

GPU tests require `PADDLEOCR_ALLOW_GPU_TEST=1`, at least 8 GiB `MemAvailable` by default, and a GPU-capable local image. Stability tests require `PADDLEOCR_ALLOW_STABILITY_TEST=1`; they are never included in `all`. API and stability inference require at least 12 GiB available and memory PSI `avg10` no higher than 10% before starting. During requests the harness samples `/proc/meminfo` and `/proc/pressure/memory` once per second. If availability falls below 8 GiB or PSI exceeds 10%, it stops **subsequent** requests and reports a failure. It cannot prevent an instantaneous OOM and does not terminate an in-flight request or container.

Thresholds and timeout can be changed explicitly with `PADDLEOCR_GPU_MIN_GIB`, `PADDLEOCR_MIN_MEM_GIB`, `PADDLEOCR_STOP_MEM_GIB`, `PADDLEOCR_MAX_PSI_AVG10`, and `PADDLEOCR_API_TIMEOUT`. Run serially; do not launch multiple harnesses at once. The stability layer also checks that the Docker container named `paddleocr-gb10` has a healthcheck applied; a source edit alone does not change a running container.

Each invocation prints PASS, FAIL, or SKIP and saves `tests/reports/<UTC timestamp>/<layer>.json`. API/stability runs save full response JSON beside the report. `tests/reports/` is Git ignored; inspect it locally, and do not publish private response content. The report includes the image, UTC timestamp, each test's status/duration/diagnosis, and pass/fail/skip totals.

The release layer honors standard `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` settings; the API layer bypasses proxies for local service calls.

For a FAIL, read its `reason` in the JSON report and the terminal output. Common causes are Docker socket permissions, missing local image, unavailable port, first-start model download, insufficient RAM, unsupported wheel metadata, proxy errors, GHCR 401/404, or a changed upstream response shape. A SKIP identifies a missing authorization flag or resource prerequisite. For API failures, check `docker compose --env-file docker/.env -f docker/compose.yaml ps` and `logs`; run the single API layer only after the service is ready.
