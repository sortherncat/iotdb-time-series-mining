#!/usr/bin/env bash
set -euo pipefail

IOTDB_VERSION="2.0.4"
ARCHIVE_NAME="apache-iotdb-${IOTDB_VERSION}-all-bin.zip"
IOTDB_DIR="apache-iotdb-${IOTDB_VERSION}-all-bin"
DOWNLOAD_URL="https://archive.apache.org/dist/iotdb/${IOTDB_VERSION}/${ARCHIVE_NAME}"

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
THIRD_PARTY_DIR="${PROJECT_ROOT}/third_party"
ARCHIVE_PATH="${THIRD_PARTY_DIR}/${ARCHIVE_NAME}"
IOTDB_PATH="${THIRD_PARTY_DIR}/${IOTDB_DIR}"

mkdir -p "${THIRD_PARTY_DIR}"

if ! command -v java >/dev/null 2>&1; then
  echo "Java is required but was not found. Please install JDK 8 or later first."
  exit 1
fi

if [ ! -f "${ARCHIVE_PATH}" ]; then
  echo "Downloading Apache IoTDB ${IOTDB_VERSION}..."
  curl -L --fail -o "${ARCHIVE_PATH}" "${DOWNLOAD_URL}"
else
  echo "Found existing archive: ${ARCHIVE_PATH}"
fi

if [ ! -d "${IOTDB_PATH}" ]; then
  echo "Extracting Apache IoTDB..."
  unzip -q "${ARCHIVE_PATH}" -d "${THIRD_PARTY_DIR}"
else
  echo "Found existing IoTDB directory: ${IOTDB_PATH}"
fi

DATANODE_ENV="${IOTDB_PATH}/conf/datanode-env.sh"
if grep -q -- "-Xss512k" "${DATANODE_ENV}"; then
  echo "Updating DataNode JVM stack size from -Xss512k to -Xss1m..."
  sed -i.bak 's/-Xss512k/-Xss1m/g' "${DATANODE_ENV}"
fi

echo "Apache IoTDB is ready at: ${IOTDB_PATH}"
echo "Start it with: bash scripts/start_iotdb.sh"
