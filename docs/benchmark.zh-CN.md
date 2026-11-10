# GB10 OCR Benchmark 方法（v0.3.0 开发中）

本工具通过 PaddleX 官方 `POST /layout-parsing` 测量**客户端 HTTP 端到端延迟**，包含传输及服务端处理时间，不能称为单独的 GPU 推理时间。旧版[性能记录](benchmarks.md)属于 2026-11-09 的另一轮实验，不与本轮合并。

## 运行与复现

先确认现有 OCR 服务健康且内存充足，再从固定 Git Commit 运行：

```bash
bash benchmarks/run-benchmark.sh --scenario basic --warmup 1 --requests 5 --concurrency 1 --timeout 300
```

默认 API 为 `PADDLEOCR_API_URL`，未设置时为 `http://127.0.0.1:8080`。`--images` 可传本地图片或目录；`--output-dir` 更改报告位置；`--scenario documents` 测试各类公开合成文件。默认一次预热、五次正式串行请求。预热单独记录，不进入延迟统计。`--requests` 在样本间轮换。B2 验收请对每个公开样本分别运行 `--scenario documents --sample-id ID --warmup 1 --requests 3`，这样每类都有独立预热和延迟统计。并发大于 1 必须同时设置 `--allow-concurrency`，且须先评估资源。

将 B2 每类报告放在同一输出目录后，运行 `python3 benchmarks/aggregate.py OUTPUT_ROOT` 生成不混合类别均值的五文件综合报告。本轮 B4 仅完成代码与 Mock 测试，运行方案见 [B4 测试计划](../benchmarks/B4-PLAN.md)。

报告位于被 Git 忽略的 `benchmarks/reports/<UTC 时间>/`，包含 `summary.json`、`requests.csv`、`resources.csv`、`environment.json`、`report.md`。每次请求均记录开始时间、HTTP 状态、PaddleX `errorCode`、耗时、请求/响应字节数、页数、Markdown 长度、超时和错误。环境文件另记录 Git Commit、工作区修改状态和 Benchmark 源码哈希。不会保存原始 OCR 响应正文；私有文件路径和哈希可能出现在环境记录中，公开前须检查。

## 数据集和统计

[清单](../benchmarks/datasets/manifest.json)记录六张合成打印 PNG、一份单页 PDF 和一份双页 PDF 的来源、许可、尺寸、页数、文件大小与 SHA256。PDF 用官方 `fileType: 0`，PNG 用 `1`，详见 [PaddleX 文档](https://paddlepaddle.github.io/PaddleX/3.7/en/pipeline_usage/tutorials/ocr_pipelines/PaddleOCR-VL.html)。可用 Pillow 及文档所述字体运行 `python3 benchmarks/datasets/generate.py` 重新生成，并检查哈希。合成字体不是实际手写准确率测试。私有作文可通过 `--images` 在本地引用，勿将儿童作业、姓名或教师批改图片提交到 Git。

新版本请求计时从发送 HTTP 前开始，在完整读取响应字节后结束；本地读图、Base64 构造和 JSON 解析不计入。`run_elapsed_s` 覆盖初始资源门槛、健康检查、预热、正式请求和监控关闭，不含环境信息收集及报告写盘。页面吞吐量用实际成功页数除以第一条正式请求开始至最后一条正式请求结束的墙钟窗口；包括请求间隔和数据集切换，但不包括预热及预检。旧 B1 报告的计时还包含本地准备和解析，已在其独立重新分析文件中说明。

成功请求分别按文档类别统计均值、中位数/P50、P90、P95、最小/最大值、总体标准差、成功率和正式请求窗口墙钟时间内的成功页吞吐量。失败或超时计入成功率分母并保留在 CSV。成功样本少于 100 时，P95 仅作描述，不能代表稳定尾延迟。横向比较须固定图片 SHA256、参数、缓存状态及软件环境。

## 资源与保护

监控目标采样间隔 0.5–1 秒，记录 MemAvailable、Swap 使用量、内存 PSI some/full、可获得的 GPU 利用率/功耗/温度/显存统计、OCR 容器健康与内存使用、可从 `docker top` 获取的 OCR 进程 RSS，以及 Benchmark 客户端进程 RSS。设备不支持的 GPU 字段用 `null`/N/A；宿主机内存和 PSI 依配置每 0.5–1 秒采样，UTC 与单调时间戳可关联请求；GPU 与 Docker 值独立更新并附在最近的采样行，命令耗时可能造成更新滞后。GB10 统一内存下，各项内存数据会重叠，不可简单相加。

推理前 MemAvailable 低于 12 GiB 即拒绝开始；运行中低于 8 GiB、PSI some avg10 达 5% 或 full avg10 达 1% 时停止发出新请求。正在进行的请求允许结束或超时；工具不杀死或重启 OCR/Qwen。采样不能保证避免瞬时 OOM。报告区分成功、失败、超时、内存保护中止、用户取消及未运行。

## 可选 Qwen 共存 B4

B4 代码已实现，但默认及 CI 都不运行。A 为 Qwen 不在场的 OCR 基线（需人工准备环境，工具不会停止 Qwen）；B 为 Qwen 加载且空闲；C 为 Qwen 正在生成时的 OCR。每次必须显式设置 `--allow-coexist-load`、宿主机可访问的 `--qwen-api-url` 和 `--qwen-model`。例如：

```bash
python3 benchmarks/coexist.py --allow-coexist-load --mode active \
  --qwen-api-url http://HOST:PORT/v1 --qwen-model MODEL \
  --qwen-cache-state unknown --requests 5 --warmup 1
```

三组使用相同 OCR 图片、次数与参数；B/C 使用相同 Qwen Prompt（默认固定或 `--qwen-prompt-file`）及 token 上限。前缀缓存需用 `--qwen-cache-state` 记录，或人工关闭服务端缓存；相同前缀可能命中缓存。`qwen.csv` 记录 TTFT、输出 tokens/s 和可获得的服务端 usage；若缺失，按输出字符数除以 4 粗略估算 token 数并明确标记，中文误差可能很大。B4 只允许串行 OCR、最多 256 输出 token，每次活动请求前重查资源。本开发周期不执行 B4 C。

[已公开准备的 B2/B3 合成数据验收报告](../benchmarks/published/b2-b3-2026-11-11/report.md)包含各类独立记录与分类对比。
