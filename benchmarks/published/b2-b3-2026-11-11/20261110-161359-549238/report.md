# GB10 OCR benchmark

Status: **success**

Times are client-measured HTTP end-to-end latency, including transfer and server work; they are not GPU inference times.
P95 is descriptive with fewer than 100 successes and must not be treated as stable tail latency.

Measured requests: 3/3; warmups: 1; concurrency: 1.
Minimum observed MemAvailable: 13.716 GiB.
Observed mean GPU utilization: 96.0%; maximum memory PSI some/full avg10: 0.0%/0.0%.
Co-resident containers at run start: ['paddleocr-gb10 Up 2 hours (healthy)', 'vllm-educhat Up 2 hours (healthy)', 'vllm-omniedu Up 2 hours (healthy)'].
Qwen-related containers may be present; generation activity and cache state were not measured. This is not a verified OCR-only baseline.

| Document category | Success/attempted | Mean s | P50 s | P90 s | P95 s | Min s | Max s | Stddev s | Pages/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| resolution_large | 3/3 | 1.210 | 0.835 | 1.743 | 1.856 | 0.826 | 1.970 | 0.537 | 0.502 |

Overall success rate: 1.000; completed pages: 3.
Pages/s uses the measured-request window from the first start to the last completion.
Categories remain separate; the overall count is not a combined latency comparison.

See requests.csv for every attempt, resources.csv for timestamped telemetry, and environment.json for reproducibility.
On GB10, system memory, Docker memory, process RSS and NVIDIA memory may overlap and must not be summed.
Sampling cannot prevent an instantaneous out-of-memory event.

## Dataset

| ID | Type | Dimensions | Bytes | Expected pages | SHA256 |
| --- | --- | --- | ---: | ---: | --- |
| large-resolution | png | 1600×900 | 31617 | 1 | `470d4af103f0712c75746f0760a8866853d30eaa19c5722d952cf955ac427b50` |
