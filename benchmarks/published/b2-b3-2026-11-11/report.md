# GB10 B2/B3 document comparison

Status: **success**. 24/24 measured requests succeeded; 8 warmups were recorded.
All latencies are client HTTP end-to-end from request opening to complete response body read. They are not internal model or GPU inference times. Each category is reported independently; no combined latency mean is calculated. P95 with three samples is descriptive only.

## Document type and size comparison

| Sample | Type | Pixels/page | File bytes | Actual pages/request | Markdown chars/request | Mean s | P50 s | P95 s | Success |
| --- | --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| english-print | png | 900×360 | 22672 | 1,1,1 | 84,84,84 | 0.775 | 0.771 | 0.795 | 3/3 |
| chinese-print | png | 1000×450 | 29499 | 1,1,1 | 34,34,34 | 1.583 | 1.213 | 2.221 | 3/3 |
| paragraph-layout | png | 1100×650 | 30532 | 1,1,1 | 182,182,182 | 2.805 | 2.333 | 3.621 | 3/3 |
| math-expression | png | 900×360 | 11850 | 1,1,1 | 85,85,85 | 1.625 | 1.256 | 2.256 | 3/3 |
| small-resolution | png | 640×240 | 8839 | 1,1,1 | 38,38,38 | 0.635 | 0.634 | 0.637 | 3/3 |
| large-resolution | png | 1600×900 | 31617 | 1,1,1 | 61,61,61 | 1.210 | 0.835 | 1.856 | 3/3 |
| one-page-pdf | pdf | 850×1100 | 28572 | 1,1,1 | 67,67,67 | 1.197 | 1.193 | 1.211 | 3/3 |
| two-page-pdf | pdf | 850×1100 | 55598 | 2,2,2 | 129,129,129 | 3.031 | 2.304 | 4.341 | 3/3 |

## PDF comparison

The one-page PDF returned [1, 1, 1] pages with mean HTTP E2E 1.197 s. The two-page PDF returned [2, 2, 2] pages with mean 3.031 s. Both sent official `fileType: 0`. The two-page result was observed in a separate run, so the difference includes run-to-run conditions.
PaddleX 3.7 documents no default PDF page limit, but server configuration can set one; this acceptance verifies only two pages.

## Resource comparison

| Sample | GPU util mean % | GPU temp max °C | GPU power max W | MemAvailable start→min GiB | Observed drop GiB | Swap start→end GiB | Docker memory first→last |
| --- | ---: | ---: | ---: | --- | ---: | --- | --- |
| english-print | 93.750 | 62.000 | 38.100 | 13.817→13.791 | 0.026 | 2.593→2.593 | 3.863GiB / 121.6GiB→3.862GiB / 121.6GiB |
| chinese-print | 94.750 | 63.000 | 42.510 | 13.784→13.757 | 0.027 | 2.593→2.593 | 3.862GiB / 121.6GiB→3.864GiB / 121.6GiB |
| paragraph-layout | 94.588 | 64.000 | 44.190 | 13.793→13.756 | 0.037 | 2.593→2.593 | 3.864GiB / 121.6GiB→3.867GiB / 121.6GiB |
| math-expression | 94.167 | 63.000 | 42.550 | 13.773→13.741 | 0.032 | 2.593→2.593 | 3.866GiB / 121.6GiB→3.867GiB / 121.6GiB |
| small-resolution | 93.000 | 63.000 | 38.290 | 13.801→13.775 | 0.026 | 2.592→2.592 | 3.867GiB / 121.6GiB→3.868GiB / 121.6GiB |
| large-resolution | 96.000 | 63.000 | 34.670 | 13.779→13.716 | 0.063 | 2.592→2.592 | 3.867GiB / 121.6GiB→3.874GiB / 121.6GiB |
| one-page-pdf | 95.720 | 65.000 | 44.240 | 13.766→13.708 | 0.058 | 2.592→2.592 | 3.914GiB / 121.6GiB→3.897GiB / 121.6GiB |
| two-page-pdf | 96.000 | 65.000 | 44.560 | 13.791→13.648 | 0.143 | 2.592→2.592 | 3.874GiB / 121.6GiB→3.914GiB / 121.6GiB |

Lowest observed MemAvailable: 13.648 GiB. PSI some/full remained below stop thresholds; the OCR container stayed healthy.
GPU memory.used was unavailable from nvidia-smi and is N/A. System MemAvailable, Docker memory, process RSS and NVIDIA memory can overlap on GB10 unified memory and must not be added.
Every resource row has a UTC and monotonic timestamp. GPU and Docker values also carry their own sample timestamps; use the monotonic timestamps in requests.csv to join them. The Docker query can refresh more slowly than host memory/PSI.

## Interpretation and limitations

- Larger pages, different layout, Chinese text, mathematics, and two PDF pages may affect processing time. These are plausible factors, not isolated causal estimates from this small sample.
- The PNG resolution comparison is between different synthetic images, so it does not isolate resolution alone. The PDFs share the first page, but were measured in separate runs.
- Qwen-related containers were present and healthy; generation activity, prefix-cache state, and background load were not controlled. This is not an OCR-only baseline or a B4 test.
- Source revisions across the eight runs: {'benchmarks/benchmark.py': 2, 'benchmarks/monitor.py': 2, 'benchmarks/datasets/manifest.json': 2}. The single-page PDF was added later; raw per-run data remains intact. Compare these results as an acceptance snapshot, not as a tightly controlled causal experiment.
- Three measurements per type are insufficient for stable tail-latency claims. No accuracy ground truth, real handwriting, high concurrency, or long-duration load was tested.
- The dataset contains only fictional synthetic content; no private student work or OCR response body is included.

## Detailed run reports

- [english-print](20261110-161221-723214/report.md)
- [chinese-print](20261110-161234-886841/report.md)
- [paragraph-layout](20261110-161259-829816/report.md)
- [math-expression](20261110-161321-668121/report.md)
- [small-resolution](20261110-161345-967613/report.md)
- [large-resolution](20261110-161359-549238/report.md)
- [one-page-pdf](20261110-162406-966854/report.md)
- [two-page-pdf](20261110-161424-328184/report.md)
