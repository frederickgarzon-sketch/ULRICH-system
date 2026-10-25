#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${1:-http://127.0.0.1:8090}"
echo "Camera devices:"
v4l2-ctl --list-devices
echo
echo "Camera-node health:"
curl --fail --silent --show-error "$BASE_URL/health"
echo
for stream in face body; do
  curl --fail --silent --max-time 3 "$BASE_URL/stream/$stream" --output "/tmp/${stream}-stream-check.mjpeg" || true
  bytes="$(wc -c < "/tmp/${stream}-stream-check.mjpeg" 2>/dev/null || echo 0)"
  echo "$stream stream captured $bytes bytes in 3 seconds"
done
vcgencmd measure_temp 2>/dev/null || true
