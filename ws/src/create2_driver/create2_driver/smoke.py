"""Gate G3 raw-serial smoke test.

Sends OI Start -> Safe -> Drive Direct -> Stop over the serial port. The robot
should move forward at ~100 mm/s for one second, then stop. Run from inside a
container with the serial device passed through.

Usage:
    python3 -m create2_driver.smoke --port /dev/ttyUSB0 --duration 1.0 --speed 100
"""
from __future__ import annotations

import argparse
import time

import serial  # type: ignore[import-not-found]

from create2_driver.oi import (
    BAUD_DEFAULT,
    OP_SAFE,
    OP_START,
    OP_STOP_OI,
    cmd_drive_direct,
    cmd_stop_motion,
)


def run(port: str, duration_s: float, speed_mm_s: int) -> None:
    with serial.Serial(port, BAUD_DEFAULT, timeout=1) as s:
        s.write(bytes([OP_START]))
        s.write(bytes([OP_SAFE]))
        time.sleep(0.1)
        s.write(cmd_drive_direct(speed_mm_s, speed_mm_s))
        time.sleep(duration_s)
        s.write(cmd_stop_motion())
        time.sleep(0.1)
        s.write(bytes([OP_STOP_OI]))


def main() -> None:
    p = argparse.ArgumentParser(description="Create 2 raw-serial smoke test")
    p.add_argument("--port", default="/dev/ttyUSB0")
    p.add_argument("--duration", type=float, default=1.0, help="seconds")
    p.add_argument("--speed", type=int, default=100, help="mm/s per wheel")
    args = p.parse_args()
    run(args.port, args.duration, args.speed)


if __name__ == "__main__":
    main()
