# GB10 OCR benchmark

Status: **success**

Times are client-measured HTTP end-to-end latency, including transfer and server work; they are not GPU inference times.
P95 is descriptive with fewer than 100 successes and must not be treated as stable tail latency.

Measured requests: 3/3; warmups: 1; concurrency: 1.
Minimum observed MemAvailable: 13.648 GiB.
Observed mean GPU utilization: 96.0%; maximum memory PSI some/full avg10: 0.0%/0.0%.
Co-resident containers at run start: ['paddleocr-gb10 Up 2 hours (healthy)', 'vllm-educhat Up 2 hours (healthy)', 'vllm-omniedu Up 2 hours (healthy)'].
Qwen-related containers may be present; generation activity and cache state were not measured. This is not a verified OCR-only baseline.

| Document category | Success/attempted | Mean s | P50 s | P90 s | P95 s | Min s | Max s | Stddev s | Pages/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_page_pdf | 3/3 | 3.031 | 2.304 | 4.115 | 4.341 | 2.223 | 4.567 | 1.087 | 0.476 |

Overall success rate: 1.000; completed pages: 6.
Pages/s uses the measured-request window from the first start to the last completion.
Categories remain separate; the overall count is not a combined latency comparison.

See requests.csv for every attempt, resources.csv for timestamped telemetry, and environment.json for reproducibility.
On GB10, system memory, Docker memory, process RSS and NVIDIA memory may overlap and must not be summed.
Sampling cannot prevent an instantaneous out-of-memory event.

## Dataset

| ID | Type | Dimensions | Bytes | Expected pages | SHA256 |
| --- | --- | --- | ---: | ---: | --- |
| two-page-pdf | pdf | 850×1100 | 55598 | 2 | `78aa0fa32ce8843bfef17fa68e9575f64df9c3a97f6b69c7bca157b93a042108` |
