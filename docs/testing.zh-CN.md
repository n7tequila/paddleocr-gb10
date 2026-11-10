# 自动化测试（v0.2.1 开发中）

在仓库根目录独立运行各层：

```bash
bash tests/run-tests.sh static
bash tests/run-tests.sh environment
PADDLEOCR_ALLOW_GPU_TEST=1 bash tests/run-tests.sh gpu
bash tests/run-tests.sh api
PADDLEOCR_ALLOW_STABILITY_TEST=1 bash tests/run-tests.sh stability
bash tests/run-tests.sh release
bash tests/run-tests.sh all
```

`all` 只运行静态、现有镜像环境和发布元数据检查；普通 GitHub Actions 只运行静态和无需 GPU 的单元测试。当前承载 Qwen3.8 的 Spark 不作为公开仓库的自托管 Runner。任一层失败返回非零码；SKIP 单独记录，不计为通过。测试不会自动拉取镜像、安装依赖、重启服务或停止 Qwen。

| 层 | 内容 | 资源 |
| --- | --- | --- |
| `static` | Shell/Python 语法、Compose、路径、忽略规则、README、差异检查 | 无 GPU、无推理 |
| `environment` | 现有镜像的版本、ARM64、`pip check`、cuSPARSELt 标签 | 无推理 |
| `gpu` | 8×8 CUDA 矩阵及数值断言 | 轻量 GPU、无模型 |
| `api` | 官方 `/health` 和一次合成图片 `/layout-parsing` | 一次真实 OCR |
| `stability` | 健康状态、串行三次 OCR、错误请求、最终健康状态 | 三次真实 OCR；不自动运行 |
| `release` | 匿名 GHCR Manifest、Release 和校验清单 | 不下载大镜像 |

镜像默认使用本地 `paddleocr-gb10:0.2.0`，可用 `PADDLEOCR_IMAGE` 改动。API 默认地址为当前 Compose 的 `http://127.0.0.1:8080`；如改用其他宿主机端口，可设置 `PADDLEOCR_API_URL`。测试图是仓库内的[合成文字图片](../tests/fixtures/README.md)，不含真实儿童作业。结果只要求一页、非空 Markdown，不做逐字比对。

GPU 层须设置 `PADDLEOCR_ALLOW_GPU_TEST=1`，默认至少 8 GiB 可用内存。稳定性层须设置 `PADDLEOCR_ALLOW_STABILITY_TEST=1`，不会包含在 `all` 中。推理开始前默认要求 `MemAvailable` 至少 12 GiB、Memory PSI `avg10` 不超过 10%；请求期间每秒采样。若可用内存低于 8 GiB 或 PSI 越界，停止发出后续请求并报告失败；不会杀死正在进行的请求或容器，监控不能保证避免瞬时 OOM。阈值和超时可通过 `PADDLEOCR_GPU_MIN_GIB`、`PADDLEOCR_MIN_MEM_GIB`、`PADDLEOCR_STOP_MEM_GIB`、`PADDLEOCR_MAX_PSI_AVG10`、`PADDLEOCR_API_TIMEOUT` 调整。

每次运行打印 PASS、FAIL、SKIP，并将 JSON 报告写入 `tests/reports/<UTC 时间>/<层>.json`；API 响应和内存采样写在同一目录。该目录已被 Git 忽略，请勿公开含私人图片的响应。失败时先看报告的 `reason`，再检查镜像是否已在本地、Docker 权限、API 端口、Compose 状态和日志、内存门槛、代理与 GHCR 错误。发布层支持标准 `HTTP_PROXY` / `HTTPS_PROXY` 环境变量。更多说明见[英文详细指南](testing.md)。
