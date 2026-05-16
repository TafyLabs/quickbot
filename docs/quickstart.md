# Quickstart — zero to a driving robot

The sequence below is the one that actually worked on a Pi 5 + iRobot Create 2 + Intel RealSense D455 with a Mac M2 Air on the other end. It runs **Gates G0–G4** end-to-end. Each gate has a stricter procedure in [`gates.md`](gates.md); this page is the path of least resistance.

For deeper context: [`master-plan.md`](master-plan.md) (full design), [`architecture.md`](architecture.md) (topic/frame contract), [`hardware-bringup.md`](hardware-bringup.md) (wiring + Pi OS), [`troubleshooting.md`](troubleshooting.md) (what to check when something is off), [`runbook.md`](runbook.md) (mapping + nav + RMF startup).

## 0. What you need

- Pi 5 (4 GB or 8 GB), microSD ≥ 32 GB, **active cooler** (passive throttles).
- iRobot Create 2 + Mini-DIN 7 → USB-serial cable.
- Intel RealSense D455 + a short USB3 cable.
- USB-C PD power bank (≥ 27 W) for the Pi — **never** power the Pi from the Create 2 Vpwr serial pins (200 mA fuse will brown out the Pi).
- A workstation (M2 Air, Linux laptop, whatever) for RViz + dev.

## 1. Prep the Pi (one time)

Flash Ubuntu Server 24.04 LTS (arm64) via Raspberry Pi Imager, set hostname `quickbot`, enable SSH, set Wi-Fi. First boot:

```bash
sudo apt update && sudo apt full-upgrade -y
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker
sudo apt install -y docker-compose-plugin git
sudo usermod -aG dialout $USER   # so /dev/ttyUSB0 is reachable without root
```

Log out and back in for the group changes to take effect.

## 2. Clone the repo + build the images (one time, ~30 min on a Pi 5)

```bash
git clone git@github.com:TafyLabs/quickbot.git ~/quickbot
cd ~/quickbot
docker build -f docker/kilted-base.Dockerfile -t quickbot:kilted-base .
docker compose build robot
```

If you've already built `quickbot:kilted-base` on another arm64 machine, you can `docker save -o kilted-base.tar quickbot:kilted-base`, `scp` it to the Pi, and `docker load -i kilted-base.tar` to skip the slow ROS-deb step.

## 3. Wire and verify hardware — Gate G2

Plug it in:

```
Pi 5 USB-A 3.0 ── short USB3 cable ── D455 USB-C
Pi 5 USB-A 2.0 ── Create 2 USB-serial ── Create 2 Mini-DIN
USB-C PD bank  ────────────────── Pi 5 USB-C power
```

Then:

```bash
./tools/g2_devices.sh
```

You want `/dev/ttyUSB0` visible (some USB-serial adapters land on `/dev/ttyACM0` — if so, edit [`compose.yaml`](../compose.yaml) and the `serial_port:=` argument below) and the D455 listed in `lsusb`.

## 4. Drive the robot the dumb way — Gate G3

This is the lowest-level check. No ROS, just pyserial over the OI. Clear a 1 m × 1 m floor area; finger on the Create 2 power button.

```bash
docker compose run --rm robot bash -lc \
  'cd /ws/src/create2_driver && python3 -m create2_driver.smoke --port /dev/ttyUSB0 --duration 1.0 --speed 100'
```

The robot should crawl forward ~10 cm in 1 second and stop. The `cd` is required because the workspace hasn't been `colcon build`'d yet, so `create2_driver` is only on `PYTHONPATH` from its source directory.

## 5. Build the workspace and bring up the ROS driver — Gate G4

```bash
docker compose run --rm robot bash -lc \
  'source /opt/ros/$ROS_DISTRO/setup.bash && cd /ws && \
   colcon build --symlink-install && source install/setup.bash && \
   ros2 launch quickbot_bringup robot.launch.py serial_port:=/dev/ttyUSB0'
```

`--symlink-install` means edits to `ws/src/create2_driver/create2_driver/*.py` take effect without rebuilding. Only changes to `setup.py`, `setup.cfg`, or `package.xml` need another `colcon build`.

You should see, among other lines:

```
[create2_driver_node]: create2_driver up on /dev/ttyUSB0 @ 115200, wheel_separation=0.235 m, poll_hz=20.0
```

**Leave that terminal running.** It's the driver.

## 6. Inspect topics from a second container shell

ROS is only inside the container. The Pi host shell doesn't have `ros2`. Open another SSH session to the Pi and start a second container shell — host networking means it discovers the running driver via DDS:

```bash
docker compose -f ~/quickbot/compose.yaml run --rm robot bash -lc \
  'source /opt/ros/$ROS_DISTRO/setup.bash && source /ws/install/setup.bash && bash'
```

Inside:

```bash
ros2 topic list                    # /cmd_vel /odom /tf /tf_static /battery_state /diagnostics
ros2 topic hz /odom                # ~20 Hz
ros2 topic echo --once /battery_state
ros2 node info /create2_driver
```

## 7. Teleop drive the robot — finishes Gate G4

In the same second-shell:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/cmd_vel
```

Pass criteria for G4:
- Robot drives via keyboard.
- Robot stops within ~0.5 s when you release the key (the `/cmd_vel` timeout).
- `/odom` and `/battery_state` keep publishing throughout.
- No bump/cliff false-positives on flat ground.

Capture a phone video + a `ros2 bag record` of `/cmd_vel /odom /tf /battery_state` for the [`validation/gates.md`](../validation/gates.md) row.

## Known gotchas (Kilted Kaiju specific)

These bit during first bring-up and the fixes are in `main` now. Listed so you know what to look for if you fork.

### `xacro` Command output rejected as YAML

```
[ERROR] [launch]: ... Unable to parse the value of parameter robot_description as yaml.
```

Kilted's launch system YAML-parses every parameter value. The `xacro`-generated `robot_description` is XML, so it needs an explicit wrap:

```python
from launch_ros.parameter_descriptions import ParameterValue
parameters=[{
    "robot_description": ParameterValue(
        Command(["xacro ", LaunchConfiguration("urdf")]),
        value_type=str,
    ),
}],
```

See [`ws/src/quickbot_description/launch/description.launch.py`](../ws/src/quickbot_description/launch/description.launch.py).

### `libexec directory does not exist`

```
package 'create2_driver' found at '/ws/install/create2_driver', but libexec
directory '/ws/install/create2_driver/lib/create2_driver' does not exist
```

ament_python packages need a `setup.cfg` next to `setup.py` that points `script_dir` and `install_scripts` at `lib/<package>/`. Without it, setuptools puts the `console_scripts` in `bin/`, which `ros2 run` doesn't search:

```ini
[develop]
script_dir=$base/lib/<package_name>
[install]
install_scripts=$base/lib/<package_name>
```

All three ament_python packages in this repo ship a `setup.cfg`.

### `ros2: command not found`

You're on the Pi host shell. ROS is only installed inside the container — see step 6.

## Next gates after G4

- **G5** — verify the TF tree (`ros2 run tf2_tools view_frames`).
- **G6** — bring up the D455 + `depthimage_to_laserscan`; confirm stable `/scan`.
- **G7** — `slam_toolbox` + teleop the room; save a map.
- **G8** — `nav2_bringup` + 5 RViz goals + cancel + lifecycle restart.

Procedures: [`gates.md`](gates.md). Operator commands: [`runbook.md`](runbook.md).
