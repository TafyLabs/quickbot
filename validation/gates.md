# Gate sign-off log

Append rows as gates pass. Failed attempts get an entry too — keep the failure visible so the root cause is recorded.

Procedures live in [`../docs/gates.md`](../docs/gates.md). Evidence files live under `bags/`, `logs/`, `screenshots/`.

| Gate | Attempt | Date | Result | Operator | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| G0 | 1 | 2026-05-12 | **PASS** | bobby | `logs/g0_build.log`, `logs/g0_verify.log` | kilted-base built on M2 Air (arm64). 967 MB content, 4.7 GB on disk. `ros2 doctor` clean. |
| G1 | 1 | 2026-05-12 | **PASS** | bobby | `logs/g1_dds.log` | Two host-networked containers, `ROS_DOMAIN_ID=9`, Cyclone DDS. Sub received pub via `ros2 topic pub/echo` on `/chatter`. |
| G2 | 1 | — | pending | — | — | Device passthrough into robot container. |
| G3 | 1 | — | pending | — | — | Raw serial drive. |
| G4 | 1 | — | pending | — | — | Teleop via ROS. |
| G5 | 1 | — | pending | — | — | TF tree complete. |
| G6 | 1 | — | pending | — | — | /scan stable. |
| G7 | 1 | — | pending | — | — | Map saved + reloads. |
| G8 | 1 | — | pending | — | — | 5 Nav2 goals + cancel + lifecycle restart. |
| G9 | 1 | — | pending | — | — | RMF demo headless. |
| G10 | 1 | — | pending | — | — | RMF task → real robot. |
| G11 | 1 | — | pending | — | — | Re-run G0–G10 on Lyrical. |
