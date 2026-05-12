# Operator runbook

All commands assume `cd ~/quickbot` and that `compose.yaml` is present.

## Normal robot startup

```bash
# On robot / Pi 5
docker compose run --rm robot bash
source /opt/ros/$ROS_DISTRO/setup.bash
source /ws/install/setup.bash 2>/dev/null || echo "ws not built yet"
ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0

# On workstation
docker compose run --rm dev bash
source /opt/ros/$ROS_DISTRO/setup.bash
source /ws/install/setup.bash 2>/dev/null || true
rviz2 -d /ws/src/quickbot_nav/rviz/nav2.rviz
```

## Mapping (Gate G7)

```bash
# Terminal 1 (robot)
ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0

# Terminal 2 (workstation)
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=false

# Terminal 3 (workstation)
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# When the map looks right:
ros2 run nav2_map_server map_saver_cli -f /maps/quickbot_lab
```

## Navigation (Gate G8)

```bash
ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0
ros2 launch nav2_bringup bringup_launch.py \
  use_sim_time:=false \
  map:=/maps/quickbot_lab.yaml \
  params_file:=/config/nav2_create2_kilted.yaml
```

In RViz: set initial pose with **2D Pose Estimate**, then send goals with **Nav2 Goal**.

## RMF demo (Gate G9)

```bash
docker compose run --rm rmf bash
# Inside the rmf service:
ros2 launch rmf_demos_gz office.launch.xml headless:=true
```

Pin the working image digest in this file once a known-good version is found:

```
ghcr.io/open-rmf/rmf/rmf_demos@sha256:<digest>
```

## RealSense source build (fallback)

```bash
# Inside the robot or dev container, if debs aren't available:
cd /ws
git clone https://github.com/realsenseai/realsense-ros.git \
  -b ros2-master src/realsense-ros
rosdep install -i --from-path src --rosdistro $ROS_DISTRO \
  --skip-keys=librealsense2 -y
colcon build --symlink-install
source install/setup.bash

ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=640x480x30 \
  rgb_camera.enable:=false \
  pointcloud.enable:=false
```

## Depth → LaserScan

```bash
ros2 run depthimage_to_laserscan depthimage_to_laserscan_node \
  --ros-args \
  -r image:=/camera/camera/depth/image_rect_raw \
  -r camera_info:=/camera/camera/depth/camera_info \
  -r scan:=/scan
```

## Calibration

See [`calibration.md`](calibration.md). Values land in [`../config/create2_calibration.yaml`](../config/create2_calibration.yaml).

## Shutdown

1. Cancel active Nav2 / RMF tasks.
2. Publish zero `/cmd_vel` or call the driver stop service.
3. Stop Nav2 lifecycle nodes (`/lifecycle_manager_navigation/manage_nodes` → shutdown).
4. Stop `create2_driver` (it must send Drive Direct 0 and OI Stop on shutdown).
5. Power down Pi cleanly before disconnecting the external battery.

## Recovery cheatsheet

| Symptom | First check |
| --- | --- |
| No topics across containers | Same `ROS_DOMAIN_ID`? Same RMW? Host networking on both? Firewall? |
| TF jumps | Is `create2_driver` publishing at expected rate? Is `robot_localization` mixing two odom sources? |
| Scan flickers | USB3 cable quality, D455 firmware, depth profile resolution. |
| Nav2 won't activate | `ros2 lifecycle list /lifecycle_manager_navigation` + Nav2 node logs. |
| RMF can't see robot | Adapter `position()` returning RMF-frame coords? Map name match? |
