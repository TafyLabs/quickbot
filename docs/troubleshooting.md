# Troubleshooting

A grab-bag of recurring failures and the first thing to check. Keep this short — deep dives belong in ADRs or runbook sections.

## DDS / ROS 2 networking

| Symptom | First check |
| --- | --- |
| `ros2 topic list` empty in one container | Same `ROS_DOMAIN_ID`? Same `RMW_IMPLEMENTATION`? `network_mode: host` on both? |
| Topics visible locally but not remote | Wi-Fi AP isolating clients? Firewall on workstation? `ros2 daemon stop && ros2 daemon start`. |
| Intermittent message drops | Mixed RMW between containers, multicast disabled, or wireless interference. Pin to one RMW per test run. |
| `ros2 doctor` complains about clock | Pi 5 NTP not synced. `timedatectl status` on the Pi. |

## Create 2 serial

| Symptom | First check |
| --- | --- |
| `/dev/ttyUSB0` missing | Cable seated; `dmesg \| tail` for USB-serial detection; some adapters expose `/dev/ttyACM0` instead. |
| Robot ignores Drive Direct | OI mode not Safe / Full. Send opcode 131 (Safe) after Start. |
| Robot stops after ~1 s on its own | Cliff sensors firing? Bump active? Battery low? Check `/diagnostics`. |
| Driver crashes on shutdown | Driver must send Drive Direct 0 + OI Stop on SIGINT before closing the port. |

## D455 / RealSense

| Symptom | First check |
| --- | --- |
| Camera not enumerated | USB3 cable quality; try a different port; `lsusb -t` should show SuperSpeed. |
| Depth blank patches near surfaces | D455 close-range limit (~0.5 m); also glass / shiny surfaces. Test in actual environment. |
| `realsense2_camera` deb missing for distro | Source build per [docs/runbook.md](runbook.md#realsense-source-build-fallback). |
| `/scan` orientation wrong | TF chain `base_link → camera_link → camera_depth_optical_frame` correct? RealSense optical frame is `rpy="-π/2 0 -π/2"` relative to physical mount. |

## Nav2

| Symptom | First check |
| --- | --- |
| Lifecycle won't activate | `ros2 lifecycle list /lifecycle_manager_navigation`; logs of the failing node; missing param? missing TF? |
| Robot oscillates on goal | Controller frequency too low, costmap inflation too tight, or `min_*_velocity_threshold` masking small commands. |
| Costmap rejects most space | `robot_radius` too large, or `/scan` frame mismatched with `global_frame`. |
| Map drift | AMCL not localizing — bad initial pose, or `/scan` rate too low. |

## Open-RMF

| Symptom | First check |
| --- | --- |
| Demo image won't pull | Tag may be retired. Use a digest from the pinned digest in [docs/runbook.md](runbook.md#rmf-demo-gate-g9). |
| Adapter sees no robot | `position()` returning RMF-frame coords? `nav_graph` name match? Robot publishing `/battery_state`? |
| Robot moves but never reports done | Nav2 action status not mapped to RMF state. Check adapter feedback wiring. |

## Docker

| Symptom | First check |
| --- | --- |
| `docker build` slow on Mac | Allocate 6+ GB RAM in Docker Desktop; turn off Rosetta emulation; ensure native arm64 build. |
| Container can't see USB device | Compose `devices:` mounted? `privileged: true`? udev rules on host? |
| Volume mount empty inside container | Path case sensitivity (macOS APFS is case-insensitive by default; some containers care). |
