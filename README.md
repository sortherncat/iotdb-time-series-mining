# IoTDB Time Series Mining

中文文档: [README.zh-CN.md](README.zh-CN.md)  
中文开发记录: [docs/development_log.zh-CN.md](docs/development_log.zh-CN.md)

This repository is for the course project **High-dimensional Time Series Segmentation, Feature Extraction, and Operating Condition Clustering**.

The project builds a complete data mining pipeline for industrial multivariate time series data:

```text
Dataset -> Apache IoTDB -> DataFrame -> Segmentation -> Feature Extraction -> Clustering -> Visualization -> Report
```

## Deployment and Usage

The repository does not commit large runtime files, raw datasets, Python virtual environments, Node dependencies, or Apache IoTDB binaries. After cloning the repository, use the following commands to reproduce the local environment and run the full pipeline.

### 1. Clone the Repository

```bash
git clone https://github.com/sortherncat/iotdb-time-series-mining.git
cd iotdb-time-series-mining
```

### 2. Prepare Python Dependencies

Using a virtual environment is recommended:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Download ETTh1

```bash
mkdir -p data/raw
curl -L -o data/raw/ETTh1.csv https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv
```

If GitHub raw download is unavailable, manually download `ETTh1.csv` from the ETT repository and place it at `data/raw/ETTh1.csv`.

### 4. Set Up and Start Apache IoTDB

```bash
bash scripts/setup_iotdb.sh
bash scripts/start_iotdb.sh
bash scripts/check_iotdb.sh
```

The setup script downloads Apache IoTDB 2.0.4 into `third_party/`. The default RPC endpoint is `127.0.0.1:6667`, with user `root` and password `root`.

### 5. Import and Query Data

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000

python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00" \
  --output data/processed/etth1_query_sample.csv
```

### 6. Run Segmentation, Feature Extraction, and Clustering

```bash
python segmentation.py --method ruptures --input data/raw/ETTh1.csv --model rbf --penalty 10 --min-size 48 --jump 10 --refine --refine-radius 20

python segmentation.py --method window_stat --input data/raw/ETTh1.csv --window-size 48 --alpha 0.5 --threshold-quantile 0.95 --min-size 48

python feature_extraction.py --input data/raw/ETTh1.csv --scaler standard

python clustering.py --input data/raw/ETTh1.csv --min-k 2 --max-k 8
```

### 7. Start the Visualization Dashboard

```bash
python scripts/prepare_frontend_data.py

cd frontend
npm install
npm run dev -- --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

### 8. Stop IoTDB

```bash
bash scripts/stop_iotdb.sh
```

## Project Background

In Industrial Internet of Things scenarios, equipment such as CNC machines, wind turbines, servers, and chemical reactors continuously generate high-frequency multivariate sensor data. Different operating stages correspond to different equipment conditions.

This project aims to automatically identify operating conditions from continuous high-dimensional time series data by combining time series storage, change point detection, feature engineering, unsupervised clustering, and visualization.

## Main Objectives

- Deploy Apache IoTDB and access data through the Python Session API.
- Import a public multivariate time series dataset into IoTDB.
- Query time series data from IoTDB and convert it into a pandas DataFrame.
- Detect change points and segment continuous high-dimensional time series.
- Extract fixed-length feature vectors from each segment.
- Cluster segments into operating condition groups.
- Assign condition IDs such as `OP_001`, `OP_002`, and `OP_003`.
- Visualize segmentation boundaries, clustering results, representative segments, and condition timelines.
- Produce an experimental report with method comparison and result analysis.

## Planned Dataset

The preferred dataset is **ETT (Electricity Transformer Temperature)**.

Reasons for choosing ETT:

- CSV format, easy to load and preprocess.
- Contains continuous multivariate time series data.
- Includes transformer temperature and load-related variables.
- Suitable for segmentation and operating condition clustering.
- Moderate dimensionality, making it practical for course project implementation.

Alternative datasets may include SMD, MSL, Weather, or Electricity Load Diagrams if needed.

## System Modules

The planned code structure is:

```text
iotdb-time-series-mining/
├── data_loader.py          # IoTDB data import, query, and DataFrame conversion
├── segmentation.py         # Change point detection and time series segmentation
├── feature_extraction.py   # Segment-level feature extraction CLI
├── src/                    # Reusable algorithm modules
│   └── ruptures_segmenter.py
│   └── window_stat_segmenter.py
│   └── feature_extractor.py
│   └── clusterer.py
├── clustering.py           # Clustering, model comparison, and condition labeling
├── frontend/               # Interactive React visualization dashboard
├── visualization.py        # Figures for segmentation, clustering, and timelines
├── main.py                 # Main pipeline orchestration
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## Technical Plan

### 1. Data Access

- Use Apache IoTDB 2.x in standalone mode.
- Use the Python Session API to connect to IoTDB.
- Store sensor channels with paths such as:

```text
root.industry.device001.temperature
root.industry.device001.load_1
root.industry.device001.load_2
```

- Use batch insertion for efficient data import.
- Query time ranges from IoTDB and convert the result into `pandas.DataFrame`.

## Apache IoTDB Setup

Apache IoTDB is not committed to this repository. Instead, the repository provides setup scripts so that another user can prepare the same local environment after cloning the project.

Prepare IoTDB:

```bash
bash scripts/setup_iotdb.sh
```

Start IoTDB:

```bash
bash scripts/start_iotdb.sh
```

Verify IoTDB with CLI:

```bash
bash scripts/check_iotdb.sh
```

Stop IoTDB:

```bash
bash scripts/stop_iotdb.sh
```

The setup script downloads Apache IoTDB 2.0.4 into `third_party/` and applies the macOS JVM stack-size fix from `-Xss512k` to `-Xss1m` when needed.

### 2. Time Series Segmentation

At least two segmentation methods will be implemented:

- Method A: change point detection with the `ruptures` library, such as PELT, Binary Segmentation, or Window-based detection.
- Method B: sliding window plus statistical distance, such as mean-distance, covariance-distance, KL divergence, or MMD-inspired distance.

The segmentation process will consider:

- Joint detection on multivariate time series.
- Minimum segment length constraints.
- Penalty or threshold selection using methods such as BIC, elbow method, or validation by visualization.

### 3. Feature Extraction

For each segment, fixed-length features will be extracted from multiple categories:

- Statistical features: mean, standard deviation, quantiles, skewness, kurtosis.
- Time-domain shape features: RMS, peak factor, zero-crossing rate.
- Correlation features: upper-triangular values of the inter-channel correlation matrix.
- Trend features: linear slope and mean difference.

The feature matrix will be standardized before clustering.

### 4. Clustering and Condition Identification

At least two clustering algorithms will be compared, such as:

- K-Means
- Gaussian Mixture Model
- Agglomerative Clustering
- DBSCAN

Evaluation metrics may include:

- Silhouette Score
- Calinski-Harabasz Index
- Elbow method

Each cluster will be mapped to an operating condition ID.

### 5. Visualization

The required visualizations include:

- Original multichannel time series with segmentation boundaries.
- 2D clustering scatter plot after dimensionality reduction.
- Representative segment comparison for each operating condition.
- Operating condition timeline using a Gantt-style chart or color band.

## Expected Outputs

- Source code for the complete pipeline.
- Visual results saved as figures.
- Segment boundary list.
- Feature matrix.
- Cluster labels and operating condition IDs.
- Duration statistics for each operating condition.
- Experimental report in PDF format.

## Current Status

- [x] Project repository created.
- [x] Initial README uploaded.
- [x] Dataset selection and download.
- [x] Apache IoTDB environment setup.
- [x] Data import implementation.
- [x] IoTDB import verification.
- [x] Time range query and DataFrame conversion.
- [x] Segmentation method A implementation.
- [x] Segmentation method B implementation.
- [x] Feature extraction implementation.
- [x] Clustering implementation.
- [x] Interactive visualization dashboard.
- [ ] Experimental report.

## Notes

This repository is currently in the planning stage. Code implementation will be added step by step after the project design is finalized.

## ETTh1 Data Import

The selected dataset is ETTh1 from the ETT dataset collection.

Download the CSV file:

```bash
mkdir -p data/raw
curl -L -o data/raw/ETTh1.csv https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv
```

Start IoTDB, then import ETTh1:

```bash
python data_loader.py --csv data/raw/ETTh1.csv --batch-size 1000
```

The IoTDB storage path is:

```text
root.industry.transformer001.high_useful_load
root.industry.transformer001.high_useless_load
root.industry.transformer001.middle_useful_load
root.industry.transformer001.middle_useless_load
root.industry.transformer001.low_useful_load
root.industry.transformer001.low_useless_load
root.industry.transformer001.oil_temperature
```

## ETTh1 Data Query

After ETTh1 has been imported, query a specified time range from IoTDB and convert it into a `pandas.DataFrame`:

```bash
python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00"
```

Save the queried DataFrame to CSV for later analysis:

```bash
python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00" \
  --output data/processed/etth1_query_sample.csv
```

The query result contains the IoTDB millisecond timestamp, a converted `datetime` column, and the seven ETTh1 measurement columns.

## Segmentation Method A: ruptures

Method A is encapsulated in `src/ruptures_segmenter.py` as `RupturesSegmenter` and uses `ruptures.Pelt` for multivariate joint change point detection. The seven ETTh1 sensor columns are standardized first, then passed to `ruptures` as one matrix with shape `(time_steps, sensors)`.

To balance speed and precision, the implementation uses a two-stage strategy:

```text
coarse search with jump > 1 -> fine local search near each coarse boundary
```

The fine search evaluates each candidate boundary in a local neighborhood and keeps the position with the lowest left-plus-right segment cost.

Run method A on the original ETTh1 CSV:

```bash
python segmentation.py \
  --input data/raw/ETTh1.csv \
  --model rbf \
  --penalty 10 \
  --min-size 48 \
  --jump 10 \
  --refine \
  --refine-radius 20
```

Default output:

```text
outputs/segmentation/method_a_ruptures.json
```

The output JSON contains:

```text
change_points: internal change point indexes
segments: [(start, end), ...]
```

## Segmentation Method B: Sliding Window Statistical Distance

Method B is encapsulated in `src/window_stat_segmenter.py`. It compares the left and right windows around each candidate point:

```text
S(t) = ||mean_left - mean_right||_2 + alpha * ||cov_left - cov_right||_F
```

Then it selects local peaks above a score quantile threshold and filters nearby change points with the minimum segment length constraint.

Run method B:

```bash
python segmentation.py \
  --method window_stat \
  --input data/raw/ETTh1.csv \
  --window-size 48 \
  --alpha 0.5 \
  --threshold-quantile 0.95 \
  --min-size 48
```

Default output:

```text
outputs/segmentation/method_b_window_stat.json
```

The output JSON contains the detected `change_points`, final `segments`, and the full sliding-window score curve.

## Segment Feature Extraction

Task 3 extracts segment-level feature vectors from each segmentation result. The implementation covers four feature categories:

```text
statistical features: mean, std, skewness, kurtosis, quantiles
time-domain shape features: zero-crossing rate, RMS, crest factor, waveform factor
correlation features: upper-triangular inter-channel correlation coefficients
trend features: linear slope, mean difference
```

Run feature extraction for both Method A and Method B segmentation results:

```bash
python feature_extraction.py \
  --input data/raw/ETTh1.csv \
  --scaler standard
```

Default outputs:

```text
outputs/features/ruptures_pelt_features_raw.csv
outputs/features/ruptures_pelt_features_scaled.csv
outputs/features/ruptures_pelt_feature_metadata.json
outputs/features/window_stat_distance_features_raw.csv
outputs/features/window_stat_distance_features_scaled.csv
outputs/features/window_stat_distance_feature_metadata.json
```

Each segment has 112 extracted features. The saved CSV files also include `segment_start`, `segment_end`, and `segment_length` as metadata columns.

## Clustering and Operating Condition Identification

Task 4 clusters segment feature matrices and maps each cluster to an operating condition ID such as `OP_001`.

The implementation compares two clustering algorithms:

```text
K-Means
Gaussian Mixture Model
```

For each algorithm, candidate cluster counts from `--min-k` to `--max-k` are evaluated by:

```text
Silhouette Score
Calinski-Harabasz Index
```

Run clustering for both Method A and Method B feature matrices:

```bash
python clustering.py \
  --input data/raw/ETTh1.csv \
  --min-k 2 \
  --max-k 8
```

Default outputs:

```text
outputs/clustering/algorithm_comparison.csv
outputs/clustering/<feature_method>/<algorithm>/segment_conditions.csv
outputs/clustering/<feature_method>/<algorithm>/condition_summary.csv
outputs/clustering/<feature_method>/<algorithm>/clustering_metrics.json
```

`segment_conditions.csv` contains each segment's condition ID, start time, end time, and duration. `condition_summary.csv` contains duration statistics for each operating condition.

## Interactive Visualization Dashboard

Task 5 is implemented as a React/Vite frontend with two design modes based on the design documents in `design/`:

```text
Apple Gallery: light, quiet, gallery-like presentation
Binance Terminal: dark, dense, financial-platform dashboard
```

Prepare frontend data from the Python pipeline outputs:

```bash
python scripts/prepare_frontend_data.py
```

Start the dashboard:

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

Open:

```text
http://127.0.0.1:5173/
```

The dashboard includes:

```text
raw multichannel time series with segmentation boundaries
2D clustering scatter plot with cluster centers
representative segment comparison by operating condition
operating-condition timeline
```

Interactive controls include design mode, segmentation method, clustering algorithm, visible sensors, and representative sensor selection.
