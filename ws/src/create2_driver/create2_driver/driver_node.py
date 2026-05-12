"""create2_driver ROS 2 node — stub for Phase 3 (Gate G4).

Implements the topic contract from master plan §5.1:
  inputs:  /cmd_vel (geometry_msgs/Twist)
  outputs: /odom (nav_msgs/Odometry), /tf odom->base_link,
           /battery_state (sensor_msgs/BatteryState)

The body is intentionally minimal; full odometry from sensor packets lands in
Phase 3 after Gate G3 passes.
"""
from __future__ import annotations


def main() -> None:
    raise SystemExit(
        "create2_driver_node is a Phase 3 deliverable. "
        "Run `python3 -m create2_driver.smoke` to validate Gate G3 first."
    )


if __name__ == "__main__":
    main()
