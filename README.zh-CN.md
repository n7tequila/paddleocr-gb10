# paddleocr-gb10：在 NVIDIA GB10 / ARM64 上运行 PaddleOCR-VL

[English README](README.md) · [完整排障记录](docs/troubleshooting.md) · [构建说明](docs/reproduction.md) · [基准测试](docs/benchmarks.md)

L1–L6 自动化测试见[中文测试指南](docs/testing.zh-CN.md)。先运行 `bash tests/run-tests.sh static`；GPU 和真实 OCR 推理层的资源要求见指南。

这是在 **FusionXpark / NVIDIA GB10（ARM64、CUDA 13.0、SM 12.1）** 上实践 PaddlePaddle GPU 编译和 PaddleOCR-VL-1.6 推理的社区记录与复现工程。不是 NVIDIA/PaddlePaddle 官方发布项目。

本项目使用 PaddleOCR 3.7.0、PaddleX 3.7.2 和 `paddle_dynamic` 推理引擎。容器直接启动 [PaddleX 官方 Serving](https://paddlepaddle.github.io/PaddleX/3.7/en/pipeline_usage/tutorials/ocr_pipelines/PaddleOCR-VL.html)，不另行实现 REST API，也不修改官方请求或响应协议。

## 快速开始：Docker

前提是 Ubuntu 24.04、NVIDIA GB10 / Linux ARM64、兼容 CUDA 13 的驱动，以及安装并配置好的 Docker 和 NVIDIA Container Toolkit。Docker 必须能通过 `--gpus all` 向容器提供 GPU。镜像**不含 OCR 模型权重**；首次启动可由官方工具下载模型，缓存应持久化挂载。

已发布的 [v0.2.0 镜像](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0)拉取命令：

```bash
docker pull --platform linux/arm64 \
  ghcr.io/n7tequila/paddleocr-gb10:0.2.0
```

**2026-11-10 发布核查：**匿名 GHCR 令牌请求和清单读取均返回 HTTP 200；OCI 索引列出 `linux/arm64`。这验证了匿名元数据访问，尚未完整拉取远端镜像或对远端镜像重新进行 GPU 测试。

镜像可拉取后，使用自己的目录持久化模型缓存，默认只监听宿主机 `127.0.0.1:8080`：

```bash
mkdir -p "$HOME/paddleocr-gb10-model-cache"
docker run --rm --gpus all --name paddleocr-gb10 \
  -p 127.0.0.1:8080:8080 \
  -v "$HOME/paddleocr-gb10-model-cache:/root/.paddlex" \
  ghcr.io/n7tequila/paddleocr-gb10:0.2.0
```

Compose 用法：仅在 `docker/.env` 不存在时复制 [docker/.env.example](docker/.env.example)；如已有旧配置，请检查 `PADDLEOCR_IMAGE` 并设为 GHCR 地址。按需将 `PADDLEX_CACHE` 改为自己的绝对缓存目录，或使用默认的持久化 `docker/model-cache`；然后运行 `docker compose --env-file docker/.env -f docker/compose.yaml up -d`。GHCR 路径无需本地 Wheel 或 Docker 构建上下文。设置 `PADDLEOCR_PUBLIC_PORT` 可更改宿主机端口。Compose 使用 `gpus: all`、`linux/arm64`，默认仅绑定 `127.0.0.1:8080`。本地构建为可选流程，详见[中文 Docker 文档](README.docker.zh-CN.md)。

## PaddleX 官方 REST API

服务端点是 `POST http://127.0.0.1:8080/layout-parsing`。以下命令使用仓库内的标准库客户端，把本地图片编码为 Base64 后按 [PaddleX 3.7 官方协议](https://paddlepaddle.github.io/PaddleX/3.7/en/pipeline_usage/tutorials/ocr_pipelines/PaddleOCR-VL.html#43-client-side-invocation)发送：

```bash
python3 docker/test-official-api.py \
  --url http://127.0.0.1:8080/layout-parsing \
  --image /path/to/image.png \
  --output /tmp/paddleocr-response.json
```

请求 JSON 包含 `file`（图片 Base64）、`fileType: 1`（图片）、`visualize: false`、`useDocOrientationClassify: false` 和 `useDocUnwarping: false`。成功响应为 HTTP 200，包含 `logId`、`errorCode: 0`、`errorMsg` 与 `result.layoutParsingResults`；每页含 `prunedResult` 和 `markdown`（`text` 与可选 `images`）。这是官方参数和结构，本项目不提供额外的 `/v1/ocr/parse`。

也可以直接用 curl 发送同一官方 JSON。将图片路径换成真实 PNG 或 JPEG；首次请求预留五分钟：

```bash
IMAGE=/path/to/image.png
python3 - "$IMAGE" > /tmp/paddleocr-request.json <<'PY'
import base64, json, pathlib, sys
print(json.dumps({"file": base64.b64encode(pathlib.Path(sys.argv[1]).read_bytes()).decode(), "fileType": 1, "visualize": False}))
PY
curl --fail-with-body --connect-timeout 10 --max-time 300 \
  -H 'Content-Type: application/json' \
  --data-binary @/tmp/paddleocr-request.json \
  http://127.0.0.1:8080/layout-parsing
```

启动后用 `docker compose --env-file docker/.env -f docker/compose.yaml logs --tail=80 paddleocr` 和同参数的 `ps` 查看状态。首次启动可能下载模型到持久化的 `/root/.paddlex` 缓存；Compose 检查 PaddleX 官方 `GET /health`，再以 `/layout-parsing` 成功响应验证 OCR 推理。

## 社区构建 PaddlePaddle GPU Wheel

仅在**宿主机 Python 安装**时需要 [v0.2.0 GitHub Release](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0) 中的 [CPython 3.12 / Linux aarch64 Wheel](https://github.com/n7tequila/paddleocr-gb10/releases/download/v0.2.0/paddlepaddle_gpu-3.5.0.dev20261109%2B6c839e963ed-cp312-cp312-linux_aarch64.whl)；[SHA256SUMS](https://github.com/n7tequila/paddleocr-gb10/releases/download/v0.2.0/SHA256SUMS) 对应文件名的 SHA256 为 `a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb`。Docker 用户无需单独下载 Wheel。此非官方社区构建仅验证于 CUDA 13.0、NVIDIA GB10 / SM 12.1，不保证适用于其他 ARM64 GPU。

安装需具备兼容的 NVIDIA CUDA Python、cuDNN、cuBLAS、NCCL 等依赖。Dockerfile 记录了已验证版本，并以 `--no-deps` 安装 Wheel，避免被其他 Paddle 构建替换。`nvidia-cusparselt-cu13==0.8.1` 的 SBSA WHEEL 标签在 ARM64 上有兼容问题；仅在对应环境使用受保护的[元数据修复脚本](docker/fix-cusparselt-wheel-tag.py)，详情见[排障文档](docs/troubleshooting.md)。

## 项目版本

- **v0.1.0：**GB10 上 PaddlePaddle GPU 编译和 PaddleOCR-VL 推理验证。
- **v0.2.0：**Docker 打包和 PaddleX 官方 REST API 实测；GHCR 匿名清单可访问且索引列出 `linux/arm64`。

## 2026-11-09 已经真实验证的事实

| 项目 | 结果 |
| --- | --- |
| 系统 | Ubuntu 24.04.5 LTS / aarch64 |
| 显卡/驱动 | GB10（sm_121）/ 580.178.04 |
| CUDA | 13.0.88 |
| Python | 3.12.3 |
| PaddlePaddle | 自编译 3.5.0.dev20261109+6c839e963ed |
| PaddleOCR / PaddleX | 3.7.0 / 3.7.2 |
| 实际模型 | PP-DocLayoutV3 + PaddleOCR-VL-1.6-0.9B |
| GPU 验证 | `paddle.utils.run_check()` 与矩阵运算成功 |
| 首次模型识别 | 生成非空 Markdown/JSON 成功 |
| 已缓存模型初始化 | 15.670 秒 |
| 同图三次推理 | 16.875 / 15.453 / 15.144 秒 |
| 内存观测 | RSS 峰值 3,376.69 MiB；`MemAvailable` 最大下降 9,311.23 MiB |

**重要声明：** 本仓库内整理的安装脚本是根据成功过程重构的**待重新端到端验证的可复现流程**。上述成功数据来自在机器上逐步修复后的环境，并不表示这个打包项目已从零安装通过。不会发布未经证实的“完美一键安装”宣传。

## 从源码构建（在 GB10 的 Ubuntu 上执行，不在 Mac 上执行）

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-dev build-essential \
    cmake ninja-build patchelf swig libopenblas-dev liblapack-dev gfortran

git clone https://github.com/n7tequila/paddleocr-gb10.git
cd paddleocr-gb10

# 编译前确保可用内存大于约 48 GiB；请自行停止大内存模型
JOBS=4 bash scripts/build-paddle.sh

# 独立运行环境；不污染系统 Python
bash scripts/setup-runtime.sh

# 本地图片，模型首次运行时自动下载
bash scripts/test-vl.sh /path/to/homework.jpg
```

所有生成文件默认放在 `$HOME/paddleocr-gb10-work`，可以通过 `WORKSPACE=/data/llm-docker/paddleocr-gb10-work` 改为数据盘。编译脚本**不会自动关闭 vLLM**；中断后 Ninja 可以增量继续。PaddlePaddle 源码固定至实际成功的 commit `6c839e963ed`。

## 为什么建立这个项目？

GB10 的核心难点不是 PaddleOCR Python API，而是 **Linux ARM64 + CUDA 13 + sm_121 的 PaddlePaddle GPU 底层构建与推理依赖**。我们在真实机器上经历了 Git/GnuTLS 网络中断、脚本重复运行保护、cuDNN namespace package 路径异常、SLEEF/TLFloat 错误链接依赖、大量 Eigen GCC 警告、Ninja 中断恢复、NumPy 依赖冲突、cuSPARSELt 的 Wheel 元数据不匹配，并最终实现了 GPU 验证与 VL 1.6 推理。

完整逐步过程：[docs/troubleshooting.md](docs/troubleshooting.md)。本仓库已去除曾导致失败的 TLFloat 错误注入；不会通过伪造 `libtlfloat.a` 解决链接问题。

## 文件结构

```text
scripts/               构建、运行环境、GPU 验证、VL 图片推理
patches/               补丁检查/修复工具
benchmarks/            可重复跑的内存与耗时基准
settings/              (无；均通过环境变量设置)
docs/                  排障、实测数据、开源发布说明
.github/workflows/     静态语法检查
```

## 重视 Qwen3.8 共存

原 GB10 上 Qwen3.8 vLLM 进程曾报告占用约 **96,501 MiB**，系统可用约 **18 GiB**。PaddleOCR-VL 单独测试中系统可用内存最大下降约 **9.09 GiB**。后续 Docker OCR 验证期间 Qwen3.8 保持运行；同时进行 Qwen 文本生成和 OCR、长期共存稳定性仍未验证。儿童手写、公式识别精度也尚无系统性评估。

## 未来计划

- [ ] 在另一干净 GB10 环境上从零验证本仓库的构建脚本
- [ ] GB10 + Qwen3.8 双进程内存与 GPU 峰值测试
- [ ] 手写语文作文、数学竖式、公式的独立测试集
- [x] 单实例官方 PaddleX Serving / Docker Compose 的启动与单次真实图片请求
- [ ] CUDA / PaddleOCR 新版本升级与回滚流程

## Wheel 与授权

最初成功的 Wheel 名称为 `paddlepaddle_gpu-3.5.0.dev20261109+6c839e963ed-cp312-cp312-linux_aarch64.whl`，约 345MB，SHA256 为：

```text
a235ad6edcdf4b499ec3f86829d5302766cee1ee66de7c7786cf44660baf75bb
```

**不把 Wheel、模型权重、原始儿童作业、环境变量或模型缓存提交 Git。** 已发布的 Wheel 请从上方 GitHub Release 下载；本文记录 checksum 是历史实测产物，不保证新构建会得到相同 hash。

参考与致谢：[sarthaknimbalkar/dgx-spark-paddlepaddle-gpu](https://github.com/sarthaknimbalkar/dgx-spark-paddlepaddle-gpu)（MIT 构建参考及 CUTLASS 补丁）；[gaozhi-ustc/paddleocr-dgx](https://github.com/gaozhi-ustc/paddleocr-dgx)（Docker 服务架构参考，未复制）；[PaddlePaddle/Paddle](https://github.com/PaddlePaddle/Paddle) 与 [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)。本仓库**原创的脚本和文档**采用 MIT，第三方依赖保留原有授权。

## 从 macOS 发布到 GitHub

仓库 `n7tequila/paddleocr-gb10` 已经创建，下载配套的 ZIP 与 macOS 一键发布脚本，按 [PUBLISHING.md](PUBLISHING.md) 执行。发布不依赖 Spark 的 GPU 服务。

## v0.2.0 Docker / 官方 REST API

`paddleocr-gb10:0.2.0` 已在 GB10 上通过 Docker GPU 验证；官方 Serving 启动后，真实手写作文调用 `/layout-parsing` 返回 HTTP 200，耗时 18.59 秒。参见 [中文 Docker 部署](README.docker.zh-CN.md) 和 [验证记录](docs/serving-validation-2026-11-10.md)。本项目不另开发 API。
