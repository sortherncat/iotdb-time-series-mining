"""Data import and query utilities for Apache IoTDB.

This module imports the ETTh1 multivariate time series dataset into IoTDB with
batched Session API writes. It also provides a query helper that converts IoTDB
results back into a pandas DataFrame for later analysis.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

try:
    from iotdb.Session import Session
    from iotdb.utils.IoTDBConstants import TSDataType
except ImportError as exc:  # pragma: no cover - depends on local environment
    raise ImportError(
        "Missing IoTDB Python client. Install dependencies with "
        "`pip install -r requirements.txt`."
    ) from exc


SENSOR_COLUMNS = ["HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
MEASUREMENT_NAMES = {
    "HUFL": "high_useful_load",
    "HULL": "high_useless_load",
    "MUFL": "middle_useful_load",
    "MULL": "middle_useless_load",
    "LUFL": "low_useful_load",
    "LULL": "low_useless_load",
    "OT": "oil_temperature",
}


@dataclass(frozen=True)
class IoTDBConfig:
    """Connection settings for a local IoTDB instance."""

    host: str = "127.0.0.1"
    port: str = "6667"
    user: str = "root"
    password: str = "root"
    fetch_size: int = 1024
    zone_id: str = "Asia/Shanghai"


def load_etth1_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load and validate the ETTh1 CSV file."""

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(
            f"ETTh1 CSV not found: {path}. Download it from "
            "https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv"
        )

    df = pd.read_csv(path)
    expected_columns = ["date", *SENSOR_COLUMNS]
    missing_columns = [column for column in expected_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"ETTh1 CSV is missing required columns: {missing_columns}")

    df = df[expected_columns].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset="date")
    df[SENSOR_COLUMNS] = df[SENSOR_COLUMNS].astype(float)
    return df.reset_index(drop=True)


def to_iotdb_timestamps(datetimes: pd.Series) -> list[int]:
    """Convert pandas datetimes to millisecond timestamps used by IoTDB."""

    return (datetimes.astype("int64") // 1_000_000).astype(int).tolist()


def chunk_dataframe(df: pd.DataFrame, batch_size: int) -> Iterable[pd.DataFrame]:
    """Yield fixed-size DataFrame chunks."""

    for start in range(0, len(df), batch_size):
        yield df.iloc[start : start + batch_size]


def create_session(config: IoTDBConfig) -> Session:
    """Create an IoTDB Session object."""

    return Session(
        config.host,
        config.port,
        config.user,
        config.password,
        config.fetch_size,
        config.zone_id,
        enable_redirection=True,
    )


def import_etth1_to_iotdb(
    csv_path: str | Path,
    device_path: str = "root.industry.transformer001",
    batch_size: int = 1000,
    config: IoTDBConfig | None = None,
) -> int:
    """Import ETTh1 into IoTDB using batched records.

    The storage path design is:

    - `root.industry.transformer001.high_useful_load`
    - `root.industry.transformer001.high_useless_load`
    - `root.industry.transformer001.middle_useful_load`
    - `root.industry.transformer001.middle_useless_load`
    - `root.industry.transformer001.low_useful_load`
    - `root.industry.transformer001.low_useless_load`
    - `root.industry.transformer001.oil_temperature`
    """

    df = load_etth1_csv(csv_path)
    config = config or IoTDBConfig()
    measurements = [MEASUREMENT_NAMES[column] for column in SENSOR_COLUMNS]
    data_types = [TSDataType.DOUBLE] * len(measurements)

    session = create_session(config)
    session.open(False)
    try:
        try:
            session.execute_non_query_statement("CREATE DATABASE root.industry")
        except Exception as exc:
            message = str(exc).lower()
            if "already" not in message and "exist" not in message:
                raise

        imported_rows = 0
        for batch in chunk_dataframe(df, batch_size):
            timestamps = to_iotdb_timestamps(batch["date"])
            devices = [device_path] * len(batch)
            measurements_list = [measurements] * len(batch)
            data_types_list = [data_types] * len(batch)
            values_list = batch[SENSOR_COLUMNS].values.tolist()

            session.insert_records(
                devices,
                timestamps,
                measurements_list,
                data_types_list,
                values_list,
            )
            imported_rows += len(batch)
            print(f"Imported {imported_rows}/{len(df)} rows")

        return imported_rows
    finally:
        session.close()


def to_query_timestamp(time_text: str) -> int:
    """Convert a time string to the millisecond timestamp used by IoTDB."""

    return int(pd.Timestamp(time_text).value // 1_000_000)


def query_etth1_from_iotdb(
    start_time: str,
    end_time: str,
    device_path: str = "root.industry.transformer001",
    config: IoTDBConfig | None = None,
) -> pd.DataFrame:
    """Query imported ETTh1 data from IoTDB and return a DataFrame."""

    config = config or IoTDBConfig()
    start_ms = to_query_timestamp(start_time)
    end_ms = to_query_timestamp(end_time)
    measurements = [MEASUREMENT_NAMES[column] for column in SENSOR_COLUMNS]
    select_columns = ", ".join(measurements)
    sql = (
        f"SELECT {select_columns} FROM {device_path} "
        f"WHERE time >= {start_ms} AND time <= {end_ms}"
    )

    session = create_session(config)
    session.open(False)
    try:
        dataset = session.execute_query_statement(sql)
        try:
            df = dataset.todf()
        finally:
            dataset.close_operation_handle()

        if df.empty:
            return df

        rename_columns = {
            f"{device_path}.{measurement}": measurement for measurement in measurements
        }
        df = df.rename(columns=rename_columns)
        if "Time" in df.columns:
            df["datetime"] = pd.to_datetime(df["Time"], unit="ms")
            ordered_columns = ["Time", "datetime", *measurements]
            existing_columns = [column for column in ordered_columns if column in df.columns]
            df = df[existing_columns]
        return df
    finally:
        session.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import and query ETTh1 data with Apache IoTDB."
    )
    subparsers = parser.add_subparsers(dest="command")

    import_parser = subparsers.add_parser(
        "import", help="Import ETTh1 CSV data into IoTDB"
    )
    import_parser.add_argument(
        "--csv", default="data/raw/ETTh1.csv", help="Path to ETTh1.csv"
    )
    import_parser.add_argument(
        "--device",
        default="root.industry.transformer001",
        help="IoTDB device path for ETTh1 measurements",
    )
    import_parser.add_argument("--batch-size", type=int, default=1000)

    query_parser = subparsers.add_parser(
        "query", help="Query ETTh1 data from IoTDB into a pandas DataFrame"
    )
    query_parser.add_argument(
        "--start",
        required=True,
        help='Start time, for example "2016-07-01 00:00:00"',
    )
    query_parser.add_argument(
        "--end",
        required=True,
        help='End time, for example "2016-07-03 00:00:00"',
    )
    query_parser.add_argument(
        "--device",
        default="root.industry.transformer001",
        help="IoTDB device path for ETTh1 measurements",
    )
    query_parser.add_argument(
        "--output",
        help="Optional CSV path for saving the queried DataFrame",
    )

    for subparser in (import_parser, query_parser):
        subparser.add_argument("--host", default="127.0.0.1")
        subparser.add_argument("--port", default="6667")
        subparser.add_argument("--user", default="root")
        subparser.add_argument("--password", default="root")
    argv = sys.argv[1:]
    if not argv or argv[0] not in {"import", "query", "-h", "--help"}:
        argv = ["import", *argv]
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if args.command is None:
        args.command = "import"

    config = IoTDBConfig(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
    )
    if args.command == "import":
        imported_rows = import_etth1_to_iotdb(
            csv_path=args.csv,
            device_path=args.device,
            batch_size=args.batch_size,
            config=config,
        )
        print(f"Finished importing {imported_rows} rows to {args.device}")
    elif args.command == "query":
        df = query_etth1_from_iotdb(
            start_time=args.start,
            end_time=args.end,
            device_path=args.device,
            config=config,
        )
        print(f"Queried {len(df)} rows from {args.device}")
        print(df.head())
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            print(f"Saved query result to {output_path}")


if __name__ == "__main__":
    main()
