# v0.2.0 release preparation — Docker + official REST API

The existing image passed the following checks on GB10. Repository cleanup and exact dependency constraints were added afterward, so rebuilding from this source remains pending:

- [x] Existing `paddleocr-gb10:0.2.0` image built with the validated ARM64 GPU Wheel.
- [x] Docker GPU validation reported compute capability 12.1.
- [x] Official PaddleX Serving started inside Docker with PaddleOCR-VL-1.6.
- [x] Official `/layout-parsing` returned HTTP 200 for a real handwritten essay in 18.59 seconds.
- [x] Python package versions captured from the validated image in `docker/requirements-verified.txt`.
- [x] GitHub Release `v0.2.0` is public with the GPU Wheel and matching `SHA256SUMS`.
- [ ] GHCR anonymous pull succeeds and the remote manifest confirms `linux/arm64` (10 Nov: anonymous token HTTP 401, Package page HTTP 404).
- [ ] Rebuild the updated source recipe with its exact constraints and repeat Docker GPU/API checks.
- [ ] Record memory metrics during repeated requests while Qwen3.8 stays online.
- [ ] Validate **simultaneous** Qwen inference + OCR before declaring production coexistence.
- [ ] Record the CUDA base image digest and RAM metrics of a successful rebuild.

The GitHub Release is already published. The GHCR image is an intended address, but public accessibility and platform remain unverified. Git push, tag changes and Release edits require a separate explicit instruction.
