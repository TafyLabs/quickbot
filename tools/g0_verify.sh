#!/usr/bin/env bash
# Gate G0 post-build verification.
# Usage: ./tools/g0_verify.sh
set -euo pipefail

IMAGE="quickbot:kilted-base"
LOG=validation/logs/g0_verify.log
mkdir -p "$(dirname "$LOG")"

echo "=== G0 verify $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "FAIL: image $IMAGE not found. Run G0 build first." | tee -a "$LOG"
  exit 1
fi

echo "-- ros2 doctor --" | tee -a "$LOG"
docker run --rm "$IMAGE" bash -lc \
  'source /opt/ros/$ROS_DISTRO/setup.bash && ros2 doctor --report' 2>&1 | tee -a "$LOG"

echo "-- ros2 pkg list (count) --" | tee -a "$LOG"
docker run --rm "$IMAGE" bash -lc \
  'source /opt/ros/$ROS_DISTRO/setup.bash && ros2 pkg list | wc -l' 2>&1 | tee -a "$LOG"

echo "PASS: G0 verification complete. Append result to validation/gates.md." | tee -a "$LOG"
