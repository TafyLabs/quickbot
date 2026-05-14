"""Create 2 Open Interface — opcodes, packet IDs, and pure parsing helpers.

Reference: iRobot Create 2 / Roomba Open Interface specification.
Pure functions only — no I/O. Everything in here is unit-testable without a
serial port.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

# ---- opcodes ----------------------------------------------------------------

OP_START = 128
OP_BAUD = 129
OP_SAFE = 131
OP_FULL = 132
OP_DRIVE = 137
OP_DRIVE_DIRECT = 145  # right (mm/s), left (mm/s) — both signed 16-bit BE
OP_DRIVE_PWM = 146
OP_LEDS = 139
OP_STOP_OI = 173
OP_SENSORS = 142       # request one packet
OP_QUERY_LIST = 149    # request multiple packets in one response
OP_STREAM = 148
OP_PAUSE_STREAM = 150

BAUD_DEFAULT = 115200

# ---- packet IDs (a small, useful subset) -----------------------------------

PKT_BUMP_WHEELDROP = 7         # 1 byte: bit0 bump right, bit1 bump left,
                               #         bit2 wheel-drop right, bit3 wheel-drop left
PKT_CLIFF_LEFT = 9             # 1 byte: 1 = cliff
PKT_CLIFF_FRONT_LEFT = 10
PKT_CLIFF_FRONT_RIGHT = 11
PKT_CLIFF_RIGHT = 12

PKT_DISTANCE = 19              # signed 16-bit BE, mm since last read. Saturates ±32768.
PKT_ANGLE = 20                 # signed 16-bit BE, degrees CCW since last read.

PKT_CHARGING_STATE = 21        # 1 byte: 0 not charging, 1-4 charging states, 5 fault
PKT_VOLTAGE = 22               # unsigned 16-bit BE, mV
PKT_CURRENT = 23               # signed 16-bit BE, mA (+ charging, − discharging)
PKT_TEMPERATURE = 24           # signed 8-bit, °C
PKT_BATTERY_CHARGE = 25        # unsigned 16-bit BE, mAh
PKT_BATTERY_CAPACITY = 26      # unsigned 16-bit BE, mAh

PKT_OI_MODE = 35               # 1 byte: 0 off, 1 passive, 2 safe, 3 full

# (packet_id, byte_width, signed?)
PKT_SPEC: dict[int, tuple[int, bool]] = {
    PKT_BUMP_WHEELDROP: (1, False),
    PKT_CLIFF_LEFT: (1, False),
    PKT_CLIFF_FRONT_LEFT: (1, False),
    PKT_CLIFF_FRONT_RIGHT: (1, False),
    PKT_CLIFF_RIGHT: (1, False),
    PKT_DISTANCE: (2, True),
    PKT_ANGLE: (2, True),
    PKT_CHARGING_STATE: (1, False),
    PKT_VOLTAGE: (2, False),
    PKT_CURRENT: (2, True),
    PKT_TEMPERATURE: (1, True),
    PKT_BATTERY_CHARGE: (2, False),
    PKT_BATTERY_CAPACITY: (2, False),
    PKT_OI_MODE: (1, False),
}

WHEEL_MM_S_MAX = 500  # OI spec hard limit for Drive Direct.


# ---- command builders -------------------------------------------------------

def _i16_be(v: int) -> bytes:
    return struct.pack(">h", int(v))


def cmd_drive_direct(right_mm_s: int, left_mm_s: int) -> bytes:
    """Build a Drive Direct command. Right wheel comes first per OI spec."""
    return bytes([OP_DRIVE_DIRECT]) + _i16_be(right_mm_s) + _i16_be(left_mm_s)


def cmd_stop_motion() -> bytes:
    return cmd_drive_direct(0, 0)


def cmd_query_list(packet_ids: list[int]) -> bytes:
    """Build a Query List command — request several packets in one round-trip."""
    if not packet_ids:
        raise ValueError("packet_ids must be non-empty")
    return bytes([OP_QUERY_LIST, len(packet_ids)] + list(packet_ids))


def clamp_wheel_mm_s(v: float) -> int:
    """Clamp a wheel velocity (mm/s) to the OI hard limit and round to int."""
    return int(max(-WHEEL_MM_S_MAX, min(WHEEL_MM_S_MAX, round(v))))


# ---- response parser --------------------------------------------------------

def parse_query_list_response(packet_ids: list[int], payload: bytes) -> dict[int, int]:
    """Parse the bytes returned for an OP_QUERY_LIST request.

    The Create 2 returns packets in the same order as requested, concatenated
    with no framing. Each packet's width is fixed and known from PKT_SPEC.

    Returns a dict {packet_id: value}.
    Raises ValueError on truncated payload or unknown packet ID.
    """
    out: dict[int, int] = {}
    cursor = 0
    for pid in packet_ids:
        if pid not in PKT_SPEC:
            raise ValueError(f"unknown packet id: {pid}")
        width, signed = PKT_SPEC[pid]
        chunk = payload[cursor:cursor + width]
        if len(chunk) != width:
            raise ValueError(
                f"truncated payload at packet {pid}: "
                f"expected {width} bytes, got {len(chunk)}"
            )
        cursor += width
        if width == 1:
            out[pid] = struct.unpack(">b" if signed else ">B", chunk)[0]
        elif width == 2:
            out[pid] = struct.unpack(">h" if signed else ">H", chunk)[0]
        else:
            raise ValueError(f"unsupported width {width} for packet {pid}")
    if cursor != len(payload):
        raise ValueError(
            f"trailing bytes in payload: consumed {cursor} of {len(payload)}"
        )
    return out


# ---- differential drive kinematics -----------------------------------------

@dataclass(frozen=True)
class WheelVelocities:
    right_mm_s: int
    left_mm_s: int


def twist_to_wheels(
    linear_mps: float,
    angular_rps: float,
    wheel_separation_m: float,
) -> WheelVelocities:
    """Convert a unicycle twist to differential wheel velocities in mm/s.

    Standard kinematics:
        v_r = v + (omega * L / 2)
        v_l = v - (omega * L / 2)
    where v is linear (m/s), omega is angular (rad/s), L is track width (m).
    """
    if wheel_separation_m <= 0:
        raise ValueError("wheel_separation_m must be positive")
    half_l = wheel_separation_m / 2.0
    v_r_mm_s = (linear_mps + angular_rps * half_l) * 1000.0
    v_l_mm_s = (linear_mps - angular_rps * half_l) * 1000.0
    return WheelVelocities(
        right_mm_s=clamp_wheel_mm_s(v_r_mm_s),
        left_mm_s=clamp_wheel_mm_s(v_l_mm_s),
    )


# ---- odometry integration ---------------------------------------------------

@dataclass
class OdomState:
    """Planar pose accumulator.  Units: m, m, rad."""
    x: float = 0.0
    y: float = 0.0
    theta: float = 0.0

    def integrate(self, distance_mm: int, angle_deg: int) -> None:
        """Apply one Distance/Angle packet pair.

        Create 2 packets 19 + 20 report deltas since the last read. Order
        matters: the spec is ambiguous on midpoint vs trapezoidal, so we use
        the simple midpoint-heading model. For the speeds we run (< 0.22 m/s)
        the difference is sub-millimeter per tick.
        """
        d_m = distance_mm / 1000.0
        d_theta = math.radians(angle_deg)
        mid = self.theta + d_theta / 2.0
        self.x += d_m * math.cos(mid)
        self.y += d_m * math.sin(mid)
        self.theta = _wrap_angle(self.theta + d_theta)


def _wrap_angle(a: float) -> float:
    """Wrap to (−π, π]."""
    return math.atan2(math.sin(a), math.cos(a))
