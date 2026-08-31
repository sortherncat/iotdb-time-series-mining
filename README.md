# IoTDB Time Series Mining

This repository is for the course project **High-dimensional Time Series Segmentation, Feature Extraction, and Operating Condition Clustering**.

The project builds a complete data mining pipeline for industrial multivariate time series data:

```text
Dataset -> Apache IoTDB -> DataFrame -> Segmentation -> Feature Extraction -> Clustering -> Visualization -> Report
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
├── feature_extraction.py   # Segment-level feature extraction
├── clustering.py           # Clustering, model comparison, and condition labeling
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
- [ ] Dataset selection and download.
- [ ] Apache IoTDB environment setup.
- [ ] Data import and query implementation.
- [ ] Segmentation implementation.
- [ ] Feature extraction implementation.
- [ ] Clustering implementation.
- [ ] Visualization implementation.
- [ ] Experimental report.

## Notes

This repository is currently in the planning stage. Code implementation will be added step by step after the project design is finalized.
