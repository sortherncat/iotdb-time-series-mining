# 任务 2-4 技术文档：分段、特征提取与工况聚类

本文档从数学角度和代码角度说明本项目在任务 2、任务 3、任务 4 中完成的核心工作。三部分之间的关系如下：

```text
高维时间序列 X
  -> 任务 2：自动分段，得到 segments = [(start_1, end_1), ...]
  -> 任务 3：对每个分段提取特征，得到特征矩阵 F
  -> 任务 4：对分段特征聚类，得到工况 ID 与持续时长统计
```

## 数据表示

ETTh1 数据集中，每个时间点有 7 个传感器变量：

```text
HUFL, HULL, MUFL, MULL, LUFL, LULL, OT
```

在项目代码中统一映射为：

```text
high_useful_load
high_useless_load
middle_useful_load
middle_useless_load
low_useful_load
low_useless_load
oil_temperature
```

从数学角度看，高维时间序列可表示为：

```text
X = {x_1, x_2, ..., x_n}
x_t in R^d
```

其中 `n` 是时间点数量，`d=7` 是传感器维度数。

代码中，数据首先通过 `normalize_etth1_columns()` 统一字段名，再由 `prepare_feature_matrix()` 提取 7 个传感器列并标准化：

```text
z_{t,j} = (x_{t,j} - mean_j) / std_j
```

这样可以避免不同量纲的变量对距离、代价函数和聚类结果产生不公平影响。

对应代码：

```text
src/ruptures_segmenter.py
- normalize_etth1_columns()
- prepare_feature_matrix()
```

## 任务 2：高维时间序列自动分段

任务 2 的目标是在连续多维时间序列中自动检测工况切换点，也就是变点。输出为分段边界：

```text
[(start_1, end_1), (start_2, end_2), ..., (start_k, end_k)]
```

本项目实现了两种方法：

```text
方法 A：基于 ruptures 的 PELT 多维联合变点检测
方法 B：滑动窗口 + 统计距离
```

### 方法 A 数学角度：ruptures PELT 变点检测

设变点集合为：

```text
C = {c_1, c_2, ..., c_K}
```

它将原始序列划分为：

```text
[0, c_1), [c_1, c_2), ..., [c_K, n)
```

变点检测的核心思想是：寻找一组边界，使每个分段内部尽可能稳定，而分段之间差异尽可能明显。

PELT 方法可以写成如下优化问题：

```text
min over C:
  sum_{i=0}^{K} Cost(X_{c_i:c_{i+1}}) + beta * K
```

其中：

- `Cost()` 表示分段内部的代价。
- `beta` 是惩罚项，对应代码中的 `penalty`。
- `K` 是变点数量。
- 惩罚项越大，变点越少；惩罚项越小，变点越多。

本项目默认使用 `rbf` 代价模型。它适合检测非线性分布变化，不只依赖均值变化，因此更适合多维工况切换检测。

为了提高速度并保留边界精度，项目使用两阶段策略：

```text
第一阶段：粗粒度搜索
第二阶段：局部细粒度修正
```

粗粒度搜索通过 `jump` 参数跳步扫描，降低计算量。得到粗变点后，在每个粗变点附近半径 `refine_radius` 的局部范围内重新搜索。

对某个粗变点 `c`，局部候选点为：

```text
t in [c - r, c + r]
```

其中 `r` 是 `refine_radius`。代码会选择使左右两段总代价最小的点：

```text
t* = argmin_t Cost(X_{left:t}) + Cost(X_{t:right})
```

这样既保留了粗搜索速度，也提升了变点位置精度。

### 方法 A 代码角度

入口命令：

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

主要代码文件：

```text
segmentation.py
src/ruptures_segmenter.py
```

核心流程：

```text
1. load_dataframe() 读取 CSV
2. segment_with_ruptures() 创建 RupturesSegmenter
3. prepare_feature_matrix() 统一字段名并标准化 7 维数据
4. rpt.Pelt(model, min_size, jump).fit(features)
5. algorithm.predict(pen=penalty) 得到粗变点
6. refine_change_points_near_coarse_boundaries() 进行局部细粒度搜索
7. segments_from_change_points() 转换为分段边界
8. save_segments() 保存 JSON
```

输出文件：

```text
outputs/segmentation/method_a_ruptures.json
```

输出内容包括：

```text
method
model
penalty
min_size
jump
refine
refine_radius
coarse_change_points
change_points
segments
```

### 方法 B 数学角度：滑动窗口 + 统计距离

方法 B 的核心思想是：对每一个候选时间点 `t`，取左窗口和右窗口，比较两边的统计分布是否发生明显变化。

左窗口：

```text
L_t = {x_{t-w}, ..., x_{t-1}}
```

右窗口：

```text
R_t = {x_t, ..., x_{t+w-1}}
```

其中 `w` 是窗口长度，项目默认使用 48，表示约 48 小时。

首先比较左右窗口均值向量：

```text
D_mu(t) = ||mu_L - mu_R||_2
```

它用于检测整体水平变化，例如负载整体上升或下降。

然后比较左右窗口协方差矩阵：

```text
D_sigma(t) = ||Sigma_L - Sigma_R||_F
```

它用于检测变量关系变化，例如不同负载通道之间的相关结构变化。

最终变化分数为：

```text
S(t) = D_mu(t) + alpha * D_sigma(t)
```

其中 `alpha` 控制协方差差异的权重。项目默认 `alpha=0.5`。

计算完整条变化分数曲线后，项目寻找局部峰值：

```text
S(t) > S(t-1)
S(t) > S(t+1)
S(t) >= threshold
```

阈值使用分位数策略：

```text
threshold = Q_{0.95}(S)
```

最后加入最小分段长度约束 `min_size`。如果两个候选变点太近，则优先保留变化分数更高的候选点。

### 方法 B 代码角度

入口命令：

```bash
python segmentation.py \
  --method window_stat \
  --input data/raw/ETTh1.csv \
  --window-size 48 \
  --alpha 0.5 \
  --threshold-quantile 0.95 \
  --min-size 48
```

主要代码文件：

```text
segmentation.py
src/window_stat_segmenter.py
```

核心流程：

```text
1. WindowStatSegmenter.segment() 接收 DataFrame
2. prepare_feature_matrix() 对 7 维数据标准化
3. compute_window_stat_scores() 计算每个候选点的变化分数 S(t)
4. np.nanquantile(scores, threshold_quantile) 得到阈值
5. find_local_peak_change_points() 找局部峰值
6. filter_change_points_by_min_size() 加最小分段长度约束
7. segments_from_change_points() 转为 [(start, end), ...]
8. save_segments() 保存 JSON
```

输出文件：

```text
outputs/segmentation/method_b_window_stat.json
```

输出内容包括：

```text
method
window_size
alpha
threshold_quantile
threshold
min_size
change_points
segments
scores
```

### 任务 2 小结

方法 A 的优势是成熟、全局优化能力强，适合写成标准变点检测方案。方法 B 的优势是直观、可解释，能明确说明变点来自均值变化还是协方差变化。

两种方法都对 7 维序列整体建模，而不是逐维检测后简单合并，因此符合高维联合变点检测要求。

## 任务 3：分段特征提取

任务 3 的目标是将每个长短不一的时间序列分段转换为固定长度特征向量。这样后续聚类算法才能处理。

设第 `i` 个分段为：

```text
X_i = X[start_i:end_i]
```

特征提取的目标是构造：

```text
f_i = phi(X_i)
```

其中 `f_i` 是固定长度向量，`phi()` 是特征提取函数。

所有分段的特征向量组成特征矩阵：

```text
F = [f_1; f_2; ...; f_m]
```

其中 `m` 是分段数量。

### 数学角度

本项目提取了四类特征。

第一类是统计特征。对每个传感器维度 `j`，计算：

```text
mean_j
std_j
skew_j
kurtosis_j
q25_j
q50_j
q75_j
```

这些特征描述分段内的整体水平、波动程度、分布偏斜程度、尾部厚度和分位数位置。

第二类是时域形状特征，包括：

```text
RMS = sqrt(mean(x^2))
crest_factor = max(|x|) / RMS
waveform_factor = RMS / mean(|x|)
zero_crossing_rate
```

其中 RMS 反映能量强度，峰值因子反映尖峰程度，波形因子反映波形形态，过零率反映围绕均值上下变化的频繁程度。

第三类是相关性特征。对一个分段内的 7 维变量计算相关系数矩阵：

```text
Corr in R^{7 x 7}
```

由于相关系数矩阵是对称矩阵，只取上三角元素：

```text
corr_{i,j}, i < j
```

7 个变量一共有：

```text
7 * 6 / 2 = 21
```

个相关性特征。

第四类是趋势特征。对每个传感器维度做一阶线性拟合：

```text
x_t = a * t + b
```

其中斜率 `a` 表示该分段内变量整体上升或下降趋势。同时计算一阶差分均值：

```text
mean(diff(x))
```

用于衡量平均变化方向和变化速度。

每个传感器提取 13 个单变量特征：

```text
mean, std, skew, kurtosis, q25, q50, q75,
rms, crest_factor, waveform_factor, zero_crossing_rate,
slope, diff_mean
```

7 个传感器得到：

```text
7 * 13 = 91
```

再加 21 个相关性特征，总特征数为：

```text
91 + 21 = 112
```

最后对特征矩阵标准化：

```text
z = (x - mean) / std
```

这样可以避免某些数值范围大的特征在聚类中占据主导。

### 代码角度

入口命令：

```bash
python feature_extraction.py \
  --input data/raw/ETTh1.csv \
  --scaler standard
```

主要代码文件：

```text
feature_extraction.py
src/feature_extractor.py
```

核心流程：

```text
1. load_time_series() 读取并规范化 ETTh1 字段
2. load_segments() 读取分段 JSON
3. extract_segment_features() 遍历每个分段
4. extract_features_for_segment() 提取单个分段特征
5. extract_channel_features() 提取单变量统计、时域、趋势特征
6. extract_correlation_features() 提取维度间相关性特征
7. scale_feature_matrix() 标准化或 MinMax 归一化
8. save_feature_result() 保存原始特征、标准化特征和元数据
```

关键函数：

```text
extract_channel_features()
zero_crossing_rate()
extract_correlation_features()
scale_feature_matrix()
extract_segment_features()
```

默认会分别处理方法 A 和方法 B 的分段结果：

```text
outputs/segmentation/method_a_ruptures.json
outputs/segmentation/method_b_window_stat.json
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

其中：

- `*_features_raw.csv` 保存未标准化特征。
- `*_features_scaled.csv` 保存标准化后的聚类输入。
- `*_feature_metadata.json` 保存特征名、特征数量、分段数量和标准化方式。

## 任务 4：聚类与工况识别

任务 4 的目标是对分段特征矩阵进行无监督聚类，并将每个聚类解释为一种工况。

输入是任务 3 得到的标准化特征矩阵：

```text
F in R^{m x p}
```

其中：

- `m` 是分段数量。
- `p=112` 是特征维度。

输出包括：

```text
每个分段的工况 ID
每个工况的起止时间
每个工况的持续时长统计
聚类算法和 K 值评价结果
```

### 数学角度：K-Means

K-Means 假设每个样本属于距离最近的聚类中心。目标函数为：

```text
min sum_{i=1}^{m} ||f_i - mu_{z_i}||_2^2
```

其中：

- `f_i` 是第 `i` 个分段的特征向量。
- `z_i` 是分段所属的簇编号。
- `mu_k` 是第 `k` 个簇的中心。

K-Means 适合发现紧凑、近似球形的簇。它的优点是直观、速度快、结果容易解释。

### 数学角度：GMM

GMM 即高斯混合模型，假设数据来自多个高斯分布的混合：

```text
p(f_i) = sum_{k=1}^{K} pi_k * N(f_i | mu_k, Sigma_k)
```

其中：

- `pi_k` 是第 `k` 个高斯分布的混合权重。
- `mu_k` 是均值向量。
- `Sigma_k` 是协方差矩阵。

GMM 相比 K-Means 更灵活，因为它允许不同簇具有不同形状和协方差结构。项目使用 `GaussianMixture` 的 `full` 协方差类型。

### 数学角度：K 值选择

项目在 `min_k` 到 `max_k` 之间遍历候选聚类数，并计算两个指标。

轮廓系数 Silhouette Score：

```text
s(i) = (b(i) - a(i)) / max(a(i), b(i))
```

其中：

- `a(i)` 是样本到同簇其他样本的平均距离。
- `b(i)` 是样本到最近其他簇样本的平均距离。

轮廓系数越高，说明簇内越紧密、簇间越分离。

Calinski-Harabasz 指数衡量簇间离散程度与簇内离散程度之比：

```text
CH = between-cluster dispersion / within-cluster dispersion
```

CH 指数越高，通常说明聚类结构越清晰。

代码中优先选择轮廓系数更高的 `K`，如果轮廓系数相同，再比较 CH 指数。

### 代码角度

入口命令：

```bash
python clustering.py \
  --input data/raw/ETTh1.csv \
  --min-k 2 \
  --max-k 8
```

主要代码文件：

```text
clustering.py
src/clusterer.py
```

核心流程：

```text
1. load_feature_matrix() 读取标准化特征矩阵
2. get_feature_values() 去除 segment_start、segment_end、segment_length 元数据列
3. valid_k_values() 生成合法候选 K
4. evaluate_algorithm() 遍历 K 并计算评价指标
5. fit_predict() 调用 KMeans 或 GaussianMixture
6. 选择 silhouette_score 最优的 K
7. build_segment_condition_table() 生成分段-工况对应表
8. build_condition_summary() 统计每个工况的持续时长
9. save_clustering_result() 保存结果
```

关键函数：

```text
fit_predict()
evaluate_algorithm()
labels_to_condition_ids()
build_segment_condition_table()
build_condition_summary()
cluster_feature_matrix()
```

当前对每种分段方法分别运行两种聚类算法：

```text
ruptures_pelt + K-Means
ruptures_pelt + GMM
window_stat_distance + K-Means
window_stat_distance + GMM
```

输出文件：

```text
outputs/clustering/algorithm_comparison.csv
outputs/clustering/<feature_method>/<algorithm>/segment_conditions.csv
outputs/clustering/<feature_method>/<algorithm>/condition_summary.csv
outputs/clustering/<feature_method>/<algorithm>/clustering_metrics.json
```

其中 `segment_conditions.csv` 包含：

```text
segment_id
segment_start
segment_end
start_time
end_time
duration_hours
cluster_label
condition_id
```

`condition_summary.csv` 包含：

```text
condition_id
segment_count
first_start_time
last_end_time
total_duration_hours
mean_duration_hours
min_duration_hours
max_duration_hours
```

### 工况 ID 映射

聚类算法输出的标签通常是无序的，例如 `0, 1, 2` 并不代表真实时间顺序。为了让结果稳定、便于展示，项目按每个聚类中分段的平均开始时间排序，将标签映射为：

```text
OP_001
OP_002
OP_003
...
```

对应代码：

```text
labels_to_condition_ids()
```

这样即使算法内部标签编号变化，最终展示的工况 ID 仍然具有一致性。

## 任务 2-4 总结

本项目从连续 7 维时间序列出发，先进行自动分段，再对每个分段提取 112 维特征，最后通过 K-Means 和 GMM 聚类得到工况 ID。

整体逻辑可以概括为：

```text
1. 分段：把长序列切成若干相对稳定的子序列
2. 特征：把长短不一的子序列变成固定长度向量
3. 聚类：把相似分段归为同一种工况
4. 统计：输出每种工况出现的时间范围和持续时长
```

从数学角度看，该流程把原始时序问题转化为“变点检测 + 特征工程 + 无监督聚类”问题。

从代码角度看，三个阶段分别由以下入口脚本完成：

```text
segmentation.py
feature_extraction.py
clustering.py
```

核心算法模块则封装在：

```text
src/ruptures_segmenter.py
src/window_stat_segmenter.py
src/feature_extractor.py
src/clusterer.py
```

这种结构使得不同分段方法、不同特征矩阵和不同聚类算法可以独立对比，也方便后续扩展新的算法。
