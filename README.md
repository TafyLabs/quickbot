# QuickBot

> ROS 2 + Nav2 + Open-RMF on iRobot Create 2 + Raspberry Pi 5 + Intel RealSense D455.

QuickBot is the fastest reliable path to a real, TurtleBot-style robot using off-the-shelf parts. The plan is opinionated: validate every layer of the stack on **ROS 2 Kilted Kaiju / Ubuntu 24.04** first, then migrate to **ROS 2 Lyrical Luth / Ubuntu 26.04** once Kilted gates pass.

The full design is in [`docs/master-plan.md`](docs/master-plan.md). This README is the short version.

## Status

| Phase | Gate | State |
| ----- | ---- | ----- |
| 0 — Host prep + repo | G0 build, G1 DDS | in progress |
| 1 — ROS container smoke | G1 | not started |
| 2 — Create 2 raw serial | G2, G3 | not started |
| 3 — Create 2 ROS driver | G4 | not started |
| 4 — D455 + scan | G5, G6 | not started |
| 5 — SLAM + map | G7 | not started |
| 6 — Nav2 real robot | G8 | not started |
| 7 — Open-RMF demo | G9 | not started |
| 8 — RMF -> Nav2 adapter | G10 | not started |
| 9 — Lyrical migration | G11 | not started |

Detailed pass/fail evidence: [`validation/gates.md`](validation/gates.md).

## Quickstart

> **You need:** Docker Desktop (Mac dev) or Docker Engine (Pi 5 robot), `ros-kilted` apt source (handled in the Dockerfile), and a Create 2 + D455 once you reach Phase 2.

```bash
# 1. Build the Kilted base image (multi-GB; do on a Linux host or beefy machine).
docker build -f docker/kilted-base.Dockerfile -t quickbot:kilted-base .

# 2. Build robot + workstation images.
docker compose build

# 3. Workstation shell.
docker compose run --rm dev bash
#   inside the container:
source /opt/ros/$ROS_DISTRO/setup.bash
ros2 doctor

# 4. Robot shell (on the Pi 5, with Create 2 + D455 plugged in).
docker compose run --rm robot bash
```

Gate G0 passes when the base image builds and `ros2 doctor` runs cleanly.
Gate G1 passes when `ros2 topic pub` from `dev` is received by a `ros2 topic echo` in `robot` (or in a second `dev` container) over host networking.

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

- [`docs/master-plan.md`](docs/master-plan.md) — full design document (the source of truth)
- [`docs/architecture.md`](docs/architecture.md) — software + hardware topology, topic/frame contract
- [`docs/runbook.md`](docs/runbook.md) — operator commands: startup, mapping, navigation, shutdown
- [`docs/gates.md`](docs/gates.md) — validation gates G0–G11 with procedures and evidence
- [`docs/calibration.md`](docs/calibration.md) — Create 2 odometry calibration procedure
- [`docs/adr/`](docs/adr/) — architecture decision records

## Safety rules

- **Do not power the Pi 5 from the Create 2 Vpwr serial pins.** The OI spec limits those pins to ~200 mA continuous. Use a USB-C PD bank or a properly rated buck converter.
- **Conservative velocity limits during bring-up:** `max_linear_mps ≤ 0.22`, `max_angular_rps ≤ 0.8`.
- **Driver must stop on `/cmd_vel` timeout** (default 0.5 s) and on shutdown.
- **Test area:** clear floor, no people/pets in the active arc, physical access to the Create 2 power button at all times.

## License

Apache-2.0.
