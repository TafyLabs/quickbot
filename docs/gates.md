# Validation gates

Each gate has a procedure, pass condition, and evidence requirement. Sign-off goes in [`../validation/gates.md`](../validation/gates.md). Logs / bags / screenshots land under `../validation/{logs,bags,screenshots}/`.

| ID | Area | Procedure | Pass condition | Evidence |
| --- | --- | --- | --- | --- |
| **G0** | Build | `docker build -f docker/kilted-base.Dockerfile -t quickbot:kilted-base .` | Build completes; image has `ros2` CLI. | Build log + `docker images` line. |
| **G1** | DDS | talker/listener in two containers on host networking | Messages flow both directions; `ros2 topic list` shows the topic on both sides. | Terminal log. |
| **G2** | Device passthrough | `ls /dev/ttyUSB0` and `rs-enumerate-devices` inside `robot` container | Create serial + D455 visible. | Log / screenshot. |
| **G3** | Create raw drive | `python3 -m create2_driver.smoke --port /dev/ttyUSB0 --duration 1.0 --speed 100` | Robot moves ~1 s and stops. | Video + log. |
| **G4** | Teleop ROS | `teleop_twist_keyboard` → `/cmd_vel` | Robot responds; timeout stops when teleop closes. | `ros2 topic hz` + video. |
| **G5** | TF | `ros2 run tf2_tools view_frames`; RViz fixed-frame checks | No missing required transforms; tree is connected. | `frames_*.pdf`. |
| **G6** | Scan | `ros2 topic hz /scan`; RViz LaserScan display | Stable rate; obstacles align with real geometry. | RViz screenshot. |
| **G7** | SLAM | `slam_toolbox online_async` + teleop + `map_saver_cli` | Map saved + reloads + matches room geometry. | `maps/quickbot_lab.{yaml,pgm}`. |
| **G8** | Nav2 | Send 5 `NavigateToPose` goals from RViz | All 5 reach goal; 1 cancel works; lifecycle restart recovers. | Nav2 logs + bag. |
| **G9** | RMF demo | `rmf_demos` office demo headless | RMF nodes launch; no fatal errors; a CLI task flows. | RMF logs. |
| **G10** | RMF adapter | Dispatch task to real robot through adapter | Robot reaches waypoint, reports completion, cancel works. | RMF + Nav2 logs. |
| **G11** | Lyrical upgrade | Repeat G0–G10 on Ubuntu 26.04 / ROS Lyrical | All gates pass or deviations explicitly accepted. | Upgrade report. |

## Standard evidence capture

```bash
mkdir -p validation/logs validation/bags validation/screenshots
ros2 topic list  | tee validation/logs/topic_list.txt
ros2 node list   | tee validation/logs/node_list.txt
ros2 run tf2_tools view_frames
ros2 bag record -o validation/bags/nav2_gate \
  /tf /tf_static /odom /scan /cmd_vel /amcl_pose /goal_pose /battery_state
```

## Gate dependencies

```
G0 -> G1 -> G2 -> G3 -> G4 -> G5 -> G6 -> G7 -> G8 -> G9 -> G10 -> G11
                         \_____ G5 also unblocks G8 (TF must be clean for AMCL)
```

Do not skip gates. If a gate must be deferred, record the reason and the unblock plan in [`../validation/gates.md`](../validation/gates.md).
