# B2/B3 acceptance — seven synthetic document types

All seven samples passed 1 warmup and 3 measured serial requests each. No category latency means are combined. Times below are client HTTP end-to-end after the timer correction. P95 is descriptive for n=3.

| Sample | Dimensions | Bytes | Pages/response | Markdown chars/response | Mean s | P50 s | P95 s | Success | Min MemAvailable GiB | Report |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| english-print | 900×360 | 22672 | 1 | 84,84,84 | 0.775 | 0.771 | 0.795 | 3/3 | 13.791 | [20261110-161221-723214](20261110-161221-723214/report.md) |
| chinese-print | 1000×450 | 29499 | 1 | 34,34,34 | 1.583 | 1.213 | 2.221 | 3/3 | 13.757 | [20261110-161234-886841](20261110-161234-886841/report.md) |
| paragraph-layout | 1100×650 | 30532 | 1 | 182,182,182 | 2.805 | 2.333 | 3.621 | 3/3 | 13.756 | [20261110-161259-829816](20261110-161259-829816/report.md) |
| math-expression | 900×360 | 11850 | 1 | 85,85,85 | 1.625 | 1.256 | 2.256 | 3/3 | 13.741 | [20261110-161321-668121](20261110-161321-668121/report.md) |
| small-resolution | 640×240 | 8839 | 1 | 38,38,38 | 0.635 | 0.634 | 0.637 | 3/3 | 13.775 | [20261110-161345-967613](20261110-161345-967613/report.md) |
| large-resolution | 1600×900 | 31617 | 1 | 61,61,61 | 1.210 | 0.835 | 1.856 | 3/3 | 13.716 | [20261110-161359-549238](20261110-161359-549238/report.md) |
| two-page-pdf | 850×1100 | 55598 | 2 | 129,129,129 | 3.031 | 2.304 | 4.341 | 3/3 | 13.648 | [20261110-161424-328184](20261110-161424-328184/report.md) |

Lowest observed MemAvailable: 13.648 GiB. All sampled PSI some/full avg10 values were 0.0%. OCR container health samples were `running/healthy`.
Resource samples carry host UTC/monotonic timestamps; GPU and Docker values carry their own sampling timestamps. Request start/end monotonic times allow joining. GPU memory.used was unavailable and remains N/A. Unified-memory measures must not be added together.
Qwen-related containers were present. This is a co-resident, uncontrolled-load measurement, not an OCR-only baseline. No B4 simultaneous-generation test was run.
The two-page PDF used official `fileType=0` and returned two pages every time. The official PaddleX 3.7 REST reference says the default page limit is unset; a server configuration can override it. This run only verifies two pages.
No raw B1 data was modified. See its separate retrospective reanalysis for the older timing definition.
