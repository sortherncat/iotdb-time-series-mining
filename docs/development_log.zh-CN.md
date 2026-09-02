# 开发记录

本文档是 [development_log.md](development_log.md) 的中文展示版本，按任务阶段记录项目实现过程、关键决策、验证结果和当前状态。

## 2026-09-01 - 任务 1.1 Apache IoTDB 部署

目标是在本机部署 Apache IoTDB 2.0.4 单机环境，并使用 CLI 验证服务可用。

环境信息：

```text
操作系统：macOS
IoTDB 版本：Apache IoTDB 2.0.4
默认地址：127.0.0.1
默认端口：6667
默认用户：root
默认密码：root
```

主要步骤：

```bash
java -version
bash scripts/setup_iotdb.sh
bash scripts/start_iotdb.sh
bash scripts/check_iotdb.sh
```

部署脚本将 IoTDB 下载到 `third_party/`，并针对 macOS 上可能出现的 DataNode JVM 栈大小问题，将 `-Xss512k` 调整为 `-Xss1m`。

验证结果：CLI 能够连接 IoTDB，`show databases;` 可正常执行，说明单机服务部署完成。

## 2026-09-01 - 任务 1.2 ETTh1 数据导入

选择 ETTh1 作为多维时间序列数据集。该数据集包含 7 个传感器变量：

```text
HUFL, HULL, MUFL, MULL, LUFL, LULL, OT
```

IoTDB 存储路径设计为：

```text
root.industry.transformer001.high_useful_load
root.industry.transformer001.high_useless_load
root.industry.transformer001.middle_useful_load
root.industry.transformer001.middle_useless_load
root.industry.transformer001.low_useful_load
root.industry.transformer001.low_useless_load
root.industry.transformer001.oil_temperature
```

实现文件：`data_loader.py`。

功能包括：

- 读取 `data/raw/ETTh1.csv`。
- 校验必需字段。
- 将 `date` 转换为毫秒时间戳。
- 创建 IoTDB 数据库 `root.industry`。
- 使用 Session API 的批量写入接口导入数据。
- 默认批大小为 1000 行。

导入命令：

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

验证结果：成功导入 17420 行数据，并通过 `show databases;`、`show timeseries root.industry.**;` 和 `select * ... limit 5;` 验证了数据库、时间序列路径和首批数据。

## 2026-09-01 - 任务 1.3 数据查询

在 `data_loader.py` 中实现时间范围查询，并将 IoTDB 查询结果转换为 `pandas.DataFrame`。

示例命令：

```bash
python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00" \
  --output data/processed/etth1_query_sample.csv
```

输出结果包含：

- IoTDB 毫秒时间戳。
- 转换后的 `datetime` 字段。
- 7 个 ETTh1 传感器变量。

## 2026-09-01 - 任务 2 方法 A：ruptures 变点检测

实现文件：

```text
src/ruptures_segmenter.py
segmentation.py
```

方法 A 使用 `ruptures.Pelt` 对标准化后的 7 维时间序列进行多维联合变点检测。

实现策略：

```text
粗粒度搜索：使用 jump 加速全局变点检测
细粒度搜索：在粗变点附近局部重算代价，寻找更精确边界
最小分段长度：通过 min-size 避免过短片段
```

运行命令：

```bash
python segmentation.py \
  --method ruptures \
  --input data/raw/ETTh1.csv \
  --model rbf \
  --penalty 10 \
  --min-size 48 \
  --jump 10 \
  --refine \
  --refine-radius 20
```

输出文件：

```text
outputs/segmentation/method_a_ruptures.json
```

## 2026-09-01 - 任务 2 方法 B：滑动窗口统计距离

实现文件：

```text
src/window_stat_segmenter.py
segmentation.py
```

核心思想是在候选点左右各取一个窗口，比较左右窗口的均值向量和协方差矩阵：

```text
S(t) = ||mu_L - mu_R||_2 + alpha * ||Sigma_L - Sigma_R||_F
```

然后在变化分数曲线上寻找局部峰值，并通过分位数阈值和最小分段长度约束筛选变点。

运行命令：

```bash
python segmentation.py \
  --method window_stat \
  --input data/raw/ETTh1.csv \
  --window-size 48 \
  --alpha 0.5 \
  --threshold-quantile 0.95 \
  --min-size 48
```

输出文件：

```text
outputs/segmentation/method_b_window_stat.json
```

两个分段方法的结果独立保存，便于后续比较。

## 2026-09-01 - 任务 3 分段特征提取

实现文件：

```text
src/feature_extractor.py
feature_extraction.py
```

对每个分段提取固定长度特征向量，覆盖以下类别：

```text
统计特征：均值、标准差、偏度、峰度、分位数
时域形状：过零率、RMS、峰值因子、波形因子
相关性特征：各维度相关系数矩阵上三角元素
趋势特征：线性拟合斜率、差分均值
```

运行命令：

```bash
python feature_extraction.py \
  --input data/raw/ETTh1.csv \
  --scaler standard
```

输出文件：

```text
outputs/features/ruptures_pelt_features_raw.csv
outputs/features/ruptures_pelt_features_scaled.csv
outputs/features/ruptures_pelt_feature_metadata.json
outputs/features/window_stat_distance_features_raw.csv
outputs/features/window_stat_distance_features_scaled.csv
outputs/features/window_stat_distance_feature_metadata.json
```

每个分段得到 112 个特征，标准化后的特征矩阵用于后续聚类。

## 2026-09-01 - 任务 4 聚类与工况识别

实现文件：

```text
src/clusterer.py
clustering.py
```

当前实现对比两种聚类算法：

```text
K-Means
Gaussian Mixture Model
```

使用以下指标选择较优聚类数：

```text
Silhouette Score
Calinski-Harabasz Index
```

运行命令：

```bash
python clustering.py \
  --input data/raw/ETTh1.csv \
  --min-k 2 \
  --max-k 8
```

输出文件：

```text
outputs/clustering/algorithm_comparison.csv
outputs/clustering/<feature_method>/<algorithm>/segment_conditions.csv
outputs/clustering/<feature_method>/<algorithm>/condition_summary.csv
outputs/clustering/<feature_method>/<algorithm>/clustering_metrics.json
```

每个聚类被映射为 `OP_001`、`OP_002` 等工况 ID，并输出每个工况的分段数量、总持续时长和平均持续时长。

## 2026-09-01 - 任务 5 交互式可视化展示

实现文件：

```text
frontend/
scripts/prepare_frontend_data.py
```

技术路线：

```text
React + TypeScript + Vite + ECharts
```

前端提供两种展示风格：

```text
Light：浅色、简洁、展示型风格
Dark：深色、高对比、仪表盘风格
```

可视化内容：

- 原始多通道时序图，并用竖虚线标注变点。
- 聚类结果二维散点图，并显示聚类中心。
- 各工况代表性片段叠加对比。
- 工况时间线，用色带展示工况切换。
- 页面底部添加特征量含义说明。

交互功能：

- 切换 Light/Dark 主题。
- 切换分段方法。
- 切换聚类算法。
- 选择多通道时序图中的可见传感器。
- 选择代表片段展示变量。

近期修正：

- 将全局控制栏拆分到对应的展示页面中。
- 修复多通道时序图横轴时间标签过密的问题。
- 代表片段数据补齐全部 7 个传感器变量。
- 对 ETTh1 中负载通道连续为 0 的片段进行了数据核验，确认该现象来自原始 CSV。

启动命令：

```bash
python scripts/prepare_frontend_data.py

cd frontend
npm install
npm run dev -- --port 5173
```

访问地址：

```text
http://127.0.0.1:5173/
```

## 当前状态

- 已完成任务 1：环境搭建、数据导入、数据查询。
- 已完成任务 2：两种高维时间序列分段方法。
- 已完成任务 3：分段特征提取与标准化。
- 已完成任务 4：聚类与工况识别。
- 已完成任务 5：交互式可视化展示。
- 已完成 Docker Compose 容器化部署方案，并将镜像推送到阿里云 ACR。
- 待完成：实验报告整理与最终结果分析。

## 2026-09-02 - Docker Compose 容器化与 ACR 镜像加速

### 目标

为了解决 Ubuntu 环境中 Java、IoTDB、Python 依赖、Node 依赖安装较慢且容易受网络影响的问题，新增 Docker Compose 部署方案，并将关键镜像推送到阿里云容器镜像服务 ACR。

### 新增文件

```text
docker-compose.yml
Dockerfile.iotdb
Dockerfile.app
frontend/Dockerfile
docker/iotdb-entrypoint.sh
scripts/wait_for_iotdb.py
scripts/run_pipeline.sh
docs/docker_usage.zh-CN.md
.dockerignore
```

### 服务划分

Docker Compose 中包含三个服务：

```text
iotdb：Apache IoTDB 2.0.4 单机服务
app：Python 数据处理与算法运行环境
frontend：React/Vite 可视化前端
```

### 镜像加速策略

为了避免普通用户在部署时重复从 Docker Hub、Debian 源、Apache Archive、PyPI、npm registry 下载依赖，将三个镜像推送到阿里云 ACR：

```text
iotdb:
crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:iotdb-2.0.4-amd64

app:
crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:app-py3.11-amd64

frontend:
crpi-um7hjt0z3pn8hy53.cn-shanghai.personal.cr.aliyuncs.com/scattt/scattt1:frontend-node22-amd64
```

其中：

- `iotdb` 镜像内置 Apache IoTDB 2.0.4。
- `app` 镜像内置 Python 依赖和 ETTh1 数据集。
- `frontend` 镜像内置 Node 环境和 npm 依赖。

### ETTh1 数据集加速

`app` 镜像内置 ETTh1 数据集：

```text
/opt/datasets/ETTh1.csv
```

`scripts/run_pipeline.sh` 中增加了优先复制内置数据的逻辑：

```text
如果 data/raw/ETTh1.csv 不存在：
  1. 优先从 /opt/datasets/ETTh1.csv 复制
  2. 如果镜像内置数据不存在，再从 GitHub 下载
```

这样可以避免每个用户首次运行时都从 GitHub 下载 ETTh1。

### 普通用户启动方式

普通部署不需要 `--build`，推荐使用：

```bash
docker compose pull
docker compose up -d
docker compose exec app bash scripts/run_pipeline.sh
```

然后访问：

```text
http://localhost:5173/
```

### 关于 --build 的说明

文档中特别说明普通用户不要使用：

```bash
docker compose up -d --build
```

因为 `docker-compose.yml` 中保留了 `build` 配置，如果使用 `--build`，Docker Compose 会强制重新构建镜像，从而重新拉取基础镜像、安装 apt 包、下载 Python/npm 依赖和 IoTDB 包。

只有修改 Dockerfile 或需要重新制作镜像时，才使用 `--build`。

### ACR 推送处理

推送 IoTDB 镜像时，阿里云 ACR 对 Docker BuildKit 默认生成的 provenance/attestation 元数据不兼容，出现过：

```text
unknown manifest class for application/vnd.oci.empty.v1+json
```

最终使用以下方式关闭 provenance 后成功推送：

```bash
docker buildx build --provenance=false ...
```

三个镜像均已推送并通过远端 manifest 检查。

### 架构修正

首次推送的镜像是在 Apple Silicon / arm64 Docker 环境中构建的。Ubuntu x86_64 宿主机拉取后会出现：

```text
exec /usr/bin/bash: exec format error
```

该错误的直接原因是镜像架构与宿主机架构不一致。后续在 `docker-compose.yml` 中为所有服务固定 `platform: linux/amd64`，并将默认镜像 tag 调整为 `linux/amd64`：

```text
iotdb-2.0.4-amd64
app-py3.11-amd64
frontend-node22-amd64
```

已使用 `docker buildx build --platform linux/amd64 --provenance=false` 重新构建并推送。远端 manifest 检查确认三个 `*-amd64` tag 均为 `architecture: amd64`、`os: linux`。

### IoTDB 时间精度修正

容器内 pipeline 出现过导入成功但样例查询返回 0 行的问题：

```text
Finished importing 17420 rows to root.industry.transformer001
Queried 0 rows from root.industry.transformer001
```

根因是 IoTDB 服务端时间精度与代码中的毫秒时间戳假设不一致。ETTh1 的原始时间从 `2016-07-01 00:00:00` 开始，导入和查询代码都按毫秒时间戳处理；如果 IoTDB 服务端按秒级精度解释，后续按毫秒范围查询就会落空。

已在 `Dockerfile.iotdb` 中向 `conf/iotdb-system.properties` 追加：

```text
timestamp_precision=ms
```

如果服务器已经生成过旧的 IoTDB volume，需要执行 `docker compose down -v` 后重新拉取镜像、启动并导入。

### pandas 时间戳单位修正

Ubuntu 容器中继续出现导入后查询为空的问题。进一步只读排查发现，IoTDB 中实际写入的首个时间为：

```text
1467331200
```

而 ETTh1 的 `2016-07-01 00:00:00` 正确毫秒时间戳应为：

```text
1467331200000
```

继续检查容器内 pandas 结果：

```text
dtype: datetime64[us]
astype int64: 1467331200000000
current code result: 1467331200
expected ms: 1467331200000
```

根因是旧实现默认认为 `datetimes.astype("int64")` 一定返回纳秒，因此固定除以 `1_000_000`。但 pandas 3.0.5 在容器中返回的是微秒级 `datetime64[us]`，导致结果被换算成秒。

已将时间戳转换改为显式转毫秒：

```python
pd.to_datetime(datetimes).astype("datetime64[ms]").astype("int64")
```

这样无论 pandas 底层是 `datetime64[ns]` 还是 `datetime64[us]`，导入和查询都会统一使用毫秒时间戳。

### 分支

容器化相关改动未合并到 `main`，而是单独提交到 GitHub 的 `docker` 分支，便于后续通过 Pull Request 审查和合并。
