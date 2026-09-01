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
./sbin/start-standalone.sh

echo "Apache IoTDB startup command finished."
echo "Waiting for IoTDB RPC service on 127.0.0.1:6667..."

for attempt in $(seq 1 30); do
  if ./sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u root -pw root -e "show databases" >/dev/null 2>&1; then
    echo "Apache IoTDB is ready."
    echo "Verify with: bash scripts/check_iotdb.sh"
    exit 0
  fi
  sleep 2
done

echo "IoTDB did not become ready within 60 seconds."
echo "Check logs under: ${IOTDB_PATH}/logs"
exit 1
