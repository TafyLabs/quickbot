# Architecture

## Topology

```
Workstation / laptop                                      Robot / Create 2
--------------------                                      ----------------
Docker: dev + RViz + RMF demos + dashboard                Docker: robot stack
ROS_DOMAIN_ID=9                                           ROS_DOMAIN_ID=9
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp                     Same RMW

        Wi-Fi / Ethernet, host networking, DDS discovery
  ----------------------------------------------------------------------->

                                                          Raspberry Pi 5
                                                          |-- USB serial -> Create 2 OI
                                                          |-- USB3 -> RealSense D455
                                                          |-- /cmd_vel -> create2_driver
                                                          |-- /odom, /tf, /scan -> Nav2
```

## Hardware

| Item | Role | Note |
| --- | --- | --- |
| iRobot Create 2 | Differential-drive base | Motors, battery, safety sensors, serial OI all ready. |
| Raspberry Pi 5 | Robot computer | Runs robot-side containers. |
| Intel RealSense D455 | Initial nav sensor | Depth → 2D LaserScan via `depthimage_to_laserscan`. |
| Workstation / laptop | Dev + RViz + RMF | Map authoring, dashboards, heavy builds. |
| USB-C PD bank / rated buck | Pi power | **Never** power Pi from Create 2 Vpwr serial pins (200 mA limit). |

## Software packages

| Package | Responsibility |
| --- | --- |
| `quickbot_description` | URDF/Xacro, frames, sensor mount transforms (no runtime logic). |
| `create2_driver` | Serial driver: `/cmd_vel` in; `/odom`, `/tf`, `/battery_state` out. |
| `quickbot_bringup` | Launch files for robot, sensors, SLAM, Nav2. |
| `quickbot_nav` | Nav2 params, maps, lifecycle configs. |
| `quickbot_rmf_adapter` | full_control RMF adapter → Nav2 `NavigateToPose`. |
| `quickbot_tools` | Smoke tests, calibration helpers, log capture. |

## Topic + frame contract

| Topic | Type | Producer → Consumer |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/Twist` | Nav2 / teleop → `create2_driver` |
| `/odom` | `nav_msgs/Odometry` | `create2_driver` → Nav2 / localization |
| `/tf` | `tf2_msgs/TFMessage` | driver, `robot_state_publisher` |
| `/tf_static` | `tf2_msgs/TFMessage` | `robot_state_publisher` |
| `/scan` | `sensor_msgs/LaserScan` | `depthimage_to_laserscan` → Nav2 |
| `/battery_state` | `sensor_msgs/BatteryState` | `create2_driver` → RMF / diagnostics |
| `/navigate_to_pose` | `nav2_msgs/action/NavigateToPose` | RMF adapter → Nav2 |

| Frame | Parent | Source |
| --- | --- | --- |
| `map` | — | SLAM / map_server |
| `odom` | `map` | `robot_localization` / AMCL |
| `base_link` | `odom` | `create2_driver` |
| `base_footprint` | `base_link` | URDF (optional) |
| `camera_link` | `base_link` | static transform |
| `camera_depth_optical_frame` | `camera_link` | RealSense driver |

## DDS configuration

- **`ROS_DOMAIN_ID=9`** everywhere (override only on domain conflict).
- **`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`** everywhere for the baseline. Test Fast DDS / Zenoh as separate experiments after Kilted gates pass.
- **Host networking** during bring-up. Migrate to bridge networks only after the stack is stable.
- Cyclone DDS config in [`config/cyclonedds.xml`](../config/cyclonedds.xml) is loaded only when `CYCLONEDDS_URI` is set.

## Release strategy

| Phase | ROS distro | Base | When |
| --- | --- | --- | --- |
| A | Kilted Kaiju | Ubuntu 24.04 | Primary implementation + validation. |
| B | Lyrical Luth | Ubuntu 26.04 | After Kilted gates G0–G10 pass. |
| C | Rolling (optional) | as needed | Upstream-fix exploration only. |

Rule: do not start Phase B until Phase A is green.
