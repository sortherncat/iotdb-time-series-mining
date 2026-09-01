#!/usr/bin/env bash
set -euo pipefail

IOTDB_VERSION="2.0.4"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IOTDB_PATH="${PROJECT_ROOT}/third_party/apache-iotdb-${IOTDB_VERSION}-all-bin"

if [ ! -d "${IOTDB_PATH}" ]; then
  echo "Apache IoTDB is not installed yet. Nothing to stop."
  exit 0
fi

cd "${IOTDB_PATH}"
./sbin/stop-standalone.sh

echo "Apache IoTDB stop command finished."
