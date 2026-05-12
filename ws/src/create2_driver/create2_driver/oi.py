"""Create 2 Open Interface opcodes and helpers.

Reference: iRobot Create 2 / Roomba Open Interface specification.
Only the subset needed for QuickBot bring-up is exposed.
"""
from __future__ import annotations

import struct

# Opcodes (per Create 2 OI spec).
OP_START = 128
OP_BAUD = 129
OP_SAFE = 131
OP_FULL = 132
OP_DRIVE = 137  # radius-based drive
OP_DRIVE_DIRECT = 145  # independent wheel velocities (mm/s)
OP_DRIVE_PWM = 146
OP_LEDS = 139
OP_STOP_OI = 173
OP_SENSORS = 142
OP_STREAM = 148
OP_PAUSE_STREAM = 150

BAUD_DEFAULT = 115200


def i16_be(value: int) -> bytes:
    """Pack a signed 16-bit integer in big-endian byte order (OI convention)."""
    return struct.pack(">h", int(value))


def cmd_drive_direct(right_mm_s: int, left_mm_s: int) -> bytes:
    """Build a Drive Direct command. Right wheel comes first per OI spec."""
    return bytes([OP_DRIVE_DIRECT]) + i16_be(right_mm_s) + i16_be(left_mm_s)


def cmd_stop_motion() -> bytes:
    return cmd_drive_direct(0, 0)
