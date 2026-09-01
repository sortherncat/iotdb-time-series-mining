"""Segment-level feature extraction for multivariate time series."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, StandardScaler

from src.ruptures_segmenter import MEASUREMENT_COLUMNS, normalize_etth1_columns


@dataclass(frozen=True)
class FeatureExtractionResult:
    """Feature matrix extracted from segmentation results."""

    method: str
    scaler: str
    feature_names: list[str]
    raw_features: pd.DataFrame
    scaled_features: pd.DataFrame


def load_segments(segment_path: str | Path) -> tuple[str, list[tuple[int, int]]]:
    """Load segmentation method name and segment boundaries from JSON."""

    payload = json.loads(Path(segment_path).read_text(encoding="utf-8"))
    segments = [tuple(segment) for segment in payload["segments"]]
    return payload["method"], segments


def load_time_series(input_path: str | Path) -> pd.DataFrame:
    """Load ETTh1 data and normalize column names."""

    df = pd.read_csv(input_path)
    return normalize_etth1_columns(df)


def safe_skew(values: pd.Series) -> float:
    """Return skewness with NaN converted to zero."""

    result = values.skew()
    return 0.0 if pd.isna(result) else float(result)


def safe_kurtosis(values: pd.Series) -> float:
    """Return kurtosis with NaN converted to zero."""

    result = values.kurt()
    return 0.0 if pd.isna(result) else float(result)


def zero_crossing_rate(values: np.ndarray) -> float:
    """Compute zero-crossing rate after centering a segment channel."""

    if len(values) < 2:
        return 0.0
    centered = values - np.mean(values)
    signs = np.sign(centered)
    return float(np.mean(signs[1:] * signs[:-1] < 0))


def extract_channel_features(values: pd.Series, column: str) -> dict[str, float]:
    """Extract statistics, shape, and trend features for one channel."""

    array = values.to_numpy(dtype=float)
    abs_mean = np.mean(np.abs(array))
    rms = np.sqrt(np.mean(np.square(array)))
    peak = np.max(np.abs(array))
    waveform_factor = rms / abs_mean if abs_mean > 1e-12 else 0.0
    crest_factor = peak / rms if rms > 1e-12 else 0.0
    slope = np.polyfit(np.arange(len(array)), array, deg=1)[0] if len(array) >= 2 else 0.0
    diff_mean = np.mean(np.diff(array)) if len(array) >= 2 else 0.0

    return {
        f"{column}_mean": float(np.mean(array)),
        f"{column}_std": float(np.std(array, ddof=0)),
        f"{column}_skew": safe_skew(values),
        f"{column}_kurtosis": safe_kurtosis(values),
        f"{column}_q25": float(np.quantile(array, 0.25)),
        f"{column}_q50": float(np.quantile(array, 0.50)),
        f"{column}_q75": float(np.quantile(array, 0.75)),
        f"{column}_rms": float(rms),
        f"{column}_crest_factor": float(crest_factor),
        f"{column}_waveform_factor": float(waveform_factor),
        f"{column}_zero_crossing_rate": zero_crossing_rate(array),
        f"{column}_slope": float(slope),
        f"{column}_diff_mean": float(diff_mean),
    }


def extract_correlation_features(segment_df: pd.DataFrame) -> dict[str, float]:
    """Extract upper-triangular inter-channel correlation coefficients."""

    corr = segment_df.corr().fillna(0.0).to_numpy(dtype=float)
    columns = list(segment_df.columns)
    features: dict[str, float] = {}
    for i, left in enumerate(columns):
        for j in range(i + 1, len(columns)):
            right = columns[j]
            features[f"corr_{left}__{right}"] = float(corr[i, j])
    return features


def extract_features_for_segment(
    df: pd.DataFrame,
    start: int,
    end: int,
    columns: list[str] | None = None,
) -> dict[str, float | int]:
    """Extract one feature row for a half-open segment interval."""

    columns = columns or MEASUREMENT_COLUMNS
    segment_df = df.iloc[start:end][columns].apply(pd.to_numeric, errors="coerce")
    segment_df = segment_df.interpolate(limit_direction="both").dropna()
    if segment_df.empty:
        raise ValueError(f"Segment ({start}, {end}) contains no valid sensor rows.")

    row: dict[str, float | int] = {
        "segment_start": start,
        "segment_end": end,
        "segment_length": end - start,
    }
    for column in columns:
        row.update(extract_channel_features(segment_df[column], column))
    row.update(extract_correlation_features(segment_df))
    return row


def scale_feature_matrix(
    raw_features: pd.DataFrame,
    scaler_name: str = "standard",
) -> pd.DataFrame:
    """Scale numeric feature columns with StandardScaler or MinMaxScaler."""

    metadata_columns = ["segment_start", "segment_end", "segment_length"]
    feature_columns = [
        column for column in raw_features.columns if column not in metadata_columns
    ]
    if scaler_name == "standard":
        scaler = StandardScaler()
    elif scaler_name == "minmax":
        scaler = MinMaxScaler()
    else:
        raise ValueError("scaler_name must be 'standard' or 'minmax'.")

    scaled_values = scaler.fit_transform(raw_features[feature_columns])
    scaled_numeric = pd.DataFrame(
        scaled_values,
        columns=feature_columns,
        index=raw_features.index,
    )
    return pd.concat([raw_features[metadata_columns], scaled_numeric], axis=1)


def extract_segment_features(
    df: pd.DataFrame,
    segments: list[tuple[int, int]],
    method: str,
    scaler_name: str = "standard",
    columns: list[str] | None = None,
) -> FeatureExtractionResult:
    """Extract and scale feature vectors for all segments."""

    normalized = normalize_etth1_columns(df)
    rows = [
        extract_features_for_segment(normalized, start, end, columns=columns)
        for start, end in segments
    ]
    raw_features = pd.DataFrame(rows)
    scaled_features = scale_feature_matrix(raw_features, scaler_name=scaler_name)
    feature_names = [
        column
        for column in raw_features.columns
        if column not in {"segment_start", "segment_end", "segment_length"}
    ]

    return FeatureExtractionResult(
        method=method,
        scaler=scaler_name,
        feature_names=feature_names,
        raw_features=raw_features,
        scaled_features=scaled_features,
    )


def save_feature_result(
    result: FeatureExtractionResult,
    output_dir: str | Path,
) -> tuple[Path, Path, Path]:
    """Save raw features, scaled features, and feature metadata."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / f"{result.method}_features_raw.csv"
    scaled_path = directory / f"{result.method}_features_scaled.csv"
    metadata_path = directory / f"{result.method}_feature_metadata.json"

    result.raw_features.to_csv(raw_path, index=False)
    result.scaled_features.to_csv(scaled_path, index=False)
    metadata = {
        "method": result.method,
        "scaler": result.scaler,
        "feature_count": len(result.feature_names),
        "segment_count": len(result.scaled_features),
        "feature_names": result.feature_names,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return raw_path, scaled_path, metadata_path
