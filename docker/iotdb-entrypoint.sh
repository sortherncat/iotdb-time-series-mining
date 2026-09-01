#!/usr/bin/env bash
set -euo pipefail

cd "${IOTDB_HOME}"
mkdir -p logs data

./sbin/start-standalone.sh

echo "IoTDB standalone startup command finished."
echo "Container will keep running and stream IoTDB logs."

touch logs/log_datanode_all.log logs/log_confignode_all.log
tail -F logs/log_datanode_all.log logs/log_confignode_all.log
