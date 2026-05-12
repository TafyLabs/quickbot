# ADR-0003: Host networking + Cyclone DDS for bring-up

- Status: **Accepted**
- Date: 2026-05-12
- Driver: master plan §6.1

## Context

Containerized ROS 2 has two recurring discovery pitfalls:

1. Bridge networking + DDS often requires careful port mapping and multicast tuning.
2. Mixed RMW implementations or mismatched `ROS_DOMAIN_ID`s silently drop messages.

QuickBot needs reliable cross-container topic flow during early bring-up, when the team's attention should be on the robot — not on DDS port lists.

## Decision

For the baseline:

- All ROS containers use **`network_mode: host`**.
- All containers use **`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`**.
- All containers use **`ROS_DOMAIN_ID=9`** (overridable only if 9 conflicts with another team on the local network).
- One RMW implementation per test run. Mixed-RMW interop tests are separate experiments, not part of the validation matrix.

## Consequences

- Bring-up is simple: launch + observe. Most DDS discovery failures become "you forgot to set the env var" rather than "we need to debug the multicast group."
- Container isolation is weaker. This is acceptable for a lab robot. Production deployments revisit this decision.
- Fast DDS / Zenoh comparisons are explicitly out of scope for the first baseline. They are recorded as follow-up experiments after Gate G10 passes.

## Alternatives considered

- **Bridge networking with port maps.** Rejected for the baseline; revisit only if host networking becomes the limiting factor.
- **Fast DDS default.** Cyclone is the recommended default in much of the ROS 2 ecosystem for the kind of single-domain robot we're building; we keep Fast DDS as a future comparison.
