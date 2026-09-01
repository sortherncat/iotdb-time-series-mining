#!/usr/bin/env bash
set -euo pipefail

IOTDB_VERSION="2.0.4"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOTDB_PATH="${PROJECT_ROOT}/third_party/apache-iotdb-${IOTDB_VERSION}-all-bin"

if [ ! -d "${IOTDB_PATH}" ]; then
  echo "Apache IoTDB is not installed yet. Run: bash scripts/setup_iotdb.sh"
  exit 1
fi

cd "${IOTDB_PATH}"
if ! ./sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u root -pw root -e "show databases"; then
  echo
  echo "Failed to connect to IoTDB at 127.0.0.1:6667."
  echo "Please make sure IoTDB is running:"
  echo "  bash scripts/start_iotdb.sh"
  echo
  echo "If startup just finished, wait a few seconds and retry."
  echo "Logs are under: ${IOTDB_PATH}/logs"
  exit 1
fi
