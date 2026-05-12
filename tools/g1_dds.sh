#!/usr/bin/env bash
# Gate G1: DDS cross-container smoke. Uses ros2 topic pub/echo so we don't need
# demo_nodes_cpp (not in ros-base).
# Usage: ./tools/g1_dds.sh
set -euo pipefail

IMAGE="${IMAGE:-quickbot:kilted-base}"
LOG=validation/logs/g1_dds.log
mkdir -p "$(dirname "$LOG")"

echo "=== G1 DDS $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG"

cleanup() {
  docker rm -f quickbot_g1_echo  >/dev/null 2>&1 || true
  docker rm -f quickbot_g1_pub   >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

# Subscriber: echo /chatter into stdout.
docker run -d --name quickbot_g1_echo \
  --network host --ipc host \
  -e ROS_DOMAIN_ID=9 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  "$IMAGE" bash -lc '
    source /opt/ros/$ROS_DISTRO/setup.bash
    ros2 topic echo --once /chatter std_msgs/msg/String
  ' >/dev/null

# Give discovery a moment.
sleep 2

# Publisher: send one message.
docker run --rm --name quickbot_g1_pub \
  --network host --ipc host \
  -e ROS_DOMAIN_ID=9 -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  "$IMAGE" bash -lc '
    source /opt/ros/$ROS_DISTRO/setup.bash
    # --once shuts down after one publish; we need at least one in-flight when subscriber starts.
    ros2 topic pub --times 5 --rate 2 /chatter std_msgs/msg/String "{data: hello from container A}"
  ' 2>&1 | tee -a "$LOG" || true

# Wait briefly for echo container to capture + exit (ros2 topic echo --once exits after first message).
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if [[ "$(docker inspect -f '{{.State.Running}}' quickbot_g1_echo 2>/dev/null)" == "false" ]]; then
    break
  fi
  sleep 1
done

echo "-- echo container output --" | tee -a "$LOG"
docker logs quickbot_g1_echo 2>&1 | tee -a "$LOG"

if grep -q "hello from container A" "$LOG"; then
  echo "PASS: subscriber received publisher message across containers." | tee -a "$LOG"
  exit 0
else
  echo "FAIL: no message received. Check ROS_DOMAIN_ID, RMW, host networking, firewall." | tee -a "$LOG"
  exit 1
fi
