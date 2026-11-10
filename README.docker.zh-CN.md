# PaddleOCR GB10 · 官方 REST API Docker 部署（v0.2.0）

本版本只做 **NVIDIA GB10 / ARM64 / CUDA 13.0 环境与 Docker 适配**，不开发自己的 OCR REST API。
容器里直接执行官方命令：

```bash
paddlex --serve --pipeline PaddleOCR-VL-1.6 --device gpu:0 --host 0.0.0.0 --port 8080
```

Docker 映射为宿主机 `http://127.0.0.1:8080/layout-parsing`，请求与响应由官方 PaddleX 提供。今后的 `edu-ocr` 属于独立项目，不并入这个基础镜像。

## 镜像状态与快速启动

已发布镜像地址为 `ghcr.io/n7tequila/paddleocr-gb10:0.2.0`。2026-11-10 匿名令牌与清单请求均返回 HTTP 200，OCI 索引列出 `linux/arm64`。尚未完整拉取远端镜像或重新做 GPU 测试。参见 [v0.2.0 Release](https://github.com/n7tequila/paddleocr-gb10/releases/tag/v0.2.0)。

```bash
docker pull --platform linux/arm64 ghcr.io/n7tequila/paddleocr-gb10:0.2.0
test -e docker/.env || cp docker/.env.example docker/.env
docker compose --env-file docker/.env -f docker/compose.yaml up -d
bash docker/check-api.sh /path/to/image.png
```

需要安装 NVIDIA Container Toolkit 并让 Docker 容器获得 GPU。直接拉取 GHCR 镜像不需要本地 Wheel 或构建上下文。模型权重不在镜像里，官方工具可在首次启动时下载；默认持久化目录为 Compose 文件旁的 `docker/model-cache`，也可在 `docker/.env` 中把 `PADDLEX_CACHE` 设成自己的绝对目录。默认仅监听 `127.0.0.1:8080`，可用 `PADDLEOCR_PUBLIC_PORT` 更改端口。本地构建为可选流程，届时将 `PADDLEOCR_IMAGE` 改为 `paddleocr-gb10:0.2.0`。

## 国内下载源（默认注释，不影响海外用户）

默认使用 CUDA 基础镜像中预配置的 Ubuntu APT 源和 PyPI 源。国内用户可打开 `docker/build-image.sh`，将这两行前面的 `#` 去掉：

```bash
# export APT_MIRROR="https://mirrors.aliyun.com/ubuntu-ports"
# export PIP_INDEX_URL="https://pypi.tuna.tsinghua.edu.cn/simple"
```

启用后 APT 使用 **ARM64 Ubuntu Ports** 阿里云镜像，pip（包括 `paddlex --install serving`）使用清华镜像。也可以不改文件，仅执行：

```bash
APT_MIRROR=https://mirrors.aliyun.com/ubuntu-ports \
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
bash docker/build-image.sh
```

**注意：** 宿主机 Docker daemon 的 registry mirror 只影响基础镜像拉取，不自动改变容器构建过程中的 APT/pip 源；镜像加速与上面两个选项相互独立。国内镜像是第三方同步源，出于可复现性与安全性考虑默认关闭。

## Spark 上的部署步骤

如需从本地 Wheel 重建镜像，进入实际 Git 仓库目录：

```bash
bash docker/preflight.sh
bash docker/build-image.sh
bash docker/check-image.sh
```

镜像构建使用此前已在宿主机测试成功的 `/data/llm-docker/paddleocr/wheels/paddlepaddle_gpu-*.whl`，**不重新编译 PaddlePaddle**，也不把 345MB Wheel 提交到 GitHub。如果 Wheel 校验值不匹配，构建会拒绝执行。

然后：

```bash
test -e docker/.env || cp docker/.env.example docker/.env
# 使用本地构建镜像时，将 docker/.env 的 PADDLEOCR_IMAGE 改成 paddleocr-gb10:0.2.0
# 可按需将 PADDLEX_CACHE 改为自己的绝对模型缓存目录
# 确认宿主机 8080 端口空闲；如已占用，可设置 PADDLEOCR_PUBLIC_PORT。
docker compose --env-file docker/.env -f docker/compose.yaml config
docker compose --env-file docker/.env -f docker/compose.yaml up -d
docker compose --env-file docker/.env -f docker/compose.yaml logs -f --tail=80
```

在另一个终端发起官方接口测试：

```bash
bash docker/check-api.sh /path/to/image.png
```

输出应包含 `SUCCESS: official API`、`errorCode=0`、`markdown` 和 `prunedResult`。现有 `paddleocr-gb10:0.2.0` 镜像已经通过 Docker GPU 验证；官方 Serving 对真实手写作文返回 HTTP 200，耗时 18.59 秒。新增的依赖约束文件取自该镜像，但整理后的源码尚需重新构建验证。

## 资源和安全

- 不会停止、重启或者修改运行中的 Qwen3.8 Docker。
- 端口默认仅绑定本机 `127.0.0.1:8080`，避免未经授权的外部访问。
- 使用已有模型缓存挂载，不在镜像中打包模型权重。
- GB10 为统一内存架构，不直接设置 12GiB 的硬内存限制；请注意内存指标。
- 正式版仍需测试 Qwen3.8 同时生成时的 OCR、长时间运行和按新约束文件重建镜像。

完整英文流程与故障说明：[docs/docker-v0.2.0.md](docs/docker-v0.2.0.md)。
