"""create2_driver ROS 2 node — Phase 3 / Gate G4 deliverable.

Inputs:
    /cmd_vel  geometry_msgs/Twist

Outputs:
    /odom            nav_msgs/Odometry
    /tf              odom -> base_link  (TransformStamped)
    /battery_state   sensor_msgs/BatteryState
    /diagnostics     diagnostic_msgs/DiagnosticArray

Parameters (see config/create2_calibration.yaml):
    serial_port, baud, wheel_separation_m, wheel_radius_m,
    odom_linear_scale, odom_angular_scale,
    max_linear_mps, max_angular_rps, cmd_timeout_s,
    poll_hz

Safety:
    * Enters OI Safe mode on start (opcode 131).
    * Drive Direct 0 + OI Stop on shutdown.
    * Zero velocity override if no /cmd_vel arrives within cmd_timeout_s.
    * Zero velocity override on any bump or cliff sensor active.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

import rclpy
import serial  # pyserial; installed via python3-serial in the robot image.
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from geometry_msgs.msg import TransformStamped, Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Header
from tf2_ros import TransformBroadcaster

from create2_driver import oi

SENSOR_PACKETS = [
    oi.PKT_BUMP_WHEELDROP,
    oi.PKT_CLIFF_LEFT,
    oi.PKT_CLIFF_FRONT_LEFT,
    oi.PKT_CLIFF_FRONT_RIGHT,
    oi.PKT_CLIFF_RIGHT,
    oi.PKT_DISTANCE,
    oi.PKT_ANGLE,
    oi.PKT_CHARGING_STATE,
    oi.PKT_VOLTAGE,
    oi.PKT_CURRENT,
    oi.PKT_TEMPERATURE,
    oi.PKT_BATTERY_CHARGE,
    oi.PKT_BATTERY_CAPACITY,
    oi.PKT_OI_MODE,
]


@dataclass
class SensorSnapshot:
    bump_left: bool = False
    bump_right: bool = False
    cliff_any: bool = False
    voltage_v: float = 0.0
    current_a: float = 0.0
    temperature_c: float = 0.0
    charge_ah: float = 0.0
    capacity_ah: float = 0.0
    charging_state: int = 0
    oi_mode: int = 0


class Create2DriverNode(Node):
    """ROS 2 wrapper around the OI serial driver."""

    def __init__(self) -> None:
        super().__init__("create2_driver")

        # ---- params --------------------------------------------------------
        p = self.declare_parameter
        self.serial_port = p("serial_port", "/dev/ttyUSB0").value
        self.baud = int(p("baud", oi.BAUD_DEFAULT).value)
        self.wheel_separation_m = float(p("wheel_separation_m", 0.235).value)
        self.odom_linear_scale = float(p("odom_linear_scale", 1.0).value)
        self.odom_angular_scale = float(p("odom_angular_scale", 1.0).value)
        self.max_linear_mps = float(p("max_linear_mps", 0.20).value)
        self.max_angular_rps = float(p("max_angular_rps", 0.7).value)
        self.cmd_timeout_s = float(p("cmd_timeout_s", 0.5).value)
        self.poll_hz = float(p("poll_hz", 20.0).value)
        self.base_frame = p("base_frame", "base_link").value
        self.odom_frame = p("odom_frame", "odom").value

        # ---- state ---------------------------------------------------------
        self._odom = oi.OdomState()
        self._snapshot = SensorSnapshot()
        self._last_cmd_time = self.get_clock().now()
        self._cmd_lock = threading.Lock()
        self._latest_cmd = Twist()
        self._io_stop = threading.Event()
        self._serial: serial.Serial | None = None

        # ---- ROS interfaces -----------------------------------------------
        odom_qos = QoSProfile(depth=10, reliability=QoSReliabilityPolicy.RELIABLE)
        battery_qos = QoSProfile(
            depth=1,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._odom_pub = self.create_publisher(Odometry, "odom", odom_qos)
        self._battery_pub = self.create_publisher(BatteryState, "battery_state", battery_qos)
        self._diag_pub = self.create_publisher(DiagnosticArray, "/diagnostics", 10)
        self._tf = TransformBroadcaster(self)

        self._cmd_sub = self.create_subscription(
            Twist, "cmd_vel", self._on_cmd_vel, 10,
        )

        # ---- I/O -----------------------------------------------------------
        self._open_serial()
        self._io_thread = threading.Thread(target=self._io_loop, name="create2_io", daemon=True)
        self._io_thread.start()

        # Publishing happens in the I/O thread to keep the snapshot fresh.
        self.get_logger().info(
            f"create2_driver up on {self.serial_port} @ {self.baud}, "
            f"wheel_separation={self.wheel_separation_m} m, poll_hz={self.poll_hz}",
        )

    # ------------------------------------------------------------------ serial
    def _open_serial(self) -> None:
        self._serial = serial.Serial(self.serial_port, self.baud, timeout=0.1)
        # Boot sequence per master plan §8.
        self._serial.write(bytes([oi.OP_START]))
        time.sleep(0.05)
        self._serial.write(bytes([oi.OP_SAFE]))
        time.sleep(0.05)

    def _close_serial(self) -> None:
        if self._serial is None:
            return
        try:
            self._serial.write(oi.cmd_stop_motion())
            time.sleep(0.02)
            self._serial.write(bytes([oi.OP_STOP_OI]))
            time.sleep(0.02)
        finally:
            self._serial.close()
            self._serial = None

    # -------------------------------------------------------------- /cmd_vel
    def _on_cmd_vel(self, msg: Twist) -> None:
        with self._cmd_lock:
            self._latest_cmd = msg
            self._last_cmd_time = self.get_clock().now()

    def _current_cmd_wheels(self) -> oi.WheelVelocities:
        with self._cmd_lock:
            t = self._latest_cmd
            last = self._last_cmd_time

        # Timeout stop.
        age_s = (self.get_clock().now() - last).nanoseconds / 1e9
        if age_s > self.cmd_timeout_s:
            return oi.WheelVelocities(0, 0)

        # Safety override on bump / cliff.
        if self._snapshot.bump_left or self._snapshot.bump_right or self._snapshot.cliff_any:
            return oi.WheelVelocities(0, 0)

        linear = max(-self.max_linear_mps, min(self.max_linear_mps, t.linear.x))
        angular = max(-self.max_angular_rps, min(self.max_angular_rps, t.angular.z))
        return oi.twist_to_wheels(linear, angular, self.wheel_separation_m)

    # ------------------------------------------------------------------ I/O loop
    def _io_loop(self) -> None:
        period = 1.0 / max(1.0, self.poll_hz)
        next_tick = time.monotonic()
        while not self._io_stop.is_set():
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001 - keep robot safe
                self.get_logger().error(f"io tick failed: {exc!r}")
                # Best-effort halt on the bus.
                self._safe_write(oi.cmd_stop_motion())
            next_tick += period
            sleep_s = next_tick - time.monotonic()
            if sleep_s > 0:
                time.sleep(sleep_s)
            else:
                next_tick = time.monotonic()  # we fell behind; resync

    def _safe_write(self, data: bytes) -> None:
        s = self._serial
        if s is None:
            return
        try:
            s.write(data)
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f"serial write failed: {exc!r}")

    def _tick(self) -> None:
        if self._serial is None:
            return

        # Send wheel command first so latency is minimized.
        wheels = self._current_cmd_wheels()
        self._safe_write(oi.cmd_drive_direct(wheels.right_mm_s, wheels.left_mm_s))

        # Request sensor packets.
        self._serial.reset_input_buffer()
        self._serial.write(oi.cmd_query_list(SENSOR_PACKETS))
        expected = sum(oi.PKT_SPEC[pid][0] for pid in SENSOR_PACKETS)
        payload = self._serial.read(expected)
        if len(payload) != expected:
            # Common during startup; warn but don't crash.
            return
        try:
            packets = oi.parse_query_list_response(SENSOR_PACKETS, payload)
        except ValueError as exc:
            self.get_logger().warning(f"packet parse: {exc}")
            return

        # Update odometry.
        d_mm = packets[oi.PKT_DISTANCE] * self.odom_linear_scale
        d_deg = packets[oi.PKT_ANGLE] * self.odom_angular_scale
        self._odom.integrate(int(round(d_mm)), int(round(d_deg)))

        # Update sensor snapshot.
        bump = packets[oi.PKT_BUMP_WHEELDROP]
        self._snapshot.bump_right = bool(bump & 0b0001)
        self._snapshot.bump_left = bool(bump & 0b0010)
        self._snapshot.cliff_any = any(
            packets[pid]
            for pid in (
                oi.PKT_CLIFF_LEFT,
                oi.PKT_CLIFF_FRONT_LEFT,
                oi.PKT_CLIFF_FRONT_RIGHT,
                oi.PKT_CLIFF_RIGHT,
            )
        )
        self._snapshot.voltage_v = packets[oi.PKT_VOLTAGE] / 1000.0
        self._snapshot.current_a = packets[oi.PKT_CURRENT] / 1000.0
        self._snapshot.temperature_c = float(packets[oi.PKT_TEMPERATURE])
        self._snapshot.charge_ah = packets[oi.PKT_BATTERY_CHARGE] / 1000.0
        self._snapshot.capacity_ah = max(packets[oi.PKT_BATTERY_CAPACITY], 1) / 1000.0
        self._snapshot.charging_state = packets[oi.PKT_CHARGING_STATE]
        self._snapshot.oi_mode = packets[oi.PKT_OI_MODE]

        # Publish.
        now = self.get_clock().now().to_msg()
        self._publish_odom(now)
        self._publish_battery(now)
        self._publish_diagnostics(now)

    # ----------------------------------------------------------- publishers
    def _publish_odom(self, stamp) -> None:
        msg = Odometry()
        msg.header = Header(stamp=stamp, frame_id=self.odom_frame)
        msg.child_frame_id = self.base_frame
        msg.pose.pose.position.x = self._odom.x
        msg.pose.pose.position.y = self._odom.y
        msg.pose.pose.orientation.z = math.sin(self._odom.theta / 2.0)
        msg.pose.pose.orientation.w = math.cos(self._odom.theta / 2.0)
        # Twist filled in once we add encoder-derived velocity; leave zero for now.
        self._odom_pub.publish(msg)

        tf = TransformStamped()
        tf.header.stamp = stamp
        tf.header.frame_id = self.odom_frame
        tf.child_frame_id = self.base_frame
        tf.transform.translation.x = self._odom.x
        tf.transform.translation.y = self._odom.y
        tf.transform.rotation.z = math.sin(self._odom.theta / 2.0)
        tf.transform.rotation.w = math.cos(self._odom.theta / 2.0)
        self._tf.sendTransform(tf)

    def _publish_battery(self, stamp) -> None:
        b = BatteryState()
        b.header = Header(stamp=stamp, frame_id=self.base_frame)
        b.voltage = self._snapshot.voltage_v
        b.current = self._snapshot.current_a
        b.charge = self._snapshot.charge_ah
        b.capacity = self._snapshot.capacity_ah
        if self._snapshot.capacity_ah > 0:
            b.percentage = max(0.0, min(1.0, self._snapshot.charge_ah / self._snapshot.capacity_ah))
        b.temperature = self._snapshot.temperature_c
        b.power_supply_status = (
            BatteryState.POWER_SUPPLY_STATUS_CHARGING
            if self._snapshot.charging_state in (1, 2, 3)
            else BatteryState.POWER_SUPPLY_STATUS_DISCHARGING
        )
        b.present = True
        self._battery_pub.publish(b)

    def _publish_diagnostics(self, stamp) -> None:
        arr = DiagnosticArray()
        arr.header = Header(stamp=stamp, frame_id=self.base_frame)
        s = DiagnosticStatus()
        s.name = "create2_driver"
        s.hardware_id = self.serial_port
        if self._snapshot.cliff_any:
            s.level = DiagnosticStatus.ERROR
            s.message = "cliff sensor active — velocity overridden to zero"
        elif self._snapshot.bump_left or self._snapshot.bump_right:
            s.level = DiagnosticStatus.WARN
            s.message = "bump active — velocity overridden to zero"
        else:
            s.level = DiagnosticStatus.OK
            s.message = "ok"
        s.values = [
            KeyValue(key="oi_mode", value=str(self._snapshot.oi_mode)),
            KeyValue(key="voltage_v", value=f"{self._snapshot.voltage_v:.2f}"),
            KeyValue(key="current_a", value=f"{self._snapshot.current_a:.2f}"),
            KeyValue(key="bump_left", value=str(self._snapshot.bump_left)),
            KeyValue(key="bump_right", value=str(self._snapshot.bump_right)),
            KeyValue(key="cliff_any", value=str(self._snapshot.cliff_any)),
        ]
        arr.status.append(s)
        self._diag_pub.publish(arr)

    # ---------------------------------------------------------------- shutdown
    def shutdown(self) -> None:
        self._io_stop.set()
        if self._io_thread.is_alive():
            self._io_thread.join(timeout=1.0)
        self._close_serial()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = Create2DriverNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
