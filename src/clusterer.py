"""Clustering and operating-condition labeling for segment features."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import calinski_harabasz_score, silhouette_score
from sklearn.mixture import GaussianMixture


METADATA_COLUMNS = ["segment_start", "segment_end", "segment_length"]


@dataclass(frozen=True)
class ClusteringMetrics:
    """Evaluation scores for one clustering run."""

    algorithm: str
    k: int
    silhouette_score: float
    calinski_harabasz_score: float


@dataclass(frozen=True)
class ClusteringResult:
    """Selected clustering result for one feature matrix."""

    feature_method: str
    algorithm: str
    selected_k: int
    metrics: list[ClusteringMetrics]
    labels: list[int]
    segment_conditions: pd.DataFrame
    condition_summary: pd.DataFrame


def load_feature_matrix(feature_path: str | Path) -> pd.DataFrame:
    """Load a scaled segment feature matrix."""

    path = Path(feature_path)
    if not path.exists():
        raise FileNotFoundError(f"Feature matrix not found: {path}")
    return pd.read_csv(path)


def load_time_index(input_path: str | Path) -> pd.Series:
    """Load ETTh1 timestamps for mapping segment indexes to real time."""

    df = pd.read_csv(input_path)
    if "datetime" in df.columns:
        return pd.to_datetime(df["datetime"])
    if "date" in df.columns:
        return pd.to_datetime(df["date"])
    if "Time" in df.columns:
        return pd.to_datetime(df["Time"], unit="ms")
    raise ValueError("Input data must contain one of: datetime, date, Time.")


def get_feature_values(feature_df: pd.DataFrame) -> np.ndarray:
    """Return numeric feature columns used for clustering."""

    feature_columns = [
        column for column in feature_df.columns if column not in METADATA_COLUMNS
    ]
    return feature_df[feature_columns].to_numpy(dtype=float)


def valid_k_values(n_samples: int, min_k: int = 2, max_k: int = 8) -> list[int]:
    """Return valid candidate cluster counts for internal metrics."""

    upper = min(max_k, n_samples - 1)
    if upper < min_k:
        raise ValueError(f"Need at least {min_k + 1} segments for clustering.")
    return list(range(min_k, upper + 1))


def fit_predict(algorithm: str, features: np.ndarray, k: int, random_state: int) -> np.ndarray:
    """Fit one clustering algorithm and return labels."""

    if algorithm == "kmeans":
        model = KMeans(n_clusters=k, n_init=20, random_state=random_state)
        return model.fit_predict(features)
    if algorithm == "gmm":
        model = GaussianMixture(
            n_components=k,
            covariance_type="full",
            reg_covar=1e-6,
            random_state=random_state,
        )
        return model.fit_predict(features)
    raise ValueError(f"Unsupported clustering algorithm: {algorithm}")


def evaluate_algorithm(
    algorithm: str,
    features: np.ndarray,
    k_values: list[int],
    random_state: int = 42,
) -> tuple[list[ClusteringMetrics], np.ndarray, int]:
    """Evaluate one algorithm over candidate K values and select best K."""

    metrics: list[ClusteringMetrics] = []
    labels_by_k: dict[int, np.ndarray] = {}

    for k in k_values:
        labels = fit_predict(algorithm, features, k=k, random_state=random_state)
        labels_by_k[k] = labels
        if len(set(labels)) < 2:
            silhouette = -1.0
            calinski = 0.0
        else:
            silhouette = float(silhouette_score(features, labels))
            calinski = float(calinski_harabasz_score(features, labels))
        metrics.append(
            ClusteringMetrics(
                algorithm=algorithm,
                k=k,
                silhouette_score=silhouette,
                calinski_harabasz_score=calinski,
            )
        )

    best = max(metrics, key=lambda item: (item.silhouette_score, item.calinski_harabasz_score))
    return metrics, labels_by_k[best.k], best.k


def labels_to_condition_ids(labels: np.ndarray, feature_df: pd.DataFrame) -> dict[int, str]:
    """Map arbitrary cluster labels to stable OP IDs by average start time."""

    label_df = pd.DataFrame(
        {
            "label": labels,
            "segment_start": feature_df["segment_start"],
        }
    )
    ordered_labels = (
        label_df.groupby("label")["segment_start"].mean().sort_values().index.tolist()
    )
    return {label: f"OP_{index + 1:03d}" for index, label in enumerate(ordered_labels)}


def build_segment_condition_table(
    feature_df: pd.DataFrame,
    labels: np.ndarray,
    time_index: pd.Series,
) -> pd.DataFrame:
    """Create per-segment operating-condition assignments."""

    condition_map = labels_to_condition_ids(labels, feature_df)
    rows = []
    n_rows = len(time_index)
    time_step = time_index.diff().dropna().median()
    if pd.isna(time_step):
        time_step = pd.Timedelta(hours=1)

    for row_index, row in feature_df.iterrows():
        start = int(row["segment_start"])
        end = int(row["segment_end"])
        start_lookup = min(max(start, 0), n_rows - 1)
        start_time = time_index.iloc[start_lookup]
        if end < n_rows:
            end_time = time_index.iloc[end]
        else:
            end_time = time_index.iloc[n_rows - 1] + time_step
        duration_hours = float((end_time - start_time) / pd.Timedelta(hours=1))
        label = int(labels[row_index])
        rows.append(
            {
                "segment_id": row_index,
                "segment_start": start,
                "segment_end": end,
                "start_time": start_time,
                "end_time": end_time,
                "duration_hours": duration_hours,
                "cluster_label": label,
                "condition_id": condition_map[label],
            }
        )
    return pd.DataFrame(rows)


def build_condition_summary(segment_conditions: pd.DataFrame) -> pd.DataFrame:
    """Summarize time span and duration statistics for each condition ID."""

    summary = (
        segment_conditions.groupby("condition_id")
        .agg(
            segment_count=("segment_id", "count"),
            first_start_time=("start_time", "min"),
            last_end_time=("end_time", "max"),
            total_duration_hours=("duration_hours", "sum"),
            mean_duration_hours=("duration_hours", "mean"),
            min_duration_hours=("duration_hours", "min"),
            max_duration_hours=("duration_hours", "max"),
        )
        .reset_index()
        .sort_values("condition_id")
    )
    return summary


def infer_feature_method(feature_path: str | Path) -> str:
    """Infer feature source method from a feature filename."""

    name = Path(feature_path).name
    suffix = "_features_scaled.csv"
    return name[: -len(suffix)] if name.endswith(suffix) else Path(feature_path).stem


def cluster_feature_matrix(
    feature_path: str | Path,
    input_data_path: str | Path,
    algorithm: str = "kmeans",
    min_k: int = 2,
    max_k: int = 8,
    random_state: int = 42,
) -> ClusteringResult:
    """Cluster one scaled feature matrix and build operating-condition outputs."""

    feature_df = load_feature_matrix(feature_path)
    features = get_feature_values(feature_df)
    k_values = valid_k_values(len(feature_df), min_k=min_k, max_k=max_k)
    metrics, labels, selected_k = evaluate_algorithm(
        algorithm,
        features,
        k_values=k_values,
        random_state=random_state,
    )
    time_index = load_time_index(input_data_path)
    segment_conditions = build_segment_condition_table(feature_df, labels, time_index)
    condition_summary = build_condition_summary(segment_conditions)

    return ClusteringResult(
        feature_method=infer_feature_method(feature_path),
        algorithm=algorithm,
        selected_k=selected_k,
        metrics=metrics,
        labels=[int(label) for label in labels],
        segment_conditions=segment_conditions,
        condition_summary=condition_summary,
    )


def save_clustering_result(result: ClusteringResult, output_dir: str | Path) -> tuple[Path, Path, Path]:
    """Save labels, condition summary, and metric comparison."""

    directory = Path(output_dir) / result.feature_method / result.algorithm
    directory.mkdir(parents=True, exist_ok=True)

    assignments_path = directory / "segment_conditions.csv"
    summary_path = directory / "condition_summary.csv"
    metrics_path = directory / "clustering_metrics.json"

    result.segment_conditions.to_csv(assignments_path, index=False)
    result.condition_summary.to_csv(summary_path, index=False)
    metrics_payload = {
        "feature_method": result.feature_method,
        "algorithm": result.algorithm,
        "selected_k": result.selected_k,
        "metrics": [asdict(metric) for metric in result.metrics],
    }
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    return assignments_path, summary_path, metrics_path
