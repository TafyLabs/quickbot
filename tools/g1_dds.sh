#!/usr/bin/env bash
# Gate G1: DDS talker/listener across two host-networked containers.
# Usage: ./tools/g1_dds.sh
set -euo pipefail

IMAGE="quickbot:kilted-base"
LOG=validation/logs/g1_dds.log
mkdir -p "$(dirname "$LOG")"

echo "=== G1 DDS $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG"

# Start listener in the background; capture 10s of output.
docker run --rm -d --name quickbot_g1_listener \
  --network host --ipc host \
  -e ROS_DOMAIN_ID=9 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  "$IMAGE" bash -lc 'source /opt/ros/$ROS_DISTRO/setup.bash && ros2 run demo_nodes_cpp listener'

# Give it a moment to come up.
sleep 2

# Talker for ~10s.
timeout 10 docker run --rm \
  --network host --ipc host \
  -e ROS_DOMAIN_ID=9 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  "$IMAGE" bash -lc 'source /opt/ros/$ROS_DISTRO/setup.bash && ros2 run demo_nodes_cpp talker' \
  2>&1 | tee -a "$LOG" || true

# Capture listener output and stop it.
docker logs quickbot_g1_listener 2>&1 | tee -a "$LOG"
docker stop quickbot_g1_listener >/dev/null 2>&1 || true

if grep -q "I heard:" "$LOG"; then
  echo "PASS: listener received talker messages." | tee -a "$LOG"
  exit 0
else
  echo "FAIL: listener did not receive messages. Check ROS_DOMAIN_ID, RMW, host networking." | tee -a "$LOG"
  exit 1
fi
