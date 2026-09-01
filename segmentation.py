"""Change point detection utilities for multivariate ETTh1 data."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.ruptures_segmenter import RupturesSegmenter, SegmentationResult
from src.window_stat_segmenter import WindowStatSegmenter


def load_dataframe(input_path: str | Path) -> pd.DataFrame:
    """Load a CSV produced by data_loader.py or the original ETTh1 file."""

    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    return pd.read_csv(path)


def segment_with_ruptures(
    df: pd.DataFrame,
    model: str = "rbf",
    penalty: float = 10.0,
    min_size: int = 48,
    jump: int = 1,
    refine: bool = True,
    refine_radius: int = 20,
    columns: list[str] | None = None,
) -> SegmentationResult:
    """Detect multivariate change points with two-stage ruptures PELT."""

    segmenter = RupturesSegmenter(
        model=model,
        penalty=penalty,
        min_size=min_size,
        jump=jump,
        refine=refine,
        refine_radius=refine_radius,
    )
    return segmenter.segment(df, columns=columns)


def save_segments(result: SegmentationResult, output_path: str | Path) -> None:
    """Save segmentation boundaries to JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    payload["segments"] = [list(segment) for segment in result.segments]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def default_output_path(method: str) -> Path:
    """Return an independent default output path for each segmentation method."""

    if method == "ruptures":
        return Path("outputs/segmentation/method_a_ruptures.json")
    if method == "window_stat":
        return Path("outputs/segmentation/method_b_window_stat.json")
    raise ValueError(f"Unsupported segmentation method: {method}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multivariate time series change point detection."
    )
    parser.add_argument(
        "--method",
        choices=["ruptures", "window_stat"],
        default="ruptures",
        help="Segmentation method to run",
    )
    parser.add_argument(
        "--input",
        default="data/processed/etth1_query_sample.csv",
        help="Input CSV from IoTDB query or original ETTh1 CSV",
    )
    parser.add_argument("--model", default="rbf", help="ruptures cost model")
    parser.add_argument("--penalty", type=float, default=10.0)
    parser.add_argument("--min-size", type=int, default=48)
    parser.add_argument("--jump", type=int, default=1)
    parser.add_argument(
        "--refine",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refine coarse change points with unit-resolution local search",
    )
    parser.add_argument(
        "--refine-radius",
        type=int,
        default=20,
        help="Search radius around each coarse change point",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=48,
        help="Window size for method B sliding-window statistics",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.5,
        help="Covariance-distance weight for method B",
    )
    parser.add_argument(
        "--threshold-quantile",
        type=float,
        default=0.95,
        help="Score quantile threshold for method B peak filtering",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for saving segmentation result JSON",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_dataframe(args.input)
    if args.method == "ruptures":
        result = segment_with_ruptures(
            df,
            model=args.model,
            penalty=args.penalty,
            min_size=args.min_size,
            jump=args.jump,
            refine=args.refine,
            refine_radius=args.refine_radius,
        )
    else:
        segmenter = WindowStatSegmenter(
            window_size=args.window_size,
            alpha=args.alpha,
            threshold_quantile=args.threshold_quantile,
            min_size=args.min_size,
        )
        result = segmenter.segment(df)
    output_path = Path(args.output) if args.output else default_output_path(args.method)
    save_segments(result, output_path)
    print(f"Detected {len(result.change_points)} change points")
    if getattr(result, "refine", False):
        print(f"Coarse change points: {result.coarse_change_points}")
        print(f"Refined change points: {result.change_points}")
    if args.method == "window_stat":
        print(f"Threshold: {result.threshold:.6f}")
    print(f"Segments: {result.segments}")
    print(f"Saved result to {output_path}")


if __name__ == "__main__":
    main()
