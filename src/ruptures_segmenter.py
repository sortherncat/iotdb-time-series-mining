"""Reusable ruptures-based change point detection module."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    import ruptures as rpt
except ImportError as exc:  # pragma: no cover - depends on local environment
    raise ImportError(
        "Missing ruptures. Install dependencies with `pip install -r requirements.txt`."
    ) from exc


MEASUREMENT_COLUMNS = [
    "high_useful_load",
    "high_useless_load",
    "middle_useful_load",
    "middle_useless_load",
    "low_useful_load",
    "low_useless_load",
    "oil_temperature",
]

RAW_ETTH1_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
RAW_TO_MEASUREMENT = dict(zip(RAW_ETTH1_COLUMNS, MEASUREMENT_COLUMNS))


@dataclass(frozen=True)
class SegmentationResult:
    """Result of one change point detection method."""

    method: str
    model: str
    penalty: float
    min_size: int
    jump: int
    refine: bool
    refine_radius: int
    coarse_change_points: list[int]
    change_points: list[int]
    segments: list[tuple[int, int]]


def normalize_etth1_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize original ETTh1 column names to project measurement names."""

    normalized = df.copy()
    if set(RAW_ETTH1_COLUMNS).issubset(normalized.columns):
        normalized = normalized.rename(columns=RAW_TO_MEASUREMENT)
    if "date" in normalized.columns and "datetime" not in normalized.columns:
        normalized["datetime"] = pd.to_datetime(normalized["date"])
    if "datetime" in normalized.columns:
        normalized["datetime"] = pd.to_datetime(normalized["datetime"])
    return normalized


def prepare_feature_matrix(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> np.ndarray:
    """Select multivariate sensor columns and standardize them jointly."""

    columns = columns or MEASUREMENT_COLUMNS
    normalized = normalize_etth1_columns(df)
    missing_columns = [column for column in columns if column not in normalized.columns]
    if missing_columns:
        raise ValueError(f"DataFrame is missing measurement columns: {missing_columns}")

    sensor_df = normalized[columns].apply(pd.to_numeric, errors="coerce")
    sensor_df = sensor_df.interpolate(limit_direction="both").dropna()
    if sensor_df.empty:
        raise ValueError("No valid sensor rows are available for segmentation.")

    std = sensor_df.std(ddof=0).replace(0, 1.0)
    standardized = (sensor_df - sensor_df.mean()) / std
    return standardized.to_numpy(dtype=float)


def segments_from_change_points(
    change_points: list[int],
    n_samples: int,
) -> list[tuple[int, int]]:
    """Convert change point end positions into half-open segments."""

    valid_points = sorted(
        {
            point
            for point in change_points
            if isinstance(point, int) and 0 < point <= n_samples
        }
    )
    if not valid_points or valid_points[-1] != n_samples:
        valid_points.append(n_samples)

    segments: list[tuple[int, int]] = []
    start = 0
    for end in valid_points:
        if end > start:
            segments.append((start, end))
        start = end
    return segments


def refine_change_points_near_coarse_boundaries(
    features: np.ndarray,
    coarse_change_points: list[int],
    model: str,
    min_size: int,
    refine_radius: int,
) -> list[int]:
    """Refine each coarse boundary by local unit-step cost minimization."""

    n_samples = len(features)
    internal_points = sorted(
        {point for point in coarse_change_points if 0 < point < n_samples}
    )
    if not internal_points or refine_radius <= 0:
        return internal_points

    cost = rpt.costs.cost_factory(model).fit(features)
    refined_points: list[int] = []
    fixed_boundaries = [0, *internal_points, n_samples]

    for index, coarse_point in enumerate(internal_points, start=1):
        left_bound = fixed_boundaries[index - 1]
        right_bound = fixed_boundaries[index + 1]
        search_start = max(coarse_point - refine_radius, left_bound + min_size)
        search_end = min(coarse_point + refine_radius, right_bound - min_size)

        if search_start > search_end:
            refined_points.append(coarse_point)
            continue

        best_point = coarse_point
        best_cost = float("inf")
        for candidate in range(search_start, search_end + 1):
            candidate_cost = cost.error(left_bound, candidate) + cost.error(
                candidate, right_bound
            )
            if candidate_cost < best_cost:
                best_cost = candidate_cost
                best_point = candidate
        refined_points.append(best_point)

    return sorted(set(refined_points))


class RupturesSegmenter:
    """Two-stage PELT segmenter for multivariate time series."""

    def __init__(
        self,
        model: str = "rbf",
        penalty: float = 10.0,
        min_size: int = 48,
        jump: int = 10,
        refine: bool = True,
        refine_radius: int = 20,
    ) -> None:
        self.model = model
        self.penalty = penalty
        self.min_size = min_size
        self.jump = jump
        self.refine = refine
        self.refine_radius = refine_radius

    def segment(
        self,
        df: pd.DataFrame,
        columns: list[str] | None = None,
    ) -> SegmentationResult:
        """Detect change points and return the final segment boundaries."""

        features = prepare_feature_matrix(df, columns=columns)
        if len(features) < self.min_size * 2:
            raise ValueError(
                f"Need at least {self.min_size * 2} rows for "
                f"min_size={self.min_size}, got {len(features)}."
            )

        algorithm = rpt.Pelt(
            model=self.model,
            min_size=self.min_size,
            jump=self.jump,
        ).fit(features)
        coarse_change_points = algorithm.predict(pen=self.penalty)
        coarse_internal_points = [
            point for point in coarse_change_points if point < len(features)
        ]

        if self.refine:
            internal_change_points = refine_change_points_near_coarse_boundaries(
                features=features,
                coarse_change_points=coarse_internal_points,
                model=self.model,
                min_size=self.min_size,
                refine_radius=self.refine_radius,
            )
            final_change_points = [*internal_change_points, len(features)]
        else:
            internal_change_points = coarse_internal_points
            final_change_points = coarse_change_points

        return SegmentationResult(
            method="ruptures_pelt",
            model=self.model,
            penalty=self.penalty,
            min_size=self.min_size,
            jump=self.jump,
            refine=self.refine,
            refine_radius=self.refine_radius,
            coarse_change_points=coarse_internal_points,
            change_points=internal_change_points,
            segments=segments_from_change_points(
                final_change_points,
                n_samples=len(features),
            ),
        )
