"""Command line entry for clustering segment feature matrices."""

from __future__ import annotations

import argparse
import os
import warnings
from pathlib import Path

import pandas as pd

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
warnings.filterwarnings(
    "ignore",
    message="Could not find the number of physical cores.*",
    category=UserWarning,
)

from src.clusterer import cluster_feature_matrix, save_clustering_result


DEFAULT_FEATURE_PATHS = [
    Path("outputs/features/ruptures_pelt_features_scaled.csv"),
    Path("outputs/features/window_stat_distance_features_scaled.csv"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cluster segment feature matrices and assign operating IDs."
    )
    parser.add_argument(
        "--input",
        default="data/raw/ETTh1.csv",
        help="Original ETTh1 CSV or IoTDB query CSV for timestamp mapping",
    )
    parser.add_argument(
        "--features",
        nargs="*",
        type=Path,
        default=None,
        help="Scaled feature matrix CSV files. Defaults to Method A and B outputs.",
    )
    parser.add_argument(
        "--algorithms",
        nargs="+",
        choices=["kmeans", "gmm"],
        default=["kmeans", "gmm"],
        help="Clustering algorithms to compare",
    )
    parser.add_argument("--min-k", type=int, default=2)
    parser.add_argument("--max-k", type=int, default=8)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--output-dir",
        default="outputs/clustering",
        help="Directory for clustering assignments, summaries, and metrics",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    feature_paths = args.features if args.features else DEFAULT_FEATURE_PATHS
    comparison_rows = []

    for feature_path in feature_paths:
        for algorithm in args.algorithms:
            result = cluster_feature_matrix(
                feature_path=feature_path,
                input_data_path=args.input,
                algorithm=algorithm,
                min_k=args.min_k,
                max_k=args.max_k,
                random_state=args.random_state,
            )
            assignments_path, summary_path, metrics_path = save_clustering_result(
                result,
                output_dir=args.output_dir,
            )
            print(
                f"{result.feature_method} / {algorithm}: "
                f"selected K={result.selected_k}, "
                f"conditions={len(result.condition_summary)}"
            )
            print(f"Assignments: {assignments_path}")
            print(f"Summary: {summary_path}")
            print(f"Metrics: {metrics_path}")

            selected_metric = next(
                metric for metric in result.metrics if metric.k == result.selected_k
            )
            comparison_rows.append(
                {
                    "feature_method": result.feature_method,
                    "algorithm": result.algorithm,
                    "selected_k": result.selected_k,
                    "condition_count": len(result.condition_summary),
                    "silhouette_score": selected_metric.silhouette_score,
                    "calinski_harabasz_score": selected_metric.calinski_harabasz_score,
                }
            )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison_path = output_dir / "algorithm_comparison.csv"
    pd.DataFrame(comparison_rows).to_csv(comparison_path, index=False)
    print(f"Algorithm comparison: {comparison_path}")


if __name__ == "__main__":
    main()
