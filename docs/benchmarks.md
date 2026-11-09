# Benchmark data and caveats

**Dataset:** one printed Chinese news page, 1524×1368 pixels. **Engine:** `paddle_dynamic`, PaddleOCR-VL-1.6-0.9B and PP-DocLayoutV3 on GB10. **Date:** 2026-11-09.

| Metric | Value |
|---|---:|
| First cold-ish run total | 54.64s |
| First initialization incl. model download | 36.92s |
| Cached initialization | 15.670s |
| Iteration 1 | 16.875s |
| Iteration 2 | 15.453s |
| Iteration 3 | 15.144s |
| Warm mean (2+3) | 15.2985s |
| Sampled RSS max | 3,376.69 MiB |
| Available-memory drop max | 9,311.23 MiB |
| Baseline available memory | 121,186.57 MiB |
| Minimum available memory | 111,875.34 MiB |

Machine has approximately 121 GiB Linux-visible of 128 GB unified memory. RSS is not a measure of sole GPU allocation, and available-memory changes include file caches and unrelated processes. Sampling intervals can miss peaks. No memory limit is asserted. The test ran **with Qwen stopped**. Qwen3.8 + OCR co-residency remains open.

To reproduce, use `bash scripts/benchmark-vl.sh /absolute/path/to/image.png`. This test script is newly assembled for publication; figures above come from an earlier, locally run measurement script. It records timing and periodic memory samples; run on a quiet system for fair comparison.

The Markdown/JSON produced by the first reference document had blocks for headline, byline, paragraph headings, text, image and image caption, plus three empty text blocks. The newspaper result does **not** benchmark handwriting or formula accuracy. For children's homework, build separate manually transcribed ground truth and measure CER, omission rate, math formula agreement, and question-answer association errors.
