# B4 coexistence test plan — not executed in B2/B3 acceptance

This plan compares three separately controlled conditions using `benchmarks/coexist.py` and the fixed `coexist` OCR scenario. It sends official PaddleX `/layout-parsing` requests; it never changes a serving container. Do not start until the operator has approved the extra Qwen load and verified both services.

1. Record the OCR image SHA256, Git commit/source hashes, Qwen model, exact prompt SHA256, Qwen host-accessible API URL, prefix-cache state, and container/driver versions. Use the same OCR image and request parameters for A/B/C; use the same Qwen prompt and `--qwen-max-tokens` for B/C.
2. Confirm PaddleOCR is healthy, Qwen is running normally, `MemAvailable >= 12 GiB`, PSI some avg10 `< 5%`, and full avg10 `< 1%`. The tool repeats the resource gate before each active Qwen request. During a run, below 8 GiB or PSI at/above those limits stops new OCR requests. Sampling cannot prevent instantaneous OOM.
3. A: an OCR-only baseline requires a separately prepared environment in which Qwen is absent. The tool does **not** stop Qwen. The current shared host cannot be treated as A while Qwen containers are present.
4. B: with Qwen loaded and idle, run `python3 benchmarks/coexist.py --allow-coexist-load --mode idle --qwen-api-url http://HOST:PORT/v1 --qwen-model MODEL --qwen-cache-state STATE --warmup 1 --requests 3 --concurrency 1`.
5. C: only after a fresh resource check, repeat the same command with `--mode active`. This starts one bounded Qwen generation per OCR attempt and measures temporal overlap. It does not change or restart the Qwen service. B4 is serial and limits output to 256 tokens; use a fixed prompt file or the built-in prompt.
6. Compare OCR HTTP E2E, Qwen TTFT, Qwen request duration, output tokens/s, overlap seconds, success rate, GPU utilization, MemAvailable and PSI across matched runs. Use server-reported completion tokens when present. Otherwise `characters/4` is explicitly labeled a rough estimate. Note cache header and declared prefix-cache state; ideally disable prefix caching or control warm/cold state before comparing.
7. Press Ctrl-C to cancel. The client closes its own Qwen HTTP response and exits through the benchmark's `user_cancelled` report path; it never kills a container. Check both containers remain healthy afterward.

No B4 API call, Qwen generation, or concurrent-load test was performed during this acceptance. The B4 behavior above has Mock coverage only.
