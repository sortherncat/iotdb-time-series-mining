"""Prepare compact JSON data for the visualization frontend."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.decomposition import PCA


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/raw/ETTh1.csv"
OUTPUT_PATH = ROOT / "frontend/public/data/dashboard_data.json"

SEGMENT_FILES = {
    "ruptures_pelt": ROOT / "outputs/segmentation/method_a_ruptures.json",
    "window_stat_distance": ROOT / "outputs/segmentation/method_b_window_stat.json",
}

CLUSTER_DIRS = {
    "ruptures_pelt": {
        "kmeans": ROOT / "outputs/clustering/ruptures_pelt/kmeans",
        "gmm": ROOT / "outputs/clustering/ruptures_pelt/gmm",
    },
    "window_stat_distance": {
        "kmeans": ROOT / "outputs/clustering/window_stat_distance/kmeans",
        "gmm": ROOT / "outputs/clustering/window_stat_distance/gmm",
    },
}

FEATURE_FILES = {
    "ruptures_pelt": ROOT / "outputs/features/ruptures_pelt_features_scaled.csv",
    "window_stat_distance": ROOT / "outputs/features/window_stat_distance_features_scaled.csv",
}

RAW_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
DISPLAY_COLUMNS = {
    "HUFL": "high_useful_load",
    "HULL": "high_useless_load",
    "MUFL": "middle_useful_load",
    "MULL": "middle_useless_load",
    "LUFL": "low_useful_load",
    "LULL": "low_useless_load",
    "OT": "oil_temperature",
}


def load_timeseries() -> tuple[pd.DataFrame, list[dict]]:
    """Load ETTh1 and downsample chart rows to keep the frontend responsive."""

    df = pd.read_csv(DATA_PATH)
    df["datetime"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    df = df.rename(columns=DISPLAY_COLUMNS)
    columns = list(DISPLAY_COLUMNS.values())

    stride = max(1, len(df) // 2400)
    sampled = df.iloc[::stride].copy()
    records = sampled[["datetime", *columns]].to_dict(orient="records")
    return df, records


def load_segments() -> dict:
    """Load segmentation results."""

    results = {}
    for method, path in SEGMENT_FILES.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        results[method] = {
            "change_points": payload["change_points"],
            "segments": payload["segments"],
        }
    return results


def build_cluster_payload(time_df: pd.DataFrame) -> dict:
    """Load clustering outputs and attach 2D PCA coordinates."""

    payload = {}
    for method, algorithms in CLUSTER_DIRS.items():
        feature_df = pd.read_csv(FEATURE_FILES[method])
        feature_values = feature_df.drop(
            columns=["segment_start", "segment_end", "segment_length"]
        )
        coords = PCA(n_components=2, random_state=42).fit_transform(feature_values)
        payload[method] = {}

        for algorithm, directory in algorithms.items():
            assignments = pd.read_csv(directory / "segment_conditions.csv")
            summary = pd.read_csv(directory / "condition_summary.csv")
            metrics = json.loads((directory / "clustering_metrics.json").read_text())
            points = []
            for index, row in assignments.iterrows():
                points.append(
                    {
                        "segment_id": int(row["segment_id"]),
                        "x": float(coords[index, 0]),
                        "y": float(coords[index, 1]),
                        "condition_id": row["condition_id"],
                        "cluster_label": int(row["cluster_label"]),
                        "segment_start": int(row["segment_start"]),
                        "segment_end": int(row["segment_end"]),
                        "start_time": row["start_time"],
                        "end_time": row["end_time"],
                        "duration_hours": float(row["duration_hours"]),
                    }
                )
            centers = (
                pd.DataFrame(points)
                .groupby("condition_id")[["x", "y"]]
                .mean()
                .reset_index()
                .to_dict(orient="records")
            )
            payload[method][algorithm] = {
                "selected_k": metrics["selected_k"],
                "points": points,
                "centers": centers,
                "summary": summary.to_dict(orient="records"),
                "metrics": metrics["metrics"],
                "representatives": select_representative_segments(points, centers, time_df),
            }
    return payload


def select_representative_segments(
    points: list[dict],
    centers: list[dict],
    time_df: pd.DataFrame,
    per_condition: int = 3,
) -> dict:
    """Select segments closest to each 2D cluster center."""

    center_map = {row["condition_id"]: row for row in centers}
    selected = {}
    for condition_id in sorted(center_map):
        center = center_map[condition_id]
        condition_points = [p for p in points if p["condition_id"] == condition_id]
        condition_points.sort(
            key=lambda p: (p["x"] - center["x"]) ** 2 + (p["y"] - center["y"]) ** 2
        )
        selected[condition_id] = []
        for point in condition_points[:per_condition]:
            start = point["segment_start"]
            end = point["segment_end"]
            segment = time_df.iloc[start:end]
            stride = max(1, len(segment) // 180)
            selected[condition_id].append(
                {
                    "segment_id": point["segment_id"],
                    "start_time": point["start_time"],
                    "end_time": point["end_time"],
                    "values": segment.iloc[::stride][
                        ["datetime", *DISPLAY_COLUMNS.values()]
                    ].to_dict(orient="records"),
                }
            )
    return selected


def main() -> None:
    time_df, timeseries = load_timeseries()
    payload = {
        "metadata": {
            "dataset": "ETTh1",
            "row_count": len(time_df),
            "sensor_count": 7,
            "sensors": list(DISPLAY_COLUMNS.values()),
        },
        "timeseries": timeseries,
        "segments": load_segments(),
        "clusters": build_cluster_payload(time_df),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"Saved frontend data to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
