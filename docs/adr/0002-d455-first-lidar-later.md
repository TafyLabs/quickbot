# ADR-0002: D455 first, salvaged LiDARs later

- Status: **Accepted**
- Date: 2026-05-12
- Driver: master plan §1, §3.2

## Context

The parts bin includes a Neato D7 LiDAR and Roborock LiDARs as candidate primary nav sensors. The robot also has an Intel RealSense D455 mounted for perception.

LiDARs ostensibly give cleaner 2D scans than depth→scan conversion, but the salvaged units have undocumented protocols and would require reverse-engineering before they emit useful data.

## Decision

Use the **D455** as the initial navigation sensor via `depthimage_to_laserscan`. The D455 has a supported ROS 2 wrapper, well-known driver behavior, and known limitations.

Treat salvaged LiDARs as a **post-baseline optimization**, not a first-milestone deliverable.

## Consequences

- We accept D455 limitations (glass, low obstacles, narrow FoV vs a true 360° LiDAR). The first map and the first Nav2 gates use a small, well-understood test area.
- The robot description includes a `camera_link` frame today and adds a `lidar_link` frame later when a LiDAR is integrated. Costmap `observation_sources` is parameterized so a LiDAR can be added without breaking existing tunes.
- We do not block Nav2 / RMF validation on LiDAR reverse-engineering work.

## Alternatives considered

- **Reverse-engineer Neato D7 first.** Rejected: introduces an open-ended driver development task before the rest of the stack is proven.
- **Buy a supported LiDAR (RPLIDAR / LD06).** Reasonable later — recorded as a follow-up after Gate G8 passes.
