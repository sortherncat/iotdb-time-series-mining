# IoTDB 高维时间序列工况识别

本仓库用于课程设计项目：**高维时间序列自动分段、特征提取与工况聚类识别**。

## 文档索引

- 英文 README：[README.md](README.md)
- 中文 README：[README.zh-CN.md](README.zh-CN.md)
- 开发记录英文版：[docs/development_log.md](docs/development_log.md)
- 开发记录中文版：[docs/development_log.zh-CN.md](docs/development_log.zh-CN.md)
- 任务 2-4 技术文档：[docs/technical_steps_2_4.zh-CN.md](docs/technical_steps_2_4.zh-CN.md)

项目构建了一条完整的数据挖掘流程：

```text
数据集 -> Apache IoTDB -> pandas.DataFrame -> 变点检测分段 -> 分段特征提取 -> 聚类 -> 工况识别 -> 可视化展示
```

## 项目目标

- 部署 Apache IoTDB 2.x 单机环境。
- 使用 Python Session API 将 ETTh1 多维时间序列批量写入 IoTDB。
- 按指定时间范围查询 IoTDB 数据，并转换为 `pandas.DataFrame`。
- 实现两种高维联合变点检测方法。
- 对每个分段提取固定长度特征向量。
- 使用两种聚类算法对分段进行工况识别。
- 输出 `OP_001`、`OP_002` 等工况编号、起止时间和持续时长统计。
- 制作交互式前端，展示时序、分段、聚类、代表片段和工况时间线。

## 数据集

本项目使用 **ETTh1** 数据集，来自 ETT Dataset。

字段说明：

```text
date: 时间戳
HUFL: high useful load
HULL: high useless load
MUFL: middle useful load
MULL: middle useless load
LUFL: low useful load
LULL: low useless load
OT: oil temperature
```

下载命令：

```bash
mkdir -p data/raw
curl -L -o data/raw/ETTh1.csv https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv
```

如果无法访问 GitHub raw 文件，可以手动从下面仓库下载 `ETTh1.csv`，并放到 `data/raw/ETTh1.csv`：

```text
https://github.com/zhouhaoyi/ETDataset/tree/main/ETT-small
```

## 项目结构

```text
iotdb-time-series-mining/
├── data_loader.py          # IoTDB 数据导入、查询与 DataFrame 转换
├── segmentation.py         # 分段方法统一入口
├── feature_extraction.py   # 分段特征提取入口
├── clustering.py           # 聚类与工况识别入口
├── src/                    # 可复用算法模块
├── scripts/                # IoTDB 和前端数据准备脚本
├── frontend/               # React/Vite 交互式可视化前端
├── docs/                   # 开发记录
├── design/                 # 可视化设计文档
├── requirements.txt        # Python 依赖
└── README.md
```

## 部署与运行说明

本仓库不提交大型运行时文件，包括原始数据、IoTDB 二进制包、Python 虚拟环境、Node 依赖和前端构建产物。拉取代码后，按下面步骤复现环境。

### 1. 克隆仓库

```bash
git clone https://github.com/sortherncat/iotdb-time-series-mining.git
cd iotdb-time-series-mining
```

### 2. 安装 Python 依赖

建议使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 下载数据集

```bash
mkdir -p data/raw
curl -L -o data/raw/ETTh1.csv https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv
```

### 4. 部署并启动 Apache IoTDB

```bash
bash scripts/setup_iotdb.sh
bash scripts/start_iotdb.sh
bash scripts/check_iotdb.sh
```

默认连接信息：

```text
host: 127.0.0.1
port: 6667
user: root
password: root
```

`setup_iotdb.sh` 会将 Apache IoTDB 2.0.4 下载到 `third_party/`，并在 macOS 上自动处理 DataNode JVM 栈大小问题。

### 5. 导入 ETTh1 到 IoTDB

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

如果之前使用旧代码导入过数据，查询结果出现 `1970-01-17` 这类异常时间，说明 IoTDB 中已有秒级时间戳误写数据。此时需要清空目标数据库并重新导入：

```bash
python data_loader.py import \
  --csv data/raw/ETTh1.csv \
  --batch-size 1000 \
  --reset-database
```

`--reset-database` 会先删除目标数据库 `root.industry`，再按毫秒级时间戳重新写入 ETTh1。

IoTDB 存储路径：

```text
root.industry.transformer001.high_useful_load
root.industry.transformer001.high_useless_load
root.industry.transformer001.middle_useful_load
root.industry.transformer001.middle_useless_load
root.industry.transformer001.low_useful_load
root.industry.transformer001.low_useless_load
root.industry.transformer001.oil_temperature
```

### 6. 查询数据并导出 DataFrame

```bash
python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00" \
  --output data/processed/etth1_query_sample.csv
```

### 7. 执行两种分段方法

方法 A：基于 `ruptures` 的 PELT 多维联合变点检测。

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

方法 B：滑动窗口 + 均值/协方差统计距离。

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
outputs/segmentation/method_a_ruptures.json
outputs/segmentation/method_b_window_stat.json
```

### 8. 提取分段特征

```bash
python feature_extraction.py \
  --input data/raw/ETTh1.csv \
  --scaler standard
```

特征覆盖：

```text
统计特征：均值、标准差、偏度、峰度、分位数
时域形状：过零率、RMS、峰值因子、波形因子
相关性特征：维度间相关系数矩阵上三角元素
趋势特征：线性拟合斜率、差分均值
```

### 9. 聚类与工况识别

```bash
python clustering.py \
  --input data/raw/ETTh1.csv \
  --min-k 2 \
  --max-k 8
```

当前实现对比：

```text
K-Means
Gaussian Mixture Model
```

评价指标：

```text
Silhouette Score
Calinski-Harabasz Index
```

输出文件：

```text
outputs/clustering/algorithm_comparison.csv
outputs/clustering/<feature_method>/<algorithm>/segment_conditions.csv
outputs/clustering/<feature_method>/<algorithm>/condition_summary.csv
outputs/clustering/<feature_method>/<algorithm>/clustering_metrics.json
```

### 10. 启动交互式可视化页面

先根据 Python 输出生成前端数据：

```bash
python scripts/prepare_frontend_data.py
```

启动前端：

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

浏览器打开：

```text
http://127.0.0.1:5173/
```

前端包含：

```text
原始多通道时序图 + 分段边界
聚类结果二维散点图 + 聚类中心
各工况代表性时序片段对比
工况时间线
特征量说明
```

### 11. 停止 IoTDB

```bash
bash scripts/stop_iotdb.sh
```

## 当前完成状态

- [x] 建立公开 GitHub 仓库
- [x] 上传初始 README
- [x] 选择并下载 ETTh1 数据集
- [x] 部署 Apache IoTDB
- [x] 实现数据导入
- [x] 验证 IoTDB 导入结果
- [x] 实现时间范围查询和 DataFrame 转换
- [x] 实现分段方法 A：ruptures
- [x] 实现分段方法 B：滑动窗口统计距离
- [x] 实现分段特征提取
- [x] 实现聚类与工况识别
- [x] 实现交互式可视化展示
- [ ] 完成实验报告

## 输出结果

主要输出包括：

```text
分段边界列表
分段特征矩阵
标准化特征矩阵
聚类算法对比结果
每个分段的工况 ID
每类工况的起止时间和持续时长统计
交互式可视化页面数据
```
