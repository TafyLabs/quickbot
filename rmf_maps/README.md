# RMF maps

Open-RMF building YAML + nav_graph YAML for the QuickBot test area.

Populate this directory in **P8** when wiring `quickbot_rmf_adapter`. Use the [traffic-editor](https://github.com/open-rmf/rmf_traffic_editor) workflow:

```bash
# Workstation
sudo apt install ros-${ROS_DISTRO}-rmf-traffic-editor
traffic-editor
```

Save the building file as `quickbot_lab.building.yaml` and the generated nav graph as `quickbot_lab.nav_graph.yaml`.

## Coordinate alignment

RMF and Nav2 do not share a coordinate frame by default. The fleet adapter is responsible for the transform — see [docs/architecture.md](../docs/architecture.md) and master plan §11.3. Document any offset/rotation in [docs/adr/](../docs/adr/) so the conversion is reproducible.

## MVP constraints

Per master plan §11.4:
- One robot: `quickbot_1`.
- One floor / one map.
- 4–8 waypoints; no doors / lifts / dispensers in the first acceptance task.
