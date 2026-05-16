# QuickBot

> ROS 2 + Nav2 + Open-RMF on iRobot Create 2 + Raspberry Pi 5 + Intel RealSense D455.

QuickBot is the fastest reliable path to a real, TurtleBot-style robot using off-the-shelf parts. The plan is opinionated: validate every layer of the stack on **ROS 2 Kilted Kaiju / Ubuntu 24.04** first, then migrate to **ROS 2 Lyrical Luth / Ubuntu 26.04** once Kilted gates pass.

The full design is in [`docs/master-plan.md`](docs/master-plan.md). This README is the short version.

## Status

| Phase | Gate | State |
| ----- | ---- | ----- |
| 0 — Host prep + repo | G0 build, G1 DDS | **done** (on M2 Air, arm64) |
| 1 — ROS container smoke | G1 | **done** |
| 2 — Create 2 raw serial | G2, G3 | hardware ready, awaiting Pi bench-up |
| 3 — Create 2 ROS driver | G4 | **code complete**, awaiting hardware test |
| 4 — D455 + scan | G5, G6 | not started |
| 5 — SLAM + map | G7 | not started |
| 6 — Nav2 real robot | G8 | not started |
| 7 — Open-RMF demo | G9 | not started |
| 8 — RMF -> Nav2 adapter | G10 | not started |
| 9 — Lyrical migration | G11 | not started |

Detailed pass/fail evidence: [`validation/gates.md`](validation/gates.md).

## Quickstart

**[→ Full quickstart: zero to a driving robot in ~30 min (`docs/quickstart.md`)](docs/quickstart.md)** — covers Pi prep, wiring, G2–G4, the second-shell pattern, and the two Kilted gotchas that bit during first bring-up.

TL;DR for someone who already has the kilted-base image built and a wired robot:

```bash
git clone git@github.com:TafyLabs/quickbot.git ~/quickbot && cd ~/quickbot
docker compose build robot
./tools/g2_devices.sh                            # G2: device passthrough
docker compose run --rm robot bash -lc \
  'cd /ws/src/create2_driver && python3 -m create2_driver.smoke --port /dev/ttyUSB0'   # G3
docker compose run --rm robot bash -lc \
  'source /opt/ros/$ROS_DISTRO/setup.bash && cd /ws && colcon build --symlink-install && \
   source install/setup.bash && ros2 launch quickbot_bringup robot.launch.py'           # G4 (driver)
```

Then from a second SSH session, open another container shell and `ros2 run teleop_twist_keyboard teleop_twist_keyboard` to actually drive it.

## Repository layout

```
quickbot/
├── docker/        Dockerfiles: kilted-base, robot, rmf-kilted (+ lyrical-base later)
├── compose.yaml   Three services: robot, dev, rmf — all host networking
├── config/        Cyclone DDS config, Nav2 params, Create 2 calibration
├── maps/          SLAM-produced occupancy maps (.yaml + .pgm)
├── rmf_maps/      Open-RMF building + nav_graph YAML
├── ws/src/        ROS 2 packages:
│   ├── quickbot_description/   URDF/Xacro + static transforms
│   ├── create2_driver/         Serial driver: /cmd_vel -> wheels, /odom + /tf out
│   ├── quickbot_bringup/       Launch files for robot / sensors / Nav2
│   ├── quickbot_nav/           Nav2 params, maps, SLAM/localization configs
│   ├── quickbot_rmf_adapter/   full_control RMF fleet adapter -> Nav2
│   └── quickbot_tools/         Validation + operator helpers
├── validation/    gates.md (pass/fail), bags/, logs/, screenshots/
└── docs/          Architecture, gates, runbook, calibration, ADRs
```

## Documentation

- [`docs/quickstart.md`](docs/quickstart.md) — zero to a driving robot, with the gotchas
- [`docs/master-plan.md`](docs/master-plan.md) — full design document (the source of truth)
- [`docs/architecture.md`](docs/architecture.md) — software + hardware topology, topic/frame contract
- [`docs/runbook.md`](docs/runbook.md) — operator commands: startup, mapping, navigation, shutdown
- [`docs/gates.md`](docs/gates.md) — validation gates G0–G11 with procedures and evidence
- [`docs/hardware-bringup.md`](docs/hardware-bringup.md) — wiring + Pi OS setup + pre-G2 sanity
- [`docs/calibration.md`](docs/calibration.md) — Create 2 odometry calibration procedure
- [`docs/troubleshooting.md`](docs/troubleshooting.md) — first-thing-to-check tables
- [`docs/adr/`](docs/adr/) — architecture decision records

## Safety rules

- **Do not power the Pi 5 from the Create 2 Vpwr serial pins.** The OI spec limits those pins to ~200 mA continuous. Use a USB-C PD bank or a properly rated buck converter.
- **Conservative velocity limits during bring-up:** `max_linear_mps ≤ 0.22`, `max_angular_rps ≤ 0.8`.
- **Driver must stop on `/cmd_vel` timeout** (default 0.5 s) and on shutdown.
- **Test area:** clear floor, no people/pets in the active arc, physical access to the Create 2 power button at all times.

## License

MIT.
