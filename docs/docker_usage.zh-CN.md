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

## 启动服务

在项目根目录执行：

```bash
docker compose up -d --build
```

这会启动三个服务：

```text
iotdb: Apache IoTDB 2.0.4
app: Python 数据处理环境
frontend: React/Vite 前端页面
```

## 一键运行完整流程

服务启动后，执行：

```bash
docker compose exec app bash scripts/run_pipeline.sh
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

## 打开前端页面

浏览器访问：

```text
http://localhost:5173/
```

如果页面已经打开但数据没有更新，可以强制刷新浏览器。

## 常用命令

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

## 注意事项

- `data/raw/`、`data/processed/`、`outputs/` 会通过挂载保存在项目目录中。
- IoTDB 的内部数据和日志使用 Docker volume 持久化。
- 如果重新导入数据，建议使用 `--reset-database`，避免旧时间戳数据残留。
- 如果 `5173` 端口被占用，可以修改 `docker-compose.yml` 中 `frontend` 的端口映射。
