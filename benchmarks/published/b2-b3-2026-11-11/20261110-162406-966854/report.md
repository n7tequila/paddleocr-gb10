# GB10 OCR benchmark

Status: **success**

Times are client-measured HTTP end-to-end latency, including transfer and server work; they are not GPU inference times.
P95 is descriptive with fewer than 100 successes and must not be treated as stable tail latency.

Measured requests: 3/3; warmups: 1; concurrency: 1.
Run elapsed time (resource preflight through monitor shutdown, excluding environment discovery and report writing): 13.400 s.
Measured-request window (first measured start to last measured completion): 7.234947960008867 s.
Minimum observed MemAvailable: 13.708 GiB.
Observed mean GPU utilization: 95.72%; maximum memory PSI some/full avg10: 0.0%/0.0%.
Co-resident containers at run start: ['paddleocr-gb10 Up 2 hours (healthy)', 'vllm-educhat Up 2 hours (healthy)', 'vllm-omniedu Up 3 hours (healthy)'].
Qwen-related containers may be present; generation activity and cache state were not measured. This is not a verified OCR-only baseline.

| Document category | Success/attempted | Mean s | P50 s | P90 s | P95 s | Min s | Max s | Stddev s | Pages/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| single_page_pdf | 3/3 | 1.197 | 1.193 | 1.209 | 1.211 | 1.185 | 1.213 | 0.012 | 0.415 |

Overall success rate: 1.000; completed pages: 3.
Pages/s uses the measured-request window from the first start to the last completion.
Categories remain separate; the overall count is not a combined latency comparison.

See requests.csv for every attempt, resources.csv for timestamped telemetry, and environment.json for reproducibility.
On GB10, system memory, Docker memory, process RSS and NVIDIA memory may overlap and must not be summed.
Sampling cannot prevent an instantaneous out-of-memory event.

## Dataset

| ID | Type | Dimensions | Bytes | Expected pages | SHA256 |
| --- | --- | --- | ---: | ---: | --- |
| one-page-pdf | pdf | 850×1100 | 28572 | 1 | `61d5c441bebf7c911ddd0d3fe6a9be62864ae88c2e65b57ca50af7c972477b04` |
