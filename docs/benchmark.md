# GB10 OCR benchmark methodology (v0.3.0 development)

The current tool measures **client HTTP end-to-end latency** through PaddleX's official `POST /layout-parsing`; it does not measure isolated GPU inference time or change the Serving API. The old numbers in [historical benchmarks](benchmarks.md) are a separate 2026-11-09 experiment and must not be pooled with new runs.

## Run and reproduce

On the GB10 host, first check that the existing PaddleOCR service is healthy and that memory is available. From a checkout at a recorded commit:

```bash
bash benchmarks/run-benchmark.sh --scenario basic --warmup 1 --requests 5 --concurrency 1 --timeout 300
```

The default API is `PADDLEOCR_API_URL` or `http://127.0.0.1:8080`. `--images` accepts a file or local directory; `--output-dir` changes report storage; `--scenario documents` selects all public synthetic types. `--concurrency 2 --allow-concurrency` is an explicit opt-in and should only be used after resource review. Nothing starts/stops containers or builds images. The default command sends one warmup and five serial measurements. A warmup is recorded but excluded from latency statistics. `--requests` distributes measurements round-robin across selected samples. For B2 acceptance, run each public sample separately with `--scenario documents --sample-id ID --warmup 1 --requests 3`; this preserves a distinct warmup and latency summary for each category.

After per-sample B2 runs under one output root, `python3 benchmarks/aggregate.py OUTPUT_ROOT` validates the runs and writes a five-file comparison report without pooling latency means. The [B4 test plan](../benchmarks/B4-PLAN.md) is code-only for this acceptance.

Reports go to ignored `benchmarks/reports/<UTC timestamp>/`: `summary.json`, `requests.csv`, `resources.csv`, `environment.json`, and `report.md`. Every attempted request has UTC and monotonic start times, HTTP status, PaddleX `errorCode`, bytes sent/received, page and Markdown counts, duration, timeout flag, and error. The environment file also records the Git commit, dirty-worktree state, and benchmark source hashes. Raw OCR response text is not saved. Private input paths and hashes may appear in environment metadata; review before sharing.

## Dataset and metrics

The public dataset has six synthetic printed PNGs, a one-page PDF, and a two-page PDF, with sources, licenses, dimensions, pages, byte sizes and SHA256 in [the manifest](../benchmarks/datasets/manifest.json). The PDF uses official `fileType: 0`; PNGs use `1`, as documented by [PaddleX](https://paddlepaddle.github.io/PaddleX/3.7/en/pipeline_usage/tutorials/ocr_pipelines/PaddleOCR-VL.html). Regenerate with `python3 benchmarks/datasets/generate.py` using Pillow and the documented fonts, then validate hashes. Synthetic font rendering is not real handwriting accuracy. Use `--images` for private local samples; do not commit children's work, names, teacher markings, or private responses.

The request timer starts immediately before the HTTP call and stops after reading all response bytes; local file reading, Base64 construction, and response JSON parsing are excluded. The separate `run_elapsed_s` spans the initial resource gate, health check, warmup, measurements, and monitor shutdown; it excludes environment discovery and report writing. Throughput divides actual successful response pages by the wall-clock window from the first measured request start to the last measured request completion. This includes gaps and any dataset changes between measured requests, but excludes warmup and preflight. See the separate B1 retrospective analysis in the ignored local report directory for the legacy timing definition.

For successful measured requests, the report gives mean, median/P50, P90, P95, minimum, maximum, population standard deviation, success rate, and successful pages per measured-request window second. Failed and timed-out attempts remain in the raw CSV and success-rate denominator. Categories have separate latency rows. With fewer than 100 successful requests, P95 is only descriptive and is not a stable tail-latency estimate. Compare runs only with matching image hashes, parameters, cache state, and model/environment versions.

## Telemetry and protection

The monitor targets 0.5–1 second sampling and records MemAvailable, swap used, memory PSI some/full, GPU utilization/power/temperature/memory when `nvidia-smi` supplies them, PaddleOCR container health and memory usage, PaddleOCR process RSS (when `docker top` exposes it), and benchmark-client process RSS. Unsupported GPU fields are `null`/N/A. Host memory/PSI samples carry UTC and monotonic timestamps at the configured 0.5–1 second interval; GPU and Docker values are collected separately and the latest available values are attached to those rows. Their refresh may lag under command latency. On GB10 unified memory, system available memory, Docker memory, RSS and NVIDIA memory can overlap; do not add them.

Before inference, MemAvailable below 12 GiB aborts the run. During the run, below 8 GiB, PSI some avg10 at least 5%, or PSI full avg10 at least 1% stops new requests. In-flight calls finish or time out; the tool never kills OCR or Qwen. Sampling cannot prevent instantaneous OOM. Reports distinguish success, failed, timeout attempts, memory-protection abort, user cancellation, and not-run work.

## Optional Qwen coexistence (B4)

B4 is implemented but is never started by the standard benchmark or CI. Run three separate, matching scenarios: A (`--mode baseline`) with Qwen absent by **manual** environment preparation, B (`--mode idle`) with Qwen loaded but idle, and C (`--mode active`) with Qwen generation running. Do not stop the existing Qwen service automatically. All runs require `--allow-coexist-load`, a host-accessible `--qwen-api-url`, and `--qwen-model`. For example, after manually verifying the service and memory:

```bash
python3 benchmarks/coexist.py --allow-coexist-load --mode active \
  --qwen-api-url http://HOST:PORT/v1 --qwen-model MODEL \
  --qwen-cache-state unknown --scenario coexist --requests 5 --warmup 1
```

Use identical OCR images, request counts, Qwen prompt (`--qwen-prompt-file` or the fixed default), model, and token limit in B/C. Record prefix-cache state with `--qwen-cache-state`; a constant prefix can hit cache, so compare only equivalent cache conditions or disable caching on the server manually. The `qwen.csv` file records TTFT, output tokens/s, server usage, and cache header when available. If server usage is absent, token count is estimated as output characters divided by four and clearly labeled; this is a rough proxy, especially for Chinese. B4 enforces serial OCR, limits Qwen output to at most 256 tokens, and rechecks memory before each active request. B4 C remains unverified in this development cycle.

The [published B2/B3 synthetic acceptance report](../benchmarks/published/b2-b3-2026-11-11/report.md) includes the individual run records and a category-separated comparison.
