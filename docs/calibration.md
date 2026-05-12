# Create 2 calibration

The Create 2 ships with reasonable nominal values, but in-place rotation and straight-line drive both drift unless calibrated. Calibrate **once per chassis** and commit the result to [`../config/create2_calibration.yaml`](../config/create2_calibration.yaml).

## 1. Track width (angular scale)

Goal: command an in-place rotation, compare commanded yaw to observed yaw.

```bash
# Place a piece of tape on the floor under the robot center.
# Command an in-place rotation of 2π rad at 0.5 rad/s for ~12.6 s.
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/Twist \
  '{angular: {z: 0.5}}'
```

Stop when the robot has rotated one full turn (eyeball or use a tape marker). Read the yaw change from `/odom`:

```bash
ros2 topic echo /odom --once | grep -A4 orientation
```

If `/odom` reports more rotation than physical, **decrease** `odom_angular_scale`. If less, increase. Aim for ±1° over one full rotation.

## 2. Straight-line scale

Goal: command 1.0 m forward, compare to tape measurement.

```bash
# 1.0 m / 0.20 m/s = 5.0 s
timeout 5 ros2 topic pub --rate 10 /cmd_vel geometry_msgs/Twist \
  '{linear: {x: 0.20}}'
```

Measure with a tape. If `/odom` reports more than measured, **decrease** `odom_linear_scale`; if less, increase. Aim for ±1 cm over 1 m.

## 3. Safe envelope

Once odometry is clean, fix the operator envelope:

| Parameter | Suggested start |
| --- | --- |
| `max_linear_mps` | `0.18 – 0.22` |
| `max_angular_rps` | `0.6 – 0.8` |
| `cmd_timeout_s` | `0.5` |

Raise only after Gate G8 passes repeatably.

## 4. Commit and tag

```bash
git add config/create2_calibration.yaml
git commit -m "calibration: track width and odom scale on chassis-01"
git tag chassis-01-calibrated
```
