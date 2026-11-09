# PaddleOCR GB10 · 官方 REST API Docker 部署（v0.2.0）

本版本只做 **NVIDIA GB10 / ARM64 / CUDA 13.0 环境与 Docker 适配**，不开发自己的 OCR REST API。
容器里直接执行官方命令：

```bash
paddlex --serve --pipeline PaddleOCR-VL-1.6 --device gpu:0 --host 0.0.0.0 --port 8080
```

Docker 映射为宿主机 `http://127.0.0.1:8004/layout-parsing`，请求与响应由官方 PaddleX 提供。今后的 `edu-ocr` 属于独立项目，不并入这个基础镜像。

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

确认你的源码仓库已经在 Spark 上。如果项目路径不同，先进入实际 Git 仓库目录：

```bash
cd /data/llm-docker/paddleocr-gb10
bash docker/preflight.sh
bash docker/build-image.sh
bash docker/check-image.sh
```

镜像构建使用此前已在宿主机测试成功的 `/data/llm-docker/paddleocr/wheels/paddlepaddle_gpu-*.whl`，**不重新编译 PaddlePaddle**，也不把 345MB Wheel 提交到 GitHub。如果 Wheel 校验值不匹配，构建会拒绝执行。

然后：

```bash
cp docker/.env.example docker/.env
# 根据机器真实用户名与模型目录修改 PADDLEX_CACHE（绝对路径）
# 先 Ctrl+C 关闭原先宿主机上的 official-serving.sh start，释放 8004 端口。
docker compose --env-file docker/.env -f docker/compose.yaml config
docker compose --env-file docker/.env -f docker/compose.yaml up -d
docker compose --env-file docker/.env -f docker/compose.yaml logs -f --tail=80
```

在另一个终端发起官方接口测试：

```bash
bash docker/check-api.sh /home/tequila/.paddlex/predict_input/paddleocr_vl_demo.png
```

输出应包含 `SUCCESS: official API`、`errorCode=0`、`markdown` 和 `prunedResult`。现有 `paddleocr-gb10:0.2.0` 镜像已经通过 Docker GPU 验证；官方 Serving 对真实手写作文返回 HTTP 200，耗时 18.59 秒。新增的依赖约束文件取自该镜像，但整理后的源码尚需重新构建验证。

## 资源和安全

- 不会停止、重启或者修改运行中的 Qwen3.8 Docker。
- 端口默认仅绑定本机 `127.0.0.1:8004`，避免未经授权的外部访问。
- 使用已有模型缓存挂载，不在镜像中打包模型权重。
- GB10 为统一内存架构，不直接设置 12GiB 的硬内存限制；请注意内存指标。
- 正式版仍需测试 Qwen3.8 同时生成时的 OCR、长时间运行和按新约束文件重建镜像。

完整英文流程与故障说明：[docs/docker-v0.2.0.md](docs/docker-v0.2.0.md)。
