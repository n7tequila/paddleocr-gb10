# GB10 HTTP OCR benchmark

Run the small, serial baseline from the repository root:

```bash
bash benchmarks/run-benchmark.sh --scenario basic --requests 5 --warmup 1
```

Default API: `PADDLEOCR_API_URL` or `http://127.0.0.1:8080`. Use `--images /local/private/directory`, `--timeout`, or `--output-dir` to customize. For separate document-type measurements, use `--scenario documents --sample-id chinese-print --warmup 1 --requests 3`; repeat with each ID in `datasets/manifest.json`. `--concurrency` defaults to 1; values above 1 require `--allow-concurrency` and are not part of the standard baseline. The tool sends only the official PaddleX `/layout-parsing` request. It never starts, stops, or restarts a container.

Reports are saved under ignored `benchmarks/reports/<UTC timestamp>/`: `summary.json`, `requests.csv`, `resources.csv`, `report.md`, and `environment.json`. Read [English methodology](../docs/benchmark.md) or [中文方法](../docs/benchmark.zh-CN.md). Older results in `docs/benchmarks.md` and `reference-2026-11-09.json` are separate historical experiments.

For a B2 comparison, run each manifest ID separately with `--scenario documents --sample-id ID --warmup 1 --requests 3 --concurrency 1`, placing the per-sample directories under one `--output-dir`. Then run `python3 benchmarks/aggregate.py PATH_TO_OUTPUT_DIR` to validate and create the five-file comprehensive report. The aggregator does not pool latency means. See [B4 plan](B4-PLAN.md) before any optional Qwen coexistence test.

Published synthetic B2/B3 acceptance data: [comparison report](published/b2-b3-2026-11-11/report.md). It contains all 8 per-sample runs and the combined request/resource CSVs without pooling category latency means.
