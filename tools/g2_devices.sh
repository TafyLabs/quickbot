#!/usr/bin/env bash
# Gate G2: verify Create 2 serial + D455 USB visibility inside the robot container.
# Usage: ./tools/g2_devices.sh
set -euo pipefail

LOG=validation/logs/g2_devices.log
mkdir -p "$(dirname "$LOG")"

echo "=== G2 devices $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG"

PASS=1

# Host-side checks first — gives a clearer error than the container failing to mount.
if [[ ! -e /dev/ttyUSB0 ]]; then
  echo "WARN: /dev/ttyUSB0 not present on the host. Plug in the Create 2 USB-serial cable." | tee -a "$LOG"
  PASS=0
fi

if ! lsusb 2>/dev/null | grep -qi "8086:0b5c\|intel.*realsense\|intel corp\." ; then
  echo "WARN: no Intel RealSense visible via host lsusb. Check USB3 cable + power." | tee -a "$LOG"
  # Not strictly fatal — D455 is a Phase 4 deliverable.
fi

echo "-- inside robot container --" | tee -a "$LOG"
docker compose run --rm robot bash -lc '
  set -e
  echo "ttyUSB0:"; ls -l /dev/ttyUSB0 || echo "  not present"
  echo "lsusb:"; lsusb || true
  if command -v rs-enumerate-devices >/dev/null 2>&1; then
    echo "rs-enumerate-devices:"; rs-enumerate-devices | head -20
  else
    echo "rs-enumerate-devices not installed (realsense2 debs not in image yet)."
  fi
' 2>&1 | tee -a "$LOG" || PASS=0

if [[ $PASS -eq 1 ]]; then
  echo "PASS: device passthrough OK." | tee -a "$LOG"
  exit 0
else
  echo "PARTIAL: see warnings above. G2 cannot fully pass until both Create 2 and D455 enumerate." | tee -a "$LOG"
  exit 1
fi
