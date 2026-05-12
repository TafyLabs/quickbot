# QuickBot ROS 2 + Nav2 + Open-RMF Master Design and Implementation Plan

Draft date: May 12, 2026

Baseline validation: ROS 2 Kilted Kaiju on Ubuntu 24.04. Controlled upgrade: ROS 2 Lyrical Luth on Ubuntu 26.04.

Project hardware: iRobot Create 2 + Raspberry Pi 5 + Intel RealSense D455.

## 1. Executive Summary

The quickest reliable path is to build a real, turtlebot-style robot around the iRobot Create 2, a Raspberry Pi 5, and the Intel RealSense D455. The first validated baseline should be ROS 2 Kilted Kaiju on Ubuntu 24.04 containers. After the complete stack is proven, the next phase upgrades the same repository and tests to ROS 2 Lyrical Luth on Ubuntu 26.04. This sequencing is intentional: Kilted is already released and supported on Ubuntu 24.04 for amd64 and arm64, while Lyrical is still a development/pre-release target at this document date. [ROS-Kilted-Install] [ROS-Kilted-Release] [ROS-Lyrical-Release]

- Use the Create 2 as the differential-drive base. It already provides working motors, battery, odometry-related sensor packets, bump/cliff safety, and a serial Open Interface.
- Use the Pi 5 as the robot computer and the workstation/laptop as the development, visualization, mapping, RMF, and dashboard host.
- Use the D455 first as the perception sensor and convert depth to a 2D LaserScan for Nav2. Salvaged LiDARs are a later optimization, not a first milestone.
- Run everything in containers using host networking and explicit device passthrough. Bind-mount source during development, then copy source into release images for reproducibility.
- Validate ROS, Nav2, and Open-RMF independently before integrating them through a fleet adapter.

## 2. Release Strategy: Kilted First, Lyrical Second

The project uses two ROS distribution phases. Phase A produces a working robot. Phase B proves the same robot and RMF workflow on Lyrical.

| Phase | ROS distro | Base | Purpose | Reason |
| --- | --- | --- | --- | --- |
| A: Baseline | ROS 2 Kilted Kaiju | Ubuntu 24.04 Noble | Primary implementation and validation target | Released standard distribution; deb packages available for Ubuntu 24.04 on amd64 and arm64; Open-RMF lists Kilted support. |
| B: Upgrade | ROS 2 Lyrical Luth | Ubuntu 26.04 Resolute | Controlled migration after Kilted gates pass | Lyrical docs currently mark it as a development version; GA is scheduled for May 22, 2026. |
| C: Optional future | Rolling or Lyrical nightlies | As needed | Exploration only | Useful for upstream fixes, but not a stable acceptance target. |

Decision rule: do not start Lyrical migration until the Kilted baseline has passed container, robot motion, TF, scan, SLAM, Nav2, RMF demo, and RMF-to-real-robot gates.

## 3. Project Scope and Definition of Done

### 3.1 Goals

- Install and run ROS 2 in containers on the Pi 5 and workstation.
- Install and run Nav2; prove simulation first, then real-robot navigation.
- Install and run Open-RMF; prove demos first, then command the real robot through an RMF fleet adapter.
- Maintain a reproducible repository with Dockerfiles, Compose files, launch files, maps, robot description, driver code, and validation scripts.
- Produce evidence for each gate: logs, screenshots, maps, bag files when useful, and a pass/fail checklist.

### 3.2 Non-goals for the first validated baseline

- Do not reverse-engineer salvaged LiDARs before the D455-based scan works.
- Do not build a custom motor-control chassis before the Create 2 proves the ROS/Nav2/RMF stack.
- Do not implement multi-floor RMF, doors, lifts, charging, traffic negotiation edge cases, or production safety certification in the first MVP.
- Do not require strict Lyrical-only operation before the Kilted baseline is working.

### 3.3 Definition of Done

| Gate | Done when |
| --- | --- |
| ROS container | Talker/listener works between two containers on host networking; ros2 doctor has no critical issues. |
| Robot motion | Create 2 moves from /cmd_vel, stops on timeout, and publishes /odom plus odom -> base_link TF. |
| Perception | D455 publishes depth; depthimage_to_laserscan publishes /scan at a stable rate in the correct frame. |
| Mapping | slam_toolbox can map the test area and save a map using map_saver_cli. |
| Navigation | Nav2 accepts at least five RViz goals, handles one cancel, and survives lifecycle restart. |
| Open-RMF demo | RMF office demo launches headless; API/dashboard or CLI task flow can be exercised. |
| RMF real robot | A single robot appears to RMF, accepts a navigation task, reaches one waypoint, reports completion, and can be stopped/cancelled. |
| Lyrical upgrade | All Kilted gates pass again on Lyrical using the same repository and acceptance matrix. |

## 4. Hardware Architecture

| Item | Role | Implementation note |
| --- | --- | --- |
| iRobot Create 2 | Primary differential-drive base | Fastest path because the base, motors, battery, safety sensors, and serial API already work. |
| Raspberry Pi 5 | Robot computer | Runs robot-side containers: Create 2 driver, TF, RealSense, depth-to-scan, SLAM/localization, Nav2. |
| Intel RealSense D455 | Initial navigation sensor | Use depthimage_to_laserscan for a first 2D scan. Build RealSense ROS wrapper from source if Kilted/Lyrical debs are not sufficient. |
| Laptop/workstation | Development/RMF/visualization host | Runs RViz, Gazebo/RMF demos, dashboard/API server, map authoring, and heavy builds. |
| USB battery pack or buck converter | Pi and sensor power | Do not power the Pi from the Create 2 serial connector Vpwr pins; the OI spec limits those pins to 200 mA continuous. |
| Neato D7, Roborock LiDARs, DIY chassis | Future parts bin | Useful later, but avoid during the first bring-up. |

```

Workstation / laptop                                      Robot / Create 2
--------------------                                      ----------------
Docker: dev + RViz + RMF demos + dashboard                Docker: robot stack
ROS_DOMAIN_ID=9                                           ROS_DOMAIN_ID=9
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp                     Same RMW as workstation

        Wi-Fi / Ethernet, host networking, DDS discovery
  ---------------------------------------------------------------------->

                                                           Raspberry Pi 5
                                                           |-- USB serial -> Create 2 OI
                                                           |-- USB3 -> RealSense D455
                                                           |-- /cmd_vel -> create2_driver
                                                           |-- /odom, /tf, /scan -> Nav2
```

Safety and power rule: the Create 2 serial connector provides battery power through Vpwr pins, but the OI specification describes these pins as protected by a 200 mA resettable fuse and not suitable for powering the Pi 5. Use a USB battery pack or a properly rated buck converter. [Create2-OI]

## 5. Software Architecture

| Package | Responsibility | Notes |
| --- | --- | --- |
| quickbot_description | URDF/Xacro, frames, robot radius/footprint, sensor mount transforms | No runtime logic. |
| create2_driver | Create 2 serial driver: /cmd_vel in; /odom, /tf, /battery_state, diagnostics out | Keep dependency-light and distribution-portable. |
| quickbot_bringup | Launch files for robot, sensors, SLAM, localization, Nav2, and validation tools | Primary operator entry point. |
| quickbot_nav | Nav2 parameter files, maps, lifecycle scripts, SLAM/localization configs | Keep Kilted and Lyrical parameter variants only when necessary. |
| quickbot_rmf_adapter | Fleet adapter or wrapper that connects RMF commands to Nav2 NavigateToPose | Start from fleet_adapter_template; keep adapter single-robot and single-floor first. |
| quickbot_tools | Smoke tests, health checks, calibration helpers, log capture scripts | Used by validation gates. |

### 5.1 Topic and frame contract

| Name | Type | Producer/consumer | Use |
| --- | --- | --- | --- |
| /cmd_vel | geometry_msgs/Twist | Nav2/teleop -> create2_driver | Velocity command. Driver stops on timeout. |
| /odom | nav_msgs/Odometry | create2_driver -> Nav2/localization | Wheel odometry estimate. |
| /tf | tf2_msgs/TFMessage | driver, robot_state_publisher | odom -> base_link plus dynamic transforms. |
| /tf_static | tf2_msgs/TFMessage | robot_state_publisher/static transforms | base_link -> sensors. |
| /scan | sensor_msgs/LaserScan | depthimage_to_laserscan -> Nav2 | Initial obstacle source. |
| /battery_state | sensor_msgs/BatteryState | create2_driver -> RMF/diagnostics | Used for monitoring and future RMF battery logic. |
| /navigate_to_pose | nav2_msgs/action/NavigateToPose | RMF adapter -> Nav2 | Primary bridge action. |

| Frame | Purpose | Notes |
| --- | --- | --- |
| map | Global map frame from SLAM/map server | Parent of odom after localization. |
| odom | Locally continuous odometry frame | Parent of base_link from driver/robot_localization. |
| base_link | Robot body center frame | The primary robot frame. |
| base_footprint | Optional planar base frame | Use if Nav2 footprint conventions require it. |
| camera_link | D455 physical frame | Static transform from base_link. |
| camera_depth_optical_frame | D455 optical depth frame | Depth image source for scan conversion. |

## 6. Repository and Container Design

```

quickbot/
  docker/
    kilted-base.Dockerfile
    robot.Dockerfile
    rmf-kilted.Dockerfile
    lyrical-base.Dockerfile          # added in the upgrade phase
  compose.yaml
  config/
    cyclonedds.xml
    nav2_create2_kilted.yaml
    nav2_create2_lyrical.yaml        # created only if migration requires changes
  maps/
    quickbot_lab.yaml
    quickbot_lab.pgm
  rmf_maps/
    quickbot_lab.building.yaml
    quickbot_lab.nav_graph.yaml
  ws/
    src/
      quickbot_description/
      create2_driver/
      quickbot_bringup/
      quickbot_nav/
      quickbot_rmf_adapter/
      quickbot_tools/
  validation/
    gates.md
    bags/
    logs/
    screenshots/
```

### 6.1 Build principles

- Use a Kilted base image from Ubuntu 24.04 first. Do not mix Kilted and Lyrical packages in one image.
- Use host networking for ROS containers during bring-up. It removes DDS port-mapping issues while the robot is still experimental.
- Use the same ROS_DOMAIN_ID everywhere. Use 9 unless there is a conflict on the local network.
- Use one RMW implementation across all containers in a test run. The baseline recommendation is Cyclone DDS for robot bring-up; test Fast DDS or Zenoh later if needed.
- Development images bind-mount ws/. Release images copy source into the image after package manifests are copied first for build caching.
- Pin working image digests for RMF nightly/demo images once a known-good image is found.

### 6.2 Kilted base Dockerfile

```

FROM ubuntu:24.04
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=kilted
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales curl ca-certificates gnupg software-properties-common git \
    build-essential python3-pip python3-venv \
    && locale-gen en_US en_US.UTF-8 \
    && add-apt-repository -y universe \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y curl \
    && export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}') \
    && curl -L -o /tmp/ros2-apt-source.deb \
       "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME:-${VERSION_CODENAME}})_all.deb" \
    && dpkg -i /tmp/ros2-apt-source.deb \
    && rm /tmp/ros2-apt-source.deb \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-dev-tools \
    ros-${ROS_DISTRO}-ros-base \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp \
    ros-${ROS_DISTRO}-tf2-ros \
    ros-${ROS_DISTRO}-robot-state-publisher \
    ros-${ROS_DISTRO}-xacro \
    ros-${ROS_DISTRO}-teleop-twist-keyboard \
    ros-${ROS_DISTRO}-robot-localization \
    ros-${ROS_DISTRO}-slam-toolbox \
    ros-${ROS_DISTRO}-depthimage-to-laserscan \
    ros-${ROS_DISTRO}-navigation2 \
    ros-${ROS_DISTRO}-nav2-bringup \
    && rm -rf /var/lib/apt/lists/*

RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> /root/.bashrc
WORKDIR /ws
```

### 6.3 Compose skeleton

```

services:
  robot:
    image: quickbot:robot-kilted
    build:
      context: .
      dockerfile: docker/robot.Dockerfile
    network_mode: host
    ipc: host
    privileged: true
    environment:
      ROS_DOMAIN_ID: "9"
      RMW_IMPLEMENTATION: rmw_cyclonedds_cpp
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
      - /dev/bus/usb:/dev/bus/usb
    volumes:
      - ./ws:/ws
      - ./config:/config
      - ./maps:/maps
      - ./rmf_maps:/rmf_maps
    command: bash

  dev:
    image: quickbot:kilted-base
    network_mode: host
    ipc: host
    environment:
      ROS_DOMAIN_ID: "9"
      RMW_IMPLEMENTATION: rmw_cyclonedds_cpp
      DISPLAY: ${DISPLAY}
    volumes:
      - ./ws:/ws
      - ./config:/config
      - ./maps:/maps
      - /tmp/.X11-unix:/tmp/.X11-unix
    command: bash
```

## 7. Implementation Phases

| Phase | Name | Work | Exit criterion |
| --- | --- | --- | --- |
| 0 | Host prep and repository | Install Docker/Compose, create repo tree, build kilted-base, pick ROS_DOMAIN_ID, verify device names. | Build succeeds; README has exact commands. |
| 1 | ROS container smoke test | Run talker/listener across containers; run ros2 topic list; verify DDS discovery. | Messages cross containers reliably. |
| 2 | Create 2 raw serial | Pass /dev/ttyUSB0 into container; send OI Start, Safe, Drive Direct, Stop. | Robot moves briefly and stops. |
| 3 | Create 2 ROS driver | Implement /cmd_vel to wheel velocity; publish /odom, /tf, battery/diagnostics; add timeout stop. | Teleop drives robot; odom and TF appear. |
| 4 | D455 scan | Run RealSense wrapper; convert depth to /scan; verify TF and scan orientation in RViz. | /scan stable; obstacles appear where expected. |
| 5 | SLAM and map | Run slam_toolbox; teleop map; save map to maps/. | Map loads and matches room geometry. |
| 6 | Nav2 real robot | Run AMCL/map_server/Nav2; tune costmaps and velocity limits; execute goals. | Five goals pass; cancel and lifecycle restart pass. |
| 7 | Open-RMF demo | Install Open-RMF Kilted binaries and/or run known-good RMF demo container; launch office demo headless. | RMF nodes launch; tasks can be submitted in demo. |
| 8 | RMF adapter to Nav2 | Implement single-robot adapter using fleet_adapter_template or Free Fleet; align RMF map and robot map. | RMF sends a task and the real robot completes it. |
| 9 | Lyrical migration | Create Ubuntu 26.04/Lyrical images; repeat gates; address Nav2 migration deltas. | All gates pass on Lyrical. |

## 8. Create 2 Bring-up and Driver Design

The Create 2 Open Interface supports two-way serial control over the Mini-DIN connector. The OI spec describes 115200 baud as the default serial rate, Safe mode as opcode 131, and Drive Direct as opcode 145 for independently commanding right and left wheel velocities in mm/s. [Create2-OI]

### 8.1 Raw serial smoke test

```

# Run from inside a container with --device=/dev/ttyUSB0:/dev/ttyUSB0.
python3 - <<'PY'
import serial, struct, time

PORT = "/dev/ttyUSB0"
BAUD = 115200

def i16(value: int) -> bytes:
    return struct.pack(">h", int(value))

s = serial.Serial(PORT, BAUD, timeout=1)
s.write(bytes([128]))       # Start Open Interface
s.write(bytes([131]))       # Safe mode
time.sleep(0.1)
s.write(bytes([145]) + i16(100) + i16(100))  # right, left wheel mm/s
time.sleep(1.0)
s.write(bytes([145]) + i16(0) + i16(0))
time.sleep(0.1)
s.write(bytes([173]))       # Stop OI
s.close()
PY
```

### 8.2 ROS 2 driver contract

| Area | Interface | Implementation note |
| --- | --- | --- |
| Inputs | /cmd_vel geometry_msgs/Twist; optional /e_stop std_msgs/Bool | Clamp velocities; stop if no command within cmd_timeout_s. |
| Outputs | /odom nav_msgs/Odometry; /tf odom->base_link; /battery_state; /diagnostics | Publish at 20-50 Hz as hardware permits. |
| Parameters | serial_port, baud, wheel_separation_m, wheel_radius_m or wheel scale, max_linear_mps, max_angular_rps, cmd_timeout_s | Keep all robot calibration outside code. |
| Safety | Safe mode by default; timeout stop; shutdown stop; bump/cliff stop; manual power access | Never rely on software only around people/pets. |
| Odom source | Start with distance/angle packets; optionally fuse with IMU/visual odom later | Expect drift; AMCL handles global correction. |

### 8.3 Calibration checklist

- Measure actual track width by commanding an in-place rotation and comparing expected vs observed yaw.
- Measure straight-line odometry scale by commanding 1.0 m forward and comparing /odom displacement to tape measurement.
- Tune max_linear_mps to a conservative value first, about 0.18-0.22 m/s.
- Tune max_angular_rps to a conservative value first, about 0.6-0.8 rad/s.
- Record calibration values in config/create2_calibration.yaml and commit them.

## 9. Sensor and TF Bring-up

Use the D455 before salvaged LiDAR. The RealSense ROS wrapper supports ROS 2 workflows on Ubuntu 24.04 and documents both deb and source installation paths, including source build from the ros2-master branch. [RealSense-ROS]

### 9.1 Sensor launch sequence

```

# First try deb packages if available for the active distro.
sudo apt install ros-$ROS_DISTRO-realsense2-* || true

# Fallback: build from source in ws/src or a separate camera workspace.
git clone https://github.com/realsenseai/realsense-ros.git -b ros2-master ws/src/realsense-ros
rosdep install -i --from-path ws/src --rosdistro $ROS_DISTRO --skip-keys=librealsense2 -y
colcon build --symlink-install

# Runtime launch example.
ros2 launch realsense2_camera rs_launch.py \
  depth_module.profile:=640x480x30 \
  rgb_camera.enable:=false \
  pointcloud.enable:=false

# Convert depth to a 2D scan.
ros2 run depthimage_to_laserscan depthimage_to_laserscan_node \
  --ros-args \
  -r image:=/camera/camera/depth/image_rect_raw \
  -r camera_info:=/camera/camera/depth/camera_info \
  -r scan:=/scan
```

### 9.2 TF validation

- Run ros2 run tf2_tools view_frames and save the generated frames report.
- Confirm map -> odom exists only when SLAM/localization is active.
- Confirm odom -> base_link is continuous and not jumping.
- Confirm base_link -> camera_link and camera optical frames are static and match the physical mount.
- In RViz, set Fixed Frame to base_link first, then odom, then map as systems come online.

## 10. SLAM and Nav2 Implementation

Nav2’s getting-started flow installs the navigation2 and nav2_bringup packages and validates with a TurtleBot simulation. For this project, run simulation first, then reuse the same Nav2 concepts with the Create 2 robot. [Nav2-Getting-Started]

### 10.1 Bring-up order

1. Teleop only: create2_driver, robot_state_publisher, and RViz. No Nav2 yet.
2. Add D455 and /scan. Confirm costmap-ready LaserScan data.
3. Run slam_toolbox online_async and teleop the robot slowly to create the first map.
4. Save the map with nav2_map_server map_saver_cli.
5. Run Nav2 with map_server, AMCL, planner, controller, behavior tree navigator, recoveries/behaviors, velocity smoother, and lifecycle manager.
6. Tune from conservative limits upward only after repeatable navigation is achieved.

### 10.2 Initial Nav2 parameter skeleton

```

amcl:
  ros__parameters:
    use_sim_time: false
    base_frame_id: base_link
    odom_frame_id: odom
    global_frame_id: map
    scan_topic: scan

controller_server:
  ros__parameters:
    controller_frequency: 10.0
    min_x_velocity_threshold: 0.001
    min_theta_velocity_threshold: 0.001

velocity_smoother:
  ros__parameters:
    smoothing_frequency: 20.0
    max_velocity: [0.22, 0.0, 0.8]
    min_velocity: [-0.08, 0.0, -0.8]
    max_accel: [0.25, 0.0, 0.8]
    max_decel: [-0.25, 0.0, -0.8]

local_costmap:
  local_costmap:
    ros__parameters:
      global_frame: odom
      robot_base_frame: base_link
      robot_radius: 0.18
      observation_sources: scan
      scan:
        topic: /scan
        data_type: LaserScan
        marking: true
        clearing: true

global_costmap:
  global_costmap:
    ros__parameters:
      global_frame: map
      robot_base_frame: base_link
      robot_radius: 0.18
      observation_sources: scan
      scan:
        topic: /scan
        data_type: LaserScan
        marking: true
        clearing: true
```

### 10.3 Nav2 validation

| Test | Procedure | Pass condition |
| --- | --- | --- |
| Sim smoke | Run Nav2 TurtleBot simulation in a dev container/workstation. | RViz displays map, costmaps, robot pose, and successful goal execution. |
| Real teleop | Run robot without Nav2; teleop through the test route. | No TF breaks; /odom and /scan stay stable. |
| Map quality | Create map and reload it. | Walls/obstacles align with live scan in RViz after pose estimate. |
| Goal set | Send five 2D Nav Goals. | At least five complete; failed attempts have logs and root cause. |
| Cancel/recovery | Cancel one goal and obstruct one short path. | Robot stops on cancel and recovers or fails safely. |
| Restart | Restart Nav2 lifecycle nodes without rebooting robot. | System returns to active state. |

## 11. Open-RMF Implementation

Open-RMF currently lists Humble, Jazzy, Kilted, and Rolling as supported ROS 2 distributions, and recommends binary installation for trying Open-RMF. The repository also provides nightly Docker images for demos and warns that latest/nightly images may break, so any working image should be pinned by digest. [Open-RMF-Root]

### 11.1 RMF bring-up sequence

1. Install Kilted ROS 2 and Open-RMF binaries in a workstation container: ros-kilted-rmf-dev.
2. Build or install rmf_demos for Kilted. The Kilted rmf_demos documentation describes it as common launch files and scripts for starting RMF systems. [RMF-Demos-Kilted]
3. Run an RMF office demo headless before involving the real robot.
4. Start API/dashboard containers only after the core RMF demo works.
5. Freeze a known-good RMF image digest or source revision in the project README.
6. Create a minimal single-floor map for the real test area; avoid doors/lifts/charging in MVP.

### 11.2 RMF installation notes

```

# Workstation/container after ROS 2 Kilted apt repositories are configured.
sudo apt update
sudo apt install ros-dev-tools ros-kilted-rmf-dev
rosdep update

# If using source/demo workspace:
mkdir -p ~/rmf_ws/src
cd ~/rmf_ws
# Use the kilted or kilted-release branch/tag when available for reproducibility.
wget https://raw.githubusercontent.com/open-rmf/rmf/kilted/rmf.repos -O rmf.repos || \
  wget https://raw.githubusercontent.com/open-rmf/rmf/main/rmf.repos -O rmf.repos
vcs import src < rmf.repos
rosdep install --from-paths src --ignore-src --rosdistro kilted -y
colcon build --mixin release

# Docker demo pattern; adjust image tag to kilted when available and pin digest after validation.
docker pull ghcr.io/open-rmf/rmf/rmf_demos:kilted-rmf-latest || \
  docker pull ghcr.io/open-rmf/rmf/rmf_demos:jazzy-rmf-latest
```

### 11.3 Fleet adapter design

The primary integration path is a small Python full_control adapter based on fleet_adapter_template. That template is explicitly intended as a reference for Python-based full_control RMF fleet adapters. [Fleet-Adapter-Template]

| Adapter method | Purpose | Implementation note |
| --- | --- | --- |
| position() | Read current robot pose in the RMF map frame. | Use AMCL pose or TF map->base_link; apply map transform if RMF and Nav2 coordinates differ. |
| navigate(map_name, x, y, yaw) | Send Nav2 NavigateToPose action. | Reject non-current floor/map in MVP. Track action feedback and result. |
| stop() | Cancel active Nav2 goal and publish zero velocity if needed. | Must be reliable before RMF demo with real motion. |
| battery_soc() | Report approximate battery state. | Use Create 2 battery packets; if unavailable, return conservative fixed value for MVP. |
| status/activity | Report moving, idle, blocked, error. | Map Nav2 action status to RMF states. |

```

class QuickBotRobotAPI:
    def position(self):
        # Return [x, y, yaw] in RMF map coordinates.
        return self.tf_lookup_map_to_base_link()

    def navigate(self, map_name, x, y, yaw, speed_limit=None):
        # Convert RMF coordinates to Nav2 map coordinates if needed.
        pose = self.rmf_to_nav2_pose(map_name, x, y, yaw)
        return self.nav2_action_client.send_goal(pose)

    def stop(self):
        self.nav2_action_client.cancel_current_goal()
        self.cmd_vel_pub.publish_zero()
        return True

    def battery_soc(self):
        return self.last_battery_state.percentage or 0.80
```

### 11.4 RMF MVP constraints

- One robot: quickbot_1.
- One floor/map only.
- No doors, lifts, dispensers, ingestors, chargers, or multi-fleet traffic edge cases in the first real robot demo.
- A small navigation graph with 4-8 waypoints is enough for the first task test.
- The acceptance task is: dispatch robot to waypoint A, then waypoint B, then stop/cancel a test task safely.

## 12. Master Validation Matrix

| Gate | Area | Procedure | Pass condition | Evidence |
| --- | --- | --- | --- | --- |
| G0 | Build | docker build quickbot:kilted-base | Build completes; image has ros2 CLI. | Build log. |
| G1 | DDS | talker/listener in two containers | Messages received both directions. | Terminal log. |
| G2 | Device passthrough | ls /dev/ttyUSB0 and rs-enumerate-devices inside robot container | Create serial and D455 visible. | Log/screenshot. |
| G3 | Create raw drive | Run raw serial smoke test | Robot moves 1 s and stops. | Video/log. |
| G4 | Teleop ROS | teleop_twist_keyboard -> /cmd_vel | Robot responds and timeout stops. | ros2 topic hz + video. |
| G5 | TF | view_frames; RViz fixed frame tests | No missing required transforms. | frames report. |
| G6 | Scan | ros2 topic hz /scan and RViz | Stable scan; obstacles align. | RViz screenshot. |
| G7 | SLAM | slam_toolbox map and save | Map saved and reloads. | map YAML/PGM. |
| G8 | Nav2 | Five NavigateToPose goals | Five successes; cancel works. | Nav2 logs, optional bag. |
| G9 | RMF demo | office.launch.xml headless demo | RMF demo launches without fatal errors. | RMF logs. |
| G10 | RMF adapter | Dispatch task to real robot | Robot reaches waypoint and reports completion. | RMF + Nav2 logs. |
| G11 | Upgrade | Repeat G0-G10 on Lyrical | All gates pass or deviations documented. | Upgrade report. |

### 12.1 Standard evidence capture commands

```

mkdir -p validation/logs validation/bags validation/screenshots
ros2 topic list | tee validation/logs/topic_list.txt
ros2 node list | tee validation/logs/node_list.txt
ros2 run tf2_tools view_frames
ros2 bag record -o validation/bags/nav2_gate \
  /tf /tf_static /odom /scan /cmd_vel /amcl_pose /goal_pose /battery_state
```

## 13. Lyrical Luth Upgrade Plan

Lyrical is the second project phase. The Lyrical docs currently show Ubuntu 26.04 deb packages and also mark the documentation as a development version, with general availability scheduled for May 22, 2026. The upgrade should therefore wait until the Kilted baseline is validated and Lyrical packages are suitable for the project. [ROS-Lyrical-Release] [ROS-Lyrical-Install]

### 13.1 Upgrade entry criteria

- Kilted gates G0 through G10 pass or failures are documented and accepted.
- The repo has a clean kilted-baseline tag.
- Validation data is checked in or archived under validation/.
- A Lyrical container can install ros-lyrical-ros-base and required packages on Ubuntu 26.04.
- Open-RMF on Lyrical is either supported by binaries, a known source branch, or an explicitly accepted source-build experiment.

### 13.2 Expected migration work

| Area | Work | Risk control |
| --- | --- | --- |
| Containers | Switch base to ubuntu:26.04 and ROS_DISTRO=lyrical; use ros2-testing apt source only while pre-GA. | Keep Kilted images intact. |
| Nav2 | Review Kilted-to-Lyrical migration notes. Nav2 adds nav2_ros_common and may affect custom plugins or code using Nav2 utility classes. | The project should minimize custom Nav2 plugin code to reduce migration. |
| RealSense | Try debs first; build realsense-ros from source if deb availability lags. | Pin source commit if building from source. |
| Open-RMF | Try Lyrical/Kilted-supported branch strategy; source build with clang/lld if binaries lag. | Do not block robot validation on RMF source-build issues. |
| Validation | Repeat the entire matrix, not just smoke tests. | Compare Kilted and Lyrical logs. |

### 13.3 Rollback plan

- Keep the Kilted branch and Docker images unchanged.
- Tag working states: kilted-g8-nav2-pass, kilted-g10-rmf-real-pass, lyrical-gX-pass.
- Never overwrite maps/configs without saving previous versions.
- If Lyrical breaks any gate, preserve the failure logs and continue demos from the Kilted image until fixed.

## 14. Fast Implementation Schedule

| Timebox | Focus | Gate target |
| --- | --- | --- |
| Day 0 | Repository, Docker base, Compose, ROS container smoke tests. | G0-G1. |
| Day 1 | Mount Pi/D455, power/cabling, raw Create 2 serial test, first create2_driver node. | G2-G4. |
| Day 2 | D455 /scan, TF cleanup, teleop route, first SLAM map. | G5-G7. |
| Day 3 | Nav2 tuning and repeated real-robot goals. | G8. |
| Day 4 | Open-RMF Kilted/demo environment and dashboard/API path. | G9. |
| Day 5-6 | Fleet adapter to Nav2, RMF map alignment, first real RMF task. | G10. |
| After baseline | Lyrical images and migration test pass. | G11. |

## 15. Risk Register

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Lyrical pre-release churn | High | Start on Kilted. Treat Lyrical as Phase B. Preserve Kilted images and tags. |
| RealSense wrapper package gaps | Medium | Build from source and pin commit; keep D455 configuration minimal. |
| Create 2 odometry drift | Medium | Calibrate distance/angle; use AMCL for global localization; keep speed conservative. |
| D455 scan limitations near glass/low obstacles | Medium | Validate in actual environment; add salvaged LiDAR only after baseline works. |
| Docker/DDS discovery issues | Medium | Use host networking; single ROS_DOMAIN_ID; single RMW per run. |
| RMF coordinate mismatch | High | Use reference points; start with a tiny map and a 4-8 waypoint graph. |
| Pi power brownouts | High | Use dedicated USB-C PD bank or rated buck; do not use Create 2 serial Vpwr for Pi. |
| Safety around people/pets | High | Low speeds, clear test area, physical access to power, timeout stop, Safe mode, bump/cliff stop. |

## 16. Operator Runbook

### 16.1 Normal robot startup

```

# On robot / Pi 5
cd ~/quickbot
docker compose run --rm robot bash
source /opt/ros/$ROS_DISTRO/setup.bash
source /ws/install/setup.bash
ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0

# On workstation
cd ~/quickbot
docker compose run --rm dev bash
source /opt/ros/$ROS_DISTRO/setup.bash
source /ws/install/setup.bash
rviz2 -d /ws/src/quickbot_nav/rviz/nav2.rviz
```

### 16.2 Mapping startup

```

ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0
ros2 launch slam_toolbox online_async_launch.py use_sim_time:=false
ros2 run teleop_twist_keyboard teleop_twist_keyboard
ros2 run nav2_map_server map_saver_cli -f /maps/quickbot_lab
```

### 16.3 Navigation startup

```

ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0
ros2 launch nav2_bringup bringup_launch.py \
  use_sim_time:=false \
  map:=/maps/quickbot_lab.yaml \
  params_file:=/config/nav2_create2_kilted.yaml
```

### 16.4 Shutdown

1. Cancel active Nav2/RMF tasks.
2. Publish zero velocity or call driver stop service.
3. Stop Nav2 lifecycle nodes.
4. Stop Create 2 driver, which must send Drive Direct zero and OI Stop on shutdown.
5. Power down Pi and disconnect external battery only after shutdown completes.

## 17. Parts and Preparation Checklist

| Priority | Item | Reason |
| --- | --- | --- |
| Required | Create 2 USB serial cable/adapter | Must handle 0-5 V serial levels correctly. |
| Required | USB-C PD power bank or rated buck converter for Pi 5 | Avoid power brownouts. |
| Required | Pi 5 active cooling | Sustained container workloads heat the Pi. |
| Required | Rigid D455 mount | Pose stability matters for scan projection and navigation. |
| Recommended | Short USB3 cable for D455 | Avoid intermittent camera disconnects. |
| Recommended | Emergency physical power access | Fast human stop during testing. |
| Optional later | Salvaged LiDAR interface hardware | Only after D455/Nav2 baseline is complete. |

## 18. Appendix: Source References

[ROS-Kilted-Install] ROS 2 Kilted Ubuntu deb packages; Ubuntu Noble 24.04 availability. https://docs.ros.org/en/kilted/Installation/Ubuntu-Install-Debs.html

[ROS-Kilted-Release] Open Robotics Kilted release announcement; support through November 2026 and platform summary. https://www.openrobotics.org/blog/2025/5/23/ros-2-kilted-kaiju-released

[ROS-Lyrical-Release] ROS 2 Lyrical Luth release timeline, development-version notice, and supported platforms. https://docs.ros.org/en/rolling/Releases/Release-Lyrical-Luth.html

[ROS-Lyrical-Install] ROS 2 Lyrical Ubuntu 26.04 deb package installation page. https://docs.ros.org/en/lyrical/Installation/Ubuntu-Install-Debs.html

[Nav2-Getting-Started] Nav2 binary install and TurtleBot simulation flow. https://docs.nav2.org/getting_started/index.html

[Nav2-Kilted-to-Lyrical] Nav2 migration notes from Kilted to Lyrical/L-turtle. https://docs.nav2.org/migration/Kilted.html

[Open-RMF-Root] Open-RMF installation, supported ROS 2 distributions, binary/source/Docker notes, and integration pointers. https://github.com/open-rmf/rmf

[RMF-Demos-Kilted] Kilted rmf_demos package documentation. https://docs.ros.org/en/ros2_packages/kilted/api/rmf_demos/

[Fleet-Adapter-Template] Python full_control fleet adapter reference/template. https://github.com/open-rmf/fleet_adapter_template

[RealSense-ROS] Intel RealSense ROS 2 wrapper install and source build instructions. https://github.com/realsenseai/realsense-ros

[Create2-OI] iRobot Create 2 / Roomba Open Interface specification. https://cdn-shop.adafruit.com/datasheets/create_2_Open_Interface_Spec.pdf

## 19. Appendix: First Commits

- commit 1: repository skeleton, README, Dockerfiles, compose.yaml, validation/gates.md.
- commit 2: quickbot_description with URDF/Xacro and static transforms.
- commit 3: create2_driver raw serial library and smoke test.
- commit 4: create2_driver ROS node and teleop launch.
- commit 5: D455 launch and depthimage_to_laserscan launch.
- commit 6: SLAM/map artifacts.
- commit 7: Nav2 params and bring-up launch.
- commit 8: RMF demo container notes and RMF source/binary setup.
- commit 9: quickbot_rmf_adapter MVP.
- commit 10: Lyrical branch Dockerfiles and migration notes.

End of document.
