# B2/B3 synthetic benchmark data

This directory is the publishable copy of the local acceptance run under `benchmarks/reports/b2-20261110-161209/`. It contains eight per-sample runs and the five-file aggregate report. CSV line endings were normalized from CRLF to LF for Git; every data cell and all JSON/Markdown content are unchanged. The private local report directory remains Git ignored.

Start with [report.md](report.md). The dataset consists only of synthetic fixtures listed in [the manifest](../../datasets/manifest.json). No original OCR response bodies, real children's work, or private images are included. Environment files record software versions, container status, dataset hashes, and source revision hashes. Seven runs preceded the addition of the single-page PDF; the aggregate report explicitly records the two source revisions and does not pool latency means.
