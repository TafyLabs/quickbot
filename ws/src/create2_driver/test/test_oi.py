"""Unit tests for create2_driver.oi — pure helpers, no hardware required."""
from __future__ import annotations

import math
import struct

import pytest

from create2_driver import oi

# ---------------------------------------------------------------- command builders

def test_drive_direct_layout():
    """Right wheel comes first per OI spec; both signed 16-bit big-endian."""
    cmd = oi.cmd_drive_direct(100, -50)
    assert cmd[0] == oi.OP_DRIVE_DIRECT
    right = struct.unpack(">h", cmd[1:3])[0]
    left = struct.unpack(">h", cmd[3:5])[0]
    assert right == 100
    assert left == -50


def test_stop_motion_is_zero_wheels():
    assert oi.cmd_stop_motion() == oi.cmd_drive_direct(0, 0)


def test_query_list_layout():
    cmd = oi.cmd_query_list([oi.PKT_DISTANCE, oi.PKT_ANGLE])
    assert cmd[0] == oi.OP_QUERY_LIST
    assert cmd[1] == 2  # count
    assert cmd[2] == oi.PKT_DISTANCE
    assert cmd[3] == oi.PKT_ANGLE


def test_query_list_rejects_empty():
    with pytest.raises(ValueError):
        oi.cmd_query_list([])


def test_clamp_wheel_mm_s():
    assert oi.clamp_wheel_mm_s(0) == 0
    assert oi.clamp_wheel_mm_s(123.7) == 124
    assert oi.clamp_wheel_mm_s(9999) == oi.WHEEL_MM_S_MAX
    assert oi.clamp_wheel_mm_s(-9999) == -oi.WHEEL_MM_S_MAX


# --------------------------------------------------------------- query parsing

def test_parse_query_list_signed_and_unsigned():
    payload = (
        struct.pack(">B", 0b0011)         # bump_wheeldrop: both bumps
        + struct.pack(">h", -500)         # distance mm (signed)
        + struct.pack(">h", 45)           # angle deg (signed)
        + struct.pack(">H", 16234)        # voltage mV (unsigned)
        + struct.pack(">h", -250)         # current mA (signed)
    )
    parsed = oi.parse_query_list_response(
        [oi.PKT_BUMP_WHEELDROP, oi.PKT_DISTANCE, oi.PKT_ANGLE, oi.PKT_VOLTAGE, oi.PKT_CURRENT],
        payload,
    )
    assert parsed[oi.PKT_BUMP_WHEELDROP] == 0b0011
    assert parsed[oi.PKT_DISTANCE] == -500
    assert parsed[oi.PKT_ANGLE] == 45
    assert parsed[oi.PKT_VOLTAGE] == 16234
    assert parsed[oi.PKT_CURRENT] == -250


def test_parse_query_list_rejects_truncated():
    with pytest.raises(ValueError, match="truncated"):
        oi.parse_query_list_response([oi.PKT_DISTANCE], b"\x00")  # 1 of 2 bytes


def test_parse_query_list_rejects_trailing_bytes():
    with pytest.raises(ValueError, match="trailing"):
        oi.parse_query_list_response(
            [oi.PKT_VOLTAGE], struct.pack(">H", 16000) + b"\x99",
        )


def test_parse_query_list_rejects_unknown_packet():
    with pytest.raises(ValueError, match="unknown packet"):
        oi.parse_query_list_response([254], b"\x00")


# --------------------------------------------------------------- kinematics

def test_twist_to_wheels_straight():
    wv = oi.twist_to_wheels(0.20, 0.0, wheel_separation_m=0.235)
    assert wv.right_mm_s == 200
    assert wv.left_mm_s == 200


def test_twist_to_wheels_in_place_rotation():
    # +0.7 rad/s ccw, no linear: right > 0, left < 0, magnitudes equal.
    wv = oi.twist_to_wheels(0.0, 0.7, wheel_separation_m=0.235)
    assert wv.right_mm_s > 0
    assert wv.left_mm_s < 0
    assert wv.right_mm_s == -wv.left_mm_s


def test_twist_to_wheels_clamps_to_oi_limit():
    wv = oi.twist_to_wheels(5.0, 0.0, wheel_separation_m=0.235)
    assert wv.right_mm_s == oi.WHEEL_MM_S_MAX
    assert wv.left_mm_s == oi.WHEEL_MM_S_MAX


def test_twist_to_wheels_rejects_bad_track_width():
    with pytest.raises(ValueError):
        oi.twist_to_wheels(0.0, 0.0, wheel_separation_m=0.0)


# --------------------------------------------------------------- odometry integration

def test_odom_pure_translation():
    o = oi.OdomState()
    o.integrate(distance_mm=1000, angle_deg=0)
    assert o.x == pytest.approx(1.0, abs=1e-6)
    assert o.y == pytest.approx(0.0, abs=1e-6)
    assert o.theta == pytest.approx(0.0, abs=1e-6)


def test_odom_pure_rotation():
    o = oi.OdomState()
    o.integrate(distance_mm=0, angle_deg=90)
    assert o.x == pytest.approx(0.0, abs=1e-6)
    assert o.y == pytest.approx(0.0, abs=1e-6)
    assert o.theta == pytest.approx(math.pi / 2.0, abs=1e-6)


def test_odom_arc_midpoint_heading():
    # 90° turn while traveling 1 m: end heading is π/2, end position uses
    # the midpoint heading (π/4).
    o = oi.OdomState()
    o.integrate(distance_mm=1000, angle_deg=90)
    assert o.theta == pytest.approx(math.pi / 2.0, abs=1e-6)
    assert o.x == pytest.approx(math.cos(math.pi / 4.0), abs=1e-6)
    assert o.y == pytest.approx(math.sin(math.pi / 4.0), abs=1e-6)


def test_odom_theta_wraps():
    o = oi.OdomState()
    # Five 90° rotations should leave theta in (−π, π], not at 5π/2.
    for _ in range(5):
        o.integrate(distance_mm=0, angle_deg=90)
    assert -math.pi < o.theta <= math.pi
