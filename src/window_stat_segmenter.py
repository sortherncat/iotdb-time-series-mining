"""Sliding-window statistical-distance change point detection module."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.ruptures_segmenter import (
    MEASUREMENT_COLUMNS,
    prepare_feature_matrix,
    segments_from_change_points,
)


@dataclass(frozen=True)
class WindowStatSegmentationResult:
    """Result of sliding-window statistical-distance segmentation."""

    method: str
    window_size: int
    alpha: float
    threshold_quantile: float
    threshold: float
    min_size: int
    change_points: list[int]
    segments: list[tuple[int, int]]
    scores: list[float | None]


def compute_window_stat_scores(
    features: np.ndarray,
    window_size: int = 48,
    alpha: float = 0.5,
) -> np.ndarray:
    """Compute S(t) = mean distance + alpha * covariance distance."""

    n_samples = len(features)
    if n_samples < window_size * 2 + 1:
        raise ValueError(
            f"Need at least {window_size * 2 + 1} rows for "
            f"window_size={window_size}, got {n_samples}."
        )

    scores = np.full(n_samples, np.nan, dtype=float)
    for t in range(window_size, n_samples - window_size + 1):
        left_window = features[t - window_size : t]
        right_window = features[t : t + window_size]

        mean_distance = np.linalg.norm(
            left_window.mean(axis=0) - right_window.mean(axis=0)
        )
        left_cov = np.cov(left_window, rowvar=False)
        right_cov = np.cov(right_window, rowvar=False)
        covariance_distance = np.linalg.norm(left_cov - right_cov, ord="fro")

        scores[t] = mean_distance + alpha * covariance_distance

    return scores


def find_local_peak_change_points(
    scores: np.ndarray,
    threshold: float,
) -> list[int]:
    """Find local peaks whose scores are no lower than the threshold."""

    change_points: list[int] = []
    for index in range(1, len(scores) - 1):
        score = scores[index]
        if np.isnan(score):
            continue
        if score > scores[index - 1] and score > scores[index + 1] and score >= threshold:
            change_points.append(index)
    return change_points


def filter_change_points_by_min_size(
    change_points: list[int],
    scores: np.ndarray,
    n_samples: int,
    min_size: int,
) -> list[int]:
    """Keep high-score change points while enforcing minimum segment length."""

    candidates = sorted(change_points, key=lambda point: scores[point], reverse=True)
    selected: list[int] = []

    for point in candidates:
        proposed = sorted([*selected, point])
        boundaries = [0, *proposed, n_samples]
        segment_lengths = [
            end - start for start, end in zip(boundaries[:-1], boundaries[1:])
        ]
        if all(length >= min_size for length in segment_lengths):
            selected.append(point)

    return sorted(selected)


class WindowStatSegmenter:
    """Sliding-window segmenter based on mean and covariance distance."""

    def __init__(
        self,
        window_size: int = 48,
        alpha: float = 0.5,
        threshold_quantile: float = 0.95,
        min_size: int = 48,
    ) -> None:
        self.window_size = window_size
        self.alpha = alpha
        self.threshold_quantile = threshold_quantile
        self.min_size = min_size

    def segment(
        self,
        df: pd.DataFrame,
        columns: list[str] | None = None,
    ) -> WindowStatSegmentationResult:
        """Detect change points from a multivariate DataFrame."""

        columns = columns or MEASUREMENT_COLUMNS
        features = prepare_feature_matrix(df, columns=columns)
        scores = compute_window_stat_scores(
            features,
            window_size=self.window_size,
            alpha=self.alpha,
        )
        threshold = float(np.nanquantile(scores, self.threshold_quantile))
        peak_points = find_local_peak_change_points(scores, threshold=threshold)
        change_points = filter_change_points_by_min_size(
            peak_points,
            scores=scores,
            n_samples=len(features),
            min_size=self.min_size,
        )

        return WindowStatSegmentationResult(
            method="window_stat_distance",
            window_size=self.window_size,
            alpha=self.alpha,
            threshold_quantile=self.threshold_quantile,
            threshold=threshold,
            min_size=self.min_size,
            change_points=change_points,
            segments=segments_from_change_points(change_points, n_samples=len(features)),
            scores=[None if np.isnan(score) else float(score) for score in scores],
        )
