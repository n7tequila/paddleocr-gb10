# GB10 OCR benchmark

Status: **success**

Times are client-measured HTTP end-to-end latency, including transfer and server work; they are not GPU inference times.
P95 is descriptive with fewer than 100 successes and must not be treated as stable tail latency.

Measured requests: 3/3; warmups: 1; concurrency: 1.
Minimum observed MemAvailable: 13.757 GiB.
Observed mean GPU utilization: 94.75%; maximum memory PSI some/full avg10: 0.0%/0.0%.
Co-resident containers at run start: ['paddleocr-gb10 Up 2 hours (healthy)', 'vllm-educhat Up 2 hours (healthy)', 'vllm-omniedu Up 2 hours (healthy)'].
Qwen-related containers may be present; generation activity and cache state were not measured. This is not a verified OCR-only baseline.

| Document category | Success/attempted | Mean s | P50 s | P90 s | P95 s | Min s | Max s | Stddev s | Pages/s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| chinese_print | 3/3 | 1.583 | 1.213 | 2.109 | 2.221 | 1.203 | 2.333 | 0.530 | 0.365 |

Overall success rate: 1.000; completed pages: 3.
Pages/s uses the measured-request window from the first start to the last completion.
Categories remain separate; the overall count is not a combined latency comparison.

See requests.csv for every attempt, resources.csv for timestamped telemetry, and environment.json for reproducibility.
On GB10, system memory, Docker memory, process RSS and NVIDIA memory may overlap and must not be summed.
Sampling cannot prevent an instantaneous out-of-memory event.

## Dataset

| ID | Type | Dimensions | Bytes | Expected pages | SHA256 |
| --- | --- | --- | ---: | ---: | --- |
| chinese-print | png | 1000×450 | 29499 | 1 | `1a1fe969022541d36ec3a1515cf88398de552631dd291f36e5737d2e44eadbd5` |
