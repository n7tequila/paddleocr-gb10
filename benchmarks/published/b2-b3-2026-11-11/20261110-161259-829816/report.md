# GB10 OCR benchmark

Status: **success**

Times are client-measured HTTP end-to-end latency, including transfer and server work; they are not GPU inference times.
P95 is descriptive with fewer than 100 successes and must not be treated as stable tail latency.

Measured requests: 3/3; warmups: 1; concurrency: 1.
Minimum observed MemAvailable: 13.756 GiB.
Observed mean GPU utilization: 94.58823529411765%; maximum memory PSI some/full avg10: 0.0%/0.0%.
Co-resident containers at run start: ['paddleocr-gb10 Up 2 hours (healthy)', 'vllm-educhat Up 2 hours (healthy)', 'vllm-omniedu Up 2 hours (healthy)'].
Qwen-related containers may be present; generation activity and cache state were not measured. This is not a verified OCR-only baseline.

| Document category | Success/attempted | Mean s | P50 s | P90 s | P95 s | Min s | Max s | Stddev s | Pages/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_paragraph | 3/3 | 2.805 | 2.333 | 3.478 | 3.621 | 2.318 | 3.764 | 0.678 | 0.259 |

Overall success rate: 1.000; completed pages: 3.
Pages/s uses the measured-request window from the first start to the last completion.
Categories remain separate; the overall count is not a combined latency comparison.

See requests.csv for every attempt, resources.csv for timestamped telemetry, and environment.json for reproducibility.
On GB10, system memory, Docker memory, process RSS and NVIDIA memory may overlap and must not be summed.
Sampling cannot prevent an instantaneous out-of-memory event.

## Dataset

| ID | Type | Dimensions | Bytes | Expected pages | SHA256 |
| --- | --- | --- | ---: | ---: | --- |
| paragraph-layout | png | 1100×650 | 30532 | 1 | `7593253a1e5861411292934434681217e359a8704e0b46aa8e1fb2206b9fcc8b` |
