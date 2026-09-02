#!/usr/bin/env bash
set -euo pipefail

IOTDB_HOST="${IOTDB_HOST:-iotdb}"
IOTDB_PORT="${IOTDB_PORT:-6667}"
DATASET_PATH="${DATASET_PATH:-data/raw/ETTh1.csv}"
ETTH1_BUNDLED_PATH="${ETTH1_BUNDLED_PATH:-/opt/datasets/ETTh1.csv}"

mkdir -p data/raw data/processed outputs

if [ ! -f "${DATASET_PATH}" ]; then
  if [ -f "${ETTH1_BUNDLED_PATH}" ]; then
    echo "Copying bundled ETTh1 dataset from ${ETTH1_BUNDLED_PATH}..."
    cp "${ETTH1_BUNDLED_PATH}" "${DATASET_PATH}"
  else
    echo "Downloading ETTh1 dataset..."
    curl -L --fail -o "${DATASET_PATH}" \
      https://raw.githubusercontent.com/zhouhaoyi/ETDataset/main/ETT-small/ETTh1.csv
  fi
fi

python scripts/wait_for_iotdb.py --host "${IOTDB_HOST}" --port "${IOTDB_PORT}"

python data_loader.py import \
  --csv "${DATASET_PATH}" \
  --host "${IOTDB_HOST}" \
  --port "${IOTDB_PORT}" \
  --batch-size 1000 \
  --reset-database

python data_loader.py query \
  --start "2016-07-01 00:00:00" \
  --end "2016-07-03 00:00:00" \
  --host "${IOTDB_HOST}" \
  --port "${IOTDB_PORT}" \
  --output data/processed/etth1_query_sample.csv

python segmentation.py \
  --method ruptures \
  --input "${DATASET_PATH}" \
  --model rbf \
  --penalty 10 \
  --min-size 48 \
  --jump 10 \
  --refine \
  --refine-radius 20

python segmentation.py \
  --method window_stat \
  --input "${DATASET_PATH}" \
  --window-size 48 \
  --alpha 0.5 \
  --threshold-quantile 0.95 \
  --min-size 48

python feature_extraction.py --input "${DATASET_PATH}" --scaler standard
python clustering.py --input "${DATASET_PATH}" --min-k 2 --max-k 8
python scripts/prepare_frontend_data.py

echo "Pipeline finished. Open http://localhost:5173/ after the frontend service starts."
