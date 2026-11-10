# Verified: official PaddleX Serving on GB10 (host Python venv)

Observed 2026-11-10 (local GB10 time):

This is a historical host test that explicitly used port 8004. Current Docker Compose examples default to 8080 on both host and container.

```text
paddlex --serve --pipeline PaddleOCR-VL-1.6 --device gpu:0 --host 127.0.0.1 --port 8004
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8004
POST /layout-parsing HTTP/1.1 200 OK
SUCCESS: official JSON REST API
Duration: 16.97 seconds
Pages: 1
Top-level keys: ['logId', 'result', 'errorCode', 'errorMsg']
Page[0] keys: ['prunedResult', 'markdown']
```

Model components: `PP-DocLayoutV3`, `PaddleOCR-VL-1.6-0.9B` loaded from `/home/tequila/.paddlex/official_models`. API returned Markdown with a Chinese newspaper title. Paddle's tensor-copy warning did not prevent HTTP 200. This block records **host Serving** evidence.

Subsequent Docker validation: the existing `paddleocr-gb10:0.2.0` image passed GPU checks with compute capability 12.1, official PaddleX Serving started, and its `/layout-parsing` endpoint returned HTTP 200 for a real handwritten essay in 18.59 seconds. The complete response and container logs are not preserved in this repository, so no further accuracy claim is made.

Observed earlier Qwen co-residency test (host Python, not active simultaneous decoding): initial MemAvailable 19.75GiB; minimum 10.20GiB; PSI some/full 0.00%; OCR model initialized 12.662s and page runs 17.466, 15.854 and 14.966 seconds; OCR exit status 0.
