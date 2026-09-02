# Docker Compose 使用说明

本文档说明如何在 Ubuntu 或其他支持 Docker 的系统上，用容器运行本项目。

## 为什么使用容器

本项目涉及多个运行环境：

```text
Apache IoTDB
Python 数据处理脚本
React/Vite 前端展示页面
```

使用 Docker Compose 可以统一 Java、Python、Node、IoTDB 等依赖，减少不同系统之间的环境差异。

## 前置条件

需要先安装：

```text
Docker
Docker Compose
```

在 Ubuntu 上可验证：

```bash
docker --version
docker compose version
```

## 镜像架构说明

默认镜像面向常见 Ubuntu 服务器和 PC：

```text
linux/amd64
```

如果宿主机是 `x86_64`，必须使用 `*-amd64` 标签。否则如果误拉了在 Apple Silicon 机器上构建的 `arm64` 镜像，容器启动时会出现：

```text
exec /usr/bin/bash: exec format error
```

可以用下面命令查看宿主机架构：

```bash
uname -m
```

常见对应关系：

```text
x86_64  -> linux/amd64
aarch64 -> linux/arm64
arm64   -> linux/arm64
```

## 启动服务

推荐启动方式是在项目根目录先拉取已经推送到阿里云 ACR 的 IoTDB 镜像，再启动服务：

```bash
docker compose pull
docker compose up -d
```

不要在普通启动时使用：

```bash
docker compose up -d --build
```

因为 `docker-compose.yml` 中的 `iotdb` 服务同时保留了 `image` 和 `build` 配置：

```yaml
iotdb:
  image: crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64
  build:
    context: .
    dockerfile: Dockerfile.iotdb
```

当命令带上 `--build` 时，Docker Compose 会强制执行 `Dockerfile.iotdb`，于是会重新从 Docker Hub 拉取 Java 基础镜像，并重新下载 Apache IoTDB 包。这样就不会走已经上传好的阿里云镜像。

默认镜像地址均为 `linux/amd64`：

```text
iotdb:    crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64
app:      crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:app-py3.11-amd64
frontend: crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:frontend-node22-amd64
```

`docker-compose.yml` 也已经为三个服务固定：

```yaml
platform: linux/amd64
```

如果运行环境在阿里云专有网络 VPC 内，可以切换为 VPC 镜像地址：

```bash
IOTDB_IMAGE=crpi-um7hjt0z3pn8hy53-vpc.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64 \
docker compose up -d
```

这会启动三个服务：

```text
iotdb: Apache IoTDB 2.0.4
app: Python 数据处理环境
frontend: React/Vite 前端页面
```

## 什么时候才需要 --build

只有在以下情况才需要使用 `--build`：

```text
1. 修改了 Dockerfile.iotdb，希望重新构建 IoTDB 镜像
2. 修改了 Dockerfile.app，希望重新构建 Python 环境
3. 修改了 frontend/Dockerfile，希望重新构建前端环境
```

如果只是运行项目、导入数据、分段、聚类或打开页面，不需要 `--build`。

开发者本地重新构建所有镜像：

```bash
docker compose up -d --build
```

但这会重新构建 IoTDB 镜像，速度较慢。

## 一键运行完整流程

服务启动后，执行：

```bash
docker compose exec app bash scripts/run_pipeline.sh
```

如果曾经用旧 IoTDB 容器导入过数据，建议先清理旧的 IoTDB volume 再重新启动：

```bash
docker compose down -v
docker compose pull
docker compose up -d
docker compose exec app bash scripts/run_pipeline.sh
```

原因是旧容器可能使用了非毫秒时间精度，导致导入成功但按 `2016-07-01` 这类真实时间范围查询时返回 0 行。当前 IoTDB 镜像已经固定：

```text
timestamp_precision=ms
```

该脚本会自动完成：

```text
1. 下载 ETTh1 数据集
2. 等待 IoTDB 启动
3. 清空旧的 root.industry 数据库
4. 使用毫秒级时间戳重新导入 ETTh1
5. 查询样例数据
6. 执行两种分段方法
7. 提取分段特征
8. 执行 K-Means 和 GMM 聚类
9. 生成前端可视化数据
```

`app` 镜像已经内置一份 ETTh1 数据集：

```text
/opt/datasets/ETTh1.csv
```

因此运行 `scripts/run_pipeline.sh` 时，会优先从镜像内复制数据到：

```text
data/raw/ETTh1.csv
```

只有当镜像内置数据不存在时，脚本才会从 GitHub 下载。这样可以避免每个用户重复慢速下载 ETTh1。

## 打开前端页面

浏览器访问：

```text
http://localhost:5173/
```

如果页面已经打开但数据没有更新，可以强制刷新浏览器。

## 常用命令

构建并推送 IoTDB 镜像到公网 ACR。注意：为了兼容阿里云 ACR，需要关闭 Docker BuildKit 的 provenance/attestation 元数据：

```bash
docker buildx build --platform linux/amd64 --provenance=false \
  -f Dockerfile.iotdb \
  -t crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64 \
  --push .
```

如果需要在阿里云 VPC 内使用专有网络地址，可以额外打 tag 并推送：

```bash
docker tag \
  crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64 \
  crpi-um7hjt0z3pn8hy53-vpc.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64

docker login crpi-um7hjt0z3pn8hy53-vpc.cn-shanghai.personal.cr.aliyuncs.com

docker push crpi-um7hjt0z3pn8hy53-vpc.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64
```

查看服务状态：

```bash
docker compose ps
```

查看 IoTDB 日志：

```bash
docker compose logs -f iotdb
```

进入 Python 容器：

```bash
docker compose exec app bash
```

重新运行数据导入：

```bash
docker compose exec app python data_loader.py import \
  --csv data/raw/ETTh1.csv \
  --host iotdb \
  --port 6667 \
  --reset-database
```

停止服务：

```bash
docker compose down
```

停止服务并删除 IoTDB 持久化数据：

```bash
docker compose down -v
```

构建并推送 Python app 镜像：

```bash
docker buildx build --platform linux/amd64 --provenance=false \
  -f Dockerfile.app \
  -t crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:app-py3.11-amd64 \
  --push .
```

构建并推送 frontend 镜像：

```bash
docker buildx build --platform linux/amd64 --provenance=false \
  -f frontend/Dockerfile \
  -t crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:frontend-node22-amd64 \
  --push frontend
```

## 注意事项

- `data/raw/`、`data/processed/`、`outputs/` 会通过挂载保存在项目目录中。
- ETTh1 已预置在 `app` 镜像中，首次运行 pipeline 会复制到 `data/raw/ETTh1.csv`。
- IoTDB 的内部数据和日志使用 Docker volume 持久化。
- 如果重新导入数据，建议使用 `--reset-database`，避免旧时间戳数据残留。
- 如果 `5173` 端口被占用，可以修改 `docker-compose.yml` 中 `frontend` 的端口映射。
