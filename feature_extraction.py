"""Command line entry for segment-level feature extraction."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.feature_extractor import (
    extract_segment_features,
    load_segments,
    load_time_series,
    save_feature_result,
)


DEFAULT_SEGMENT_PATHS = [
    Path("outputs/segmentation/method_a_ruptures.json"),
    Path("outputs/segmentation/method_b_window_stat.json"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract standardized feature matrices from segmentation results."
    )
    parser.add_argument(
        "--input",
        default="data/raw/ETTh1.csv",
        help="Input CSV from IoTDB query or original ETTh1 CSV",
    )
    parser.add_argument(
        "--segments",
        nargs="*",
        type=Path,
        default=None,
        help="Segmentation JSON files. Defaults to Method A and Method B outputs.",
    )
    parser.add_argument(
        "--scaler",
        choices=["standard", "minmax"],
        default="standard",
        help="Feature scaling method",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/features",
        help="Directory for raw/scaled feature matrices and metadata",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = load_time_series(args.input)
    segment_paths = args.segments if args.segments else DEFAULT_SEGMENT_PATHS

    for segment_path in segment_paths:
        method, segments = load_segments(segment_path)
        result = extract_segment_features(
            df=df,
            segments=segments,
            method=method,
            scaler_name=args.scaler,
        )
        raw_path, scaled_path, metadata_path = save_feature_result(
            result,
            output_dir=args.output_dir,
        )
        print(
            f"{method}: {len(result.scaled_features)} segments, "
            f"{len(result.feature_names)} features"
        )
        print(f"Raw features: {raw_path}")
        print(f"Scaled features: {scaled_path}")
        print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
